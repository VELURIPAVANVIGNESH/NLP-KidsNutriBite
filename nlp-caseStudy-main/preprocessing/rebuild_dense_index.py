import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import json
import time
import sys
import numpy as np
import faiss
import torch
from transformers import AutoTokenizer, AutoModel

sys.stdout.reconfigure(encoding='utf-8')

corpus_path = "data/processed/preprocessed_corpus.json"
dense_index_path = "data/processed/dense_index.faiss"
dense_map_path = "data/processed/dense_index_map.json"
model_name = "BAAI/bge-small-en-v1.5"
EXPECTED_COUNT = 6422

print(f"Loading corpus from {corpus_path}...")
with open(corpus_path, "r", encoding="utf-8") as f:
    corpus = json.load(f)

print(f"Corpus loaded: {len(corpus)} chunks.")
if len(corpus) != EXPECTED_COUNT:
    print(f"Error: Expected {EXPECTED_COUNT} chunks, got {len(corpus)}")
    sys.exit(1)

texts = [chunk.get("search_text", chunk.get("text", "")) for chunk in corpus]
doc_ids = [chunk["chunk_id"] for chunk in corpus]

print(f"Loading AutoTokenizer & AutoModel ({model_name})...")
tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=True)
model = AutoModel.from_pretrained(model_name, local_files_only=True)
model.eval()

def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

batch_size = 128
total_chunks = len(texts)
all_embeddings = []

print(f"Starting pure PyTorch encoding for {total_chunks} chunks in batches of {batch_size}...")
t0 = time.time()

with torch.no_grad():
    for i in range(0, total_chunks, batch_size):
        batch_texts = texts[i:i + batch_size]
        encoded_inputs = tokenizer(
            batch_texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )
        model_output = model(**encoded_inputs)
        sentence_embeddings = mean_pooling(model_output, encoded_inputs['attention_mask'])
        sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)
        all_embeddings.append(sentence_embeddings.cpu().numpy())
        
        processed = min(i + batch_size, total_chunks)
        print(f"Progress: {processed}/{total_chunks} encoded ({time.time() - t0:.1f}s)...")
        sys.stdout.flush()

embeddings = np.vstack(all_embeddings)
print(f"Encoding complete! Shape: {embeddings.shape}. Total time: {time.time() - t0:.1f}s")

has_nan_or_inf = np.isnan(embeddings).any() or np.isinf(embeddings).any()
print(f"NaN/Inf check: {'FAIL' if has_nan_or_inf else 'PASS'}")

embedding_dim = embeddings.shape[1]
print(f"Creating FAISS IndexFlatIP index (dim={embedding_dim})...")
index = faiss.IndexFlatIP(embedding_dim)
index.add(embeddings.astype("float32"))

print(f"Writing FAISS index to {dense_index_path}...")
faiss.write_index(index, dense_index_path)

dense_map = {str(idx): cid for idx, cid in enumerate(doc_ids)}
print(f"Writing dense index map to {dense_map_path}...")
with open(dense_map_path, "w", encoding="utf-8") as f:
    json.dump(dense_map, f, indent=2, ensure_ascii=False)

print(f"FAISS rebuild SUCCESSFUL! Total vectors: {index.ntotal}, Map entries: {len(dense_map)}")

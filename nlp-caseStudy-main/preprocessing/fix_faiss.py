"""
fix_faiss.py — Rebuild FAISS dense index with exactly 6422 vectors.
Run in your own terminal: python preprocessing/fix_faiss.py
"""
import os, sys, json, time, warnings
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding='utf-8')

CORPUS_PATH = "data/processed/preprocessed_corpus.json"
FAISS_PATH  = "data/processed/dense_index.faiss"
MAP_PATH    = "data/processed/dense_index_map.json"
MODEL_NAME  = "BAAI/bge-small-en-v1.5"
EXPECTED    = 6422

print(f"[1/5] Loading corpus from {CORPUS_PATH}...")
with open(CORPUS_PATH, encoding="utf-8") as f:
    corpus = json.load(f)
print(f"      Loaded {len(corpus)} chunks.")
assert len(corpus) == EXPECTED

texts    = [c.get("search_text", c.get("text", "")) for c in corpus]
doc_ids  = [c["chunk_id"] for c in corpus]

print(f"[2/5] Loading SentenceTransformer: {MODEL_NAME}")
from sentence_transformers import SentenceTransformer
import numpy as np, faiss, torch

model = SentenceTransformer(MODEL_NAME, device="cpu")
dim   = model.get_sentence_embedding_dimension()
print(f"      Dimension: {dim}")

# Encode in small batches, printing progress manually
BATCH = 64
all_embeddings = []
n_batches = (EXPECTED + BATCH - 1) // BATCH

print(f"[3/5] Encoding {EXPECTED} texts in {n_batches} batches...")
t0 = time.time()
with torch.no_grad():
    for i in range(n_batches):
        batch = texts[i*BATCH:(i+1)*BATCH]
        emb = model.encode(batch, batch_size=BATCH, show_progress_bar=False,
                           normalize_embeddings=True, convert_to_numpy=True)
        all_embeddings.append(emb)
        if (i+1) % 10 == 0 or (i+1) == n_batches:
            done = min((i+1)*BATCH, EXPECTED)
            elapsed = time.time() - t0
            print(f"      [{done}/{EXPECTED}] {elapsed:.0f}s elapsed")
            sys.stdout.flush()

embeddings = np.vstack(all_embeddings)
print(f"      Encoded shape: {embeddings.shape}  time: {time.time()-t0:.1f}s")

print("[4/5] Building FAISS IndexFlatIP and writing files...")
index = faiss.IndexFlatIP(dim)
index.add(embeddings.astype("float32"))
faiss.write_index(index, FAISS_PATH)
print(f"      FAISS written: ntotal={index.ntotal}")

dense_map = {str(i): doc_ids[i] for i in range(EXPECTED)}
with open(MAP_PATH, "w", encoding="utf-8") as f:
    json.dump(dense_map, f, ensure_ascii=False, indent=2)
print(f"      Dense map written: {len(dense_map)} entries")

print("[5/5] Verification...")
idx2 = faiss.read_index(FAISS_PATH)
with open(MAP_PATH, encoding="utf-8") as f:
    m2 = json.load(f)
print(f"      FAISS ntotal={idx2.ntotal}, dim={idx2.d}, type={type(idx2).__name__}")
print(f"      Dense map count={len(m2)}")
assert idx2.ntotal == EXPECTED, f"FAISS ntotal {idx2.ntotal} != {EXPECTED}"
assert len(m2) == EXPECTED

print(f"\n[+] FAISS dense index rebuilt successfully with {EXPECTED} vectors!")

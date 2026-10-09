import os
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from preprocessing.rerank import evaluate_rerankers

print("Running evaluate_rerankers()...")
summary = evaluate_rerankers()

csv_path = os.path.join(BASE_DIR, "data", "processed", "reranking_evaluation.csv")
md_path = os.path.join(BASE_DIR, "data", "processed", "reranking_summary.md")

print("CSV Exists?", os.path.exists(csv_path), csv_path)
print("MD Exists?", os.path.exists(md_path), md_path)

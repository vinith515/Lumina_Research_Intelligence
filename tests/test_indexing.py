"""Unit tests for Vector and BM25 indexing."""

import shutil
from pathlib import Path
import numpy as np
from researchmind.indexing.vector_index import VectorIndexManager
from researchmind.indexing.bm25_index import BM25IndexManager, scientific_tokenize


def test_scientific_tokenize():
    text = "Evaluating ResNet-50 on zero-shot anomaly detection with F1-score of 94.5%."
    tokens = scientific_tokenize(text)
    assert "resnet-50" in tokens
    assert "zero-shot" in tokens
    assert "f1-score" in tokens
    assert "anomaly" in tokens


def test_bm25_index_lifecycle(sample_chunks, tmp_path):
    bm25_mgr = BM25IndexManager(index_dir=tmp_path / "bm25")
    bm25_mgr.build_index(sample_chunks)
    assert bm25_mgr.count() == 2

    # Query for exact keyword
    results = bm25_mgr.query("on-policy distillation", top_k=2)
    assert len(results) >= 1
    assert results[0].chunk_id == "test_paper_001_chk_001"
    assert results[0].bm25_score > 0

    # Reload from disk
    bm25_mgr_reloaded = BM25IndexManager(index_dir=tmp_path / "bm25")
    assert bm25_mgr_reloaded.count() == 2
    results2 = bm25_mgr_reloaded.query("anomaly detection", top_k=2)
    assert len(results2) >= 1
    assert results2[0].chunk_id == "test_paper_001_chk_000"


def test_vector_index_lifecycle(sample_chunks, tmp_path):
    v_mgr = VectorIndexManager(persist_dir=tmp_path / "chroma", collection_name="test_col")
    fake_embs = np.array([
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
    ], dtype=np.float32)

    v_mgr.add_chunks(sample_chunks, fake_embs)
    assert v_mgr.count() == 2

    # Query with vector closest to chunk 0
    query_vec = np.array([0.9, 0.1, 0.0, 0.0], dtype=np.float32)
    cands = v_mgr.query(query_vec, top_k=2)
    assert len(cands) == 2
    assert cands[0].chunk_id == "test_paper_001_chk_000"
    assert cands[0].dense_score > 0.8

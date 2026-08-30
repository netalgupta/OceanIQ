"""
Unit tests for text embedder and vector representation.
"""
from __future__ import annotations
import pytest
from src.llm.embedder import embed_texts, _hash_vector

def test_hash_vector_dimensions():
    v1 = _hash_vector("Arabian Sea temperature profile", dim=768)
    assert len(v1) == 768
    assert isinstance(v1[0], float)

def test_hash_vector_determinism():
    text = "Surface salinity in Bay of Bengal"
    v1 = _hash_vector(text, dim=768)
    v2 = _hash_vector(text, dim=768)
    assert v1 == v2

def test_embed_texts_batch():
    texts = [
        "Float 1902303 recorded high sea surface temperature.",
        "Oxygen minimum zone expansion detected off the Malabar coast."
    ]
    vectors = embed_texts(texts)
    assert len(vectors) == 2
    assert len(vectors[0]) == 768
    assert len(vectors[1]) == 768

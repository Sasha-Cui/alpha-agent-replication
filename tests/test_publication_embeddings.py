import copy
import numpy as np
import pytest
from alpha_evolve.publication_embeddings import BatchEmbeddingCache


class Characters:
    def encode(self, text):
        return list(text)

    def decode(self, tokens):
        return "".join(tokens)


class Meter:
    def __init__(self):
        self.calls = []

    def embeddings(self, texts):
        self.calls.append(texts)
        vectors = {"ab": [1.0, 0.0, 0.0], "cd": [0.0, 1.0, 0.0], "e": [0.0, 0.0, 1.0]}
        rows = [{"index": i, "embedding": vectors[t]} for i, t in enumerate(texts)]
        return {"data": list(reversed(rows))}, "request_" + str(len(self.calls))


def test_batch_deduplicates_real_queries_and_preserves_chunk_weighting():
    meter = Meter()
    cache = BatchEmbeddingCache(meter, tokenizer=Characters(), dimensions=3, chunk_tokens=2, batch_tokens=10)
    cache.prefetch(["abcde", "ab", "abcde"])
    assert len(meter.calls) == 1
    assert np.allclose(cache.embed("abcde"), np.array([2, 2, 1]) / 3)
    assert cache.embed("ab") == [1.0, 0.0, 0.0]
    assert len(meter.calls) == 1
    clone = copy.deepcopy(cache)
    assert clone.meter is meter and clone.embed("abcde") == cache.embed("abcde")


def test_batch_missing_vector_fails_instead_of_inventing_embedding():
    meter = Meter()
    meter.embeddings = lambda _: ({"data": []}, "bad")
    cache = BatchEmbeddingCache(meter, tokenizer=Characters(), dimensions=3)
    with pytest.raises(ValueError, match="cardinality"):
        cache.embed("ab")


def test_concurrent_prefetch_keeps_individual_function_calls_and_input_order():
    import time
    from alpha_evolve.publication_embeddings import ConcurrentEmbeddingCache

    calls = []

    def native(text):
        calls.append(text)
        if text == "a":
            time.sleep(0.01)
        return [1.0, 0.0] if text == "a" else [0.0, 1.0]

    cache = ConcurrentEmbeddingCache(native, dimensions=2, workers=2)
    cache.prefetch(["a", "b", "a"])
    assert sorted(calls) == ["a", "b"]
    assert cache.embed("a") == [1.0, 0.0] and cache.embed("b") == [0.0, 1.0]
    assert len(calls) == 2

"""Batch independent real embedding inputs without changing their mathematical use."""

from __future__ import annotations
import json
import numpy as np


class BatchEmbeddingCache:
    def __init__(self, meter, tokenizer=None, dimensions=1536, chunk_tokens=8191, batch_tokens=24000):
        if tokenizer is None:
            import tiktoken

            tokenizer = tiktoken.get_encoding("cl100k_base")
        self.meter = meter
        self.tokenizer = tokenizer
        self.dimensions = dimensions
        self.chunk_tokens = chunk_tokens
        self.batch_tokens = batch_tokens
        self.cache = {}
        self.lineage = {}

    @staticmethod
    def text(value):
        return value if isinstance(value, str) else json.dumps(value, sort_keys=True)

    def prefetch(self, texts):
        unknown = list(dict.fromkeys(self.text(t) for t in texts if self.text(t) not in self.cache))
        pieces = []
        parts = {t: [] for t in unknown}
        parents = {t: [] for t in unknown}
        for text in unknown:
            tokens = self.tokenizer.encode(text)
            for start in range(0, max(1, len(tokens)), self.chunk_tokens):
                chunk = tokens[start : start + self.chunk_tokens]
                pieces.append((text, self.tokenizer.decode(chunk), max(1, len(chunk))))
        batch = []
        size = 0

        def submit(batch):
            if not batch:
                return
            response, key = self.meter.embeddings([item[1] for item in batch])
            rows = sorted(response["data"], key=lambda row: row["index"])
            if [row["index"] for row in rows] != list(range(len(batch))):
                raise ValueError("Embedding batch cardinality/order mismatch")
            for (text, _, weight), row in zip(batch, rows):
                vector = np.asarray(row["embedding"], float)
                if vector.shape != (self.dimensions,) or not np.isfinite(vector).all():
                    raise ValueError("Invalid real embedding vector")
                parts[text].append((vector, weight))
                parents[text].append(key)

        for item in pieces:
            if batch and size + item[2] > self.batch_tokens:
                submit(batch)
                batch = []
                size = 0
            batch.append(item)
            size += item[2]
        submit(batch)
        for text in unknown:
            vector = np.average(np.stack([v for v, w in parts[text]]), axis=0, weights=[w for v, w in parts[text]])
            norm = np.linalg.norm(vector)
            if norm <= 0:
                raise ValueError("Zero embedding cannot enter the memory")
            self.cache[text] = tuple((vector / norm).tolist())
            self.lineage[text] = tuple(dict.fromkeys(parents[text]))

    def embed(self, text):
        text = self.text(text)
        self.prefetch([text])
        return list(self.cache[text])

    def __deepcopy__(self, memo):
        # Keep metering/trace ownership shared; cached vectors are immutable tuples.
        result = type(self).__new__(type(self))
        result.__dict__ = dict(self.__dict__)
        result.cache = dict(self.cache)
        result.lineage = dict(self.lineage)
        return result


class ConcurrentEmbeddingCache:
    """Prefetch independent calls to an unchanged per-document embedding function."""

    def __init__(self, embed_function, dimensions, workers=4):
        self.embed_function = embed_function
        self.dimensions = dimensions
        self.workers = workers
        self.cache = {}

    @staticmethod
    def text(value):
        return value if isinstance(value, str) else json.dumps(value, sort_keys=True)

    def prefetch(self, texts):
        from concurrent.futures import ThreadPoolExecutor

        unknown = list(dict.fromkeys(self.text(t) for t in texts if self.text(t) not in self.cache))
        if not unknown:
            return

        def run(text):
            vector = np.asarray(self.embed_function(text), float)
            if (
                vector.shape != (self.dimensions,)
                or not np.isfinite(vector).all()
                or abs(np.linalg.norm(vector) - 1) > 1e-6
            ):
                raise ValueError("Native embedding is invalid")
            return tuple(vector.tolist())

        # Executor waits for all in-flight calls even if one raises. No paid call
        # is abandoned merely because another independent document failed.
        with ThreadPoolExecutor(max_workers=min(self.workers, len(unknown))) as pool:
            results = list(pool.map(run, unknown))
        for text, vector in zip(unknown, results):
            self.cache[text] = vector

    def embed(self, text):
        text = self.text(text)
        self.prefetch([text])
        return list(self.cache[text])

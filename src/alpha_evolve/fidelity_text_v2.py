"""Lossless bounded text chunks for a provider with conservative context estimates."""
from __future__ import annotations


def context_safe_chunks(text, encoder, token_limit=6000, byte_limit=12000):
    """Retain legacy chunks when safe; split oversized chunks without dropping text.

    Token counts alone proved insufficient for OpenRouter's preflight estimator
    on a whitespace-heavy filing. The UTF-8 bound leaves room for instructions,
    role envelopes and completion tokens even under one-token-per-byte counting.
    """
    if token_limit < 1 or byte_limit < 4:
        raise ValueError('Invalid context limits')
    if not text:
        return []
    tokens = encoder.encode(text)
    candidates = [encoder.decode(tokens[i:i+token_limit]) for i in range(0,len(tokens),token_limit)]
    # A token boundary can split one Unicode character. Never retain replacement
    # characters from decoding such a slice; repartition the original text.
    if ''.join(candidates) != text:
        candidates = [text]
    def split(chunk):
        if len(chunk.encode('utf-8')) <= byte_limit and len(encoder.encode(chunk)) <= token_limit:
            return [chunk]
        if len(chunk) == 1:
            raise ValueError('One character exceeds the configured token bound')
        midpoint = len(chunk)//2
        return split(chunk[:midpoint])+split(chunk[midpoint:])
    result = [part for candidate in candidates for part in split(candidate)]
    if ''.join(result) != text:
        raise ValueError('Chunking lost source text')
    return result

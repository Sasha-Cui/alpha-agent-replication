import pytest
from alpha_evolve.fidelity_text_v2 import context_safe_chunks


class ByteEncoder:
    def encode(self,text):
        return list(text.encode('utf-8'))
    def decode(self,tokens):
        return bytes(tokens).decode('utf-8',errors='replace')


def test_utf8_boundary_never_loses_characters():
    text = ('😀本é\n'*20)+'tail'
    chunks = context_safe_chunks(text,ByteEncoder(),token_limit=17,byte_limit=20)
    assert ''.join(chunks) == text
    assert all(len(x.encode('utf-8')) <= 17 for x in chunks)
    assert '\ufffd' not in ''.join(chunks)


def test_provider_byte_bound_applies_independently_of_token_count():
    class CompressedEncoder:
        def encode(self,text):
            return [text]
        def decode(self,tokens):
            return ''.join(tokens)
    text = ' '*60000+'last sentence'
    chunks = context_safe_chunks(text,CompressedEncoder())
    assert ''.join(chunks) == text
    assert len(chunks) > 1
    assert all(len(x.encode()) <= 12000 for x in chunks)


def test_safe_chunks_and_empty_input_preserved():
    assert context_safe_chunks('short',ByteEncoder()) == ['short']
    assert context_safe_chunks('',ByteEncoder()) == []
    with pytest.raises(ValueError):
        context_safe_chunks('x',ByteEncoder(),byte_limit=0)

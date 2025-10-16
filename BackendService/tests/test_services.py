from src.services.embedding_provider import EmbeddingProvider

def test_embedding_stub_has_length():
    ep = EmbeddingProvider()
    vec = ep.embed("Hello")
    assert isinstance(vec, list)
    assert len(vec) == 128

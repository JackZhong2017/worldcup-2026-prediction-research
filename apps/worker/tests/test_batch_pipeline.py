from pathlib import Path

from sprp_worker import batch_pipeline


def test_discovery_paginates(monkeypatch) -> None:
    class Response:
        def __init__(self, payload): self.payload = payload
        def __enter__(self): return self
        def __exit__(self, *_): return None
    pages = [[{"id": str(i)} for i in range(100)], [{"id": "last"}]]
    def fake_open(*_args, **_kwargs):
        response = Response(pages.pop(0))
        response.read = lambda: __import__("json").dumps(response.payload).encode()
        return response
    monkeypatch.setattr(batch_pipeline, "urlopen", fake_open)
    assert len(batch_pipeline._discover("1")) == 101

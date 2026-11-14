"""The picture door answers 429/503 when pressed: wait and retry, but only a bounded number of times."""

import io
import urllib.error
import urllib.request
from email.message import Message

import pytest

from src.processing import markdown_parser as mp
from src.processing.inherit import FETCH_WORKERS, fetch_image


def _err(code: int, retry_after: str | None = None) -> urllib.error.HTTPError:
    hdrs = Message()
    if retry_after is not None:
        hdrs["Retry-After"] = retry_after
    return urllib.error.HTTPError("http://x/a.png", code, "e", hdrs, io.BytesIO())


class _Resp:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, n=-1):
        return b"data"


def _script(monkeypatch, outcomes):
    seen = []

    def fake(req, timeout=None):
        seen.append(req)
        out = outcomes.pop(0)
        if isinstance(out, Exception):
            raise out
        return out

    sleeps = []
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    monkeypatch.setattr(mp.time, "sleep", sleeps.append)
    return seen, sleeps


def test_at_most_four_at_once():
    assert mp.DOOR_WORKERS == 4 and FETCH_WORKERS == 4


def test_429_honours_retry_after_then_succeeds(monkeypatch):
    seen, sleeps = _script(monkeypatch, [_err(429, "2"), _Resp()])
    assert fetch_image("http://x/a.png") == b"data"
    assert sleeps == [2.0] and len(seen) == 2


def test_503_backs_off_without_retry_after(monkeypatch):
    _, sleeps = _script(monkeypatch, [_err(503), _err(503), _Resp()])
    assert mp._check_url("http://x/a.png", {}, 5.0) is True
    assert len(sleeps) == 2 and sleeps[1] > sleeps[0] > 0


def test_429_forever_gives_up_after_bounded_retries(monkeypatch):
    seen, sleeps = _script(monkeypatch, [_err(429, "0") for _ in range(20)])
    assert fetch_image("http://x/a.png") is None
    assert len(seen) == mp._MAX_RETRIES + 1


def test_404_fails_at_once(monkeypatch):
    seen, sleeps = _script(monkeypatch, [_err(404)])
    assert mp._check_url("http://x/a.png", {}, 5.0) is False
    assert len(seen) == 1 and sleeps == []

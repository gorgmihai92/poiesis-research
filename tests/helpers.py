"""Shared by the tests: the scripts on the import path, a fake network, and a clean request layer per test.

Nothing here touches a real database. `FakeNet` stands in for the one function that opens a connection, serves
canned answers by a piece of the URL, and counts what it was asked.
"""
import contextlib
import email.message
import io
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "plugins" / "poiesis-research" / "skills" / "research" / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
RECORDINGS = Path(__file__).resolve().parent / "recordings"
sys.path.insert(0, str(SCRIPTS))
sys.dont_write_bytecode = True

import scholarly as sc  # noqa: E402


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def headers(pairs: dict | None) -> email.message.Message:
    m = email.message.Message()
    for k, v in (pairs or {}).items():
        m[k] = str(v)
    return m


class Answer:
    """What the fake network sends back for one request."""

    def __init__(self, body: str = "{}", status: int = 200, head: dict | None = None):
        self.body, self.status, self.head = body, status, head or {}


class _Response:
    def __init__(self, answer: Answer):
        self._body = answer.body.encode("utf-8")
        self.status = answer.status
        self.headers = headers(answer.head)

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> bool:
        return False


class FakeNet:
    """Routes are (piece of the URL, Answer or list of Answers). The first route whose piece is in the URL
    answers; a list is served one item per request, the last one repeating. An unknown URL fails the test."""

    def __init__(self, routes: list[tuple[str, object]]):
        self.routes = routes
        self.calls: list[str] = []
        self.sent: list[dict] = []  # the headers of each request, to check that nothing personal is sent

    def __call__(self, req, timeout=60):
        url = req.full_url
        self.calls.append(url)
        self.sent.append(dict(req.header_items()))
        for piece, answer in self.routes:
            if piece in url:
                if isinstance(answer, list):
                    answer = answer.pop(0) if len(answer) > 1 else answer[0]
                if isinstance(answer, BaseException):  # what opening the connection raises, as it is
                    raise answer
                if answer.status >= 400:
                    raise urllib.error.HTTPError(url, answer.status, "refused by the fake network", headers(answer.head), io.BytesIO(answer.body.encode()))
                return _Response(answer)
        raise AssertionError(f"the test did not expect a request to {url}")

    def count(self, piece: str) -> int:
        return sum(1 for u in self.calls if piece in u)


class LayerCase(unittest.TestCase):
    """A test with its own cache folder, no waiting, and a fake network that refuses everything by default."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.sleeps: list[float] = []
        # A key set in the shell would change what the scripts send and say: a test that wants one sets its own.
        self._keys = {name: os.environ.pop(name, None) for name in ("OPENALEX_API_KEY", "S2_API_KEY")}
        self._saved = (sc.LAYER, sc._open, sc._sleep)
        sc.LAYER = sc._Layer()
        sc.configure(cache_dir=self.tmp / "cache", fresh=False, record=None, replay=None, hours=24)
        sc._sleep = self.sleeps.append
        self.net = self.use([])

    def tearDown(self) -> None:
        sc.LAYER, sc._open, sc._sleep = self._saved
        for name, value in self._keys.items():
            os.environ.pop(name, None)
            if value is not None:
                os.environ[name] = value
        self._tmp.cleanup()

    def use(self, routes: list[tuple[str, object]]) -> FakeNet:
        self.net = FakeNet(routes)
        sc._open = self.net
        return self.net

    def run_script(self, module, argv: list[str]) -> tuple[int, str, str]:
        """Run a script's main() the way its last line does, and return (exit code, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        saved = sys.argv
        sys.argv = [module.__name__ + ".py", *argv]
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    code = sc.finish(module.main)
                except SystemExit as e:  # argparse errors and explicit exits
                    code = e.code
        finally:
            sys.argv = saved
        return code, out.getvalue(), err.getvalue()

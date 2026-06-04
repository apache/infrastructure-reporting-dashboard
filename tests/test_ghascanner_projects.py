import importlib.util
import sys
import types
import unittest
from pathlib import Path


class FetchProjectsTest(unittest.IsolatedAsyncioTestCase):
    # The retry helper is intentionally private; these tests exercise it directly to avoid
    # sleeping through the public retry loop.
    # pylint: disable=protected-access

    @classmethod
    def setUpClass(cls):
        cls.ghascanner = load_ghascanner()

    async def test_fetch_projects_attempt_populates_projects_on_success(self):
        self.ghascanner._projects = []
        self.ghascanner.aiohttp.ClientSession = fake_session_factory(
            FakeResponse(200, {"projects": {"cassandra": {}, "polaris": {}}})
        )

        ok = await self.ghascanner._fetch_projects_attempt()

        self.assertTrue(ok)
        self.assertEqual(self.ghascanner.get_projects(), ["cassandra", "polaris"])

    async def test_fetch_projects_attempt_returns_false_on_non_200(self):
        self.ghascanner._projects = ["existing"]
        self.ghascanner.aiohttp.ClientSession = fake_session_factory(
            FakeResponse(503, {}, reason="Service Unavailable")
        )

        ok = await self.ghascanner._fetch_projects_attempt()

        self.assertFalse(ok)
        self.assertEqual(self.ghascanner.get_projects(), ["existing"])

    async def test_fetch_projects_attempt_returns_false_on_missing_projects_key(self):
        self.ghascanner._projects = ["existing"]
        self.ghascanner.aiohttp.ClientSession = fake_session_factory(
            FakeResponse(200, {"not_projects": {}})
        )

        ok = await self.ghascanner._fetch_projects_attempt()

        self.assertFalse(ok)
        self.assertEqual(self.ghascanner.get_projects(), ["existing"])


class FakeClientSession:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, _url):
        return self.response


class FakeResponse:
    def __init__(self, status, payload, reason="OK"):
        self.status = status
        self.payload = payload
        self.reason = reason

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        return self.payload


def fake_session_factory(response):
    return lambda *args, **kwargs: FakeClientSession(response)


def load_ghascanner():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "server" / "app" / "plugins" / "ghascanner.py"

    aiohttp = types.ModuleType("aiohttp")
    aiohttp.ClientTimeout = lambda *args, **kwargs: None
    aiohttp.ClientSession = None
    aiohttp.ClientError = Exception
    sys.modules["aiohttp"] = aiohttp

    asfpy = types.ModuleType("asfpy")
    asfpy.pubsub = types.ModuleType("asfpy.pubsub")
    asfpy.sqlite = types.ModuleType("asfpy.sqlite")
    sys.modules["asfpy"] = asfpy
    sys.modules["asfpy.pubsub"] = asfpy.pubsub
    sys.modules["asfpy.sqlite"] = asfpy.sqlite

    server = types.ModuleType("server")
    server_app = types.ModuleType("server.app")
    server_app_lib = types.ModuleType("server.app.lib")
    config = types.ModuleType("server.app.lib.config")
    plugins = types.ModuleType("server.app.plugins")
    plugins.root = types.SimpleNamespace(register=lambda *args, **kwargs: None)

    sys.modules["server"] = server
    sys.modules["server.app"] = server_app
    sys.modules["server.app.lib"] = server_app_lib
    sys.modules["server.app.lib.config"] = config
    sys.modules["server.app.plugins"] = plugins

    spec = importlib.util.spec_from_file_location("server.app.plugins.ghascanner", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    unittest.main()

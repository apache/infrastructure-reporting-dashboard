import importlib.util
import sys
import types
import unittest
from pathlib import Path


class GhaScannerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ghascanner = load_ghascanner()

    def test_parse_jobs_counts_only_jobs_assigned_to_runners(self):
        data = {
            "jobs": [
                {
                    "name": "real macOS job",
                    "workflow_name": "Java CI",
                    "runner_name": "GitHub Actions 1019729395",
                    "runner_group_name": "GitHub Actions",
                    "started_at": "2026-06-02T15:59:43Z",
                    "completed_at": "2026-06-02T16:00:02Z",
                    "steps": [
                        {
                            "name": "Set up job",
                            "started_at": "2026-06-02T15:59:43Z",
                            "completed_at": "2026-06-02T15:59:44Z",
                        }
                    ],
                    "labels": ["macos-latest"],
                    "conclusion": "failure",
                },
                {
                    "name": "queued cancelled job without runner",
                    "workflow_name": "Java CI",
                    "runner_name": "",
                    "runner_group_name": None,
                    "started_at": "2026-06-01T15:59:28Z",
                    "completed_at": "2026-06-02T15:59:28Z",
                    "steps": [],
                    "labels": ["missing-runner"],
                    "conclusion": "cancelled",
                },
                {
                    "name": "cancelled after runner assignment",
                    "workflow_name": "Java CI",
                    "runner_name": "GitHub Actions 123",
                    "runner_group_name": "GitHub Actions",
                    "started_at": "2026-06-04T07:53:03Z",
                    "completed_at": "2026-06-04T07:55:30Z",
                    "steps": [
                        {
                            "name": "Set up job",
                            "started_at": "2026-06-04T07:53:03Z",
                            "completed_at": "2026-06-04T07:53:04Z",
                        }
                    ],
                    "labels": ["ubuntu-latest"],
                    "conclusion": "cancelled",
                },
            ]
        }

        seconds_used, earliest_runner, last_finish, jobs = self.ghascanner.parse_jobs(data, "mina")

        self.assertEqual(seconds_used, 166)
        self.assertEqual(len(jobs), 2)
        self.assertEqual([job["job_duration"] for job in jobs], [19, 147])
        self.assertEqual([job["runner_name"] for job in jobs], ["GitHub Actions 1019729395", "GitHub Actions 123"])
        self.assertEqual(earliest_runner, 1780415983)
        self.assertEqual(last_finish, 1780559730)

    def test_normalize_run_row_filters_legacy_no_runner_jobs(self):
        row = {
            "seconds_used": 24 * 3600 + 19,
            "jobs": [
                {
                    "name": "Java CI",
                    "job_duration": 19,
                    "steps": [("Set up job", 1780415983, 1)],
                    "labels": ["macos-latest"],
                },
                {
                    "name": "Java CI",
                    "job_duration": 24 * 3600,
                    "steps": [],
                    "labels": ["missing-runner"],
                },
            ],
        }

        normalized = self.ghascanner.normalize_run_row(row)

        self.assertEqual(len(normalized["jobs"]), 1)
        self.assertEqual(normalized["seconds_used"], sum(job["job_duration"] for job in normalized["jobs"]))
        self.assertFalse(any(not job.get("steps") for job in normalized["jobs"]))


def load_ghascanner():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "server" / "app" / "plugins" / "ghascanner.py"

    aiohttp = types.ModuleType("aiohttp")
    aiohttp.ClientTimeout = lambda *args, **kwargs: None
    aiohttp.ClientSession = object
    aiohttp.ClientError = Exception
    sys.modules.setdefault("aiohttp", aiohttp)

    asfpy = types.ModuleType("asfpy")
    asfpy.pubsub = types.ModuleType("asfpy.pubsub")
    asfpy.sqlite = types.ModuleType("asfpy.sqlite")
    sys.modules.setdefault("asfpy", asfpy)
    sys.modules.setdefault("asfpy.pubsub", asfpy.pubsub)
    sys.modules.setdefault("asfpy.sqlite", asfpy.sqlite)

    server = types.ModuleType("server")
    server_app = types.ModuleType("server.app")
    server_app_lib = types.ModuleType("server.app.lib")
    config = types.ModuleType("server.app.lib.config")
    plugins = types.ModuleType("server.app.plugins")
    plugins.root = types.SimpleNamespace(register=lambda *args, **kwargs: None)

    sys.modules.setdefault("server", server)
    sys.modules.setdefault("server.app", server_app)
    sys.modules.setdefault("server.app.lib", server_app_lib)
    sys.modules.setdefault("server.app.lib.config", config)
    sys.modules.setdefault("server.app.plugins", plugins)

    spec = importlib.util.spec_from_file_location("server.app.plugins.ghascanner", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    unittest.main()

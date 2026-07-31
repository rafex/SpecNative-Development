import importlib.util
import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import specnative

import install


def load_mcp_module():
    """Load the MCP server with a minimal decorator stub for unit tests."""
    class FakeMCP:
        def __init__(self, *args, **kwargs):
            pass

        @staticmethod
        def tool(*args, **kwargs):
            return lambda function: function

        @staticmethod
        def resource(*args, **kwargs):
            return lambda function: function

        @staticmethod
        def prompt(*args, **kwargs):
            return lambda function: function

    mcp_module = types.ModuleType("mcp")
    server_module = types.ModuleType("mcp.server")
    fastmcp_module = types.ModuleType("mcp.server.fastmcp")
    fastmcp_module.FastMCP = FakeMCP
    previous = {name: sys.modules.get(name) for name in ("mcp", "mcp.server", "mcp.server.fastmcp")}
    sys.modules.update({"mcp": mcp_module, "mcp.server": server_module, "mcp.server.fastmcp": fastmcp_module})
    try:
        module_path = Path(__file__).parents[1] / "tools" / "specnative_mcp.py"
        spec = importlib.util.spec_from_file_location("specnative_mcp_test", module_path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for name, module in previous.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


class FrameworkTests(unittest.TestCase):
    def test_template_validates(self):
        self.assertEqual(specnative.validate(), 0)

    def test_toml_parser_handles_commas_inside_strings(self):
        parsed = specnative.parse_simple_toml(
            'validation = ["login, logout walkthrough", "pytest tests/auth.py"]\n'
            'enabled = true\n'
        )
        self.assertEqual(
            parsed["validation"],
            ["login, logout walkthrough", "pytest tests/auth.py"],
        )
        self.assertTrue(parsed["enabled"])

    def test_board_derives_columns_from_state_and_dependencies(self):
        board = specnative.build_board()
        self.assertEqual(
            [task["id"] for task in board["columns"]["done"]],
            ["TASK-AUTH-0001"],
        )
        self.assertEqual(
            [task["id"] for task in board["columns"]["in_progress"]],
            ["TASK-AUTH-0002"],
        )
        self.assertEqual(
            [task["id"] for task in board["columns"]["waiting"]],
            ["TASK-AUTH-0003"],
        )
        self.assertIn("TASK-AUTH-0003", specnative.render_board_markdown(board))
        self.assertIn("flowchart LR", specnative.render_board_mermaid(board))

    def test_github_project_plan_is_dry_run_and_uses_task_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "github-project.toml"
            config.write_text(
                """[github_project]
project_id = \"PVT_test\"
owner = \"test-org\"

[status_map]
ready = \"Todo\"
in_progress = \"In Progress\"
blocked = \"Blocked\"
waiting = \"Todo\"
done = \"Done\"
""",
                encoding="utf-8",
            )
            plan = specnative.github_project_plan(config)

        self.assertEqual(plan["mode"], "dry_run")
        self.assertEqual(plan["project"]["project_id"], "PVT_test")
        self.assertEqual(plan["items"][0]["operation"], "upsert_draft_item")
        self.assertTrue(all(item["external_key"].startswith("TASK-") for item in plan["items"]))

    def test_backlog_capture_creates_intake_or_canonical_task(self):
        mcp = load_mcp_module()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "spec-native/specs/payments").mkdir(parents=True)
            (target / "spec-native/specs/payments/SPEC.md").write_text(
                """```toml
artifact_type = "spec"
id = "SPEC-PAY-0001"
state = "active"
owner = "payments"
created_at = "2026-01-01"
updated_at = "2026-01-01"
```
""",
                encoding="utf-8",
            )
            mcp.REPO = target
            mcp.SN = target / "spec-native"

            intake = mcp.capture_backlog_item("Investigar pagos", "Evaluar proveedores de pago.")
            task = mcp.capture_backlog_item(
                "Crear puerto de pagos",
                "Definir contrato para iniciar un pago.",
                initiative="payments",
                close_criteria="El contrato se compila y cubre el caso de inicio.",
                validation=["pytest tests/payments/test_port.py"],
            )

            self.assertIn("IDEA-0001", intake)
            self.assertIn("TASK-PAYMENTS-0001", task)
            self.assertIn("triaged", (target / "spec-native/intake/IDEAS.md").read_text(encoding="utf-8"))
            task_file = (target / "spec-native/tasks/payments/TASKS.md").read_text(encoding="utf-8")
            self.assertIn('spec_id = "SPEC-PAY-0001"', task_file)
            self.assertIn('priority = "p2"', task_file)

    def test_context_profile_contains_navigation_contract(self):
        required = {
            "spec-native/README.md",
            "spec-native/specs/README.md",
            "spec-native/tasks/README.md",
            "spec-native/workflows/README.md",
            "spec-native/workflows/IMPLEMENTATION.md",
            "spec-native/pipelines/README.md",
            ".specnative/SCHEMA.md",
        }
        self.assertTrue(required.issubset(set(install.PATHS_CONTEXT)))

    def test_team_profile_contains_work_management_assets(self):
        self.assertIn("spec-native/backlog/README.md", install.PATHS_SPEC)
        self.assertIn(
            ".specnative/integrations/github-project.toml.example",
            install.PATHS_TEAM,
        )

    def test_context_profile_contains_agent_skills(self):
        self.assertIn(".claude/skills/specnative-workflow/SKILL.md", install.PATHS_CONTEXT)
        self.assertIn(".codex/skills/specnative-workflow/SKILL.md", install.PATHS_CONTEXT)

    def test_opencode_configuration_is_merged_without_losing_existing_values(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            config_path = target / "opencode.json"
            config_path.write_text(
                json.dumps(
                    {
                        "$schema": "custom-schema",
                        "provider": {"name": "existing"},
                        "command": {"custom-command": {"template": "keep me"}},
                    }
                ),
                encoding="utf-8",
            )
            created = []
            errors = []

            install.setup_mcp_configs(target, created, errors)

            self.assertEqual(errors, [])
            merged = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(merged["$schema"], "custom-schema")
            self.assertEqual(merged["provider"], {"name": "existing"})
            self.assertEqual(merged["command"]["custom-command"]["template"], "keep me")
            self.assertIn("specnative", merged["mcp"])
            self.assertIn("spec-init", merged["command"])
            self.assertIn("spec", merged["command"])
            self.assertIn("spec-backlog-add", merged["command"])

    def test_install_creates_clean_branch_and_context_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=target, check=True)
            (target / "README.md").write_text("# Existing project\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=target, check=True)
            subprocess.run(
                ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qm", "init"],
                cwd=target,
                check=True,
            )

            template_root = Path(__file__).parents[1] / "Template-Project-Agents-AI"

            def fake_download(url: str) -> bytes:
                if url.endswith("/specnative_mcp.py"):
                    return b"# test MCP asset\n"
                relative = url.split("/Template-Project-Agents-AI/", 1)[1]
                return (template_root / relative).read_bytes()

            with patch.object(install, "download_file", side_effect=fake_download), patch.object(
                install, "setup_venv", return_value=(target / ".specnative/.venv", [])
            ):
                install.install(
                    target=target,
                    version="vtest",
                    profile="context",
                    include_examples=False,
                    branch="specnative/test",
                    force=False,
                )

            branch = subprocess.check_output(
                ["git", "branch", "--show-current"], cwd=target, text=True
            ).strip()
            self.assertEqual(branch, "specnative/test")
            self.assertTrue((target / "spec-native/README.md").exists())
            self.assertTrue((target / "spec-native/workflows/IMPLEMENTATION.md").exists())
            self.assertTrue((target / ".specnative/SCHEMA.md").exists())
            self.assertTrue((target / ".specnative/specnative_mcp.py").exists())


if __name__ == "__main__":
    unittest.main()

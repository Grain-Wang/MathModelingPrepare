from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "skillctl", REPO_ROOT / "scripts" / "skillctl.py"
)
assert SPEC and SPEC.loader
skillctl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(skillctl)


class SkillCtlTests(unittest.TestCase):
    def test_current_registry_matches_schema(self):
        registry = skillctl.load_registry()
        skillctl.validate_registry_schema(registry)
        self.assertEqual("math_modeling", registry["environment"]["name"])
        self.assertEqual("win-64", registry["environment"]["platform"])

    def test_registry_names_are_unique_and_paths_match_status(self):
        registry = skillctl.load_registry()
        names = [item["name"] for item in registry["skills"]]
        self.assertEqual(len(names), len(set(names)))
        for item in registry["skills"]:
            expected = skillctl.expected_skill_prefix(item["status"])
            self.assertTrue(item["path"].startswith(expected))

    def test_safe_repo_path_rejects_escape_and_competition(self):
        with self.assertRaises(skillctl.SkillCtlError):
            skillctl.safe_repo_path("../outside")
        with self.assertRaises(skillctl.SkillCtlError):
            skillctl.safe_repo_path("competition/new-file")
        with self.assertRaises(skillctl.SkillCtlError):
            skillctl.safe_repo_path(".env")

    def test_frontmatter_parser(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "SKILL.md").write_text(
                "---\nname: sample-skill\ndescription: A sample.\n---\n\n# Sample\n",
                encoding="utf-8",
            )
            metadata = skillctl.parse_skill_frontmatter(root)
            self.assertEqual("sample-skill", metadata["name"])

    def test_tree_hash_is_deterministic_and_content_sensitive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "SKILL.md").write_text("first", encoding="utf-8")
            first = skillctl.tree_hash(root)
            self.assertEqual(first, skillctl.tree_hash(root))
            (root / "SKILL.md").write_text("second", encoding="utf-8")
            self.assertNotEqual(first, skillctl.tree_hash(root))

    def test_tree_hash_ignores_python_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "SKILL.md").write_text("stable", encoding="utf-8")
            first = skillctl.tree_hash(root)
            cache = root / "__pycache__"
            cache.mkdir()
            (cache / "x.pyc").write_bytes(b"runtime")
            self.assertEqual(first, skillctl.tree_hash(root))

    def test_dependency_commands_are_argv_not_shell_strings(self):
        skill = {
            "dependencies": {
                "conda": ["numpy"],
                "pip": ["demo==1.0"],
                "external": [],
                "mcp": [],
            }
        }
        commands = skillctl.dependency_commands(skill, "math_modeling")
        self.assertTrue(all(isinstance(command, list) for command in commands))
        self.assertEqual("conda", commands[0][0])
        self.assertIn("demo==1.0", commands[1])

    def test_environment_manifest_is_registry_derived(self):
        registry = skillctl.load_registry()
        rendered = skillctl.render_environment(registry)
        self.assertEqual(
            (REPO_ROOT / "environment.yml").read_text(encoding="utf-8"), rendered
        )

    def test_search_parser_and_dry_run_default(self):
        parser = skillctl.build_parser()
        args = parser.parse_args(["stage", "--source", ".", "--license", "internal"])
        self.assertFalse(args.apply)


if __name__ == "__main__":
    unittest.main()

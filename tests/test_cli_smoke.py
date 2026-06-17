from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "examples"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, "-m", "app.cli", *map(str, args)]
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


class CliSmokeTests(unittest.TestCase):
    def test_validate_dvd_example(self) -> None:
        result = run_cli("validate", EXAMPLES_DIR / "dvd.json")
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        self.assertIn("VALID", result.stdout)

    def test_build_dvd_example_writes_expected_files(self) -> None:
        example_path = EXAMPLES_DIR / "dvd.json"
        example = load_json(example_path)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "dvd-output"

            result = run_cli("build", example_path, "--output-dir", output_dir)

            self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
            self.assertTrue((output_dir / "validated.json").exists())
            self.assertTrue((output_dir / "fabrication.json").exists())

            validated = load_json(output_dir / "validated.json")
            fabrication = load_json(output_dir / "fabrication.json")

            self.assertEqual(validated["project_name"], example["project_name"])
            self.assertIn("parts", fabrication)
            self.assertTrue(fabrication["parts"])

    def test_build_books_examples_writes_expected_files(self) -> None:
        examples = [
            "libros_4_4.json",
            "libros_5_3.json",
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            for file_name in examples:
                example_path = EXAMPLES_DIR / file_name
                example = load_json(example_path)
                output_dir = Path(temp_dir) / example["project_name"]

                result = run_cli("build", example_path, "--output-dir", output_dir)

                self.assertEqual(
                    result.returncode,
                    0,
                    msg=f"{file_name}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
                )
                self.assertTrue((output_dir / "validated.json").exists())
                self.assertTrue((output_dir / "fabrication.json").exists())

                validated = load_json(output_dir / "validated.json")
                self.assertEqual(validated["project_name"], example["project_name"])


if __name__ == "__main__":
    unittest.main()
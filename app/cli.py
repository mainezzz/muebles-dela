# app/cli.py
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from app.fabrication import build_and_write
from app.spec_builder import prepare_specs
from app.validator import ValidationError, load_json, validate_file


def _echo(message: str) -> None:
    print(message)


def _fail(message: str, code: int = 1) -> int:
    print(message, file=sys.stderr)
    return code


def _resolve_output_dir(spec_path: Path, project_name: str, explicit_output_dir: Path | None) -> Path:
    if explicit_output_dir is not None:
        output_dir = explicit_output_dir
    else:
        output_dir = Path("outputs") / project_name

    if not output_dir.is_absolute():
        output_dir = (Path.cwd() / output_dir).resolve()

    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _write_json(payload: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)
    return output_path


def _prepare_outputs(spec_path: Path, output_dir: Path | None) -> tuple[dict, dict, Path, Path, Path]:
    raw_spec = load_json(spec_path)
    visual_spec, fabrication_request = prepare_specs(raw_spec)
    validated_spec = validate_file(spec_path)

    project_name = str(validated_spec["project_name"])
    resolved_output_dir = _resolve_output_dir(spec_path, project_name, output_dir)

    validated_path = _write_json(validated_spec, resolved_output_dir / "validated.json")
    fabrication_path = build_and_write(fabrication_request, resolved_output_dir, "fabrication.json")

    return validated_spec, fabrication_request, resolved_output_dir, validated_path, fabrication_path


def _run_blender(blender_exe: Path, script_path: Path, input_path: Path, output_dir: Path) -> None:
    resolved_blender = blender_exe.expanduser().resolve()
    resolved_script = script_path.expanduser().resolve()
    resolved_input = input_path.expanduser().resolve()
    resolved_output = output_dir.expanduser().resolve()

    if not resolved_blender.exists():
        raise FileNotFoundError(f"Blender executable not found: {resolved_blender}")
    if not resolved_script.exists():
        raise FileNotFoundError(f"Blender script not found: {resolved_script}")
    if not resolved_input.exists():
        raise FileNotFoundError(f"Input file not found: {resolved_input}")

    command = [
        str(resolved_blender),
        "--background",
        "--python",
        str(resolved_script),
        "--",
        str(resolved_input),
        str(resolved_output),
    ]
    subprocess.run(command, check=True)


def validate_command(spec_path: Path) -> int:
    spec = validate_file(spec_path)
    _echo(f"VALID: {spec['project_name']}")
    return 0


def build_command(spec_path: Path, blender_exe: Path | None = None, output_dir: Path | None = None) -> int:
    validated_spec, _, resolved_output_dir, validated_path, fabrication_path = _prepare_outputs(spec_path, output_dir)

    _echo(f"VALIDATED: {validated_spec['project_name']}")
    _echo(f"WROTE: {validated_path}")
    _echo(f"WROTE: {fabrication_path}")

    if blender_exe is None:
        return 0

    _run_blender(blender_exe, Path("blender") / "generate_bookshelf.py", validated_path, resolved_output_dir)
    _echo(f"RENDERED: {resolved_output_dir}")

    _run_blender(blender_exe, Path("blender") / "generate_kerf_layout.py", fabrication_path, resolved_output_dir)
    _echo(f"KERF: {resolved_output_dir}")
    return 0


def generate_command(spec_path: Path, blender_exe: Path, output_dir: Path | None = None) -> int:
    validated_spec, _, resolved_output_dir, validated_path, _ = _prepare_outputs(spec_path, output_dir)

    _echo(f"VALIDATED: {validated_spec['project_name']}")
    _echo(f"WROTE: {validated_path}")

    _run_blender(blender_exe, Path("blender") / "generate_bookshelf.py", validated_path, resolved_output_dir)
    _echo(f"RENDERED: {resolved_output_dir}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="DELA furniture CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate a furniture specification")
    validate_parser.add_argument("spec_path", type=Path)

    build_parser = subparsers.add_parser(
        "build",
        help="Validate, normalize, and generate fabrication payload. Optionally run Blender renders.",
    )
    build_parser.add_argument("spec_path", type=Path)
    build_parser.add_argument("--blender-exe", type=Path)
    build_parser.add_argument("--output-dir", type=Path)

    generate_parser = subparsers.add_parser(
        "generate",
        help="Validate and render the visual bookshelf with Blender.",
    )
    generate_parser.add_argument("spec_path", type=Path)
    generate_parser.add_argument("--blender-exe", type=Path, required=True)
    generate_parser.add_argument("--output-dir", type=Path)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "validate":
            return validate_command(args.spec_path)
        if args.command == "build":
            return build_command(args.spec_path, args.blender_exe, args.output_dir)
        if args.command == "generate":
            return generate_command(args.spec_path, args.blender_exe, args.output_dir)
    except ValidationError as exc:
        return _fail(f"Validation error: {exc}")
    except subprocess.CalledProcessError as exc:
        return _fail(f"Blender command failed with exit code {exc.returncode}")
    except FileNotFoundError as exc:
        return _fail(str(exc))
    except Exception as exc:
        return _fail(f"Unexpected error: {exc}")

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

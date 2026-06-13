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


CLI_DESCRIPTION = """DELA furniture CLI

Modelo v2:
- el usuario fija medidas exteriores máximas
- define construcción del armazón
- define huecos y distribución
- el sistema valida viabilidad y genera visual + fabricación
"""

CLI_EPILOG = """Ejemplos:
  python -m app.cli validate examples/dvd.json
  python -m app.cli build examples/dvd.json
  python -m app.cli build examples/libros_4_4.json --output-dir outputs/libros
  python -m app.cli build examples/dvd.json --blender-exe "C:/Program Files/Blender Foundation/Blender 4.2/blender.exe"

Campos v2 esperados en el JSON:
  content_type: dvd | books
  outer.width / outer.height / outer.depth
  material.board_thickness / material.back_thickness
  construction.shell_mode: sides_outside | top_bottom_outside
  construction.columns: 1 | 2
  construction.back_panel: true | false
  layout.openings o layout.opening_groups
  layout.distribution_mode: manual | symmetric | large_top | large_bottom

Comandos:
  validate  Valida que el mueble sea viable
  build     Genera validated.json y fabrication.json; opcionalmente renderiza
  generate  Renderiza la vista visual en Blender
"""


def _echo(message: str) -> None:
    print(message)


def _fail(message: str, code: int = 1) -> int:
    print(message, file=sys.stderr)
    return code


def _resolve_output_dir(project_name: str, explicit_output_dir: Path | None) -> Path:
    output_dir = explicit_output_dir if explicit_output_dir is not None else Path("outputs") / project_name
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
    resolved_output_dir = _resolve_output_dir(project_name, output_dir)

    validated_path = _write_json(visual_spec, resolved_output_dir / "validated.json")
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
        raise FileNotFoundError(f"Input JSON not found: {resolved_input}")

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

    outer = spec["overall_dimensions"]
    material = spec["material"]
    construction = spec["construction"]

    _echo(f"VALID: {spec['project_name']}")
    _echo(
        "OUTER: "
        f"{int(round(float(outer['width'])))}x"
        f"{int(round(float(outer['height'])))}x"
        f"{int(round(float(outer['depth'])))} mm"
    )
    _echo(
        "BUILD: "
        f"shell_mode={construction['shell_mode']} "
        f"columns={construction['columns']} "
        f"board={int(round(float(material['board_thickness'])))} mm"
    )
    return 0


def build_command(spec_path: Path, blender_exe: Path | None = None, output_dir: Path | None = None) -> int:
    validated_spec, _, resolved_output_dir, validated_path, fabrication_path = _prepare_outputs(spec_path, output_dir)

    _echo(f"VALIDATED: {validated_spec['project_name']}")
    _echo(f"WROTE: {validated_path}")
    _echo(f"WROTE: {fabrication_path}")

    if blender_exe is None:
        _echo("DONE: build finished without Blender")
        return 0

    _run_blender(blender_exe, Path("blender") / "generate_bookshelf.py", validated_path, resolved_output_dir)
    _echo(f"RENDERED: {resolved_output_dir}")

    kerf_script = Path("blender") / "generate_kerf_layout.py"
    if kerf_script.exists():
        _run_blender(blender_exe, kerf_script, fabrication_path, resolved_output_dir)
        _echo(f"KERF: {resolved_output_dir}")
    else:
        _echo("INFO: blender/generate_kerf_layout.py not found; skipping kerf layout render")

    _echo("DONE: build finished with Blender")
    return 0


def generate_command(spec_path: Path, blender_exe: Path, output_dir: Path | None = None) -> int:
    validated_spec, _, resolved_output_dir, validated_path, _ = _prepare_outputs(spec_path, output_dir)

    _echo(f"VALIDATED: {validated_spec['project_name']}")
    _echo(f"WROTE: {validated_path}")

    _run_blender(blender_exe, Path("blender") / "generate_bookshelf.py", validated_path, resolved_output_dir)
    _echo(f"RENDERED: {resolved_output_dir}")
    _echo("DONE: visual render finished")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description=CLI_DESCRIPTION,
        epilog=CLI_EPILOG,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate",
        help="Valida la viabilidad del mueble v2",
        description=(
            "Valida una especificación v2.\n"
            "Comprueba medidas exteriores, construcción, columnas y que los huecos caben."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    validate_parser.add_argument("spec_path", type=Path, help="Ruta al JSON del mueble")

    build_parser = subparsers.add_parser(
        "build",
        help="Genera visual + fabricación; opcionalmente renderiza con Blender",
        description=(
            "Procesa una especificación v2.\n"
            "Siempre genera:\n"
            "  - validated.json\n"
            "  - fabrication.json\n\n"
            "Si se indica --blender-exe también genera:\n"
            "  - renders cliente\n"
            "  - plano carpintería\n"
            "  - layout kerf (si existe el script)"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    build_parser.add_argument("spec_path", type=Path, help="Ruta al JSON del mueble")
    build_parser.add_argument(
        "--blender-exe",
        type=Path,
        help="Ruta al ejecutable de Blender para render y plano carpintería",
    )
    build_parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directorio de salida. Por defecto: outputs/<project_name>",
    )

    generate_parser = subparsers.add_parser(
        "generate",
        help="Renderiza solo la parte visual con Blender",
        description=(
            "Valida la especificación v2 y renderiza la vista visual del mueble.\n"
            "No genera layout kerf."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    generate_parser.add_argument("spec_path", type=Path, help="Ruta al JSON del mueble")
    generate_parser.add_argument(
        "--blender-exe",
        type=Path,
        required=True,
        help="Ruta al ejecutable de Blender",
    )
    generate_parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directorio de salida. Por defecto: outputs/<project_name>",
    )

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
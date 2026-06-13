from pathlib import Path
import json
import subprocess

import typer

from app.fabrication import build_and_write
from app.spec_builder import prepare_specs
from app.validator import (
    validate_file,
    ValidationError,
    load_json,
)


app = typer.Typer()


def _run_blender(blender_exe: Path, script_path: Path, input_path: Path, output_dir: Path) -> None:
    cmd = [
        str(blender_exe),
        "--background",
        "--python",
        str(script_path),
        "--",
        str(input_path),
        str(output_dir),
    ]
    subprocess.run(cmd, check=True)


def _prepare_output(spec_path: Path) -> tuple[dict, dict, Path, Path, Path]:
    raw_spec = load_json(spec_path)
    visual_spec, fabrication_request = prepare_specs(raw_spec)
    validated_spec = validate_file(spec_path)

    output_dir = Path("outputs") / validated_spec["project_name"]
    output_dir.mkdir(parents=True, exist_ok=True)

    validated_path = output_dir / "validated.json"
    fabrication_path = output_dir / "fabrication.json"

    with open(validated_path, "w", encoding="utf-8") as file:
        json.dump(visual_spec, file, indent=2, ensure_ascii=False)

    build_and_write(fabrication_request, output_dir, fabrication_path.name)
    return visual_spec, fabrication_request, output_dir, validated_path, fabrication_path


@app.command()
def validate(
    spec_path: Path
) -> None:

    try:

        spec = validate_file(
            spec_path
        )

    except ValidationError as exc:

        typer.echo(str(exc))

        raise typer.Exit(code=1)

    typer.echo(
        f"VALID: {spec['project_name']}"
    )


@app.command()
def generate(
    spec_path: Path,
    blender_exe: Path = typer.Option(...)
) -> None:

    try:
        _, _, output_dir, validated_path, _ = _prepare_output(spec_path)
    except ValidationError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)

    typer.echo("Running Blender render...")
    _run_blender(blender_exe, Path("blender") / "generate_bookshelf.py", validated_path, output_dir)

    typer.echo(
        f"DONE → {output_dir}"
    )


@app.command()
def build(
    spec_path: Path,
    blender_exe: Path | None = typer.Option(None)
) -> None:
    try:
        _, _, output_dir, validated_path, fabrication_path = _prepare_output(spec_path)
    except ValidationError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)

    if blender_exe is None:
        typer.echo(f"OK → {output_dir}")
        typer.echo("Generated validated.json and fabrication.json")
        return

    typer.echo("Running Blender render...")
    _run_blender(blender_exe, Path("blender") / "generate_bookshelf.py", validated_path, output_dir)

    typer.echo("Running kerf layout...")
    _run_blender(blender_exe, Path("blender") / "generate_kerf_layout.py", fabrication_path, output_dir)

    typer.echo(f"DONE → {output_dir}")


if __name__ == "__main__":
    app()

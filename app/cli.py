from pathlib import Path
import json
import subprocess

import typer

from app.validator import (
    validate_file,
    ValidationError
)


app = typer.Typer()


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

        spec = validate_file(
            spec_path
        )

    except ValidationError as exc:

        typer.echo(str(exc))

        raise typer.Exit(code=1)

    output_dir = (
        Path("outputs")
        / spec["project_name"]
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    validated_path = (
        output_dir
        / "validated.json"
    )

    with open(
        validated_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            spec,
            f,
            indent=2,
            ensure_ascii=False
        )

    blender_script = (
        Path("blender")
        / "generate_bookshelf.py"
    )

    cmd = [
        str(blender_exe),
        "--background",
        "--python",
        str(blender_script),
        "--",
        str(validated_path),
        str(output_dir)
    ]

    typer.echo(
        "Running Blender..."
    )

    subprocess.run(
        cmd,
        check=True
    )

    typer.echo(
        f"DONE → {output_dir}"
    )


if __name__ == "__main__":
    app()
from pathlib import Path
import json

from jsonschema import Draft7Validator


BASE_DIR = Path(__file__).resolve().parent.parent

SCHEMA_PATH = (
    BASE_DIR
    / "schemas"
    / "bookshelf.schema.json"
)


class ValidationError(Exception):
    pass


def load_json(path: Path) -> dict:

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except FileNotFoundError as exc:

        raise ValidationError(
            f"File not found: {path}"
        ) from exc

    except json.JSONDecodeError as exc:

        raise ValidationError(
            f"Invalid JSON in {path}: {exc}"
        ) from exc


def validate_spec(
    spec: dict,
    schema: dict
) -> None:

    validator = Draft7Validator(
        schema
    )

    errors = sorted(
        validator.iter_errors(spec),
        key=lambda error: error.path
    )

    if not errors:
        return

    messages = []

    for error in errors:

        path = ".".join(
            str(part)
            for part in error.path
        )

        if path:
            messages.append(
                f"{path}: {error.message}"
            )

        else:
            messages.append(
                error.message
            )

    raise ValidationError(
        "\n".join(messages)
    )


def validate_file(
    spec_path: Path,
    schema_path: Path = SCHEMA_PATH
) -> dict:

    spec = load_json(spec_path)

    schema = load_json(schema_path)

    validate_spec(spec, schema)

    return spec
from __future__ import annotations

import json
from pathlib import Path

from app.spec_builder import SimpleSpecError, build_visual_spec, is_simple_spec, normalize_request

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = BASE_DIR / "schemas" / "bookshelf.schema.json"

try:
    from jsonschema import Draft7Validator  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    Draft7Validator = None  # type: ignore[assignment]


class ValidationError(Exception):
    pass


def load_json(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8-sig") as file:
            return json.load(file)
    except FileNotFoundError as exc:
        raise ValidationError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON in {path}: {exc}") from exc


def _validate_simple_request(request: dict) -> None:
    outer = request["outer"]
    material = request["material"]
    construction = request["construction"]
    layout = request["layout"]

    width = float(outer["width"])
    height = float(outer["height"])
    depth = float(outer["depth"])
    board_thickness = float(material["board_thickness"])
    back_thickness = float(material["back_thickness"])
    columns = int(construction["columns"])
    openings = list(layout["openings"])

    if width <= 0 or height <= 0 or depth <= 0:
        raise ValidationError("Outer dimensions must be greater than 0")
    if board_thickness <= 0:
        raise ValidationError("material.board_thickness must be greater than 0")
    if back_thickness <= 0:
        raise ValidationError("material.back_thickness must be greater than 0")
    if columns not in {1, 2}:
        raise ValidationError("construction.columns must be 1 or 2")
    if not openings:
        raise ValidationError("At least one opening is required")

    for index, opening in enumerate(openings):
        clear_height = float(opening["clear_height"])
        if clear_height <= 0:
            raise ValidationError(f"layout.openings[{index}].clear_height must be greater than 0")

    internal_clear_height = height - (2.0 * board_thickness)
    internal_clear_width = width - (2.0 * board_thickness) - ((columns - 1) * board_thickness)
    section_width = internal_clear_width / columns
    required_height = sum(float(opening["clear_height"]) for opening in openings) + max(len(openings) - 1, 0) * board_thickness

    if internal_clear_height <= 0:
        raise ValidationError("Outer height is too small for the selected board thickness")
    if internal_clear_width <= 0 or section_width <= 0:
        raise ValidationError("Outer width is too small for the selected board thickness and columns")
    if required_height > internal_clear_height:
        raise ValidationError(
            "Openings do not fit the available inner height. Reduce opening heights or increase outer height."
        )


def _manual_validate_normalized_spec(spec: dict) -> None:
    if spec.get("type") != "bookshelf":
        raise ValidationError("type must be 'bookshelf'")
    if spec.get("units") != "mm":
        raise ValidationError("units must be 'mm'")
    if not spec.get("project_name"):
        raise ValidationError("project_name is required")

    dimensions = spec.get("overall_dimensions", {})
    for key in ("width", "height", "depth"):
        if float(dimensions.get(key, 0)) <= 0:
            raise ValidationError(f"overall_dimensions.{key} must be greater than 0")

    construction = spec.get("construction", {})
    if not construction.get("is_viable", False):
        raise ValidationError("The bookshelf is not viable with the given dimensions and openings")

    zones = spec.get("zones") or []
    if not zones:
        raise ValidationError("zones must contain at least one opening")

    for index, zone in enumerate(zones):
        if float(zone.get("clear_height", 0)) <= 0:
            raise ValidationError(f"zones[{index}].clear_height must be greater than 0")
        if int(zone.get("count", 0)) <= 0:
            raise ValidationError(f"zones[{index}].count must be greater than 0")


def validate_spec(spec: dict, schema: dict | None = None) -> None:
    _manual_validate_normalized_spec(spec)

    if Draft7Validator is None or schema is None:
        return

    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(spec), key=lambda error: list(error.path))
    if not errors:
        return

    messages: list[str] = []
    for error in errors:
        path = ".".join(str(part) for part in error.path)
        messages.append(f"{path}: {error.message}" if path else error.message)
    raise ValidationError("\n".join(messages))


def validate_file(spec_path: Path, schema_path: Path = SCHEMA_PATH) -> dict:
    raw_spec = load_json(spec_path)

    try:
        if is_simple_spec(raw_spec):
            request = normalize_request(raw_spec)
            _validate_simple_request(request)
        spec = build_visual_spec(raw_spec)
    except SimpleSpecError as exc:
        raise ValidationError(str(exc)) from exc

    schema = load_json(schema_path) if schema_path.exists() else None
    validate_spec(spec, schema)
    return spec
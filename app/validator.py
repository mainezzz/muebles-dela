from __future__ import annotations

import json
from pathlib import Path

from app.spec_builder import SimpleSpecError, build_visual_spec


BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = BASE_DIR / "schemas" / "bookshelf.schema.json"

try:
    from jsonschema import Draft7Validator  # type: ignore
except ModuleNotFoundError:
    Draft7Validator = None  # type: ignore[assignment]


class ValidationError(Exception):
    pass


def load_json(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError as exc:
        raise ValidationError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON in {path}: {exc}") from exc


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _require_mapping(name: str, value: object) -> dict:
    if not isinstance(value, dict):
        raise ValidationError(f"{name} must be an object")
    return value


def _require_list(name: str, value: object) -> list:
    if not isinstance(value, list):
        raise ValidationError(f"{name} must be an array")
    return value


def _require_string(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} must be a non-empty string")
    return value


def _require_bool(name: str, value: object) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{name} must be a boolean")
    return value


def _require_number(
    name: str,
    value: object,
    *,
    positive: bool = False,
    non_negative: bool = False,
) -> float:
    if not _is_number(value):
        raise ValidationError(f"{name} must be a number")
    number = float(value)
    if positive and number <= 0:
        raise ValidationError(f"{name} must be greater than 0")
    if non_negative and number < 0:
        raise ValidationError(f"{name} must be greater than or equal to 0")
    return number


def _validate_without_jsonschema(spec: dict) -> None:
    _require_string("project_name", spec.get("project_name"))

    furniture_type = _require_string("type", spec.get("type"))
    if furniture_type != "bookshelf":
        raise ValidationError("type must be 'bookshelf'")

    units = _require_string("units", spec.get("units"))
    if units != "mm":
        raise ValidationError("units must be 'mm'")

    overall_dimensions = _require_mapping("overall_dimensions", spec.get("overall_dimensions"))
    _require_number("overall_dimensions.width", overall_dimensions.get("width"), positive=True)
    _require_number("overall_dimensions.height", overall_dimensions.get("height"), positive=True)
    _require_number("overall_dimensions.depth", overall_dimensions.get("depth"), positive=True)

    structure = _require_mapping("structure", spec.get("structure"))
    _require_number("structure.board_thickness", structure.get("board_thickness"), positive=True)
    for key in ("side_panels", "top_panel", "bottom_panel"):
        if key in structure:
            _require_bool(f"structure.{key}", structure[key])

    dividers = spec.get("dividers")
    if dividers is not None:
        dividers = _require_mapping("dividers", dividers)
        if "center" in dividers:
            _require_bool("dividers.center", dividers["center"])

    zones = _require_list("zones", spec.get("zones"))
    if not zones:
        raise ValidationError("zones must contain at least one entry")

    for index, zone in enumerate(zones):
        zone_name = f"zones[{index}]"
        zone = _require_mapping(zone_name, zone)
        _require_string(f"{zone_name}.type", zone.get("type"))
        count = zone.get("count")
        if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
            raise ValidationError(f"{zone_name}.count must be a positive integer")
        _require_number(f"{zone_name}.clear_height", zone.get("clear_height"), positive=True)

    solver = spec.get("solver")
    if solver is not None:
        solver = _require_mapping("solver", solver)
        if "remaining_distribution" in solver:
            _require_string("solver.remaining_distribution", solver["remaining_distribution"])

    back_panel = spec.get("back_panel")
    if back_panel is not None:
        back_panel = _require_mapping("back_panel", back_panel)
        enabled = _require_bool("back_panel.enabled", back_panel.get("enabled"))
        if "split_vertical_panels" in back_panel:
            _require_bool("back_panel.split_vertical_panels", back_panel["split_vertical_panels"])
        if enabled:
            if "panel_width" in back_panel:
                _require_number("back_panel.panel_width", back_panel["panel_width"], positive=True)
            if "panel_height" in back_panel:
                _require_number("back_panel.panel_height", back_panel["panel_height"], positive=True)
            if "thickness" in back_panel:
                _require_number("back_panel.thickness", back_panel["thickness"], positive=True)

    visualization = spec.get("visualization")
    if visualization is not None:
        visualization = _require_mapping("visualization", visualization)
        if "add_dvds" in visualization:
            _require_bool("visualization.add_dvds", visualization["add_dvds"])
        if "add_books" in visualization:
            _require_bool("visualization.add_books", visualization["add_books"])
        if "gap" in visualization:
            _require_number("visualization.gap", visualization["gap"], non_negative=True)
        for key in (
            "book_small_width",
            "book_small_height",
            "book_small_depth",
            "book_large_width",
            "book_large_height",
            "book_large_depth",
        ):
            if key in visualization:
                _require_number(f"visualization.{key}", visualization[key], positive=True)


def validate_spec(spec: dict, schema: dict | None = None) -> None:
    if Draft7Validator is None:
        _validate_without_jsonschema(spec)
        return

    if schema is None:
        schema = load_json(SCHEMA_PATH)

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
        spec = build_visual_spec(raw_spec)
    except SimpleSpecError as exc:
        raise ValidationError(str(exc)) from exc

    schema = load_json(schema_path) if schema_path.exists() else None
    validate_spec(spec, schema)
    return spec
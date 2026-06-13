from __future__ import annotations

from copy import deepcopy

from app.presets import list_opening_heights, resolve_preset


class SimpleSpecError(ValueError):
    pass


def is_simple_spec(spec: dict) -> bool:
    return "preset" in spec or (
        "width" in spec and "height" in spec and "depth" in spec and "type" not in spec
    )


def _legacy_project_name(spec: dict) -> str:
    return str(spec.get("project_name") or "bookshelf")


def _flatten_zone_heights(zones: list[dict]) -> list[float]:
    return list_opening_heights(zones)


def infer_pattern_from_zones(zones: list[dict]) -> str | None:
    heights = _flatten_zone_heights(zones)
    if heights == [249.0, 210.0, 210.0, 249.0, 249.0, 211.0, 211.0, 249.0]:
        return "4_4"
    if heights == [256.0, 214.0, 214.0, 256.0, 214.0, 214.0, 214.0, 256.0]:
        return "5_3"
    return None


def build_visual_spec(raw_spec: dict) -> dict:
    if not is_simple_spec(raw_spec):
        return deepcopy(raw_spec)

    preset_name = str(raw_spec.get("preset") or "").strip().lower()
    if not preset_name:
        raise SimpleSpecError("Missing required field: preset")

    preset = resolve_preset(preset_name, raw_spec.get("pattern"))
    defaults = preset["defaults"]

    width = float(raw_spec.get("width", defaults["width"]))
    height = float(raw_spec.get("height", defaults["height"]))
    depth = float(raw_spec.get("depth", defaults["depth"]))
    board_thickness = float(raw_spec.get("board_thickness", defaults["board_thickness"]))
    back_enabled = bool(raw_spec.get("back_panel", defaults["back_panel"]))
    back_thickness = float(raw_spec.get("back_thickness", defaults["back_thickness"]))
    render_contents = bool(raw_spec.get("render_contents", defaults["render_contents"]))
    gap = float(raw_spec.get("gap", defaults["gap"]))

    project_name = str(raw_spec.get("project_name") or preset["project_name"])
    visualization = deepcopy(preset["visualization"])
    visualization[visualization.pop("content_key")] = render_contents
    visualization["gap"] = gap

    return {
        "project_name": project_name,
        "preset": preset_name,
        "pattern": preset.get("pattern"),
        "type": "bookshelf",
        "units": "mm",
        "overall_dimensions": {
            "width": width,
            "height": height,
            "depth": depth,
        },
        "structure": {
            "board_thickness": board_thickness,
            "side_panels": True,
            "top_panel": True,
            "bottom_panel": True,
        },
        "dividers": {
            "center": True,
        },
        "zones": deepcopy(preset["zones"]),
        "solver": deepcopy(preset["solver"]),
        "back_panel": {
            "enabled": back_enabled,
            "split_vertical_panels": True,
            "panel_width": width / 2.0,
            "panel_height": height,
            "thickness": back_thickness,
        },
        "visualization": visualization,
    }


def extract_fabrication_request(spec: dict) -> dict:
    if is_simple_spec(spec):
        visual_spec = build_visual_spec(spec)
        preset_name = visual_spec["preset"]
        pattern = visual_spec.get("pattern")
    else:
        visual_spec = deepcopy(spec)
        zones = visual_spec.get("zones", [])
        zone_types = {zone.get("type") for zone in zones}
        if {"dvds", "dvd_boxsets"} & zone_types:
            preset_name = "dvd"
            pattern = None
        else:
            preset_name = "libros"
            pattern = infer_pattern_from_zones(zones)
        if preset_name == "libros" and pattern is None:
            raise SimpleSpecError(
                "Could not infer book pattern from legacy spec. Use a simple spec or add a supported opening layout."
            )

    preset = resolve_preset(preset_name, pattern)
    defaults = preset["defaults"]

    width = float(visual_spec["overall_dimensions"]["width"])
    height = float(visual_spec["overall_dimensions"]["height"])
    depth = float(visual_spec["overall_dimensions"]["depth"])
    board_thickness = float(visual_spec["structure"]["board_thickness"])
    back_panel = bool(visual_spec.get("back_panel", {}).get("enabled", defaults["back_panel"]))
    back_thickness = float(visual_spec.get("back_panel", {}).get("thickness", defaults["back_thickness"]))

    return {
        "project_name": str(visual_spec["project_name"]),
        "preset": preset_name,
        "pattern": pattern,
        "type": preset["type"],
        "width": width,
        "height": height,
        "depth": depth,
        "board_thickness": board_thickness,
        "back_panel": back_panel,
        "back_thickness": back_thickness,
        "internal_horizontal": float(preset["fabrication"]["internal_horizontal"]),
        "fabrication_depth": max(depth - float(preset["fabrication"]["depth_adjustment"]), 0.0),
        "variant": preset["fabrication"]["variant"],
        "opening_heights": list_opening_heights(visual_spec["zones"]),
    }


def prepare_specs(raw_spec: dict) -> tuple[dict, dict]:
    visual_spec = build_visual_spec(raw_spec)
    fabrication_request = extract_fabrication_request(visual_spec)
    return visual_spec, fabrication_request

from __future__ import annotations

from copy import deepcopy
from typing import Iterable

from app.presets import (
    get_visualization_defaults,
    list_opening_heights,
    normalize_content_type,
    normalize_layout_mode,
    normalize_opening_kind,
    normalize_remaining_distribution,
    normalize_shell_mode,
    resolve_example_preset,
)


class SimpleSpecError(ValueError):
    pass


def is_simple_spec(spec: dict) -> bool:
    if "type" in spec and spec.get("type") == "bookshelf":
        return False
    return any(
        key in spec
        for key in (
            "preset",
            "content_type",
            "outer",
            "layout",
            "width",
            "height",
            "depth",
        )
    )


def _as_float(name: str, value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise SimpleSpecError(f"{name} must be a number") from exc
    return number


def _expand_counted_groups(content_type: str, groups: list[dict]) -> list[dict]:
    openings: list[dict] = []
    for index, group in enumerate(groups):
        kind = normalize_opening_kind(content_type, str(group.get("kind") or group.get("type") or ""))
        clear_height = _as_float(f"opening_groups[{index}].clear_height", group.get("clear_height"))
        count = int(group.get("count", 1))
        if count <= 0:
            raise SimpleSpecError(f"opening_groups[{index}].count must be greater than 0")
        for _ in range(count):
            openings.append({"type": kind, "clear_height": clear_height})
    return openings


def _normalize_manual_openings(content_type: str, openings: list[object]) -> list[dict]:
    normalized: list[dict] = []
    for index, opening in enumerate(openings):
        if isinstance(opening, (int, float)) and not isinstance(opening, bool):
            kind = "dvd" if content_type == "dvd" else "books_standard"
            normalized.append({"type": kind, "clear_height": float(opening)})
            continue
        if not isinstance(opening, dict):
            raise SimpleSpecError(f"openings[{index}] must be a number or object")
        kind = normalize_opening_kind(
            content_type,
            str(opening.get("kind") or opening.get("type") or ("dvd" if content_type == "dvd" else "books_standard")),
        )
        clear_height = _as_float(f"openings[{index}].clear_height", opening.get("clear_height"))
        count = int(opening.get("count", 1))
        if count <= 0:
            raise SimpleSpecError(f"openings[{index}].count must be greater than 0")
        for _ in range(count):
            normalized.append({"type": kind, "clear_height": clear_height})
    return normalized


def _build_symmetric_layout(openings: list[dict]) -> list[dict]:
    if not openings:
        return []
    sorted_openings = sorted(
        [dict(item) for item in openings],
        key=lambda item: (float(item["clear_height"]), item["type"]),
        reverse=True,
    )
    arranged: list[dict | None] = [None] * len(sorted_openings)
    left = 0
    right = len(sorted_openings) - 1
    for item in sorted_openings:
        arranged[left] = dict(item)
        if left != right:
            arranged[right] = dict(item)
            if len([slot for slot in arranged if slot is not None]) > len(sorted_openings):
                break
        left += 1
        right -= 1
        if left > right:
            break

    # fill possible None values with remaining sorted items in stable order
    remaining = [dict(item) for item in sorted_openings]
    for value in arranged:
        if value is not None and value in remaining:
            remaining.remove(value)
    for index, value in enumerate(arranged):
        if value is None:
            arranged[index] = remaining.pop(0)
    return [dict(item) for item in arranged if item is not None]



def _arrange_openings(openings: list[dict], layout_mode: str) -> list[dict]:
    arranged = [dict(item) for item in openings]
    if layout_mode == "manual":
        return arranged
    if layout_mode == "large_top":
        return sorted(arranged, key=lambda item: (float(item["clear_height"]), item["type"]), reverse=True)
    if layout_mode == "large_bottom":
        return sorted(arranged, key=lambda item: (float(item["clear_height"]), item["type"]))
    if layout_mode == "symmetric":
        sorted_items = sorted(arranged, key=lambda item: (float(item["clear_height"]), item["type"]), reverse=True)
        result: list[dict | None] = [None] * len(sorted_items)
        left = 0
        right = len(sorted_items) - 1
        index = 0
        while left <= right and index < len(sorted_items):
            result[left] = dict(sorted_items[index])
            index += 1
            if left == right:
                break
            result[right] = dict(sorted_items[index])
            index += 1
            left += 1
            right -= 1
        return [dict(item) for item in result if item is not None]
    raise SimpleSpecError(f"Unsupported distribution_mode: {layout_mode}")


def _zones_from_openings(openings: list[dict]) -> list[dict]:
    return [{"type": item["type"], "count": 1, "clear_height": float(item["clear_height"])} for item in openings]


def _convert_preset_request(raw_spec: dict) -> dict:
    preset = resolve_example_preset(str(raw_spec.get("preset") or ""), raw_spec.get("pattern"))
    merged = deepcopy(preset)

    for key in ("project_name", "content_type", "outer", "material", "construction", "layout", "visualization"):
        if key in raw_spec:
            if isinstance(merged.get(key), dict) and isinstance(raw_spec.get(key), dict):
                merged[key].update(deepcopy(raw_spec[key]))
            else:
                merged[key] = deepcopy(raw_spec[key])

    # convenient top-level overrides
    outer = merged.setdefault("outer", {})
    material = merged.setdefault("material", {})
    construction = merged.setdefault("construction", {})
    visualization = merged.setdefault("visualization", {})
    layout = merged.setdefault("layout", {})

    for field in ("width", "height", "depth"):
        if field in raw_spec:
            outer[field] = raw_spec[field]
    if "board_thickness" in raw_spec:
        material["board_thickness"] = raw_spec["board_thickness"]
    if "back_thickness" in raw_spec:
        material["back_thickness"] = raw_spec["back_thickness"]
    if "shell_mode" in raw_spec:
        construction["shell_mode"] = raw_spec["shell_mode"]
    if "columns" in raw_spec:
        construction["columns"] = raw_spec["columns"]
    if "back_panel" in raw_spec:
        construction["back_panel"] = raw_spec["back_panel"]
    if "render_contents" in raw_spec:
        visualization["fill_contents"] = raw_spec["render_contents"]
    if "gap" in raw_spec:
        visualization["gap"] = raw_spec["gap"]
    if "distribution_mode" in raw_spec:
        layout["distribution_mode"] = raw_spec["distribution_mode"]
    if "remaining_distribution" in raw_spec:
        layout["remaining_distribution"] = raw_spec["remaining_distribution"]
    if "opening_groups" in raw_spec:
        layout["opening_groups"] = deepcopy(raw_spec["opening_groups"])
    if "openings" in raw_spec:
        layout["openings"] = deepcopy(raw_spec["openings"])

    return merged


def normalize_request(raw_spec: dict) -> dict:
    if "preset" in raw_spec:
        raw_spec = _convert_preset_request(raw_spec)

    if not isinstance(raw_spec, dict):
        raise SimpleSpecError("Specification must be a JSON object")

    project_name = str(raw_spec.get("project_name") or "bookshelf").strip()
    if not project_name:
        raise SimpleSpecError("project_name must be a non-empty string")

    content_type = normalize_content_type(str(raw_spec.get("content_type") or raw_spec.get("collection_type") or "books"))

    outer_source = dict(raw_spec.get("outer") or {})
    material_source = dict(raw_spec.get("material") or {})
    construction_source = dict(raw_spec.get("construction") or {})
    layout_source = dict(raw_spec.get("layout") or {})
    visualization_source = dict(raw_spec.get("visualization") or {})

    for field in ("width", "height", "depth"):
        if field in raw_spec and field not in outer_source:
            outer_source[field] = raw_spec[field]

    if "board_thickness" in raw_spec and "board_thickness" not in material_source:
        material_source["board_thickness"] = raw_spec["board_thickness"]
    if "back_thickness" in raw_spec and "back_thickness" not in material_source:
        material_source["back_thickness"] = raw_spec["back_thickness"]

    if "shell_mode" in raw_spec and "shell_mode" not in construction_source:
        construction_source["shell_mode"] = raw_spec["shell_mode"]
    if "columns" in raw_spec and "columns" not in construction_source:
        construction_source["columns"] = raw_spec["columns"]
    if "back_panel" in raw_spec and "back_panel" not in construction_source:
        construction_source["back_panel"] = raw_spec["back_panel"]

    if "distribution_mode" in raw_spec and "distribution_mode" not in layout_source:
        layout_source["distribution_mode"] = raw_spec["distribution_mode"]
    if "remaining_distribution" in raw_spec and "remaining_distribution" not in layout_source:
        layout_source["remaining_distribution"] = raw_spec["remaining_distribution"]
    if "opening_groups" in raw_spec and "opening_groups" not in layout_source:
        layout_source["opening_groups"] = deepcopy(raw_spec["opening_groups"])
    if "openings" in raw_spec and "openings" not in layout_source:
        layout_source["openings"] = deepcopy(raw_spec["openings"])

    if "render_contents" in raw_spec and "fill_contents" not in visualization_source:
        visualization_source["fill_contents"] = raw_spec["render_contents"]
    if "gap" in raw_spec and "gap" not in visualization_source:
        visualization_source["gap"] = raw_spec["gap"]

    width = _as_float("outer.width", outer_source.get("width"))
    height = _as_float("outer.height", outer_source.get("height"))
    depth = _as_float("outer.depth", outer_source.get("depth"))
    board_thickness = _as_float("material.board_thickness", material_source.get("board_thickness", 18.0))
    back_thickness = _as_float("material.back_thickness", material_source.get("back_thickness", 5.0))

    shell_mode = normalize_shell_mode(construction_source.get("shell_mode"))
    columns = int(construction_source.get("columns", 2))
    back_panel = bool(construction_source.get("back_panel", True))

    layout_mode = normalize_layout_mode(layout_source.get("distribution_mode"))
    remaining_distribution = normalize_remaining_distribution(layout_source.get("remaining_distribution"), content_type)

    openings: list[dict]
    if "openings" in layout_source:
        openings = _normalize_manual_openings(content_type, list(layout_source["openings"]))
    elif "opening_groups" in layout_source:
        openings = _expand_counted_groups(content_type, list(layout_source["opening_groups"]))
    else:
        raise SimpleSpecError("layout.openings or layout.opening_groups is required")

    openings = _arrange_openings(openings, layout_mode)

    visualization_defaults = get_visualization_defaults(content_type)
    visualization = {
        **visualization_defaults,
        **deepcopy(visualization_source),
    }
    visualization["fill_contents"] = bool(visualization.get("fill_contents", True))
    visualization["gap"] = float(visualization.get("gap", visualization_defaults.get("gap", 2.0)))
    visualization["views"] = list(visualization.get("views") or ["client", "carpentry"])

    return {
        "project_name": project_name,
        "content_type": content_type,
        "outer": {
            "width": width,
            "height": height,
            "depth": depth,
        },
        "material": {
            "board_thickness": board_thickness,
            "back_thickness": back_thickness,
        },
        "construction": {
            "shell_mode": shell_mode,
            "columns": columns,
            "back_panel": back_panel,
        },
        "layout": {
            "distribution_mode": layout_mode,
            "remaining_distribution": remaining_distribution,
            "openings": openings,
        },
        "visualization": visualization,
    }


def compute_geometry(request: dict) -> dict:
    outer = request["outer"]
    material = request["material"]
    construction = request["construction"]
    openings = request["layout"]["openings"]

    width = float(outer["width"])
    height = float(outer["height"])
    depth = float(outer["depth"])
    board_thickness = float(material["board_thickness"])
    columns = int(construction["columns"])
    shell_mode = str(construction["shell_mode"])

    divider_count = max(columns - 1, 0)
    internal_clear_width = width - (2.0 * board_thickness) - (divider_count * board_thickness)
    internal_clear_height = height - (2.0 * board_thickness)
    section_width = internal_clear_width / columns if columns else 0.0
    shelf_count = max(len(openings) - 1, 0)
    required_opening_height = sum(float(item["clear_height"]) for item in openings)
    required_internal_height = required_opening_height + (shelf_count * board_thickness)
    remaining_height = internal_clear_height - required_internal_height

    if shell_mode == "sides_outside":
        side_height = height
        horizontal_length = width - (2.0 * board_thickness)
    elif shell_mode == "top_bottom_outside":
        side_height = height - (2.0 * board_thickness)
        horizontal_length = width
    else:  # pragma: no cover
        raise SimpleSpecError(f"Unsupported shell_mode '{shell_mode}'")

    divider_height = max(height - (2.0 * board_thickness), 0.0)
    back_panel_width = width / columns if construction["back_panel"] and columns > 1 else width

    return {
        "outer_width": width,
        "outer_height": height,
        "outer_depth": depth,
        "board_thickness": board_thickness,
        "columns": columns,
        "divider_count": divider_count,
        "internal_clear_width": internal_clear_width,
        "internal_clear_height": internal_clear_height,
        "section_width": section_width,
        "shelf_count": shelf_count,
        "required_opening_height": required_opening_height,
        "required_internal_height": required_internal_height,
        "remaining_height": remaining_height,
        "side_height": side_height,
        "horizontal_length": horizontal_length,
        "divider_height": divider_height,
        "back_panel_width": back_panel_width,
        "is_viable": internal_clear_width > 0 and section_width > 0 and remaining_height >= 0,
    }


def _build_visualization_payload(request: dict) -> dict:
    visualization = deepcopy(request["visualization"])
    fill_contents = bool(visualization.pop("fill_contents", True))
    content_type = request["content_type"]

    payload = deepcopy(visualization)
    payload["add_dvds"] = content_type == "dvd" and fill_contents
    payload["add_books"] = content_type == "books" and fill_contents
    return payload


def build_visual_spec(raw_spec: dict) -> dict:
    if not is_simple_spec(raw_spec):
        return deepcopy(raw_spec)

    request = normalize_request(raw_spec)
    geometry = compute_geometry(request)
    openings = request["layout"]["openings"]

    return {
        "project_name": request["project_name"],
        "type": "bookshelf",
        "units": "mm",
        "content_type": request["content_type"],
        "overall_dimensions": {
            "width": request["outer"]["width"],
            "height": request["outer"]["height"],
            "depth": request["outer"]["depth"],
        },
        "material": deepcopy(request["material"]),
        "structure": {
            "board_thickness": request["material"]["board_thickness"],
            "side_panels": True,
            "top_panel": True,
            "bottom_panel": True,
        },
        "construction": {
            "shell_mode": request["construction"]["shell_mode"],
            "columns": request["construction"]["columns"],
            "back_panel": request["construction"]["back_panel"],
            **geometry,
        },
        "dividers": {
            "center": request["construction"]["columns"] == 2,
            "count": max(request["construction"]["columns"] - 1, 0),
        },
        "zones": _zones_from_openings(openings),
        "openings": deepcopy(openings),
        "solver": {
            "remaining_distribution": request["layout"]["remaining_distribution"],
        },
        "back_panel": {
            "enabled": request["construction"]["back_panel"],
            "split_vertical_panels": request["construction"]["columns"] > 1,
            "panel_width": geometry["back_panel_width"],
            "panel_height": request["outer"]["height"],
            "thickness": request["material"]["back_thickness"],
        },
        "visualization": _build_visualization_payload(request),
    }


def infer_pattern_from_zones(zones: list[dict]) -> str | None:
    heights = list_opening_heights(zones)
    if heights == [249.0, 210.0, 210.0, 249.0, 249.0, 211.0, 211.0, 249.0]:
        return "4_4"
    if heights == [256.0, 214.0, 214.0, 256.0, 214.0, 214.0, 214.0, 256.0]:
        return "5_3"
    return None


def extract_fabrication_request(spec: dict) -> dict:
    visual_spec = build_visual_spec(spec) if is_simple_spec(spec) else deepcopy(spec)
    construction = visual_spec["construction"]
    material = visual_spec["material"]
    dimensions = visual_spec["overall_dimensions"]
    openings = deepcopy(visual_spec.get("openings") or _zones_from_openings(visual_spec["zones"]))

    return {
        "project_name": visual_spec["project_name"],
        "type": "dvd_shelf" if visual_spec["content_type"] == "dvd" else "book_shelf",
        "content_type": visual_spec["content_type"],
        "shell_mode": construction["shell_mode"],
        "columns": int(construction["columns"]),
        "outer_width": float(dimensions["width"]),
        "height": float(dimensions["height"]),
        "depth": float(dimensions["depth"]),
        "fabrication_depth": float(dimensions["depth"]),
        "board_thickness": float(material["board_thickness"]),
        "back_panel": bool(visual_spec["back_panel"]["enabled"]),
        "back_thickness": float(visual_spec["back_panel"]["thickness"]),
        "horizontal_length": float(construction["horizontal_length"]),
        "side_height": float(construction["side_height"]),
        "divider_height": float(construction["divider_height"]),
        "section_width": float(construction["section_width"]),
        "back_panel_width": float(visual_spec["back_panel"]["panel_width"]),
        "opening_heights": [float(item["clear_height"]) for item in openings],
        "openings": openings,
        "remaining_distribution": str(visual_spec.get("solver", {}).get("remaining_distribution", "none")),
    }


def prepare_specs(raw_spec: dict) -> tuple[dict, dict]:
    visual_spec = build_visual_spec(raw_spec)
    fabrication_request = extract_fabrication_request(visual_spec)
    return visual_spec, fabrication_request

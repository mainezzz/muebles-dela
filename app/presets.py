from __future__ import annotations

from copy import deepcopy


DVD_ZONES = [
    {"type": "dvd_boxsets", "count": 1, "clear_height": 255},
    {"type": "dvds", "count": 6, "clear_height": 205},
    {"type": "dvd_boxsets", "count": 1, "clear_height": 255},
]

BOOKS_4_4_ZONES = [
    {"type": "books_large", "count": 1, "clear_height": 249},
    {"type": "books_small", "count": 2, "clear_height": 210},
    {"type": "books_large", "count": 2, "clear_height": 249},
    {"type": "books_small", "count": 2, "clear_height": 211},
    {"type": "books_large", "count": 1, "clear_height": 249},
]

BOOKS_5_3_ZONES = [
    {"type": "books_large", "count": 1, "clear_height": 256},
    {"type": "books_small", "count": 2, "clear_height": 214},
    {"type": "books_large", "count": 1, "clear_height": 256},
    {"type": "books_small", "count": 3, "clear_height": 214},
    {"type": "books_large", "count": 1, "clear_height": 256},
]

BOOKS_VISUALIZATION = {
    "book_small_width": 20,
    "book_small_height": 200,
    "book_small_depth": 140,
    "book_large_width": 24,
    "book_large_height": 240,
    "book_large_depth": 170,
    "gap": 2,
}

PRESETS = {
    "dvd": {
        "project_name": "dvd",
        "defaults": {
            "width": 2036,
            "height": 2000,
            "depth": 200,
            "board_thickness": 18,
            "back_panel": True,
            "back_thickness": 5,
            "render_contents": True,
            "gap": 2,
        },
        "type": "dvd_shelf",
        "zones": DVD_ZONES,
        "solver": {"remaining_distribution": "top_bottom_large"},
        "visualization": {"content_key": "add_dvds"},
        "fabrication": {
            "variant": "dvd",
            "internal_horizontal": 2000,
            "depth_adjustment": 0.0,
        },
    },
    "libros": {
        "project_name": "libros",
        "defaults": {
            "width": 1636,
            "height": 2000,
            "depth": 300,
            "board_thickness": 18,
            "back_panel": True,
            "back_thickness": 5,
            "render_contents": True,
            "gap": 2,
        },
        "type": "book_shelf",
        "solver": {"remaining_distribution": "none"},
        "patterns": {
            "4_4": {
                "project_suffix": "4_4",
                "zones": BOOKS_4_4_ZONES,
                "visualization": {"content_key": "add_books", **BOOKS_VISUALIZATION},
                "fabrication": {
                    "variant": "4_4_160",
                    "internal_horizontal": 1600.0,
                    "depth_adjustment": 1.5,
                },
            },
            "5_3": {
                "project_suffix": "5_3",
                "zones": BOOKS_5_3_ZONES,
                "visualization": {"content_key": "add_books", **BOOKS_VISUALIZATION},
                "fabrication": {
                    "variant": "5_3_160",
                    "internal_horizontal": 1600.0,
                    "depth_adjustment": 1.5,
                },
            },
        },
    },
}


def list_opening_heights(zones: list[dict]) -> list[float]:
    heights: list[float] = []
    for zone in zones:
        heights.extend([float(zone["clear_height"])] * int(zone["count"]))
    return heights


def _clone(data):
    return deepcopy(data)


def resolve_preset(preset: str, pattern: str | None = None) -> dict:
    key = preset.strip().lower()
    if key not in PRESETS:
        raise ValueError(f"Unsupported preset: {preset}")

    preset_data = _clone(PRESETS[key])
    if key != "libros":
        return preset_data

    resolved_pattern = (pattern or "4_4").strip().lower()
    patterns = preset_data.pop("patterns")
    if resolved_pattern not in patterns:
        raise ValueError(
            f"Unsupported pattern '{pattern}'. Valid options: {', '.join(sorted(patterns))}"
        )

    pattern_data = _clone(patterns[resolved_pattern])
    preset_data["pattern"] = resolved_pattern
    preset_data["project_name"] = f"{preset_data['project_name']}_{resolved_pattern}"
    preset_data["zones"] = pattern_data["zones"]
    preset_data["visualization"] = pattern_data["visualization"]
    preset_data["fabrication"] = pattern_data["fabrication"]
    preset_data["project_suffix"] = pattern_data["project_suffix"]
    return preset_data

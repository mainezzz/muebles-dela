from __future__ import annotations

from copy import deepcopy


SHELL_MODES = {"sides_outside", "top_bottom_outside"}
LAYOUT_MODES = {"manual", "symmetric", "large_top", "large_bottom"}
REMAINING_DISTRIBUTIONS = {"none", "uniform", "top_bottom_large", "large_openings"}

CONTENT_TYPES = {
    "dvd": {
        "aliases": {"dvd", "dvds", "movie", "movies"},
        "default_depth": 190.0,
        "default_views": ["client", "carpentry"],
        "default_remaining_distribution": "top_bottom_large",
        "visualization": {
            "gap": 2.0,
            "item_defaults": {
                "dvd": {"width": 14.0, "height": 190.0, "depth": 135.0},
                "dvd_boxset": {"width": 28.0, "height": 190.0, "depth": 135.0},
            },
        },
        "opening_aliases": {
            "dvd": "dvd",
            "dvds": "dvd",
            "small": "dvd",
            "standard": "dvd",
            "dvd_boxset": "dvd_boxset",
            "dvd_boxsets": "dvd_boxset",
            "boxset": "dvd_boxset",
            "large": "dvd_boxset",
        },
    },
    "books": {
        "aliases": {"books", "book", "libros", "bookshelf"},
        "default_depth": 280.0,
        "default_views": ["client", "carpentry"],
        "default_remaining_distribution": "large_openings",
        "visualization": {
            "gap": 2.0,
            "book_small_width": 20.0,
            "book_small_height": 200.0,
            "book_small_depth": 140.0,
            "book_large_width": 24.0,
            "book_large_height": 240.0,
            "book_large_depth": 170.0,
            "item_defaults": {
                "books_small": {"width": 20.0, "height": 200.0, "depth": 140.0},
                "books_large": {"width": 24.0, "height": 240.0, "depth": 170.0},
                "books_standard": {"width": 22.0, "height": 220.0, "depth": 155.0},
            },
        },
        "opening_aliases": {
            "small": "books_small",
            "books_small": "books_small",
            "paperback": "books_small",
            "standard": "books_standard",
            "books_standard": "books_standard",
            "large": "books_large",
            "books_large": "books_large",
            "hardcover": "books_large",
        },
    },
}

PRESET_EXAMPLES = {
    "dvd": {
        "project_name": "dvd_1960",
        "content_type": "dvd",
        "outer": {"width": 1200.0, "height": 2000.0, "depth": 190.0},
        "material": {"board_thickness": 18.0, "back_thickness": 5.0},
        "construction": {"shell_mode": "sides_outside", "columns": 2, "back_panel": True},
        "layout": {
            "distribution_mode": "symmetric",
            "remaining_distribution": "top_bottom_large",
            "opening_groups": [
                {"kind": "dvd_boxset", "clear_height": 255.0, "count": 2},
                {"kind": "dvd", "clear_height": 205.0, "count": 6},
            ],
        },
        "visualization": {"fill_contents": True, "gap": 2.0, "views": ["client", "carpentry"]},
    },
    "libros_4_4": {
        "project_name": "libros_4_4",
        "content_type": "books",
        "outer": {"width": 1600.0, "height": 2000.0, "depth": 280.0},
        "material": {"board_thickness": 18.0, "back_thickness": 5.0},
        "construction": {"shell_mode": "sides_outside", "columns": 2, "back_panel": True},
        "layout": {
            "distribution_mode": "manual",
            "remaining_distribution": "large_openings",
            "openings": [
                {"kind": "books_large", "clear_height": 249.0},
                {"kind": "books_small", "clear_height": 210.0},
                {"kind": "books_small", "clear_height": 210.0},
                {"kind": "books_large", "clear_height": 249.0},
                {"kind": "books_large", "clear_height": 249.0},
                {"kind": "books_small", "clear_height": 211.0},
                {"kind": "books_small", "clear_height": 211.0},
                {"kind": "books_large", "clear_height": 249.0},
            ],
        },
        "visualization": {"fill_contents": True, "gap": 2.0, "views": ["client", "carpentry"]},
    },
    "libros_5_3": {
        "project_name": "libros_5_3",
        "content_type": "books",
        "outer": {"width": 1600.0, "height": 2000.0, "depth": 280.0},
        "material": {"board_thickness": 18.0, "back_thickness": 5.0},
        "construction": {"shell_mode": "sides_outside", "columns": 2, "back_panel": True},
        "layout": {
            "distribution_mode": "manual",
            "remaining_distribution": "large_openings",
            "openings": [
                {"kind": "books_large", "clear_height": 256.0},
                {"kind": "books_small", "clear_height": 214.0},
                {"kind": "books_small", "clear_height": 214.0},
                {"kind": "books_large", "clear_height": 256.0},
                {"kind": "books_small", "clear_height": 214.0},
                {"kind": "books_small", "clear_height": 214.0},
                {"kind": "books_small", "clear_height": 214.0},
                {"kind": "books_large", "clear_height": 256.0},
            ],
        },
        "visualization": {"fill_contents": True, "gap": 2.0, "views": ["client", "carpentry"]},
    },
}


def _clone(data):
    return deepcopy(data)


def normalize_content_type(value: str) -> str:
    key = value.strip().lower()
    for canonical, data in CONTENT_TYPES.items():
        if key == canonical or key in data["aliases"]:
            return canonical
    raise ValueError(f"Unsupported content_type: {value}")


def normalize_shell_mode(value: str | None) -> str:
    if value is None:
        return "sides_outside"
    key = value.strip().lower()
    if key not in SHELL_MODES:
        raise ValueError(f"Unsupported shell_mode '{value}'. Valid options: {', '.join(sorted(SHELL_MODES))}")
    return key


def normalize_layout_mode(value: str | None) -> str:
    if value is None:
        return "manual"
    key = value.strip().lower()
    if key not in LAYOUT_MODES:
        raise ValueError(f"Unsupported distribution_mode '{value}'. Valid options: {', '.join(sorted(LAYOUT_MODES))}")
    return key


def normalize_remaining_distribution(value: str | None, content_type: str) -> str:
    if value is None:
        return CONTENT_TYPES[content_type]["default_remaining_distribution"]
    key = value.strip().lower()
    if key not in REMAINING_DISTRIBUTIONS:
        raise ValueError(
            f"Unsupported remaining_distribution '{value}'. Valid options: {', '.join(sorted(REMAINING_DISTRIBUTIONS))}"
        )
    return key


def normalize_opening_kind(content_type: str, value: str) -> str:
    aliases = CONTENT_TYPES[content_type]["opening_aliases"]
    key = value.strip().lower()
    if key not in aliases:
        raise ValueError(f"Unsupported opening kind '{value}' for content type '{content_type}'")
    return aliases[key]


def list_opening_heights(zones: list[dict]) -> list[float]:
    heights: list[float] = []
    for zone in zones:
        heights.extend([float(zone["clear_height"])] * int(zone.get("count", 1)))
    return heights


def resolve_example_preset(preset: str, pattern: str | None = None) -> dict:
    key = preset.strip().lower()
    if key == "dvd":
        return _clone(PRESET_EXAMPLES["dvd"])
    if key == "libros":
        pattern_key = (pattern or "4_4").strip().lower()
        if pattern_key not in {"4_4", "5_3"}:
            raise ValueError("Unsupported libros pattern. Valid options: 4_4, 5_3")
        return _clone(PRESET_EXAMPLES[f"libros_{pattern_key}"])
    if key in PRESET_EXAMPLES:
        return _clone(PRESET_EXAMPLES[key])
    raise ValueError(f"Unsupported preset '{preset}'")


def get_visualization_defaults(content_type: str) -> dict:
    return _clone(CONTENT_TYPES[content_type]["visualization"])

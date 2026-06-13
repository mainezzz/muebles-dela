
from __future__ import annotations

import json
from pathlib import Path


OUTPUT_DIR = Path("outputs/kerf_estanteria_libros_4_4_160")
OUTPUT_FILE = OUTPUT_DIR / "kerf_estanteria_libros_4_4_160.json"

KERF_MM = 3.0

INTERNAL_HORIZONTAL = 1600.0
CABINET_HEIGHT = 2000.0
NOMINAL_DEPTH = 300.0
FABRICATION_DEPTH = 298.5

BOARD_THICKNESS = 18.0
BACK_THICKNESS = 5.0

OUTER_WIDTH = INTERNAL_HORIZONTAL + (2 * BOARD_THICKNESS)
DIVIDER_HEIGHT = CABINET_HEIGHT - (2 * BOARD_THICKNESS)
SECTION_WIDTH = (INTERNAL_HORIZONTAL - BOARD_THICKNESS) / 2
BACK_PANEL_WIDTH = OUTER_WIDTH / 2
SHELF_LEVELS = 7

OPENING_HEIGHTS = [
    249.0,
    210.0,
    210.0,
    249.0,
    249.0,
    211.0,
    211.0,
    249.0,
]

PINE_BOARD = {
    "material": "PINE 2000x600x18",
    "width": 600.0,
    "height": 2000.0,
    "thickness": 18.0,
}

BACK_BOARD = {
    "material": "MDF 2440x1220x5",
    "width": 1220.0,
    "height": 2440.0,
    "thickness": 5.0,
}

COLORS = {
    "side": [0.88, 0.24, 0.18],
    "divider": [0.95, 0.58, 0.12],
    "shelf": [0.16, 0.42, 0.82],
    "top_bottom": [0.28, 0.68, 0.30],
    "back": [0.82, 0.82, 0.82],
    "remaining": [0.22, 0.22, 0.22],
    "kerf": [0.02, 0.02, 0.02],
    "pine": [0.78, 0.62, 0.42],
    "mdf": [0.73, 0.72, 0.69],
}


def make_piece(
    name: str,
    semantic: str,
    width: float,
    height: float,
    thickness: float,
) -> dict:
    return {
        "name": name,
        "semantic": semantic,
        "width": width,
        "height": height,
        "thickness": thickness,
        "label": f"{name}\n{height:g}x{width:g}x{thickness:g}",
    }


def make_board(name: str, stock: dict) -> dict:
    return {
        "name": name,
        "material": stock["material"],
        "width": stock["width"],
        "height": stock["height"],
        "thickness": stock["thickness"],
        "pieces": [],
        "cuts": [],
        "remainders": [],
    }


def place_piece(
    board: dict,
    piece: dict,
    x: float,
    y: float,
    width: float | None = None,
    height: float | None = None,
) -> None:
    board["pieces"].append(
        {
            "name": piece["name"],
            "semantic": piece["semantic"],
            "x": x,
            "y": y,
            "width": piece["width"] if width is None else width,
            "height": piece["height"] if height is None else height,
            "thickness": piece["thickness"],
            "label": piece["label"],
        }
    )


def add_vertical_cut(
    board: dict,
    x: float,
    y: float = 0.0,
    height: float | None = None,
) -> None:
    board["cuts"].append(
        {
            "type": "vertical",
            "x": x,
            "y": y,
            "width": KERF_MM,
            "height": board["height"] if height is None else height,
        }
    )


def add_horizontal_cut(
    board: dict,
    x: float,
    y: float,
    width: float,
) -> None:
    board["cuts"].append(
        {
            "type": "horizontal",
            "x": x,
            "y": y,
            "width": width,
            "height": KERF_MM,
        }
    )


def add_remainder(
    board: dict,
    x: float,
    y: float,
    width: float,
    height: float,
) -> None:
    if width <= 0 or height <= 0:
        return

    board["remainders"].append(
        {
            "name": "REMAINING",
            "semantic": "remaining",
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "thickness": board["thickness"],
            "label": f"REMAINING\n{height:g}x{width:g}",
        }
    )


def find_piece(parts: list[dict], name: str) -> dict:
    for item in parts:
        if item["name"] == name:
            return item
    raise ValueError(f"Piece not found: {name}")


def place_two_stacked_shelves_in_column(
    board: dict,
    bottom_piece: dict,
    top_piece: dict,
    x: float,
) -> None:
    place_piece(
        board,
        bottom_piece,
        x,
        0.0,
        width=FABRICATION_DEPTH,
        height=SECTION_WIDTH,
    )

    add_horizontal_cut(
        board,
        x,
        SECTION_WIDTH,
        FABRICATION_DEPTH,
    )

    top_y = SECTION_WIDTH + KERF_MM

    place_piece(
        board,
        top_piece,
        x,
        top_y,
        width=FABRICATION_DEPTH,
        height=SECTION_WIDTH,
    )

    add_horizontal_cut(
        board,
        x,
        top_y + SECTION_WIDTH,
        FABRICATION_DEPTH,
    )

    add_remainder(
        board,
        x,
        top_y + SECTION_WIDTH + KERF_MM,
        FABRICATION_DEPTH,
        PINE_BOARD["height"] - (top_y + SECTION_WIDTH + KERF_MM),
    )


def place_four_shelves_with_full_top_strip(
    board: dict,
    bottom_left: dict,
    bottom_right: dict,
    top_left: dict,
    top_right: dict,
) -> None:
    second_column_x = FABRICATION_DEPTH + KERF_MM

    place_piece(
        board,
        bottom_left,
        0.0,
        0.0,
        width=FABRICATION_DEPTH,
        height=SECTION_WIDTH,
    )
    place_piece(
        board,
        bottom_right,
        second_column_x,
        0.0,
        width=FABRICATION_DEPTH,
        height=SECTION_WIDTH,
    )

    top_row_y = SECTION_WIDTH + KERF_MM

    place_piece(
        board,
        top_left,
        0.0,
        top_row_y,
        width=FABRICATION_DEPTH,
        height=SECTION_WIDTH,
    )
    place_piece(
        board,
        top_right,
        second_column_x,
        top_row_y,
        width=FABRICATION_DEPTH,
        height=SECTION_WIDTH,
    )

    split_height = (SECTION_WIDTH * 2) + KERF_MM

    add_vertical_cut(
        board,
        FABRICATION_DEPTH,
        height=split_height,
    )
    add_horizontal_cut(
        board,
        0.0,
        SECTION_WIDTH,
        PINE_BOARD["width"],
    )
    add_horizontal_cut(
        board,
        0.0,
        top_row_y + SECTION_WIDTH,
        PINE_BOARD["width"],
    )

    add_remainder(
        board,
        0.0,
        top_row_y + SECTION_WIDTH + KERF_MM,
        PINE_BOARD["width"],
        PINE_BOARD["height"] - (top_row_y + SECTION_WIDTH + KERF_MM),
    )


def build_parts() -> list[dict]:
    parts = [
        make_piece("LEFT SIDE", "side", FABRICATION_DEPTH, CABINET_HEIGHT, BOARD_THICKNESS),
        make_piece("RIGHT SIDE", "side", FABRICATION_DEPTH, CABINET_HEIGHT, BOARD_THICKNESS),
        make_piece("CENTER DIVIDER", "divider", FABRICATION_DEPTH, DIVIDER_HEIGHT, BOARD_THICKNESS),
        make_piece("TOP PANEL", "top_bottom", FABRICATION_DEPTH, INTERNAL_HORIZONTAL, BOARD_THICKNESS),
        make_piece("BOTTOM PANEL", "top_bottom", FABRICATION_DEPTH, INTERNAL_HORIZONTAL, BOARD_THICKNESS),
    ]

    for index in range(1, SHELF_LEVELS + 1):
        parts.append(
            make_piece(
                f"SHELF L{index}",
                "shelf",
                FABRICATION_DEPTH,
                SECTION_WIDTH,
                BOARD_THICKNESS,
            )
        )
        parts.append(
            make_piece(
                f"SHELF R{index}",
                "shelf",
                FABRICATION_DEPTH,
                SECTION_WIDTH,
                BOARD_THICKNESS,
            )
        )

    parts.extend(
        [
            make_piece("BACK LEFT", "back", BACK_PANEL_WIDTH, CABINET_HEIGHT, BACK_THICKNESS),
            make_piece("BACK RIGHT", "back", BACK_PANEL_WIDTH, CABINET_HEIGHT, BACK_THICKNESS),
        ]
    )

    return parts


def build_pine_boards(parts: list[dict]) -> list[dict]:
    boards: list[dict] = []

    left_side = find_piece(parts, "LEFT SIDE")
    right_side = find_piece(parts, "RIGHT SIDE")
    center_divider = find_piece(parts, "CENTER DIVIDER")
    top_panel = find_piece(parts, "TOP PANEL")
    bottom_panel = find_piece(parts, "BOTTOM PANEL")

    shelves = [item for item in parts if item["semantic"] == "shelf"]
    second_column_x = FABRICATION_DEPTH + KERF_MM

    board = make_board("PINE BOARD 1", PINE_BOARD)
    place_piece(board, left_side, 0.0, 0.0)
    add_vertical_cut(board, FABRICATION_DEPTH)
    place_piece(board, right_side, second_column_x, 0.0)
    boards.append(board)

    board = make_board("PINE BOARD 2", PINE_BOARD)
    place_piece(board, top_panel, 0.0, 0.0)
    place_piece(board, bottom_panel, second_column_x, 0.0)
    add_vertical_cut(board, FABRICATION_DEPTH, height=INTERNAL_HORIZONTAL)
    add_horizontal_cut(board, 0.0, INTERNAL_HORIZONTAL, PINE_BOARD["width"])
    add_remainder(
        board,
        0.0,
        INTERNAL_HORIZONTAL + KERF_MM,
        PINE_BOARD["width"],
        PINE_BOARD["height"] - INTERNAL_HORIZONTAL - KERF_MM,
    )
    boards.append(board)

    board = make_board("PINE BOARD 3", PINE_BOARD)
    place_piece(board, center_divider, 0.0, 0.0)
    add_horizontal_cut(board, 0.0, DIVIDER_HEIGHT, FABRICATION_DEPTH)
    add_remainder(
        board,
        0.0,
        DIVIDER_HEIGHT + KERF_MM,
        FABRICATION_DEPTH,
        PINE_BOARD["height"] - DIVIDER_HEIGHT - KERF_MM,
    )
    add_vertical_cut(board, FABRICATION_DEPTH)
    place_two_stacked_shelves_in_column(board, shelves[0], shelves[1], second_column_x)
    boards.append(board)

    remaining_shelves = shelves[2:]
    shelf_chunks = [
        remaining_shelves[0:4],
        remaining_shelves[4:8],
        remaining_shelves[8:12],
    ]

    for board_number, chunk in enumerate(shelf_chunks, start=4):
        board = make_board(f"PINE BOARD {board_number}", PINE_BOARD)
        place_four_shelves_with_full_top_strip(
            board,
            chunk[0],
            chunk[1],
            chunk[2],
            chunk[3],
        )
        boards.append(board)

    return boards


def build_back_boards(parts: list[dict]) -> list[dict]:
    boards: list[dict] = []
    back_left = find_piece(parts, "BACK LEFT")
    back_right = find_piece(parts, "BACK RIGHT")

    for index, back_piece in enumerate([back_left, back_right], start=1):
        board = make_board(f"BACK BOARD {index}", BACK_BOARD)
        place_piece(board, back_piece, 0.0, 0.0)
        add_horizontal_cut(board, 0.0, CABINET_HEIGHT, BACK_BOARD["width"])
        add_vertical_cut(board, BACK_PANEL_WIDTH, height=CABINET_HEIGHT)
        add_remainder(
            board,
            0.0,
            CABINET_HEIGHT + KERF_MM,
            BACK_BOARD["width"],
            BACK_BOARD["height"] - CABINET_HEIGHT - KERF_MM,
        )
        add_remainder(
            board,
            BACK_PANEL_WIDTH + KERF_MM,
            0.0,
            BACK_BOARD["width"] - BACK_PANEL_WIDTH - KERF_MM,
            CABINET_HEIGHT,
        )
        boards.append(board)

    return boards


def build_boards(parts: list[dict]) -> list[dict]:
    boards: list[dict] = []
    boards.extend(build_pine_boards(parts))
    boards.extend(build_back_boards(parts))
    return boards


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    parts = build_parts()
    boards = build_boards(parts)

    payload = {
        "project_name": "kerf_estanteria_libros_4_4_160",
        "kerf_mm": KERF_MM,
        "cabinet": {
            "type": "book_shelf",
            "variant": "4_4_160",
            "construction_type": "laterales continuos + horizontales entre laterales + separador central + trasera superpuesta dividida",
            "internal_horizontal": INTERNAL_HORIZONTAL,
            "horizontal_length": INTERNAL_HORIZONTAL,
            "outer_width": OUTER_WIDTH,
            "height": CABINET_HEIGHT,
            "depth": FABRICATION_DEPTH,
            "nominal_depth": NOMINAL_DEPTH,
            "board_thickness": BOARD_THICKNESS,
            "back_thickness": BACK_THICKNESS,
            "divider_height": DIVIDER_HEIGHT,
            "section_width": SECTION_WIDTH,
            "back_panel_width": BACK_PANEL_WIDTH,
            "shelf_levels": SHELF_LEVELS,
            "opening_heights": OPENING_HEIGHTS,
        },
        "colors": COLORS,
        "parts": parts,
        "boards": boards,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            payload,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print(f"DONE -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
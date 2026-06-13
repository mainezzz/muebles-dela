from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path


KERF_MM = 3.0

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
    fabrication_depth: float,
    section_width: float,
) -> None:
    place_piece(
        board,
        bottom_piece,
        x,
        0.0,
        width=fabrication_depth,
        height=section_width,
    )
    add_horizontal_cut(board, x, section_width, fabrication_depth)

    top_y = section_width + KERF_MM

    place_piece(
        board,
        top_piece,
        x,
        top_y,
        width=fabrication_depth,
        height=section_width,
    )
    add_horizontal_cut(board, x, top_y + section_width, fabrication_depth)

    add_remainder(
        board,
        x,
        top_y + section_width + KERF_MM,
        fabrication_depth,
        PINE_BOARD["height"] - (top_y + section_width + KERF_MM),
    )


def place_four_shelves_with_full_top_strip(
    board: dict,
    bottom_left: dict,
    bottom_right: dict,
    top_left: dict,
    top_right: dict,
    fabrication_depth: float,
    section_width: float,
) -> None:
    second_column_x = fabrication_depth + KERF_MM

    place_piece(board, bottom_left, 0.0, 0.0, width=fabrication_depth, height=section_width)
    place_piece(board, bottom_right, second_column_x, 0.0, width=fabrication_depth, height=section_width)

    top_row_y = section_width + KERF_MM

    place_piece(board, top_left, 0.0, top_row_y, width=fabrication_depth, height=section_width)
    place_piece(board, top_right, second_column_x, top_row_y, width=fabrication_depth, height=section_width)

    split_height = (section_width * 2) + KERF_MM

    add_vertical_cut(board, fabrication_depth, height=split_height)
    add_horizontal_cut(board, 0.0, section_width, PINE_BOARD["width"])
    add_horizontal_cut(board, 0.0, top_row_y + section_width, PINE_BOARD["width"])

    add_remainder(
        board,
        0.0,
        top_row_y + section_width + KERF_MM,
        PINE_BOARD["width"],
        PINE_BOARD["height"] - (top_row_y + section_width + KERF_MM),
    )


def build_parts(request: dict) -> list[dict]:
    fabrication_depth = float(request["fabrication_depth"])
    cabinet_height = float(request["height"])
    board_thickness = float(request["board_thickness"])
    back_thickness = float(request["back_thickness"])
    internal_horizontal = float(request["internal_horizontal"])
    divider_height = cabinet_height - (2 * board_thickness)
    section_width = (internal_horizontal - board_thickness) / 2
    shelf_levels = max(len(request["opening_heights"]) - 1, 0)

    parts = [
        make_piece("LEFT SIDE", "side", fabrication_depth, cabinet_height, board_thickness),
        make_piece("RIGHT SIDE", "side", fabrication_depth, cabinet_height, board_thickness),
        make_piece("CENTER DIVIDER", "divider", fabrication_depth, divider_height, board_thickness),
        make_piece("TOP PANEL", "top_bottom", fabrication_depth, internal_horizontal, board_thickness),
        make_piece("BOTTOM PANEL", "top_bottom", fabrication_depth, internal_horizontal, board_thickness),
    ]

    for index in range(1, shelf_levels + 1):
        parts.append(make_piece(f"SHELF L{index}", "shelf", fabrication_depth, section_width, board_thickness))
        parts.append(make_piece(f"SHELF R{index}", "shelf", fabrication_depth, section_width, board_thickness))

    if request["back_panel"]:
        back_panel_width = (internal_horizontal + (2 * board_thickness)) / 2
        parts.extend(
            [
                make_piece("BACK LEFT", "back", back_panel_width, cabinet_height, back_thickness),
                make_piece("BACK RIGHT", "back", back_panel_width, cabinet_height, back_thickness),
            ]
        )

    return parts


def build_pine_boards(parts: list[dict], request: dict) -> list[dict]:
    boards: list[dict] = []
    fabrication_depth = float(request["fabrication_depth"])
    internal_horizontal = float(request["internal_horizontal"])
    cabinet_height = float(request["height"])
    board_thickness = float(request["board_thickness"])
    divider_height = cabinet_height - (2 * board_thickness)
    section_width = (internal_horizontal - board_thickness) / 2
    second_column_x = fabrication_depth + KERF_MM

    left_side = find_piece(parts, "LEFT SIDE")
    right_side = find_piece(parts, "RIGHT SIDE")
    center_divider = find_piece(parts, "CENTER DIVIDER")
    top_panel = find_piece(parts, "TOP PANEL")
    bottom_panel = find_piece(parts, "BOTTOM PANEL")
    shelves = [item for item in parts if item["semantic"] == "shelf"]

    board = make_board("PINE BOARD 1", PINE_BOARD)
    place_piece(board, left_side, 0.0, 0.0)
    add_vertical_cut(board, fabrication_depth)
    place_piece(board, right_side, second_column_x, 0.0)
    boards.append(board)

    board = make_board("PINE BOARD 2", PINE_BOARD)
    place_piece(board, top_panel, 0.0, 0.0)
    place_piece(board, bottom_panel, second_column_x, 0.0)
    add_vertical_cut(board, fabrication_depth, height=internal_horizontal)
    add_horizontal_cut(board, 0.0, internal_horizontal, PINE_BOARD["width"])
    add_remainder(
        board,
        0.0,
        internal_horizontal + KERF_MM,
        PINE_BOARD["width"],
        PINE_BOARD["height"] - internal_horizontal - KERF_MM,
    )
    boards.append(board)

    if not shelves:
        return boards

    board = make_board("PINE BOARD 3", PINE_BOARD)
    place_piece(board, center_divider, 0.0, 0.0)
    add_horizontal_cut(board, 0.0, divider_height, fabrication_depth)
    add_remainder(
        board,
        0.0,
        divider_height + KERF_MM,
        fabrication_depth,
        PINE_BOARD["height"] - divider_height - KERF_MM,
    )
    add_vertical_cut(board, fabrication_depth)
    place_two_stacked_shelves_in_column(
        board,
        shelves[0],
        shelves[1],
        second_column_x,
        fabrication_depth,
        section_width,
    )
    boards.append(board)

    remaining_shelves = shelves[2:]
    for chunk_index, start in enumerate(range(0, len(remaining_shelves), 4), start=4):
        chunk = remaining_shelves[start : start + 4]
        if len(chunk) < 4:
            board = make_board(f"PINE BOARD {chunk_index}", PINE_BOARD)
            y_cursor = 0.0
            for piece in chunk:
                place_piece(board, piece, 0.0, y_cursor, width=fabrication_depth, height=section_width)
                y_cursor += section_width
                add_horizontal_cut(board, 0.0, y_cursor, fabrication_depth)
                y_cursor += KERF_MM
            add_remainder(
                board,
                fabrication_depth + KERF_MM,
                0.0,
                PINE_BOARD["width"] - fabrication_depth - KERF_MM,
                PINE_BOARD["height"],
            )
            boards.append(board)
            continue

        board = make_board(f"PINE BOARD {chunk_index}", PINE_BOARD)
        place_four_shelves_with_full_top_strip(
            board,
            chunk[0],
            chunk[1],
            chunk[2],
            chunk[3],
            fabrication_depth,
            section_width,
        )
        boards.append(board)

    return boards


def build_back_boards(parts: list[dict], request: dict) -> list[dict]:
    if not request["back_panel"]:
        return []

    boards: list[dict] = []
    cabinet_height = float(request["height"])
    board_thickness = float(request["board_thickness"])
    internal_horizontal = float(request["internal_horizontal"])
    back_panel_width = (internal_horizontal + (2 * board_thickness)) / 2

    back_left = find_piece(parts, "BACK LEFT")
    back_right = find_piece(parts, "BACK RIGHT")

    for index, back_piece in enumerate([back_left, back_right], start=1):
        board = make_board(f"BACK BOARD {index}", BACK_BOARD)
        place_piece(board, back_piece, 0.0, 0.0)
        add_horizontal_cut(board, 0.0, cabinet_height, BACK_BOARD["width"])
        add_vertical_cut(board, back_panel_width, height=cabinet_height)
        add_remainder(
            board,
            0.0,
            cabinet_height + KERF_MM,
            BACK_BOARD["width"],
            BACK_BOARD["height"] - cabinet_height - KERF_MM,
        )
        add_remainder(
            board,
            back_panel_width + KERF_MM,
            0.0,
            BACK_BOARD["width"] - back_panel_width - KERF_MM,
            cabinet_height,
        )
        boards.append(board)

    return boards


def build_payload(request: dict) -> dict:
    internal_horizontal = float(request["internal_horizontal"])
    cabinet_height = float(request["height"])
    nominal_depth = float(request["depth"])
    fabrication_depth = float(request["fabrication_depth"])
    board_thickness = float(request["board_thickness"])
    back_thickness = float(request["back_thickness"])
    outer_width = internal_horizontal + (2 * board_thickness)
    divider_height = cabinet_height - (2 * board_thickness)
    section_width = (internal_horizontal - board_thickness) / 2
    back_panel_width = outer_width / 2
    shelf_levels = max(len(request["opening_heights"]) - 1, 0)

    parts = build_parts(request)
    boards = build_pine_boards(parts, request) + build_back_boards(parts, request)

    payload = {
        "project_name": f"kerf_{request['project_name']}",
        "kerf_mm": KERF_MM,
        "cabinet": {
            "type": request["type"],
            "variant": request.get("variant"),
            "construction_type": "laterales continuos + horizontales entre laterales + separador central + trasera superpuesta dividida",
            "internal_horizontal": internal_horizontal,
            "horizontal_length": internal_horizontal,
            "outer_width": outer_width,
            "height": cabinet_height,
            "depth": fabrication_depth,
            "nominal_depth": nominal_depth,
            "board_thickness": board_thickness,
            "back_thickness": back_thickness,
            "divider_height": divider_height,
            "section_width": section_width,
            "back_panel_width": back_panel_width,
            "shelf_levels": shelf_levels,
            "opening_heights": deepcopy(request["opening_heights"]),
        },
        "colors": deepcopy(COLORS),
        "parts": parts,
        "boards": boards,
    }
    return payload


def write_payload(payload: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)
    return output_path


def build_and_write(request: dict, output_dir: Path, filename: str = "fabrication.json") -> Path:
    payload = build_payload(request)
    return write_payload(payload, output_dir / filename)

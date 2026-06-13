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


def make_piece(name: str, semantic: str, width: float, height: float, thickness: float) -> dict:
    return {
        "name": name,
        "semantic": semantic,
        "width": float(width),
        "height": float(height),
        "thickness": float(thickness),
        "label": f"{name}\n{int(round(height))}x{int(round(width))}x{int(round(thickness))}",
    }


def make_board(name: str, stock: dict) -> dict:
    return {
        "name": name,
        "material": stock["material"],
        "width": float(stock["width"]),
        "height": float(stock["height"]),
        "thickness": float(stock["thickness"]),
        "pieces": [],
        "cuts": [],
        "remainders": [],
    }


def _pack_pieces_into_boards(stock: dict, pieces: list[dict], prefix: str) -> list[dict]:
    boards: list[dict] = []
    sorted_pieces = sorted(
        [deepcopy(piece) for piece in pieces],
        key=lambda piece: (piece["height"], piece["width"]),
        reverse=True,
    )

    for piece in sorted_pieces:
        placed = False
        for board in boards:
            x_cursor = board.setdefault("_x_cursor", 0.0)
            y_cursor = board.setdefault("_y_cursor", 0.0)
            row_height = board.setdefault("_row_height", 0.0)

            needed_width = piece["width"] + (KERF_MM if x_cursor > 0 else 0.0)
            if x_cursor + needed_width <= stock["width"] and y_cursor + piece["height"] <= stock["height"]:
                x = x_cursor + (KERF_MM if x_cursor > 0 else 0.0)
                board["pieces"].append(
                    {
                        "name": piece["name"],
                        "semantic": piece["semantic"],
                        "x": x,
                        "y": y_cursor,
                        "width": piece["width"],
                        "height": piece["height"],
                        "thickness": piece["thickness"],
                        "label": piece["label"],
                    }
                )
                board["_x_cursor"] = x + piece["width"]
                board["_row_height"] = max(row_height, piece["height"])
                placed = True
                break

            new_y = y_cursor + row_height + KERF_MM
            if new_y + piece["height"] <= stock["height"] and piece["width"] <= stock["width"]:
                board["_x_cursor"] = piece["width"]
                board["_y_cursor"] = new_y
                board["_row_height"] = piece["height"]
                board["pieces"].append(
                    {
                        "name": piece["name"],
                        "semantic": piece["semantic"],
                        "x": 0.0,
                        "y": new_y,
                        "width": piece["width"],
                        "height": piece["height"],
                        "thickness": piece["thickness"],
                        "label": piece["label"],
                    }
                )
                placed = True
                break

        if placed:
            continue

        if piece["width"] > stock["width"] or piece["height"] > stock["height"]:
            raise ValueError(
                f"Piece '{piece['name']}' ({piece['height']}x{piece['width']}) does not fit stock board "
                f"{stock['height']}x{stock['width']}"
            )

        board = make_board(f"{prefix} {len(boards) + 1}", stock)
        board["_x_cursor"] = piece["width"]
        board["_y_cursor"] = 0.0
        board["_row_height"] = piece["height"]
        board["pieces"].append(
            {
                "name": piece["name"],
                "semantic": piece["semantic"],
                "x": 0.0,
                "y": 0.0,
                "width": piece["width"],
                "height": piece["height"],
                "thickness": piece["thickness"],
                "label": piece["label"],
            }
        )
        boards.append(board)

    for board in boards:
        x_cursor = board.pop("_x_cursor", 0.0)
        y_cursor = board.pop("_y_cursor", 0.0)
        row_height = board.pop("_row_height", 0.0)

        if x_cursor < stock["width"] and row_height > 0:
            board["remainders"].append(
                {
                    "name": "REMAINING",
                    "semantic": "remaining",
                    "x": x_cursor + (KERF_MM if x_cursor > 0 else 0.0),
                    "y": y_cursor,
                    "width": max(stock["width"] - x_cursor - (KERF_MM if x_cursor > 0 else 0.0), 0.0),
                    "height": row_height,
                    "thickness": stock["thickness"],
                    "label": "REMAINING",
                }
            )

        bottom_used = y_cursor + row_height
        if bottom_used < stock["height"]:
            board["remainders"].append(
                {
                    "name": "REMAINING",
                    "semantic": "remaining",
                    "x": 0.0,
                    "y": bottom_used + (KERF_MM if bottom_used > 0 else 0.0),
                    "width": stock["width"],
                    "height": max(stock["height"] - bottom_used - (KERF_MM if bottom_used > 0 else 0.0), 0.0),
                    "thickness": stock["thickness"],
                    "label": "REMAINING",
                }
            )

    return boards


def build_parts(request: dict) -> list[dict]:
    depth = float(request["fabrication_depth"])
    outer_height = float(request["height"])
    board_thickness = float(request["board_thickness"])
    back_thickness = float(request["back_thickness"])
    columns = int(request["columns"])
    shell_mode = str(request["shell_mode"])
    horizontal_length = float(request["horizontal_length"])
    side_height = float(request["side_height"])
    divider_height = float(request["divider_height"])
    section_width = float(request["section_width"])
    shelf_levels = max(len(request["opening_heights"]) - 1, 0)

    parts = [
        make_piece("LEFT SIDE", "side", depth, side_height, board_thickness),
        make_piece("RIGHT SIDE", "side", depth, side_height, board_thickness),
        make_piece("TOP PANEL", "top_bottom", depth, horizontal_length, board_thickness),
        make_piece("BOTTOM PANEL", "top_bottom", depth, horizontal_length, board_thickness),
    ]

    if columns == 2:
        parts.append(make_piece("CENTER DIVIDER", "divider", depth, divider_height, board_thickness))

    for level in range(1, shelf_levels + 1):
        for column_name in ("L", "R")[:columns]:
            parts.append(
                make_piece(
                    f"SHELF {column_name}{level}",
                    "shelf",
                    depth,
                    section_width,
                    board_thickness,
                )
            )

    if request["back_panel"]:
        panel_width = float(request["back_panel_width"])
        panel_count = columns if columns > 1 else 1
        for index in range(panel_count):
            suffix = f" {index + 1}" if panel_count > 1 else ""
            parts.append(
                make_piece(
                    f"BACK PANEL{suffix}",
                    "back",
                    panel_width,
                    outer_height,
                    back_thickness,
                )
            )

    return parts


def build_pine_boards(parts: list[dict]) -> list[dict]:
    pine_parts = [piece for piece in parts if piece["semantic"] != "back"]
    return _pack_pieces_into_boards(PINE_BOARD, pine_parts, "PINE BOARD")


def build_back_boards(parts: list[dict]) -> list[dict]:
    back_parts = [piece for piece in parts if piece["semantic"] == "back"]
    return _pack_pieces_into_boards(BACK_BOARD, back_parts, "BACK BOARD") if back_parts else []


def build_payload(request: dict) -> dict:
    parts = build_parts(request)
    boards = build_pine_boards(parts) + build_back_boards(parts)

    columns = int(request["columns"])
    board_thickness = float(request["board_thickness"])
    outer_width = float(request["outer_width"])
    depth = float(request["depth"])
    section_width = float(request["section_width"])
    divider_height = float(request["divider_height"])

    payload = {
        "project_name": f"kerf_{request['project_name']}",
        "kerf_mm": KERF_MM,
        "cabinet": {
            "type": request["type"],
            "content_type": request["content_type"],
            "shell_mode": request["shell_mode"],
            "columns": columns,
            "construction_type": (
                "laterales exteriores + horizontales entre laterales"
                if request["shell_mode"] == "sides_outside"
                else "tapa/base exteriores + laterales entre horizontales"
            ),
            "horizontal_length": float(request["horizontal_length"]),
            "outer_width": outer_width,
            "height": float(request["height"]),
            "depth": float(request["fabrication_depth"]),
            "nominal_depth": depth,
            "board_thickness": board_thickness,
            "back_thickness": float(request["back_thickness"]),
            "divider_height": divider_height,
            "section_width": section_width,
            "back_panel_width": float(request["back_panel_width"]),
            "shelf_levels": max(len(request["opening_heights"]) - 1, 0),
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

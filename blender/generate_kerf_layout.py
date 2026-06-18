# FILE: blender/generate_kerf_layout.py
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Callable

import bpy

MM = 0.001
PNG_WIDTH = 3200
PNG_HEIGHT = 1800
IMAGE_ASPECT = PNG_WIDTH / PNG_HEIGHT
PANEL_BORDER_MM = 4.0
BACKGROUND_PANEL_OFFSET_MM = 24.0


def mm(value: float) -> float:
    return value * MM


def resolve_cli_paths() -> tuple[Path, Path]:
    if "--" not in sys.argv:
        raise SystemExit("Uso: blender --background --python script.py -- input.json output_dir")

    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) < 2:
        raise SystemExit("Faltan argumentos: input_json output_dir")

    project_root = Path.cwd()

    input_json = Path(argv[0])
    if not input_json.is_absolute():
        input_json = project_root / input_json
    input_json = input_json.resolve()

    output_dir = Path(argv[1])
    if not output_dir.is_absolute():
        output_dir = project_root / output_dir
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    return input_json, output_dir


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    collections = [
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.images,
        bpy.data.cameras,
        bpy.data.lights,
    ]

    for collection in collections:
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)


def setup_scene() -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_x = PNG_WIDTH
    scene.render.resolution_y = PNG_HEIGHT
    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    scene.render.use_overwrite = True

    scene.eevee.taa_render_samples = 64
    scene.eevee.use_gtao = True
    scene.view_settings.exposure = -0.72

    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")

    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (0.91, 0.91, 0.91, 1.0)
    background.inputs[1].default_value = 0.24


def setup_lights() -> None:
    bpy.ops.object.light_add(type="AREA", location=(4.1, -5.7, 5.6))
    key = bpy.context.object
    key.data.energy = 1800
    key.data.shape = "RECTANGLE"
    key.data.size = 3.6
    key.data.size_y = 3.6

    bpy.ops.object.light_add(type="AREA", location=(-2.8, -4.2, 4.0))
    fill = bpy.context.object
    fill.data.energy = 760
    fill.data.shape = "RECTANGLE"
    fill.data.size = 2.8
    fill.data.size_y = 2.8


def make_material(
    name: str,
    color: tuple[float, float, float],
    roughness: float = 0.5,
) -> bpy.types.Material:
    material = bpy.data.materials.get(name)
    if material is not None:
        return material

    material = bpy.data.materials.new(name=name)
    material.use_nodes = True

    bsdf = material.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness

    return material


def get_materials(data: dict) -> dict[str, bpy.types.Material]:
    colors = data.get("colors", {})

    return {
        "pine": make_material(
            "mat_pine",
            tuple(colors.get("pine", [0.82, 0.68, 0.46])),
            0.58,
        ),
        "pine_dark": make_material(
            "mat_pine_dark",
            (0.72, 0.59, 0.40),
            0.58,
        ),
        "side": make_material(
            "mat_side",
            tuple(colors.get("side", [0.93, 0.43, 0.36])),
            0.50,
        ),
        "divider": make_material(
            "mat_divider",
            tuple(colors.get("divider", [0.96, 0.75, 0.28])),
            0.50,
        ),
        "shelf": make_material(
            "mat_shelf",
            tuple(colors.get("shelf", [0.40, 0.73, 0.99])),
            0.50,
        ),
        "top_bottom": make_material(
            "mat_top_bottom",
            tuple(colors.get("top_bottom", [0.58, 0.88, 0.50])),
            0.50,
        ),
        "back": make_material(
            "mat_back",
            tuple(colors.get("pine", [0.82, 0.68, 0.46])),
            0.58,
        ),
        "remaining": make_material(
            "mat_remaining",
            tuple(colors.get("remaining", [0.32, 0.32, 0.32])),
            0.92,
        ),
        "kerf": make_material(
            "mat_kerf",
            tuple(colors.get("kerf", [0.02, 0.02, 0.02])),
            0.42,
        ),
        "text": make_material(
            "mat_text",
            (0.06, 0.06, 0.06),
            0.35,
        ),
        "panel": make_material(
            "mat_panel",
            (0.985, 0.985, 0.985),
            0.94,
        ),
        "panel_border": make_material(
            "mat_panel_border",
            (0.16, 0.16, 0.16),
            0.70,
        ),
    }


def new_bounds() -> dict[str, float]:
    return {
        "min_x": float("inf"),
        "max_x": float("-inf"),
        "min_y": float("inf"),
        "max_y": float("-inf"),
        "min_z": float("inf"),
        "max_z": float("-inf"),
    }


def is_empty_bounds(bounds: dict[str, float]) -> bool:
    return bounds["min_x"] == float("inf")


def extend_bounds(
    bounds: dict[str, float],
    center_x_m: float,
    center_y_m: float,
    center_z_m: float,
    size_x_mm: float,
    size_y_mm: float,
    size_z_mm: float,
) -> None:
    half_x = mm(size_x_mm) / 2.0
    half_y = mm(size_y_mm) / 2.0
    half_z = mm(size_z_mm) / 2.0

    bounds["min_x"] = min(bounds["min_x"], center_x_m - half_x)
    bounds["max_x"] = max(bounds["max_x"], center_x_m + half_x)
    bounds["min_y"] = min(bounds["min_y"], center_y_m - half_y)
    bounds["max_y"] = max(bounds["max_y"], center_y_m + half_y)
    bounds["min_z"] = min(bounds["min_z"], center_z_m - half_z)
    bounds["max_z"] = max(bounds["max_z"], center_z_m + half_z)


def extend_text_bounds(
    bounds: dict[str, float],
    x_mm: float,
    y_mm: float,
    z_mm: float,
    width_mm: float,
    height_mm: float,
) -> None:
    extend_bounds(
        bounds,
        mm(x_mm),
        mm(y_mm),
        mm(z_mm),
        width_mm,
        2.0,
        height_mm,
    )


def merge_bounds(*items: dict[str, float]) -> dict[str, float]:
    merged = new_bounds()

    for item in items:
        if is_empty_bounds(item):
            continue

        merged["min_x"] = min(merged["min_x"], item["min_x"])
        merged["max_x"] = max(merged["max_x"], item["max_x"])
        merged["min_y"] = min(merged["min_y"], item["min_y"])
        merged["max_y"] = max(merged["max_y"], item["max_y"])
        merged["min_z"] = min(merged["min_z"], item["min_z"])
        merged["max_z"] = max(merged["max_z"], item["max_z"])

    return merged


def estimate_text_block_mm(text: str, size: float) -> tuple[float, float]:
    lines = text.splitlines() or [text]
    longest = max((len(line) for line in lines), default=1)
    width_mm = max(90.0, longest * size * 560.0)
    height_mm = max(40.0, len(lines) * size * 920.0)
    return width_mm, height_mm


def create_cube(
    name: str,
    size_x_mm: float,
    size_y_mm: float,
    size_z_mm: float,
    center_x_mm: float,
    center_y_mm: float,
    center_z_mm: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(
        location=(mm(center_x_mm), mm(center_y_mm), mm(center_z_mm))
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (
        mm(size_x_mm) / 2.0,
        mm(size_y_mm) / 2.0,
        mm(size_z_mm) / 2.0,
    )
    obj.data.materials.clear()
    obj.data.materials.append(material)
    return obj


def create_front_text(
    text: str,
    x_mm: float,
    y_mm: float,
    z_mm: float,
    size: float,
    material: bpy.types.Material,
    align_x: str = "CENTER",
) -> bpy.types.Object:
    bpy.ops.object.text_add(
        location=(mm(x_mm), mm(y_mm), mm(z_mm)),
        rotation=(math.radians(90.0), 0.0, 0.0),
    )
    obj = bpy.context.active_object
    obj.data.body = text
    obj.data.size = size
    obj.data.extrude = 0.0012
    obj.data.align_x = align_x
    obj.data.align_y = "CENTER"
    obj.data.materials.clear()
    obj.data.materials.append(material)
    return obj


def add_text_with_bounds(
    bounds: dict[str, float],
    text: str,
    x_mm: float,
    y_mm: float,
    z_mm: float,
    size: float,
    material: bpy.types.Material,
    align_x: str = "CENTER",
) -> bpy.types.Object:
    obj = create_front_text(text, x_mm, y_mm, z_mm, size, material, align_x=align_x)
    width_mm, height_mm = estimate_text_block_mm(text, size)

    center_x_mm = x_mm
    if align_x == "LEFT":
        center_x_mm = x_mm + width_mm / 2.0
    elif align_x == "RIGHT":
        center_x_mm = x_mm - width_mm / 2.0

    extend_text_bounds(bounds, center_x_mm, y_mm, z_mm, width_mm, height_mm)
    return obj


def clamp_text_size(width_mm: float, height_mm: float, factor: float = 0.24) -> float:
    return max(0.026, min(0.064, mm(min(width_mm, height_mm)) * factor))


def add_panel(
    bounds: dict[str, float],
    mats: dict[str, bpy.types.Material],
    padding_left_mm: float,
    padding_right_mm: float,
    padding_bottom_mm: float,
    padding_top_mm: float,
    name_prefix: str,
) -> dict[str, float]:
    width_mm = ((bounds["max_x"] - bounds["min_x"]) / MM) + padding_left_mm + padding_right_mm
    height_mm = ((bounds["max_z"] - bounds["min_z"]) / MM) + padding_bottom_mm + padding_top_mm

    content_center_x_mm = ((bounds["min_x"] + bounds["max_x"]) / 2.0) / MM
    content_center_z_mm = ((bounds["min_z"] + bounds["max_z"]) / 2.0) / MM

    center_x_mm = content_center_x_mm + (padding_right_mm - padding_left_mm) / 2.0
    center_z_mm = content_center_z_mm + (padding_top_mm - padding_bottom_mm) / 2.0

    panel_y_mm = (bounds["max_y"] / MM) + BACKGROUND_PANEL_OFFSET_MM

    create_cube(
        f"{name_prefix}_PANEL",
        width_mm,
        6.0,
        height_mm,
        center_x_mm,
        panel_y_mm,
        center_z_mm,
        mats["panel"],
    )
    create_cube(
        f"{name_prefix}_BORDER_TOP",
        width_mm,
        PANEL_BORDER_MM,
        PANEL_BORDER_MM,
        center_x_mm,
        panel_y_mm - 1.0,
        center_z_mm + height_mm / 2.0,
        mats["panel_border"],
    )
    create_cube(
        f"{name_prefix}_BORDER_BOTTOM",
        width_mm,
        PANEL_BORDER_MM,
        PANEL_BORDER_MM,
        center_x_mm,
        panel_y_mm - 1.0,
        center_z_mm - height_mm / 2.0,
        mats["panel_border"],
    )
    create_cube(
        f"{name_prefix}_BORDER_LEFT",
        PANEL_BORDER_MM,
        PANEL_BORDER_MM,
        height_mm,
        center_x_mm - width_mm / 2.0,
        panel_y_mm - 1.0,
        center_z_mm,
        mats["panel_border"],
    )
    create_cube(
        f"{name_prefix}_BORDER_RIGHT",
        PANEL_BORDER_MM,
        PANEL_BORDER_MM,
        height_mm,
        center_x_mm + width_mm / 2.0,
        panel_y_mm - 1.0,
        center_z_mm,
        mats["panel_border"],
    )

    panel_bounds = new_bounds()
    extend_bounds(
        panel_bounds,
        mm(center_x_mm),
        mm(panel_y_mm),
        mm(center_z_mm),
        width_mm,
        6.0,
        height_mm,
    )
    return panel_bounds


def add_section_title(
    panel_bounds: dict[str, float],
    mats: dict[str, bpy.types.Material],
    title: str,
    subtitle: str,
    title_size: float = 0.094,
    subtitle_size: float = 0.038,
    align_x: str = "LEFT",
) -> None:
    title_bounds = new_bounds()

    if align_x == "CENTER":
        title_x_mm = ((panel_bounds["min_x"] + panel_bounds["max_x"]) / 2.0) / MM
    else:
        title_x_mm = (panel_bounds["min_x"] / MM) + 72.0
    y_mm = (panel_bounds["min_y"] / MM) - 18.0
    title_z_mm = (panel_bounds["max_z"] / MM) - 74.0
    subtitle_z_mm = title_z_mm - 92.0

    add_text_with_bounds(
        title_bounds,
        title,
        title_x_mm,
        y_mm,
        title_z_mm,
        title_size,
        mats["text"],
        align_x=align_x,
    )
    add_text_with_bounds(
        title_bounds,
        subtitle,
        title_x_mm,
        y_mm,
        subtitle_z_mm,
        subtitle_size,
        mats["text"],
        align_x=align_x,
    )


def add_overview_header(
    bounds: dict[str, float],
    mats: dict[str, bpy.types.Material],
    data: dict,
) -> dict[str, float]:
    header_bounds = new_bounds()

    center_x_mm = ((bounds["min_x"] + bounds["max_x"]) / 2.0) / MM
    top_z_mm = (bounds["max_z"] / MM) + 170.0
    y_mm = -24.0

    cabinet = data["cabinet"]
    title = f"KERF FABRICATION POSTER — {data['project_name']}"
    subtitle = (
        f"Width {int(cabinet['outer_width'])} mm | "
        f"Height {int(cabinet['height'])} mm | "
        f"Depth {int(cabinet['depth'])} mm | "
        f"Kerf {int(data['kerf_mm'])} mm"
    )

    add_text_with_bounds(header_bounds, title, center_x_mm, y_mm, top_z_mm, 0.108, mats["text"])
    add_text_with_bounds(
        header_bounds,
        subtitle,
        center_x_mm,
        y_mm,
        top_z_mm - 118.0,
        0.042,
        mats["text"],
    )

    return header_bounds


def create_camera_from_bounds(
    name: str,
    bounds: dict[str, float],
    angle_deg: float = 80.0,
    padding_x: float = 1.04,
    padding_z: float = 1.08,
    distance: float = 5.2,
    offset_x_mm: float = 0.0,
    offset_z_mm: float = 0.0,
    vertical_bias: float = 0.0,
) -> bpy.types.Object:
    center_x = (bounds["min_x"] + bounds["max_x"]) / 2.0 + mm(offset_x_mm)
    center_y = (bounds["min_y"] + bounds["max_y"]) / 2.0

    span_x = max(bounds["max_x"] - bounds["min_x"], mm(10.0))
    span_z = max(bounds["max_z"] - bounds["min_z"], mm(10.0))

    center_z = (
        (bounds["min_z"] + bounds["max_z"]) / 2.0
        + mm(offset_z_mm)
        + (span_z * vertical_bias)
    )

    bpy.ops.object.camera_add(
        location=(center_x, center_y - distance, center_z + 0.10),
        rotation=(math.radians(angle_deg), 0.0, 0.0),
    )
    camera = bpy.context.object
    camera.name = name
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = max(
        span_x * padding_x,
        span_z * padding_z * IMAGE_ASPECT,
        3.2,
    )
    camera.data.clip_start = 0.01
    camera.data.clip_end = 1000.0

    bpy.context.scene.camera = camera
    return camera


def render_to_file(output_path: Path) -> None:
    if output_path.exists():
        output_path.unlink()

    scene = bpy.context.scene
    scene.render.use_overwrite = True
    scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)


def save_blend_copy(output_path: Path) -> None:
    if output_path.exists():
        output_path.unlink()

    bpy.ops.wm.save_as_mainfile(
        filepath=str(output_path),
        check_existing=False,
        copy=True,
    )


def export_glb(output_path: Path) -> None:
    if output_path.exists():
        output_path.unlink()

    bpy.ops.export_scene.gltf(
        filepath=str(output_path),
        check_existing=False,
        export_format="GLB",
        export_apply=True,
        use_selection=False,
    )


def export_final_assembly_assets(output_dir: Path, data: dict) -> None:
    clear_scene()
    setup_scene()
    setup_lights()

    mats = get_materials(data)
    bounds = build_assembly(
        data,
        mats,
        exploded=False,
        piece_labels=False,
        include_section_title=False,
        include_panel=False,
    )

    create_camera_from_bounds(
        "CAM_EXPORT_FINAL",
        bounds,
        angle_deg=80.0,
        padding_x=1.02,
        padding_z=1.06,
        distance=5.1,
        offset_z_mm=36.0,
        vertical_bias=0.08,
    )

    save_blend_copy(output_dir / "06_final_assembly.blend")
    export_glb(output_dir / "06_final_assembly.glb")


def build_board_layout(
    data: dict,
    mats: dict[str, bpy.types.Material],
    origin_x_mm: float = 0.0,
    origin_z_mm: float = 0.0,
    layout_scale: float = 1.0,
    piece_labels: bool = True,
    include_section_title: bool = True,
    title_align: str = "LEFT",
) -> dict[str, float]:
    bounds = new_bounds()
    boards = data["boards"]

    x_cursor_mm = origin_x_mm
    gap_mm = 160.0 * layout_scale

    for board_index, board in enumerate(boards, start=1):
        board_width = float(board["width"]) * layout_scale
        board_height = float(board["height"]) * layout_scale
        board_thickness = float(board["thickness"])

        board_center_x = x_cursor_mm + board_width / 2.0
        board_center_z = origin_z_mm + board_height / 2.0

        board_material = mats["pine"]
        if "MDF" in board["material"].upper():
            board_material = mats["back"]

        create_cube(
            f"BOARD_{board_index}",
            board_width,
            board_thickness,
            board_height,
            board_center_x,
            0.0,
            board_center_z,
            board_material,
        )
        extend_bounds(
            bounds,
            mm(board_center_x),
            0.0,
            mm(board_center_z),
            board_width,
            board_thickness,
            board_height,
        )

        compact_board_labels = layout_scale < 0.3
        board_label = (
            board["name"]
            if compact_board_labels
            else f"{board['name']}\n{int(board['height'])}x{int(board['width'])}x{int(board['thickness'])}"
        )
        board_label_x = board_center_x if not compact_board_labels else (x_cursor_mm + 12.0)
        board_label_align = "CENTER" if not compact_board_labels else "LEFT"
        board_label_z = origin_z_mm + board_height + (108.0 if not compact_board_labels else 74.0)
        if compact_board_labels and board_index % 2 == 0:
            board_label_z += 24.0
        add_text_with_bounds(
            bounds,
            board_label,
            board_label_x,
            -18.0,
            board_label_z,
            0.026 if compact_board_labels else (0.040 if layout_scale < 0.5 else 0.050),
            mats["text"],
            align_x=board_label_align,
        )

        face_y = -board_thickness / 2.0 - 2.0

        for remainder in board["remainders"]:
            rem_width = float(remainder["width"]) * layout_scale
            rem_height = float(remainder["height"]) * layout_scale
            rem_x = float(remainder["x"]) * layout_scale
            rem_y = float(remainder["y"]) * layout_scale

            create_cube(
                "REMAINING",
                rem_width,
                2.0,
                rem_height,
                x_cursor_mm + rem_x + rem_width / 2.0,
                face_y - 1.1,
                origin_z_mm + rem_y + rem_height / 2.0,
                mats["remaining"],
            )

        for cut in board["cuts"]:
            cut_width = float(cut["width"]) * layout_scale
            cut_height = float(cut["height"]) * layout_scale
            cut_x = float(cut["x"]) * layout_scale
            cut_y = float(cut["y"]) * layout_scale

            create_cube(
                "CUT",
                cut_width,
                1.0,
                cut_height,
                x_cursor_mm + cut_x + cut_width / 2.0,
                face_y - 2.5,
                origin_z_mm + cut_y + cut_height / 2.0,
                mats["kerf"],
            )

        for piece in board["pieces"]:
            piece_width = float(piece["width"]) * layout_scale
            piece_height = float(piece["height"]) * layout_scale
            piece_x = float(piece["x"]) * layout_scale
            piece_y = float(piece["y"]) * layout_scale

            center_x = x_cursor_mm + piece_x + piece_width / 2.0
            center_z = origin_z_mm + piece_y + piece_height / 2.0

            create_cube(
                piece["name"],
                piece_width,
                3.0,
                piece_height,
                center_x,
                face_y,
                center_z,
                mats.get(piece["semantic"], mats["shelf"]),
            )

            if piece_labels:
                label = f"{piece['name']}\n{int(piece['height'])}x{int(piece['width'])}"
                label_z = center_z
                label_factor = 0.22 if layout_scale >= 0.8 else 0.18
                if piece["name"] in {"LEFT SIDE", "TOP PANEL"}:
                    label_z = center_z - piece_height * 0.18
                    label_factor = 0.16 if layout_scale >= 0.8 else 0.15
                elif piece["name"] in {"RIGHT SIDE", "BOTTOM PANEL"}:
                    label_z = center_z + piece_height * 0.18
                    label_factor = 0.16 if layout_scale >= 0.8 else 0.15
                add_text_with_bounds(
                    bounds,
                    label,
                    center_x,
                    face_y - 12.0,
                    label_z,
                    clamp_text_size(piece_width, piece_height, label_factor),
                    mats["text"],
                )

        x_cursor_mm += board_width + gap_mm

    panel_bounds = add_panel(
        bounds,
        mats,
        padding_left_mm=90.0,
        padding_right_mm=90.0,
        padding_bottom_mm=52.0,
        padding_top_mm=190.0 if include_section_title else 70.0,
        name_prefix="BOARD_LAYOUT",
    )

    if include_section_title:
        add_section_title(
            panel_bounds,
            mats,
            "01. BOARD LAYOUT",
            "Boards, cuts, kerf and remaining material",
            title_size=0.098,
            subtitle_size=0.040,
            align_x=title_align,
        )

    return panel_bounds


def build_cut_parts(
    data: dict,
    mats: dict[str, bpy.types.Material],
    origin_x_mm: float = 0.0,
    origin_z_mm: float = 0.0,
    layout_scale: float = 1.0,
    piece_labels: bool = True,
    include_section_title: bool = True,
    title_align: str = "LEFT",
) -> dict[str, float]:
    bounds = new_bounds()
    parts = data["parts"]

    groups = [
        {
            "name": "STRUCTURE",
            "semantics": ["side", "divider", "top_bottom"],
            "group_x": origin_x_mm + 120.0 * layout_scale,
            "columns": 2,
            "col_step": 540.0 * layout_scale,
            "row_step": 720.0 * layout_scale,
            "top_z": origin_z_mm + 1220.0 * layout_scale,
            "header_z": origin_z_mm + 1840.0 * layout_scale,
            "label_offset": 56.0,
        },
        {
            "name": "SHELVES",
            "semantics": ["shelf"],
            "group_x": origin_x_mm + 1750.0 * layout_scale,
            "columns": 4,
            "col_step": 520.0 * layout_scale,
            "row_step": 690.0 * layout_scale,
            "top_z": origin_z_mm + 1450.0 * layout_scale,
            "header_z": origin_z_mm + 1930.0 * layout_scale,
            "label_offset": 72.0,
        },
        {
            "name": "BACK PANELS",
            "semantics": ["back"],
            "group_x": origin_x_mm + 4050.0 * layout_scale,
            "columns": 1,
            "col_step": 0.0,
            "row_step": 1120.0 * layout_scale,
            "top_z": origin_z_mm + 1450.0 * layout_scale,
            "header_z": origin_z_mm + 2110.0 * layout_scale,
            "label_offset": 72.0,
        },
    ]

    longest_dim = max(max(float(part["width"]), float(part["height"])) for part in parts)
    base_scale = min(1.0, 900.0 / longest_dim)
    scale = base_scale * layout_scale

    default_top_z_mm = origin_z_mm + 1450.0 * layout_scale

    for group in groups:
        group_parts = [part for part in parts if part["semantic"] in group["semantics"]]
        group_parts.sort(
            key=lambda part: (
                -max(float(part["width"]), float(part["height"])),
                -min(float(part["width"]), float(part["height"])),
                part["name"],
            )
        )

        header_x = group["group_x"] + ((group["columns"] - 1) * group["col_step"] / 2.0)
        add_text_with_bounds(
            bounds,
            group["name"],
            header_x,
            -16.0,
            group.get("header_z", origin_z_mm + 1930.0 * layout_scale),
            0.058 if layout_scale >= 0.8 else 0.046,
            mats["text"],
        )

        for index, piece in enumerate(group_parts):
            row = index // group["columns"]
            col = index % group["columns"]

            long_dim = max(float(piece["width"]), float(piece["height"])) * scale
            short_dim = min(float(piece["width"]), float(piece["height"])) * scale
            thickness_dim = max(6.0, float(piece["thickness"]))

            center_x = group["group_x"] + col * group["col_step"]
            group_top_z_mm = group.get("top_z", default_top_z_mm)
            center_z = group_top_z_mm - row * group["row_step"]

            create_cube(
                piece["name"],
                short_dim,
                thickness_dim,
                long_dim,
                center_x,
                0.0,
                center_z,
                mats.get(piece["semantic"], mats["shelf"]),
            )
            extend_bounds(
                bounds,
                mm(center_x),
                0.0,
                mm(center_z),
                short_dim,
                thickness_dim,
                long_dim,
            )

            if piece_labels:
                label = (
                    f"{piece['name']}\n"
                    f"{int(piece['height'])}x{int(piece['width'])}x{int(piece['thickness'])}"
                )
                add_text_with_bounds(
                    bounds,
                    label,
                    center_x,
                    -16.0,
                    center_z + long_dim / 2.0 + group.get("label_offset", 72.0),
                    0.034 if layout_scale < 0.8 else 0.040,
                    mats["text"],
                )

    panel_bounds = add_panel(
        bounds,
        mats,
        padding_left_mm=120.0,
        padding_right_mm=120.0,
        padding_bottom_mm=72.0,
        padding_top_mm=180.0 if include_section_title else 70.0,
        name_prefix="CUT_PARTS",
    )

    if include_section_title:
        add_section_title(
            panel_bounds,
            mats,
            "02. CUT PARTS",
            "Grouped into structure, shelves and back panels",
            title_size=0.098,
            subtitle_size=0.040,
            align_x=title_align,
        )

    return panel_bounds


def build_shelf_centers_z(opening_heights: list[float], thickness: float) -> list[float]:
    values: list[float] = []
    current_bottom = thickness

    for opening_height in opening_heights[:-1]:
        values.append(current_bottom + opening_height + thickness / 2.0)
        current_bottom += opening_height + thickness

    return values


def build_assembly(
    data: dict,
    mats: dict[str, bpy.types.Material],
    exploded: bool,
    origin_x_mm: float = 0.0,
    origin_z_mm: float = 0.0,
    layout_scale: float = 1.0,
    piece_labels: bool = True,
    include_section_title: bool = True,
    include_panel: bool = True,
    title_align: str = "LEFT",
    title_size: float = 0.096,
    subtitle_size: float = 0.038,
) -> dict[str, float]:
    bounds = new_bounds()
    cabinet = data["cabinet"]

    outer_width = float(cabinet["outer_width"]) * layout_scale
    height = float(cabinet["height"]) * layout_scale
    depth = float(cabinet["depth"])
    thickness = float(cabinet["board_thickness"]) * layout_scale
    divider_height = float(cabinet["divider_height"]) * layout_scale
    horizontal_length = float(cabinet["horizontal_length"]) * layout_scale
    section_width = float(cabinet["section_width"]) * layout_scale
    back_panel_width = float(cabinet["back_panel_width"]) * layout_scale
    back_thickness = float(cabinet["back_thickness"])
    opening_heights = [float(value) * layout_scale for value in cabinet["opening_heights"]]

    explode_side_x = 185.0 * layout_scale if exploded else 0.0
    explode_shelf_x = 105.0 * layout_scale if exploded else 0.0
    explode_top_z = 155.0 * layout_scale if exploded else 0.0
    explode_bottom_z = 155.0 * layout_scale if exploded else 0.0
    explode_back_y = 170.0 * layout_scale if exploded else 0.0
    explode_divider_y = 40.0 * layout_scale if exploded else 0.0

    left_side_x = origin_x_mm - (outer_width / 2.0 - thickness / 2.0) - explode_side_x
    right_side_x = origin_x_mm + (outer_width / 2.0 - thickness / 2.0) + explode_side_x

    structure_mat = mats["side"] if exploded else mats["pine"]
    divider_mat = mats["divider"] if exploded else mats["pine"]
    shelf_mat = mats["shelf"] if exploded else mats["pine"]
    top_bottom_mat = mats["top_bottom"] if exploded else mats["pine"]
    back_mat = mats["back"]

    create_cube(
        "LEFT_SIDE",
        thickness,
        depth,
        height,
        left_side_x,
        0.0,
        origin_z_mm + height / 2.0,
        structure_mat,
    )
    extend_bounds(
        bounds,
        mm(left_side_x),
        0.0,
        mm(origin_z_mm + height / 2.0),
        thickness,
        depth,
        height,
    )

    create_cube(
        "RIGHT_SIDE",
        thickness,
        depth,
        height,
        right_side_x,
        0.0,
        origin_z_mm + height / 2.0,
        structure_mat,
    )
    extend_bounds(
        bounds,
        mm(right_side_x),
        0.0,
        mm(origin_z_mm + height / 2.0),
        thickness,
        depth,
        height,
    )

    top_z = origin_z_mm + height - thickness / 2.0 + explode_top_z
    bottom_z = origin_z_mm + thickness / 2.0 - explode_bottom_z

    create_cube(
        "TOP_PANEL",
        horizontal_length,
        depth,
        thickness,
        origin_x_mm,
        0.0,
        top_z,
        top_bottom_mat,
    )
    extend_bounds(bounds, mm(origin_x_mm), 0.0, mm(top_z), horizontal_length, depth, thickness)

    create_cube(
        "BOTTOM_PANEL",
        horizontal_length,
        depth,
        thickness,
        origin_x_mm,
        0.0,
        bottom_z,
        top_bottom_mat,
    )
    extend_bounds(bounds, mm(origin_x_mm), 0.0, mm(bottom_z), horizontal_length, depth, thickness)

    divider_z = origin_z_mm + thickness + divider_height / 2.0
    create_cube(
        "CENTER_DIVIDER",
        thickness,
        depth,
        divider_height,
        origin_x_mm,
        explode_divider_y,
        divider_z,
        divider_mat,
    )
    extend_bounds(
        bounds,
        mm(origin_x_mm),
        mm(explode_divider_y),
        mm(divider_z),
        thickness,
        depth,
        divider_height,
    )

    left_shelf_x = origin_x_mm - (thickness / 2.0 + section_width / 2.0) - explode_shelf_x
    right_shelf_x = origin_x_mm + (thickness / 2.0 + section_width / 2.0) + explode_shelf_x

    for index, shelf_z in enumerate(build_shelf_centers_z(opening_heights, thickness), start=1):
        shelf_z_world = origin_z_mm + shelf_z

        create_cube(
            f"SHELF_L_{index}",
            section_width,
            depth,
            thickness,
            left_shelf_x,
            0.0,
            shelf_z_world,
            shelf_mat,
        )
        extend_bounds(
            bounds,
            mm(left_shelf_x),
            0.0,
            mm(shelf_z_world),
            section_width,
            depth,
            thickness,
        )

        create_cube(
            f"SHELF_R_{index}",
            section_width,
            depth,
            thickness,
            right_shelf_x,
            0.0,
            shelf_z_world,
            shelf_mat,
        )
        extend_bounds(
            bounds,
            mm(right_shelf_x),
            0.0,
            mm(shelf_z_world),
            section_width,
            depth,
            thickness,
        )

        if exploded and piece_labels:
            add_text_with_bounds(
                bounds,
                f"SHELF L{index}",
                left_shelf_x,
                -18.0,
                shelf_z_world + 34.0,
                0.042,
                mats["text"],
            )
            add_text_with_bounds(
                bounds,
                f"SHELF R{index}",
                right_shelf_x,
                -18.0,
                shelf_z_world + 34.0,
                0.042,
                mats["text"],
            )

    back_y = depth / 2.0 + back_thickness / 2.0 + explode_back_y
    back_left_x = origin_x_mm - back_panel_width / 2.0
    back_right_x = origin_x_mm + back_panel_width / 2.0

    create_cube(
        "BACK_LEFT",
        back_panel_width,
        back_thickness,
        height,
        back_left_x,
        back_y,
        origin_z_mm + height / 2.0,
        back_mat,
    )
    extend_bounds(
        bounds,
        mm(back_left_x),
        mm(back_y),
        mm(origin_z_mm + height / 2.0),
        back_panel_width,
        back_thickness,
        height,
    )

    create_cube(
        "BACK_RIGHT",
        back_panel_width,
        back_thickness,
        height,
        back_right_x,
        back_y,
        origin_z_mm + height / 2.0,
        back_mat,
    )
    extend_bounds(
        bounds,
        mm(back_right_x),
        mm(back_y),
        mm(origin_z_mm + height / 2.0),
        back_panel_width,
        back_thickness,
        height,
    )

    if exploded and piece_labels:
        side_label_z = origin_z_mm + height + 78.0
        add_text_with_bounds(
            bounds,
            "LEFT SIDE",
            left_side_x,
            -18.0,
            side_label_z,
            0.042,
            mats["text"],
        )
        add_text_with_bounds(
            bounds,
            "RIGHT SIDE",
            right_side_x,
            -18.0,
            side_label_z,
            0.042,
            mats["text"],
        )
        add_text_with_bounds(
            bounds,
            "TOP PANEL",
            origin_x_mm,
            -18.0,
            top_z + 58.0,
            0.042,
            mats["text"],
        )
        add_text_with_bounds(
            bounds,
            "BOTTOM PANEL",
            origin_x_mm,
            -18.0,
            bottom_z - 58.0,
            0.042,
            mats["text"],
        )
        add_text_with_bounds(
            bounds,
            "CENTER DIVIDER",
            origin_x_mm,
            -18.0,
            divider_z + 24.0,
            0.040,
            mats["text"],
        )
        add_text_with_bounds(
            bounds,
            "BACK LEFT",
            back_left_x,
            -18.0,
            origin_z_mm + height * 0.13,
            0.040,
            mats["text"],
        )
        add_text_with_bounds(
            bounds,
            "BACK RIGHT",
            back_right_x,
            -18.0,
            origin_z_mm + height * 0.13,
            0.040,
            mats["text"],
        )

    panel_top_padding_mm = 190.0 if exploded else 215.0

    if include_panel:
        panel_bounds = add_panel(
            bounds,
            mats,
            padding_left_mm=95.0,
            padding_right_mm=95.0,
            padding_bottom_mm=50.0,
            padding_top_mm=panel_top_padding_mm if include_section_title else 70.0,
            name_prefix="EXPLODED" if exploded else "FINAL",
        )

        if include_section_title:
            add_section_title(
                panel_bounds,
                mats,
                "03. EXPLODED ASSEMBLY" if exploded else "04. FINAL ASSEMBLY",
                "Separated assembly view" if exploded else "Finished cabinet assembled from kerf data",
                title_size=title_size,
                subtitle_size=subtitle_size,
                align_x=title_align,
            )

        return panel_bounds

    return bounds


def render_single_view(
    output_path: Path,
    data: dict,
    build_fn: Callable[[dict, dict[str, bpy.types.Material]], dict[str, float]],
    camera_name: str,
    camera_angle: float,
    camera_padding_x: float,
    camera_padding_z: float,
    camera_distance: float,
    camera_offset_z_mm: float = 0.0,
    camera_vertical_bias: float = 0.0,
) -> None:
    clear_scene()
    setup_scene()
    setup_lights()

    mats = get_materials(data)
    bounds = build_fn(data, mats)

    create_camera_from_bounds(
        camera_name,
        bounds,
        angle_deg=camera_angle,
        padding_x=camera_padding_x,
        padding_z=camera_padding_z,
        distance=camera_distance,
        offset_z_mm=camera_offset_z_mm,
        vertical_bias=camera_vertical_bias,
    )
    render_to_file(output_path)


def render_overview(output_path: Path, data: dict) -> None:
    clear_scene()
    setup_scene()
    setup_lights()

    mats = get_materials(data)

    board_bounds = build_board_layout(
        data,
        mats,
        origin_x_mm=1700.0,
        origin_z_mm=1080.0,
        layout_scale=0.18,
        piece_labels=False,
        include_section_title=True,
    )

    cut_parts_bounds = build_cut_parts(
        data,
        mats,
        origin_x_mm=160.0,
        origin_z_mm=360.0,
        layout_scale=0.20,
        piece_labels=False,
        include_section_title=True,
    )

    exploded_bounds = build_assembly(
        data,
        mats,
        exploded=True,
        origin_x_mm=1760.0,
        origin_z_mm=240.0,
        layout_scale=0.24,
        piece_labels=False,
        include_section_title=True,
        title_align="CENTER",
        title_size=0.075,
        subtitle_size=0.031,
    )

    final_bounds = build_assembly(
        data,
        mats,
        exploded=False,
        origin_x_mm=3000.0,
        origin_z_mm=240.0,
        layout_scale=0.25,
        piece_labels=False,
        include_section_title=True,
        title_align="CENTER",
        title_size=0.075,
        subtitle_size=0.031,
    )

    overview_bounds = merge_bounds(
        board_bounds,
        cut_parts_bounds,
        exploded_bounds,
        final_bounds,
    )

    create_camera_from_bounds(
        "CAM_OVERVIEW",
        overview_bounds,
        angle_deg=82.0,
        padding_x=1.05,
        padding_z=1.24,
        distance=8.4,
        offset_z_mm=400.0,
        vertical_bias=0.30,
    )
    render_to_file(output_path)


def main() -> None:
    input_json, output_dir = resolve_cli_paths()
    data = json.loads(input_json.read_text(encoding="utf-8-sig"))

    render_single_view(
        output_dir / "01_board_layout.png",
        data,
        build_fn=lambda d, m: build_board_layout(d, m),
        camera_name="CAM_BOARD",
        camera_angle=84.0,
        camera_padding_x=1.02,
        camera_padding_z=1.05,
        camera_distance=6.0,
        camera_offset_z_mm=18.0,
    )

    render_single_view(
        output_dir / "02_cut_parts.png",
        data,
        build_fn=lambda d, m: build_cut_parts(d, m),
        camera_name="CAM_PARTS",
        camera_angle=84.0,
        camera_padding_x=1.00,
        camera_padding_z=1.02,
        camera_distance=6.0,
        camera_offset_z_mm=48.0,
        camera_vertical_bias=0.14,
    )

    render_single_view(
        output_dir / "03_exploded_assembly.png",
        data,
        build_fn=lambda d, m: build_assembly(d, m, exploded=True),
        camera_name="CAM_EXPLODED",
        camera_angle=80.0,
        camera_padding_x=1.01,
        camera_padding_z=1.09,
        camera_distance=5.3,
        camera_offset_z_mm=156.0,
        camera_vertical_bias=0.27,
    )

    render_single_view(
        output_dir / "04_final_assembly.png",
        data,
        build_fn=lambda d, m: build_assembly(
            d,
            m,
            exploded=False,
            piece_labels=False,
        ),
        camera_name="CAM_FINAL",
        camera_angle=80.0,
        camera_padding_x=1.01,
        camera_padding_z=1.09,
        camera_distance=5.1,
        camera_offset_z_mm=148.0,
        camera_vertical_bias=0.28,
    )

    render_overview(output_dir / "05_overview.png", data)
    export_final_assembly_assets(output_dir, data)

    print(f"DONE -> {output_dir}")


if __name__ == "__main__":
    main()
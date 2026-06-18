# blender/generate_bookshelf.py
from __future__ import annotations

import json
import random
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Vector


RANDOM_SEED = 42


def resolve_cli_paths() -> tuple[Path, Path]:
    if "--" not in sys.argv:
        raise SystemExit("Uso: blender --background --python blender/generate_bookshelf.py -- input.json output_dir")

    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) < 2:
        raise SystemExit("Faltan argumentos: input_json output_dir")

    input_path = Path(argv[0]).resolve()
    output_dir = Path(argv[1]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    return input_path, output_dir


def resolve_project_root() -> Path:
    if "__file__" in globals():
        return Path(__file__).resolve().parent.parent
    return Path.cwd()


def mm(value: float) -> float:
    return value / 1000.0


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for collection in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.images,
        bpy.data.lights,
        bpy.data.cameras,
    ):
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)


def safe_unlink(path: Path) -> None:
    if not path.exists():
        return
    if path.is_file() or path.is_symlink():
        path.unlink()
    else:
        shutil.rmtree(path)


def create_box(name: str, sx: float, sy: float, sz: float, x: float, y: float, z: float) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=(mm(x), mm(y), mm(z)))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (mm(sx) / 2.0, mm(sy) / 2.0, mm(sz) / 2.0)

    bevel = obj.modifiers.new(name="Bevel", type="BEVEL")
    bevel.width = 0.0008
    bevel.segments = 2
    return obj


def create_plane(name: str, sx: float, sy: float, x: float, y: float, z: float) -> bpy.types.Object:
    bpy.ops.mesh.primitive_plane_add(location=(mm(x), mm(y), mm(z)))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (mm(sx) / 2.0, mm(sy) / 2.0, 1.0)
    return obj


def make_material(name: str, color: tuple[float, float, float, float], roughness: float = 0.5) -> bpy.types.Material:
    existing = bpy.data.materials.get(name)
    if existing is not None:
        return existing

    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = 0.18
    return material


def apply_material(obj: bpy.types.Object, material: bpy.types.Material) -> None:
    if obj.data.materials:
        obj.data.materials[0] = material
    else:
        obj.data.materials.append(material)


def create_pine_material(base_dir: Path) -> bpy.types.Material:
    pine_dir = base_dir / "assets" / "materials" / "pine"
    basecolor = pine_dir / "pine_basecolor.jpg"
    roughness = pine_dir / "pine_roughness.jpg"
    normal = pine_dir / "pine_normal.png"

    if not (basecolor.exists() and roughness.exists() and normal.exists()):
        return make_material("pine_fallback", (0.82, 0.76, 0.69, 1.0), roughness=0.72)

    existing = bpy.data.materials.get("pine_wood")
    if existing is not None:
        return existing

    material = bpy.data.materials.new(name="pine_wood")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new(type="ShaderNodeOutputMaterial")
    output.location = (900, 0)

    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.location = (520, 0)
    bsdf.inputs["Roughness"].default_value = 0.72
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.18

    texcoord = nodes.new(type="ShaderNodeTexCoord")
    texcoord.location = (-850, 0)

    mapping = nodes.new(type="ShaderNodeMapping")
    mapping.location = (-620, 0)
    mapping.inputs["Scale"].default_value = (5.6, 1.0, 5.6)

    tex_base = nodes.new(type="ShaderNodeTexImage")
    tex_base.location = (-320, 140)
    tex_base.image = bpy.data.images.load(str(basecolor), check_existing=True)

    tex_rough = nodes.new(type="ShaderNodeTexImage")
    tex_rough.location = (-320, -50)
    tex_rough.image = bpy.data.images.load(str(roughness), check_existing=True)
    tex_rough.image.colorspace_settings.name = "Non-Color"

    tex_normal = nodes.new(type="ShaderNodeTexImage")
    tex_normal.location = (-320, -250)
    tex_normal.image = bpy.data.images.load(str(normal), check_existing=True)
    tex_normal.image.colorspace_settings.name = "Non-Color"

    normal_map = nodes.new(type="ShaderNodeNormalMap")
    normal_map.location = (170, -250)
    normal_map.inputs["Strength"].default_value = 0.22

    links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex_base.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex_rough.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex_normal.inputs["Vector"])
    links.new(tex_base.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(tex_rough.outputs["Color"], bsdf.inputs["Roughness"])
    links.new(tex_normal.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return material


def add_text(
    text: str,
    x: float,
    y: float,
    z: float,
    size: float,
    material: bpy.types.Material,
    align_x: str = "CENTER",
) -> bpy.types.Object:
    bpy.ops.object.text_add(location=(mm(x), mm(y), mm(z)))
    obj = bpy.context.object
    obj.data.body = text
    obj.data.size = size
    obj.data.align_x = align_x
    obj.data.extrude = 0.001
    apply_material(obj, material)
    return obj


def setup_world(client_mode: bool) -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_x = 2200
    scene.render.resolution_y = 1600
    scene.render.use_overwrite = True
    scene.eevee.taa_render_samples = 64

    if hasattr(scene.eevee, "use_gtao"):
        scene.eevee.use_gtao = True

    if hasattr(scene.eevee, "use_bloom"):
        scene.eevee.use_bloom = False

    # bajar exposición para evitar imagen lavada/quemada
    scene.view_settings.exposure = -0.55 if client_mode else -0.08

    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")

    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes["Background"]

    if client_mode:
        background.inputs[0].default_value = (0.92, 0.93, 0.94, 1.0)
        background.inputs[1].default_value = 0.38
    else:
        background.inputs[0].default_value = (0.985, 0.985, 0.985, 1.0)
        background.inputs[1].default_value = 0.18


def setup_client_lights() -> None:
    bpy.ops.object.light_add(type="AREA", location=(2.8, -3.2, 3.6))
    key = bpy.context.object
    key.data.energy = 900
    key.data.shape = "RECTANGLE"
    key.data.size = 2.8
    key.data.size_y = 2.8

    bpy.ops.object.light_add(type="AREA", location=(-2.2, -2.2, 2.6))
    fill = bpy.context.object
    fill.data.energy = 260
    fill.data.shape = "RECTANGLE"
    fill.data.size = 2.0
    fill.data.size_y = 2.0


def setup_carpentry_lights() -> None:
    bpy.ops.object.light_add(type="SUN", location=(0.0, 0.0, 4.0))
    sun = bpy.context.object
    sun.data.energy = 1.2


def create_floor(width: float, depth: float) -> None:
    floor_width = width * 1.8
    floor_depth = max(depth * 8.0, 1400.0)

    # plano horizontal real, ligeramente por debajo del mueble
    floor = create_plane(
        "FLOOR",
        floor_width,
        floor_depth,
        width / 2.0,
        0.0,
        -2.0,
    )

    # NO rotar: el primitive_plane_add ya nace horizontal en XY
    apply_material(floor, make_material("floor_mat", (0.93, 0.93, 0.93, 1.0), roughness=0.98))


def expand_openings(spec: dict) -> list[dict]:
    if spec.get("openings"):
        return [dict(item) for item in spec["openings"]]

    openings: list[dict] = []
    for zone in spec["zones"]:
        count = int(zone.get("count", 1))
        for _ in range(count):
            openings.append({"type": zone["type"], "clear_height": float(zone["clear_height"])})
    return openings


def calculate_geometry(spec: dict) -> dict:
    dimensions = spec["overall_dimensions"]
    board_thickness = float(spec["structure"]["board_thickness"])
    construction = dict(spec.get("construction") or {})
    shell_mode = str(construction.get("shell_mode", "sides_outside"))
    columns = int(construction.get("columns", 2))
    width = float(dimensions["width"])
    height = float(dimensions["height"])
    depth = float(dimensions["depth"])

    divider_count = max(columns - 1, 0)
    internal_clear_width = width - (2 * board_thickness) - (divider_count * board_thickness)
    section_width = internal_clear_width / columns
    internal_clear_height = height - (2 * board_thickness)
    horizontal_length = width - (2 * board_thickness) if shell_mode == "sides_outside" else width
    side_height = height if shell_mode == "sides_outside" else height - (2 * board_thickness)
    divider_height = height - (2 * board_thickness)

    return {
        "width": width,
        "height": height,
        "depth": depth,
        "board_thickness": board_thickness,
        "shell_mode": shell_mode,
        "columns": columns,
        "divider_count": divider_count,
        "section_width": section_width,
        "internal_clear_height": internal_clear_height,
        "horizontal_length": horizontal_length,
        "side_height": side_height,
        "divider_height": divider_height,
    }


def get_sections(geometry: dict) -> list[dict]:
    t = geometry["board_thickness"]
    width = geometry["width"]
    section_width = geometry["section_width"]
    columns = geometry["columns"]

    if columns == 1:
        return [{"name": "C1", "x_start": t, "x_end": width - t, "width": section_width}]

    return [
        {"name": "L", "x_start": t, "x_end": t + section_width, "width": section_width},
        {"name": "R", "x_start": width - t - section_width, "x_end": width - t, "width": section_width},
    ]


def distribute_remaining_space(openings: list[dict], remaining: float, mode: str) -> list[dict]:
    adjusted = [dict(item) for item in openings]
    if remaining <= 0:
        return adjusted

    if mode == "top_bottom_large":
        targets = [0]
        if len(adjusted) > 1:
            targets.append(len(adjusted) - 1)
        extra = remaining / len(targets)
        for index in targets:
            adjusted[index]["clear_height"] += extra
    elif mode == "large_openings":
        targets = [
            index
            for index, opening in enumerate(adjusted)
            if opening["type"] in {"books_large", "books_standard", "dvd_boxset"}
        ]
        if targets:
            extra = remaining / len(targets)
            for index in targets:
                adjusted[index]["clear_height"] += extra
    elif mode == "uniform":
        extra = remaining / len(adjusted)
        for opening in adjusted:
            opening["clear_height"] += extra

    return adjusted


def create_structure(geometry: dict, mats: dict[str, bpy.types.Material]) -> None:
    width = geometry["width"]
    height = geometry["height"]
    depth = geometry["depth"]
    t = geometry["board_thickness"]
    horizontal_length = geometry["horizontal_length"]
    side_height = geometry["side_height"]
    divider_height = geometry["divider_height"]
    shell_mode = geometry["shell_mode"]
    columns = geometry["columns"]

    if shell_mode == "sides_outside":
        side_z = height / 2.0
        top_z = height - t / 2.0
        bottom_z = t / 2.0
    else:
        side_z = height / 2.0
        top_z = height - t / 2.0
        bottom_z = t / 2.0

    left_side = create_box("LEFT_SIDE", t, depth, side_height, t / 2.0, 0.0, side_z)
    right_side = create_box("RIGHT_SIDE", t, depth, side_height, width - t / 2.0, 0.0, side_z)
    apply_material(left_side, mats["wood"])
    apply_material(right_side, mats["wood"])

    top_panel = create_box("TOP_PANEL", horizontal_length, depth, t, width / 2.0, 0.0, top_z)
    bottom_panel = create_box("BOTTOM_PANEL", horizontal_length, depth, t, width / 2.0, 0.0, bottom_z)
    apply_material(top_panel, mats["wood"])
    apply_material(bottom_panel, mats["wood"])

    if columns == 2:
        divider = create_box("CENTER_DIVIDER", t, depth, divider_height, width / 2.0, 0.0, height / 2.0)
        apply_material(divider, mats["wood"])


def create_shelves(geometry: dict, openings: list[dict], mats: dict[str, bpy.types.Material]) -> None:
    sections = get_sections(geometry)
    t = geometry["board_thickness"]
    depth = geometry["depth"]
    current_z = t

    for level_index, opening in enumerate(openings[:-1], start=1):
        current_z += float(opening["clear_height"])
        shelf_z = current_z + (t / 2.0)

        for section in sections:
            shelf = create_box(
                f"SHELF_{section['name']}_{level_index}",
                section["width"],
                depth,
                t,
                section["x_start"] + section["width"] / 2.0,
                0.0,
                shelf_z,
            )
            apply_material(shelf, mats["wood"])

        current_z += t


def create_back_panels(spec: dict, geometry: dict, mats: dict[str, bpy.types.Material]) -> None:
    back_panel = spec.get("back_panel", {})
    if not back_panel.get("enabled", False):
        return

    width = geometry["width"]
    height = geometry["height"]
    depth = geometry["depth"]
    t_back = float(back_panel.get("thickness", 5.0))
    columns = geometry["columns"]

    y_pos = (depth / 2.0) + (t_back / 2.0)

    if columns == 1:
        panel = create_box("BACK_PANEL", width, t_back, height, width / 2.0, y_pos, height / 2.0)
        apply_material(panel, mats["back"])
        return

    panel_width = width / 2.0
    left = create_box("BACK_LEFT", panel_width, t_back, height, panel_width / 2.0, y_pos, height / 2.0)
    right = create_box("BACK_RIGHT", panel_width, t_back, height, width - panel_width / 2.0, y_pos, height / 2.0)
    apply_material(left, mats["back"])
    apply_material(right, mats["back"])


def _get_item_dimensions(spec: dict, opening_type: str) -> tuple[float, float, float]:
    visualization = spec.get("visualization", {})
    if opening_type == "dvd":
        return 14.0, 190.0, 135.0
    if opening_type == "dvd_boxset":
        return 28.0, 190.0, 135.0
    if opening_type == "books_small":
        return (
            float(visualization.get("book_small_width", 20.0)),
            float(visualization.get("book_small_height", 200.0)),
            float(visualization.get("book_small_depth", 140.0)),
        )
    if opening_type in {"books_large", "books_standard"}:
        return (
            float(visualization.get("book_large_width", 24.0 if opening_type == "books_large" else 22.0)),
            float(visualization.get("book_large_height", 240.0 if opening_type == "books_large" else 220.0)),
            float(visualization.get("book_large_depth", 170.0 if opening_type == "books_large" else 155.0)),
        )
    return 20.0, 200.0, 140.0


def populate_contents(spec: dict, geometry: dict, openings: list[dict]) -> dict[str, int]:
    visualization = spec.get("visualization", {})
    add_dvds = visualization.get("add_dvds", False)
    add_books = visualization.get("add_books", False)
    if not add_dvds and not add_books:
        return {"dvd_count": 0, "book_count": 0, "boxset_count": 0}

    counts = {"dvd_count": 0, "book_count": 0, "boxset_count": 0}
    sections = get_sections(geometry)
    gap = float(visualization.get("gap", 2.0))
    current_z = geometry["board_thickness"]

    random.seed(RANDOM_SEED)

    for opening_index, opening in enumerate(openings, start=1):
        clear_height = float(opening["clear_height"])
        opening_type = str(opening["type"])
        item_width, item_height, item_depth = _get_item_dimensions(spec, opening_type)
        base_z = current_z

        for section in sections:
            usable_width = section["width"] - (2.0 * gap)
            usable_depth = geometry["depth"] - gap - 10.0
            count = max(int(usable_width // (item_width + gap)), 0)

            for item_index in range(count):
                x = section["x_start"] + gap + item_width / 2.0 + item_index * (item_width + gap)
                y = -(geometry["depth"] / 2.0) + item_depth / 2.0 + gap + 10.0
                z = base_z + min(item_height, clear_height) / 2.0

                obj = create_box(
                    f"ITEM_{section['name']}_{opening_index}_{item_index}",
                    item_width,
                    min(item_depth, usable_depth),
                    min(item_height, clear_height),
                    x,
                    y,
                    z,
                )

                hue = (item_index % 8) / 8.0
                color = (0.38 + hue * 0.25, 0.44 + (1 - hue) * 0.18, 0.48 + hue * 0.18, 1.0)
                apply_material(obj, make_material(f"content_{opening_type}_{item_index % 8}", color, roughness=0.88))

                if opening_type == "dvd":
                    counts["dvd_count"] += 1
                elif opening_type == "dvd_boxset":
                    counts["boxset_count"] += 1
                else:
                    counts["book_count"] += 1

        current_z += clear_height + geometry["board_thickness"]

    return counts


def setup_camera_perspective(name: str, location: tuple[float, float, float], target: tuple[float, float, float], lens: float) -> bpy.types.Object:
    bpy.ops.object.camera_add(location=tuple(mm(value) for value in location))
    camera = bpy.context.object
    camera.name = name
    direction = Vector(
        (
            mm(target[0]) - camera.location.x,
            mm(target[1]) - camera.location.y,
            mm(target[2]) - camera.location.z,
        )
    )
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = lens
    return camera


def setup_camera_front(name: str, width: float, height: float, distance_mm: float, ortho_scale_factor: float) -> bpy.types.Object:
    bpy.ops.object.camera_add(location=(mm(width / 2.0), mm(-distance_mm), mm(height / 2.0)))
    camera = bpy.context.object
    camera.name = name
    camera.rotation_euler = (1.5708, 0.0, 0.0)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = mm(max(width * ortho_scale_factor, height * (ortho_scale_factor + 0.08)))
    return camera


def render_to_file(path: Path, camera: bpy.types.Object) -> None:
    scene = bpy.context.scene
    scene.camera = camera
    safe_unlink(path)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def export_blend(path: Path) -> None:
    safe_unlink(path)
    bpy.ops.wm.save_as_mainfile(filepath=str(path), copy=True)


def export_glb(path: Path) -> None:
    safe_unlink(path)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_visible=True)


def add_carpentry_annotations(geometry: dict, openings: list[dict], mats: dict[str, bpy.types.Material]) -> None:
    width = geometry["width"]
    height = geometry["height"]
    depth = geometry["depth"]
    section_width = geometry["section_width"]
    t = geometry["board_thickness"]
    text_mat = mats["text"]

    add_text(f"ANCHO TOTAL {int(round(width))} mm", width / 2.0, -(depth / 2.0) - 60.0, height + 80.0, 0.05, text_mat)
    add_text(f"ALTO TOTAL {int(round(height))} mm", width + 90.0, -(depth / 2.0) - 60.0, height / 2.0, 0.05, text_mat, align_x="LEFT")
    add_text(f"FONDO {int(round(depth))} mm", width / 2.0, -(depth / 2.0) - 60.0, -60.0, 0.042, text_mat)
    add_text(f"ANCHO HUECO {int(round(section_width))} mm", width / 2.0, -(depth / 2.0) - 60.0, 20.0, 0.038, text_mat)

    current_z = t
    for opening in openings:
        clear_height = float(opening["clear_height"])
        center_z = current_z + clear_height / 2.0
        add_text(f"{int(round(clear_height))}", -70.0, -(depth / 2.0) - 60.0, center_z, 0.034, text_mat, align_x="RIGHT")
        current_z += clear_height + t


def build_scene(spec: dict, base_dir: Path, carpentry: bool, include_floor: bool = False) -> dict[str, int]:
    geometry = calculate_geometry(spec)
    openings = expand_openings(spec)
    remaining_mode = str(spec.get("solver", {}).get("remaining_distribution", "none"))
    remaining = float(geometry["internal_clear_height"]) - (
        sum(float(item["clear_height"]) for item in openings)
        + max(len(openings) - 1, 0) * geometry["board_thickness"]
    )
    openings = distribute_remaining_space(openings, remaining, remaining_mode)

    clear_scene()
    setup_world(client_mode=not carpentry)

    wood_mat = (
        create_pine_material(base_dir)
        if not carpentry
        else make_material("wood_carpentry", (0.87, 0.74, 0.56, 1.0), 0.78)
    )

    mats = {
        "wood": wood_mat,
        "back": make_material("back_panel", (0.87, 0.87, 0.87, 1.0), 0.94),
        "text": make_material("text_black", (0.10, 0.10, 0.10, 1.0), 0.4),
    }

    create_structure(geometry, mats)
    create_shelves(spec, geometry, openings, mats)
    create_back_panels(spec, geometry, mats)

    counts = (
        populate_contents(spec, geometry, openings, mats)
        if not carpentry
        else {"dvd_count": 0, "book_count": 0, "boxset_count": 0}
    )

    if not carpentry:
        if include_floor:
            create_floor(geometry["width"], geometry["depth"])
        setup_client_lights()
    else:
        setup_carpentry_lights()
        add_carpentry_annotations(spec, geometry, openings, mats)

    return counts


def save_report(output_dir: Path, spec: dict, geometry: dict, openings: list[dict], counts: dict[str, int]) -> None:
    report = {
        "project_name": spec["project_name"],
        "content_type": spec["content_type"],
        "construction": spec["construction"],
        "overall_dimensions": spec["overall_dimensions"],
        "opening_heights": [float(item["clear_height"]) for item in openings],
        "counts": counts,
        "remaining_distribution": spec.get("solver", {}).get("remaining_distribution", "none"),
    }
    (output_dir / "layout_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    input_path, output_dir = resolve_cli_paths()
    spec = json.loads(input_path.read_text(encoding="utf-8"))
    base_dir = Path.cwd()

    geometry = calculate_geometry(spec)

    # 1) frontal cliente SIN suelo
    counts = build_scene(spec, base_dir, carpentry=False, include_floor=False)
    client_front = setup_camera_front("CAM_CLIENT_FRONT", geometry["width"], geometry["height"])
    render_to_file(output_dir / "render_client_front.png", client_front)

    # 2) perspectiva cliente CON suelo
    build_scene(spec, base_dir, carpentry=False, include_floor=True)
    client_angle = setup_camera_perspective(
        "CAM_CLIENT_ANGLE",
        (geometry["width"] * 1.35, -geometry["depth"] * 6.0, geometry["height"] * 0.62),
        (geometry["width"] / 2.0, 0.0, geometry["height"] * 0.48),
    )
    render_to_file(output_dir / "render_client_angle.png", client_angle)

    export_blend(output_dir / f"{spec['project_name']}.blend")
    export_glb(output_dir / f"{spec['project_name']}.glb")
    save_report(output_dir, spec, geometry, counts)

    # 3) plano carpintería
    build_scene(spec, base_dir, carpentry=True, include_floor=False)
    carpentry_camera = setup_camera_front("CAM_CARPENTRY", geometry["width"], geometry["height"])
    render_to_file(output_dir / "plano_carpinteria.png", carpentry_camera)

    print(f"DONE -> {output_dir}")

if __name__ == "__main__":
    main()

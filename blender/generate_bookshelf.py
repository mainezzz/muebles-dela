# blender/generate_bookshelf.py

from __future__ import annotations

import json
import math
import random
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Vector


RANDOM_SEED = 42


def resolve_cli_paths() -> tuple[Path, Path]:
    if "--" not in sys.argv:
        raise SystemExit(
            "Uso: blender --background --python blender/generate_bookshelf.py -- input.json output_dir"
        )

    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) < 2:
        raise SystemExit("Faltan argumentos: input_json output_dir")

    input_path = Path(argv[0]).resolve()
    output_dir = Path(argv[1]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    return input_path, output_dir


def mm(value: float) -> float:
    return value / 1000.0


def safe_unlink(path: Path) -> None:
    if path.exists():
        if path.is_file() or path.is_symlink():
            path.unlink()
        else:
            shutil.rmtree(path)


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    data_blocks = (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.images,
        bpy.data.lights,
        bpy.data.cameras,
    )
    for collection in data_blocks:
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)


def create_box(
    name: str,
    x: float,
    y: float,
    z: float,
    sx: float,
    sy: float,
    sz: float,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=(mm(x), mm(y), mm(z)))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (mm(sx) / 2.0, mm(sy) / 2.0, mm(sz) / 2.0)

    bevel = obj.modifiers.new(name="Bevel", type="BEVEL")
    bevel.width = 0.0008
    bevel.segments = 2
    return obj


def create_plane(
    name: str,
    x: float,
    y: float,
    z: float,
    sx: float,
    sy: float,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_plane_add(location=(mm(x), mm(y), mm(z)))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (mm(sx) / 2.0, mm(sy) / 2.0, 1.0)
    return obj


def make_material(
    name: str,
    color: tuple[float, float, float, float],
    roughness: float = 0.45,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name=name)
    material.use_nodes = True

    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness

        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = 0.20

    return material


def apply_material(obj: bpy.types.Object, material: bpy.types.Material) -> None:
    if obj.data.materials:
        obj.data.materials[0] = material
    else:
        obj.data.materials.append(material)


def create_pine_material(base_dir: Path) -> bpy.types.Material:
    pine_dir = base_dir / "assets" / "materials" / "pine"
    pine_basecolor = pine_dir / "pine_basecolor.jpg"
    pine_roughness = pine_dir / "pine_roughness.jpg"
    pine_normal = pine_dir / "pine_normal.png"

    if not (pine_basecolor.exists() and pine_roughness.exists() and pine_normal.exists()):
        return make_material("pine_wood_fallback", (0.73, 0.62, 0.52, 1.0), roughness=0.74)

    material = bpy.data.materials.new(name="pine_wood_pbr")
    material.use_nodes = True

    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new(type="ShaderNodeOutputMaterial")
    output.location = (1100, 0)

    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.location = (700, 0)
    bsdf.inputs["Roughness"].default_value = 0.72
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.18

    texcoord = nodes.new(type="ShaderNodeTexCoord")
    texcoord.location = (-1400, 0)

    mapping = nodes.new(type="ShaderNodeMapping")
    mapping.location = (-1150, 0)
    mapping.inputs["Scale"].default_value = (2.2, 2.2, 2.2)

    color_tex = nodes.new(type="ShaderNodeTexImage")
    color_tex.location = (-850, 250)
    color_tex.image = bpy.data.images.load(str(pine_basecolor))

    color_adjust = nodes.new(type="ShaderNodeBrightContrast")
    color_adjust.location = (-550, 250)
    color_adjust.inputs["Bright"].default_value = -0.10
    color_adjust.inputs["Contrast"].default_value = 0.10

    roughness_tex = nodes.new(type="ShaderNodeTexImage")
    roughness_tex.location = (-850, 0)
    roughness_tex.image = bpy.data.images.load(str(pine_roughness))
    roughness_tex.image.colorspace_settings.name = "Non-Color"

    normal_tex = nodes.new(type="ShaderNodeTexImage")
    normal_tex.location = (-850, -250)
    normal_tex.image = bpy.data.images.load(str(pine_normal))
    normal_tex.image.colorspace_settings.name = "Non-Color"

    normal_map = nodes.new(type="ShaderNodeNormalMap")
    normal_map.location = (-550, -250)
    normal_map.inputs["Strength"].default_value = 0.25

    links.new(texcoord.outputs["UV"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], color_tex.inputs["Vector"])
    links.new(mapping.outputs["Vector"], roughness_tex.inputs["Vector"])
    links.new(mapping.outputs["Vector"], normal_tex.inputs["Vector"])

    links.new(color_tex.outputs["Color"], color_adjust.inputs["Color"])
    links.new(color_adjust.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(roughness_tex.outputs["Color"], bsdf.inputs["Roughness"])
    links.new(normal_tex.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return material


def create_floor_material() -> bpy.types.Material:
    return make_material("studio_floor", (0.78, 0.79, 0.81, 1.0), roughness=0.99)


def setup_render() -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 1800
    scene.render.resolution_y = 1800
    scene.render.image_settings.file_format = "PNG"
    scene.render.use_file_extension = True
    scene.render.use_overwrite = True
    scene.render.film_transparent = False

    scene.eevee.taa_render_samples = 96
    scene.eevee.taa_samples = 48

    if hasattr(scene.eevee, "use_gtao"):
        scene.eevee.use_gtao = True
    if hasattr(scene.eevee, "gtao_factor"):
        scene.eevee.gtao_factor = 1.0
    if hasattr(scene.eevee, "gtao_quality"):
        scene.eevee.gtao_quality = 0.25

    if hasattr(scene.eevee, "shadow_pool_size"):
        try:
            scene.eevee.shadow_pool_size = "1024"
        except Exception:
            pass

    if hasattr(scene.eevee, "use_shadows"):
        try:
            scene.eevee.use_shadows = True
        except Exception:
            pass

    if hasattr(scene.view_settings, "view_transform"):
        try:
            scene.view_settings.view_transform = "AgX"
        except Exception:
            pass

    if hasattr(scene.view_settings, "look"):
        try:
            scene.view_settings.look = "None"
        except Exception:
            pass

    # Menos quemado
    scene.view_settings.exposure = -0.90
    scene.view_settings.gamma = 1.0

    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")

    world = scene.world
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    background.inputs["Strength"].default_value = 0.03


def add_area_light(
    name: str,
    location: tuple[float, float, float],
    rotation: tuple[float, float, float],
    energy: float,
    size: float,
    size_y: float,
    color: tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> bpy.types.Object:
    bpy.ops.object.light_add(type="AREA", location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.energy = energy
    obj.data.shape = "RECTANGLE"
    obj.data.size = size
    obj.data.size_y = size_y
    obj.data.color = color
    return obj


def render_png(camera: bpy.types.Object, output_path: Path) -> None:
    safe_unlink(output_path)
    scene = bpy.context.scene
    scene.camera = camera
    scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)


def export_blend(output_path: Path) -> None:
    safe_unlink(output_path)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_path), check_existing=False, copy=False)


def export_glb(output_path: Path) -> None:
    safe_unlink(output_path)
    bpy.ops.export_scene.gltf(
        filepath=str(output_path),
        export_format="GLB",
        check_existing=False,
    )


def main() -> None:
    input_path, output_dir = resolve_cli_paths()
    spec = json.loads(input_path.read_text(encoding="utf-8"))
    base_dir = Path(__file__).resolve().parent.parent

    random.seed(RANDOM_SEED)
    clear_scene()
    setup_render()

    w = float(spec["overall_dimensions"]["width"])
    h = float(spec["overall_dimensions"]["height"])
    d = float(spec["overall_dimensions"]["depth"])

    structure = spec["structure"]
    t = float(structure["board_thickness"])

    side_panels = structure.get("side_panels", True)
    top_panel = structure.get("top_panel", True)
    bottom_panel = structure.get("bottom_panel", True)

    dividers = spec.get("dividers", {})
    has_center_divider = dividers.get("center", False)

    zones = spec["zones"]

    solver = spec.get("solver", {})
    remaining_distribution = solver.get("remaining_distribution", "none")

    back_panel = spec.get("back_panel", {})
    has_back = back_panel.get("enabled", False)
    back_panel_thickness = float(back_panel.get("thickness", 5))

    visualization = spec.get("visualization", {})

    dvd_count = 0
    boxset_count = 0
    book_count = 0
    item_material_cache: dict[str, bpy.types.Material] = {}

    pine_material = create_pine_material(base_dir)
    floor_material = create_floor_material()

    def get_sections() -> list[dict]:
        if has_center_divider:
            section_width = (w - (3.0 * t)) / 2.0
            return [
                {"name": "left", "x_start": t, "x_end": t + section_width, "width": section_width},
                {"name": "right", "x_start": w - t - section_width, "x_end": w - t, "width": section_width},
            ]
        return [{"name": "full", "x_start": t, "x_end": w - t, "width": w - (2.0 * t)}]

    def expand_openings() -> list[dict]:
        openings: list[dict] = []
        for zone in zones:
            for _ in range(zone["count"]):
                openings.append({"type": zone["type"], "clear_height": float(zone["clear_height"])})
        return openings

    def calculate_height_report(openings: list[dict]) -> dict:
        usable_height = h - (t if top_panel else 0.0) - (t if bottom_panel else 0.0)
        clear_height_total = sum(opening["clear_height"] for opening in openings)
        internal_shelves = max(len(openings) - 1, 0)
        required_height = clear_height_total + (internal_shelves * t)
        remaining = usable_height - required_height
        return {
            "usable_height": usable_height,
            "clear_height_total": clear_height_total,
            "internal_shelves": internal_shelves,
            "required_height": required_height,
            "remaining": remaining,
        }

    def distribute_remaining_space(openings: list[dict], remaining: float) -> list[dict]:
        if remaining <= 0:
            return openings

        adjusted = [dict(opening) for opening in openings]

        if remaining_distribution == "top_bottom_large":
            targets = [0]
            if len(adjusted) > 1:
                targets.append(len(adjusted) - 1)
            extra = remaining / len(targets)
            for index in targets:
                adjusted[index]["clear_height"] += extra
        elif remaining_distribution == "large_openings":
            targets = [
                index
                for index, opening in enumerate(adjusted)
                if opening["type"] in ["books_large", "books_standard", "dvd_boxsets"]
            ]
            if targets:
                extra = remaining / len(targets)
                for index in targets:
                    adjusted[index]["clear_height"] += extra
        elif remaining_distribution == "uniform":
            extra = remaining / len(adjusted)
            for opening in adjusted:
                opening["clear_height"] += extra

        return adjusted

    def material_from_palette(prefix: str, index: int) -> bpy.types.Material:
        cache_key = f"{prefix}_{index % 12}"
        if cache_key in item_material_cache:
            return item_material_cache[cache_key]

        palette = [
    		(0.90, 0.10, 0.10, 1.0),  # rojo fuerte
   		 (0.10, 0.35, 0.90, 1.0),  # azul intenso
   		 (0.10, 0.70, 0.20, 1.0),  # verde vivo
    		(0.95, 0.65, 0.10, 1.0),  # naranja
   		 (0.60, 0.10, 0.80, 1.0),  # violeta fuerte
   		 (0.10, 0.75, 0.75, 1.0),  # cian
   		 (0.95, 0.20, 0.50, 1.0),  # magenta
   		 (0.15, 0.15, 0.15, 1.0),  # negro/gris oscuro
   		 (0.95, 0.85, 0.10, 1.0),  # amarillo fuerte
    		(0.20, 0.60, 0.90, 1.0),  # azul claro vivo
	]
        material = make_material(cache_key, palette[index % len(palette)], roughness=0.82)
        item_material_cache[cache_key] = material
        return material

    def create_structure() -> None:
        if side_panels:
            apply_material(create_box("left_side", t / 2.0, d / 2.0, h / 2.0, t, d, h), pine_material)
            apply_material(create_box("right_side", w - (t / 2.0), d / 2.0, h / 2.0, t, d, h), pine_material)

        horizontal_width = w - (2.0 * t)

        if bottom_panel:
            apply_material(
                create_box("bottom_panel", w / 2.0, d / 2.0, t / 2.0, horizontal_width, d, t),
                pine_material,
            )
        if top_panel:
            apply_material(
                create_box("top_panel", w / 2.0, d / 2.0, h - (t / 2.0), horizontal_width, d, t),
                pine_material,
            )

        if has_center_divider:
            divider_bottom = t if bottom_panel else 0.0
            divider_top = h - t if top_panel else h
            divider_height = divider_top - divider_bottom
            apply_material(
                create_box(
                    "center_divider",
                    w / 2.0,
                    d / 2.0,
                    divider_bottom + (divider_height / 2.0),
                    t,
                    d,
                    divider_height,
                ),
                pine_material,
            )

    def create_internal_shelves(openings: list[dict]) -> None:
        current_z = t if bottom_panel else 0.0
        shelf_index = 0
        sections = get_sections()

        for opening_index, opening in enumerate(openings):
            clear_height = opening["clear_height"]
            opening_top_z = current_z + clear_height
            is_last = opening_index == len(openings) - 1

            if not is_last:
                shelf_z = opening_top_z + (t / 2.0)
                for section in sections:
                    apply_material(
                        create_box(
                            f"shelf_{section['name']}_{shelf_index}",
                            section["x_start"] + (section["width"] / 2.0),
                            d / 2.0,
                            shelf_z,
                            section["width"],
                            d,
                            t,
                        ),
                        pine_material,
                    )
                current_z = opening_top_z + t
                shelf_index += 1
            else:
                current_z = opening_top_z

    def create_back_panels() -> None:
        if not has_back:
            return

        panel_height = float(back_panel.get("panel_height", h))
        split_vertical_panels = back_panel.get("split_vertical_panels", back_panel.get("split", False))
        panel_width = float(back_panel.get("panel_width", w / 2.0 if split_vertical_panels else w))
        y_pos = d + (back_panel_thickness / 2.0)
        z_pos = panel_height / 2.0

        if split_vertical_panels:
            seam_x = w / 2.0
            apply_material(
                create_box(
                    "back_panel_left",
                    panel_width / 2.0,
                    y_pos,
                    z_pos,
                    panel_width,
                    back_panel_thickness,
                    panel_height,
                ),
                pine_material,
            )
            apply_material(
                create_box(
                    "back_panel_right",
                    seam_x + (panel_width / 2.0),
                    y_pos,
                    z_pos,
                    panel_width,
                    back_panel_thickness,
                    panel_height,
                ),
                pine_material,
            )
            return

        apply_material(
            create_box(
                "back_panel",
                w / 2.0,
                y_pos,
                z_pos,
                panel_width,
                back_panel_thickness,
                panel_height,
            ),
            pine_material,
        )

    def create_visual_item(
        prefix: str,
        x: float,
        y: float,
        z: float,
        sx: float,
        sy: float,
        sz: float,
        tilt_radians: float = 0.0,
    ) -> None:
        nonlocal dvd_count, boxset_count, book_count

        if prefix == "dvd":
            index = dvd_count
            dvd_count += 1
        elif prefix == "boxset":
            index = boxset_count
            boxset_count += 1
        else:
            index = book_count
            book_count += 1

        obj = create_box(f"{prefix}_{index}", x, y, z, sx, sy, sz)
        apply_material(obj, material_from_palette(prefix, index))
        if tilt_radians != 0.0:
            obj.rotation_euler[1] = tilt_radians

    def populate_visuals(openings: list[dict]) -> None:
        current_z = t if bottom_panel else 0.0
        sections = get_sections()

        gap = float(visualization.get("gap", 2))
        add_dvds = visualization.get("add_dvds", False)
        add_books = visualization.get("add_books", False)

        dvd_width = float(visualization.get("dvd_width", 14))
        dvd_height = float(visualization.get("dvd_height", 190))
        dvd_depth = float(visualization.get("dvd_depth", 135))

        boxset_width = float(visualization.get("boxset_width", 50))
        boxset_height = float(visualization.get("boxset_height", 200))
        boxset_depth = float(visualization.get("boxset_depth", 135))

        book_small_width = float(visualization.get("book_small_width", 20))
        book_small_height = float(visualization.get("book_small_height", 200))
        book_small_depth = float(visualization.get("book_small_depth", 140))

        book_large_width = float(visualization.get("book_large_width", 24))
        book_large_height = float(visualization.get("book_large_height", 240))
        book_large_depth = float(visualization.get("book_large_depth", 180))

        for opening in openings:
            opening_type = opening["type"]

            for section in sections:
                x_cursor = section["x_start"] + gap
                item_index = 0

                while True:
                    if add_dvds and opening_type == "dvd_boxsets":
                        item_prefix = "boxset"
                        item_width = boxset_width
                        item_height = boxset_height
                        item_depth = boxset_depth
                    elif add_dvds and opening_type == "dvds":
                        item_prefix = "dvd"
                        item_width = dvd_width
                        item_height = dvd_height
                        item_depth = dvd_depth
                    elif add_books and opening_type == "books_small":
                        item_prefix = "book_small"
                        item_width = book_small_width
                        item_height = book_small_height
                        item_depth = book_small_depth
                    elif add_books and opening_type in ["books_large", "books_standard"]:
                        item_prefix = "book_large"
                        item_width = book_large_width
                        item_height = book_large_height
                        item_depth = book_large_depth
                    else:
                        break

                    if x_cursor + item_width > section["x_end"] - gap:
                        break

                    y_pos = min(item_depth / 2.0, d - 8.0) - 4.0
                    z_pos = current_z + (item_height / 2.0)

                    tilt = 0.0
                    if item_prefix.startswith("book") and item_index % 9 == 4:
                        tilt = 0.04
                    elif item_prefix.startswith("book") and item_index % 11 == 7:
                        tilt = -0.04

                    create_visual_item(
                        item_prefix,
                        x_cursor + (item_width / 2.0),
                        y_pos,
                        z_pos,
                        item_width,
                        item_depth,
                        item_height,
                        tilt_radians=tilt,
                    )

                    x_cursor += item_width + gap
                    item_index += 1

            current_z += opening["clear_height"] + t

    def setup_floor() -> None:
        floor = create_plane(
            "studio_floor",
            w / 2.0,
            d * 0.46,
            0.0,
            max(w * 2.0, 4000.0),
            max(h * 1.8, 3200.0),
        )
        apply_material(floor, floor_material)

    def setup_lights() -> None:
        for obj in list(bpy.data.objects):
            if obj.type == "LIGHT":
                bpy.data.objects.remove(obj, do_unlink=True)

        # Luz principal frontal muy suave
        add_area_light(
            name="Key_Front",
            location=(0.0, -5.8, 2.35),
            rotation=(math.radians(78), 0.0, 0.0),
            energy=850,
            size=7.8,
            size_y=7.8,
            color=(1.0, 0.985, 0.97),
        )

        # Relleno frontal superior
        add_area_light(
            name="Fill_Front_Upper",
            location=(0.0, -4.6, 3.35),
            rotation=(math.radians(74), 0.0, 0.0),
            energy=320,
            size=6.2,
            size_y=6.2,
            color=(1.0, 1.0, 1.0),
        )

        # Rebote frontal bajo
        add_area_light(
            name="Bounce_Front_Low",
            location=(0.0, -3.2, 0.85),
            rotation=(math.radians(60), 0.0, 0.0),
            energy=180,
            size=5.8,
            size_y=3.8,
            color=(1.0, 0.99, 0.97),
        )

        # Laterales suaves
        add_area_light(
            name="Fill_Left",
            location=(-3.8, -2.4, 2.3),
            rotation=(math.radians(76), 0.0, math.radians(32)),
            energy=220,
            size=4.8,
            size_y=4.8,
            color=(0.98, 0.99, 1.0),
        )

        add_area_light(
            name="Fill_Right",
            location=(3.8, -2.4, 2.3),
            rotation=(math.radians(76), 0.0, math.radians(-32)),
            energy=220,
            size=4.8,
            size_y=4.8,
            color=(0.98, 0.99, 1.0),
        )

        # Cenital muy suave para evitar franja negra arriba
        add_area_light(
            name="Top_Soft",
            location=(0.0, -0.8, 4.6),
            rotation=(math.radians(90), 0.0, 0.0),
            energy=120,
            size=5.4,
            size_y=5.4,
            color=(1.0, 1.0, 1.0),
        )

    def create_front_camera() -> bpy.types.Object:
        bpy.ops.object.camera_add(location=(mm(w * 0.5), -mm(max(w, h) * 1.48), mm(h * 0.52)))
        camera = bpy.context.object
        camera.name = "Camera_Front"
        camera.data.type = "ORTHO"
        camera.data.ortho_scale = mm(max(w * 1.36, h * 1.18))
        camera.rotation_euler = (1.5708, 0.0, 0.0)
        return camera

    def create_angle_camera() -> bpy.types.Object:
        target = Vector((mm(w * 0.5), mm(d * 0.40), mm(h * 0.54)))
        bpy.ops.object.camera_add(location=(mm(w * 1.12), -mm(max(w, h) * 1.30), mm(h * 0.73)))
        camera = bpy.context.object
        camera.name = "Camera_Angle"
        direction = target - camera.location
        camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        camera.data.lens = 44
        return camera

    def save_report(report: dict) -> None:
        report_path = output_dir / "layout_report.json"
        data = {
            "project_name": spec["project_name"],
            "height": report,
            "remaining_distribution": remaining_distribution,
            "dvd_count": dvd_count,
            "boxset_count": boxset_count,
            "book_count": book_count,
        }
        report_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    openings = expand_openings()
    height_report = calculate_height_report(openings)
    openings = distribute_remaining_space(openings, height_report["remaining"])
    height_report = calculate_height_report(openings)

    print("\nHEIGHT REPORT")
    print("--------------------")
    print(f"Usable height: {height_report['usable_height']} mm")
    print(f"Required height: {height_report['required_height']} mm")
    print(f"Remaining: {height_report['remaining']} mm")
    print(f"Distribution: {remaining_distribution}")

    create_structure()
    create_internal_shelves(openings)
    create_back_panels()
    populate_visuals(openings)

    setup_floor()
    setup_lights()

    front_camera = create_front_camera()
    angle_camera = create_angle_camera()

    render_png(front_camera, output_dir / "render_front.png")
    render_png(angle_camera, output_dir / "render_angle.png")

    save_report(height_report)

    blend_path = output_dir / f"{spec['project_name']}.blend"
    export_blend(blend_path)

    glb_path = output_dir / f"{spec['project_name']}.glb"
    export_glb(glb_path)

    print(f"\nDVDs: {dvd_count}")
    print(f"Boxsets: {boxset_count}")
    print(f"Books: {book_count}")
    print("\nDONE")


if __name__ == "__main__":
    main()
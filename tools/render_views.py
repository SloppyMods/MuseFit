"""Render a build standing, with the skin bright cyan so any skin showing through cloth is easy to see. New file for MuseFit
(simplified from XIVAutoFit tools/dionys_render.py: no test poses; they need XIVAutoFit's pose table, see HANDOFF there).

    PATH=/usr/bin:/bin blender -b --factory-startup --disable-autoexec -P render_views.py -- <build.glb> <out prefix> [centre height m (1.15)] [view width m (0.9)]

Writes <prefix>_<view>.png for view = front, back, side, q34, and <prefix>_side_cut.png: the side view with everything on
the camera's side of the body's middle plane cut away, so the skin and cloth profiles at the chest can be compared.
Refuses to overwrite a PNG. Not a game render: Workbench shading, simulated lighting.
"""
import math
import os
import sys

import bpy

CLOTH_COLOURS = ((0.35, 0.4, 0.5, 1), (0.3, 0.5, 0.4, 1), (0.5, 0.45, 0.3, 1), (0.45, 0.35, 0.5, 1))
VIEWS = {"front": ((0, -3), (90, 0, 0)), "back": ((0, 3), (90, 0, 180)), "side": ((3, 0), (90, 0, 90)), "q34": ((2.1213, -2.1213), (90, 0, 45))}


def material_name(obj):
    slot = obj.material_slots[0] if obj.material_slots else None
    return slot.material.name if slot and slot.material else ""


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    source, prefix = args[0], args[1]
    centre = float(args[2]) if len(args) > 2 else 1.15
    width = float(args[3]) if len(args) > 3 else 0.9
    targets = [f"{prefix}_{v}.png" for v in VIEWS] + [f"{prefix}_side_cut.png"]
    taken = [t for t in targets if os.path.exists(t)]
    if taken:
        sys.exit(f"refusing to overwrite {taken}")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=source)
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("mesh ")]
    for obj in meshes:
        if material_name(obj).startswith("/mt_c0201b0001_"):
            obj.color = (0, 1, 1, 1)
        else:
            obj.color = CLOTH_COLOURS[(int(obj.name.split()[1].split(".")[0]) - 1) % 4]
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_cavity = True
    scene.render.resolution_x = scene.render.resolution_y = 900
    camera = bpy.data.objects.new("c", bpy.data.cameras.new("c"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = width
    camera.data.clip_end = 20
    for view, ((x, y), rotation) in VIEWS.items():
        camera.location = (x, y, centre)
        camera.rotation_euler = tuple(math.radians(a) for a in rotation)
        scene.render.filepath = f"{prefix}_{view}.png"
        bpy.ops.render.render(write_still=True)
    (x, y), rotation = VIEWS["side"]
    camera.location = (x, y, centre)
    camera.rotation_euler = tuple(math.radians(a) for a in rotation)
    camera.data.clip_start = 3.0  # the camera is 3 m from the middle plane, so everything nearer is cut away
    scene.render.filepath = f"{prefix}_side_cut.png"
    bpy.ops.render.render(write_still=True)


main()

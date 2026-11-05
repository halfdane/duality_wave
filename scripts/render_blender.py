"""Render the README images from the meshes written by render.py.

Run with: blender -b -P render_blender.py -- <mesh dir> <image dir>
`task render` does this for you.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

MESH_DIR, IMAGE_DIR = sys.argv[sys.argv.index("--") + 1:][:2]

COLORS = {
    "keywell": (0.03, 0.17, 0.28, 1),
    "keyplate": (0.75, 0.5, 0.1, 1),
    "bottom": (0.1, 0.11, 0.12, 1),
    "switches": (0.03, 0.03, 0.035, 1),
    "caps": (0.5, 0.51, 0.54, 1),
    "xiao": (0.02, 0.1, 0.06, 1),
    "usb": (0.85, 0.85, 0.88, 1),
    "magnets": (0.85, 0.85, 0.88, 1),
}
METALS = ("usb", "magnets")
SIZE = (1800, 1100)
SAMPLES = 64


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = SIZE
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 90
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    nodes, links = world.node_tree.nodes, world.node_tree.links
    nodes.clear()
    # camera rays see a plain backdrop, reflections see a gradient so metal does not look flat
    plain = nodes.new("ShaderNodeBackground")
    plain.inputs["Color"].default_value = (0.93, 0.94, 0.96, 1)
    plain.inputs["Strength"].default_value = 0.55
    coords = nodes.new("ShaderNodeTexCoord")
    split = nodes.new("ShaderNodeSeparateXYZ")
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.3
    ramp.color_ramp.elements[0].color = (0.03, 0.03, 0.035, 1)
    ramp.color_ramp.elements[1].position = 0.7
    ramp.color_ramp.elements[1].color = (0.8, 0.82, 0.85, 1)
    gradient = nodes.new("ShaderNodeBackground")
    gradient.inputs["Strength"].default_value = 0.7
    camera_ray = nodes.new("ShaderNodeLightPath")
    mix = nodes.new("ShaderNodeMixShader")
    output = nodes.new("ShaderNodeOutputWorld")
    links.new(coords.outputs["Generated"], split.inputs["Vector"])
    links.new(split.outputs["Z"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], gradient.inputs["Color"])
    links.new(camera_ray.outputs["Is Camera Ray"], mix.inputs["Fac"])
    links.new(gradient.outputs["Background"], mix.inputs[1])
    links.new(plain.outputs["Background"], mix.inputs[2])
    links.new(mix.outputs["Shader"], output.inputs["Surface"])
    scene.world = world
    return scene


def material(name, color, roughness=0.45, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def load(kind, side, offset=(0, 0, 0)):
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=os.path.join(MESH_DIR, f"{kind}_{side}.stl"))
    obj = (set(bpy.data.objects) - before).pop()
    obj.location = Vector(offset)
    if kind in METALS:
        obj.data.materials.append(material(f"{kind}_{side}", COLORS[kind], roughness=0.25, metallic=1.0))
    else:
        obj.data.materials.append(material(f"{kind}_{side}", COLORS[kind], roughness=0.6 if kind == "caps" else 0.4))
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    obj.select_set(False)
    return obj


def bounds(objects):
    bpy.context.view_layer.update()
    corners = [obj.matrix_world @ Vector(c) for obj in objects for c in obj.bound_box]
    low = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    high = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    return low, high


def add_lights(center, radius):
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.0
    sun.angle = math.radians(6)
    obj = bpy.data.objects.new("sun", sun)
    obj.rotation_euler = (math.radians(45), math.radians(10), math.radians(-35))
    bpy.context.scene.collection.objects.link(obj)

    fill = bpy.data.lights.new("fill", "AREA")
    fill.energy = 4000
    fill.size = radius
    obj = bpy.data.objects.new("fill", fill)
    obj.location = center + Vector((-radius, -radius, radius * 1.5))
    obj.rotation_euler = (math.radians(45), 0, math.radians(-40))
    bpy.context.scene.collection.objects.link(obj)


def add_floor(low, radius):
    bpy.ops.mesh.primitive_plane_add(size=radius * 12, location=((low.x), (low.y), low.z - 0.05))
    floor = bpy.context.active_object
    floor.data.materials.append(material("floor", (0.72, 0.73, 0.75, 1), roughness=0.9))


def add_camera(center, radius, direction, ortho=False):
    cam_data = bpy.data.cameras.new("camera")
    cam = bpy.data.objects.new("camera", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    direction = Vector(direction).normalized()
    if ortho:
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = radius * 2.1
        cam.location = center + direction * radius * 4
    else:
        cam_data.lens = 55
        fov = 2 * math.atan(cam_data.sensor_width / 2 / cam_data.lens)
        cam.location = center + direction * radius / math.sin(fov / 2) * 1.3
    target = bpy.data.objects.new("target", None)
    target.location = center
    bpy.context.scene.collection.objects.link(target)
    track = cam.constraints.new("TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"
    bpy.context.scene.camera = cam


def render(name, objects, direction, ortho=False, flip=False, zoom=1.0):
    if flip:
        # look at the underside: turn the model over so it rests on the floor
        low, high = bounds(objects)
        pivot = (low + high) / 2
        for obj in objects:
            obj.location = pivot + Vector((obj.location.x - pivot.x, -(obj.location.y - pivot.y), -(obj.location.z - pivot.z)))
            obj.rotation_euler = (math.pi, 0, 0)
        bpy.context.view_layer.update()
    low, high = bounds(objects)
    center = (low + high) / 2
    radius = (high - low).length / 2 / zoom
    add_floor(low, radius)
    add_lights(center, radius)
    add_camera(center, radius, direction, ortho)
    path = os.path.join(IMAGE_DIR, f"{name}.jpg")
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("rendered", path)


def assembled(sides=("left", "right"), kinds=("keywell", "keyplate", "bottom", "switches", "caps", "xiao", "usb", "magnets")):
    return [load(kind, side) for side in sides for kind in kinds]


os.makedirs(IMAGE_DIR, exist_ok=True)

reset_scene()
render("hero", assembled(), direction=(0.25, -1.0, 0.85), zoom=1.3)

reset_scene()
render("top", assembled(), direction=(0, 0, 1), ortho=True, zoom=1.2)

reset_scene()
render("bottom", assembled(kinds=("keywell", "bottom", "xiao", "usb")), direction=(0.25, -1.0, 0.85), flip=True, zoom=1.3)

reset_scene()
exploded = [
    load("keywell", "left", (0, 0, 0)),
    load("magnets", "left", (0, 0, 0)),
    load("keyplate", "left", (0, 0, -26)),
    load("switches", "left", (0, 0, -26)),
    load("caps", "left", (0, 0, -26)),
    load("xiao", "left", (0, 0, -26)),
    load("usb", "left", (0, 0, -26)),
    load("bottom", "left", (0, 0, -52)),
]
render("exploded", exploded, direction=(0.9, -1.0, 0.75), zoom=0.95)

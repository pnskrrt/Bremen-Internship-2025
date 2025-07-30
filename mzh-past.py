{\rtf1\ansi\ansicpg1252\cocoartf2761
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import bpy\
import bmesh\
import math\
from mathutils import Vector, Euler\
\
def select_object(name):\
    #Select the object by name and make it active\
    obj = bpy.data.objects.get(name)\
    if not obj:\
        raise Exception(f"Object '\{name\}' not found.")\
    bpy.context.view_layer.objects.active = obj\
    obj.select_set(True)\
    return obj\
\
def remove_roof_floor_thin_faces(obj, normal_angle_threshold=0.3, thin_face_threshold=0.02):\
    #Remove faces that are nearly horizontal(roof or floor) or faces with very small area(thin glass or thin parts)\
    \
    bpy.ops.object.mode_set(mode='EDIT')\
    bm = bmesh.from_edit_mesh(obj.data)\
    faces_to_delete = []\
    for face in bm.faces:\
        angle = face.normal.angle(Vector((0, 0, 1)))  # Angle with Z-axis\
        if angle < normal_angle_threshold or angle > math.pi - normal_angle_threshold:\
            faces_to_delete.append(face)\
            continue\
        if face.calc_area() < thin_face_threshold:\
            faces_to_delete.append(face)\
\
    #Delete selected faces\
    bmesh.ops.delete(bm, geom=faces_to_delete, context='FACES')\
    bmesh.update_edit_mesh(obj.data)\
    bpy.ops.object.mode_set(mode='OBJECT')\
\
def remove_large_area_faces(obj, area_threshold=0.05):\
    #Remove faces that have an area larger than a given threshold\
    #Useful to clear large flat surfaces for bare structure effect\
    bpy.ops.object.mode_set(mode='EDIT')\
    bm = bmesh.from_edit_mesh(obj.data)\
    faces_to_remove = [f for f in bm.faces if f.calc_area() > area_threshold]\
    print(f"Removing \{len(faces_to_remove)\} faces with area > \{area_threshold\}")\
    for f in faces_to_remove:\
        bm.faces.remove(f)\
    bmesh.update_edit_mesh(obj.data)\
    bpy.ops.object.mode_set(mode='OBJECT')\
\
def apply_modifiers_and_smooth(obj):\
    #Apply Solidify and Bevel modifiers to add thickness and rounded edges, and enable smooth shading on the mesh\
    solidify = obj.modifiers.new(name="Solidify", type='SOLIDIFY')\
    solidify.thickness = 0.05\
\
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')\
    bevel.width = 0.01\
    bevel.segments = 3\
    bevel.limit_method = 'ANGLE'\
    bevel.angle_limit = math.radians(30)\
\
    mesh = obj.data\
    for face in mesh.polygons:\
        face.use_smooth = True\
\
def add_ground_plane(obj):\
    #Add a ground plane underneath the building, sized and positioned based on the building's bounding box\
    #Adds a Solidify modifier to make the plane thicker\
  \
    bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]\
    min_x = min(v.x for v in bbox)\
    max_x = max(v.x for v in bbox)\
    min_y = min(v.y for v in bbox)\
    max_y = max(v.y for v in bbox)\
    min_z = min(v.z for v in bbox)\
\
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))\
    plane = bpy.context.active_object\
    plane.name = "Ground_Plane"\
\
    # Scale plane to slightly larger than building footprint\
    plane.scale.x = (max_x - min_x) / 2 * 1.1\
    plane.scale.y = (max_y - min_y) / 2 * 1.1\
\
    # Position plane just below the lowest point of building\
    plane.location.x = (max_x + min_x) / 2\
    plane.location.y = (max_y + min_y) / 2\
    plane.location.z = min_z - 0.01\
\
    # Add thickness to ground plane\
    solid = plane.modifiers.new(name="Ground_Solid", type='SOLIDIFY')\
    solid.thickness = 0.05\
\
    return plane\
\
#Create a simple base cube under the building as a foundation\
#If a base with the same name exists, it will be removed first\
#Assigns a simple gray material\
def create_base(size_x=10, size_y=10, thickness=0.2, base_name="Building_Base"):\
    if base_name in bpy.data.objects:\
        bpy.data.objects.remove(bpy.data.objects[base_name], do_unlink=True)\
\
    bpy.ops.mesh.primitive_cube_add(size=1)\
    base = bpy.context.active_object\
    base.name = base_name\
\
    #Scale base to given size and position it below ground level\
    base.scale = (size_x / 2, size_y / 2, thickness / 2)\
    base.location = (0, 0, -thickness / 2)\
\
    #Create or assign gray material\
    mat = bpy.data.materials.get("Base_Material")\
    if mat is None:\
        mat = bpy.data.materials.new(name="Base_Material")\
        mat.diffuse_color = (0.2, 0.2, 0.2, 1)  # Dark gray\
    if len(base.data.materials):\
        base.data.materials[0] = mat\
    else:\
        base.data.materials.append(mat)\
\
    print("Created base plane")\
    return base\
\
#Create a rectangular beam between two points with given thickness\
#The beam is rotated to align with the vector from start to end\
def create_scaffold_beam(start, end, thickness, name):\
    vec = end - start\
    length = vec.length\
    loc = (start + end) / 2\
\
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)\
    beam = bpy.context.active_object\
    beam.name = name\
\
    #Scale beam along length and thickness\
    beam.scale = (length / 2, thickness, thickness)\
\
    #Calculate rotation angle around Z axis to align beam correctly\
    angle = vec.to_2d().angle_signed(Vector((1, 0)))\
    beam.rotation_euler = Euler((0, 0, angle), 'XYZ')\
\
    return beam\
\
#Example of usage:\
obj_name = "MZH_FINAL"\
obj = select_object(obj_name)\
remove_roof_floor_thin_faces(obj)\
remove_large_area_faces(obj)\
apply_modifiers_and_smooth(obj)\
add_ground_plane(obj)\
create_base()\
\
#Create one example scaffold beam\
start_point = Vector((0, 0, 0))\
end_point = Vector((2, 3, 0))\
create_scaffold_beam(start_point, end_point, 0.05, "Scaffold_Beam_01")\
}
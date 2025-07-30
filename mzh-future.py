import bpy
import bmesh
import math
import random

#Body

obj = bpy.context.active_object
mesh = obj.data

bm = bmesh.new()
bm.from_mesh(mesh)

# --- Wave Facade (ผิวโค้ง) ---
use_wave = True
amplitude = 15
frequency = 0.2
falloff_power = 0.8

# --- Layer Offset (ซ้อนชั้น) ---
layer_height = 10      # ความสูงแต่ละชั้น
offset_x = 0.3            # เยื้อง X ต่อชั้น
offset_z = 0.25            # เพิ่ม Z ต่อชั้น
alternate = True         # สลับทิศชั้น

for v in bm.verts:
    x = v.co.x
    layer = int(x / layer_height)
    
    # --- เยื้องตาม X + Z ---
    direction = -1
    v.co.z += offset_z * layer * direction

    # --- WAVE FAÇADE (ยังใช้ได้อยู่) ---
    if use_wave:
        wave = math.sin(x * frequency)
        wave *= abs(wave) ** falloff_power
        v.co.z += 0.3 * amplitude * wave


bm.to_mesh(mesh)
bm.free()

#------------------------------------------------------------------------------#
#each floor

obj = bpy.context.active_object
mesh = obj.data

# ลบ Vertex Group ชื่อเดิมก่อน (กันซ้อน)
fl_name = "AllFloor"
if fl_name in obj.vertex_groups:
    obj.vertex_groups.remove(obj.vertex_groups[fl_name])
fl = obj.vertex_groups.new(name=fl_name)

bm = bmesh.new()
bm.from_mesh(mesh)
bm.verts.ensure_lookup_table()

# Parameters
num_layers = 4               # จำนวนชั้นกันสาด
layer_spacing_eachlayer = [8.0, 7.4, 7.9, 8.8]          # ระยะห่างแต่ละชั้น
falloff = 0.5                # นุ่ม/ชัน
wave_amplitude = 1.3
wave_frequency = 0.6

# ความยื่นแต่ละชั้น (ไม่เท่ากัน)
push_strengths = [random.uniform(2.5, 6.4) for _ in range(num_layers)]

# ความหนาแต่ละชั้น (ไม่เท่ากัน)
layer_thicknesses = [random.uniform(0.5, 1.8) for _ in range(num_layers)]

# หาค่า Y max (ความสูงสุดของตึก)
y_max = max(v.co.y for v in bm.verts)
selected_verts = []

for i in range(num_layers):
    layer_spacing = layer_spacing_eachlayer[i]
    thickness = layer_thicknesses[i]
    layer_y_top = (y_max - 16) - i * layer_spacing
    layer_y_bottom = layer_y_top - thickness
    push_strength = push_strengths[i]

    for v in bm.verts:
        y = v.co.y
        if layer_y_bottom <= y <= layer_y_top:
            factor = ((y - layer_y_bottom) / (layer_y_top - layer_y_bottom)) ** falloff

            # ดันออกจากจุดศูนย์กลาง (X-Z)
            center_vec = math.sqrt(v.co.x**2 + v.co.z**2)
            if center_vec > 0:
                norm_x = v.co.x / center_vec
                norm_z = v.co.z / center_vec
            else:
                norm_x = 0
                norm_z = 0

            # ดันออกทุกด้าน
            v.co.x += push_strength * factor * norm_x * 1.2
            v.co.z += push_strength * factor * norm_z * 2

            # คลื่น
            wave = math.sin(y * wave_frequency)
            wave2 = math.cos(y * wave_frequency * 0.8)
            v.co.x += wave_amplitude * wave * factor
            v.co.z += wave_amplitude * wave2 * factor

            selected_verts.append(v.index)

bm.to_mesh(mesh)
bm.free()

# ใส่เข้า Vertex Group ทีหลัง (บน mesh จริง)
fl.add(selected_verts, 1.0, 'ADD')

#roof modifier
solid = obj.modifiers.new(name="RoofSolid", type='SOLIDIFY')
solid.thickness = 1.25 
solid.offset = 0.12       
solid.vertex_group = "AllFloor"

deform = obj.modifiers.new(name="RoofTaper", type='SIMPLE_DEFORM')
deform.deform_method = 'TAPER'
deform.deform_axis = 'Z'
deform.factor = 0.15
deform.vertex_group = "AllFloor"

bend = obj.modifiers.new(name="RoofBend", type='SIMPLE_DEFORM')
bend.deform_method = 'BEND'
bend.deform_axis = 'X'
bend.angle = -0.08 
bend.vertex_group = "AllFloor"

#------------------------------------------------------------------------------#

#Roof
obj = bpy.context.active_object
mesh = obj.data
world_matrix = obj.matrix_world 

bm = bmesh.new()
bm.from_mesh(mesh)

# --- Parameters ---
roof_curve_strength = 5.0       # ความสูงโค้ง
roof_influence_range = 12.0      # ความกว้างของ roof area (แกน Z)
roof_y_threshold = 0.98         # ดัดเฉพาะ vertex ที่สูงกว่าเปอร์เซ็นต์นี้ของตึก

# --- คำนวณความสูงของตึก ---
y_vals = [v.co.y for v in bm.verts]
min_y = min(y_vals)
max_y = max(y_vals)
height = max_y - min_y if max_y != min_y else 1

y_threshold = min_y + roof_y_threshold * height

# --- Duplicate ส่วนบนของ mesh ---
roof_faces = []
roof_verts_set = set()

for f in bm.faces:
    if all(v.co.y >= y_threshold for v in f.verts):
        roof_faces.append(f)
        roof_verts_set.update(f.verts)

# เตรียมข้อมูลสำหรับสร้าง mesh ใหม่
old_to_new = {}

# --- Step 3: สร้าง mesh ใหม่ ---
mesh_new = bpy.data.meshes.new("RoofMesh")
obj_new = bpy.data.objects.new("Roof", mesh_new)
bpy.context.collection.objects.link(obj_new)

bm_new = bmesh.new()

# --- STEP FIX: Convert world position → new local position ---
inv_matrix_new = obj_new.matrix_world.inverted()

for v in roof_verts_set:
    world_co = world_matrix @ v.co  # → world space
    local_new_co = inv_matrix_new @ world_co
    new_v = bm_new.verts.new(local_new_co)
    old_to_new[v] = new_v

bm_new.verts.ensure_lookup_table()

# สร้าง faces ใหม่จาก face เดิม
for f in roof_faces:
    try:
        bm_new.faces.new([old_to_new[v] for v in f.verts])
    except:
        # กันกรณี face ซ้ำ
        continue

bm_new.faces.ensure_lookup_table()


for v in bm_new.verts:
    v.co.z += 1
    v.co.y += 2 * (3 if v.co.y >=0 else -0.8)
    v.co.x += 2 * (0.6 if v.co.x >=0 else -3)

bm_new.to_mesh(mesh_new)
bm_new.free()
bm.free()

# --- Add Solidify Modifier to make roof thick ---
solidify = obj_new.modifiers.new(name="Roof_Thickness", type='SOLIDIFY')
solidify.thickness = 3  # ปรับได้ตามใจ
solidify.offset = 0  # 1 = หนาขึ้นด้านบน, -1 = ด้านล่าง, 0 = ขยายทั้งสองฝั่ง

#------------------------------------------------------------------------------#

# Base

bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0.5))

# ปรับขนาดฐาน (ความกว้าง x ยาว x สูง)
base = bpy.context.object
base.name = "Building_Base"
base.scale[0] = 40    # กว้าง
base.scale[1] = 40    # ลึก
base.scale[2] = 1.0  # ความสูงของฐาน

# สร้างวัสดุสีเทาให้ฐาน
mat = bpy.data.materials.new(name="Base_Material")
mat.diffuse_color = (0.5, 0.5, 0.5, 1)  # สีเทา
base.data.materials.append(mat)

print("✅ สร้างฐานตึกเรียบร้อยแล้ว!")

#------------------------------------------------------------------------------#

objects_to_merge = ["Building_Base","MZH", "Roof"]

# Apply Modifier ให้ทุก object ก่อน
for obj_name in objects_to_merge:
    obj = bpy.data.objects.get(obj_name)
    if obj:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)

        for modifier in obj.modifiers:
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        print(f"✅ Applied modifiers on {obj.name}")
    else:
        print(f"❌ Object not found: {obj_name}")

obj_base = bpy.data.objects.get("Building_Base")
obj_building = bpy.data.objects.get("MZH")
obj_roof = bpy.data.objects.get("Roof")

if obj_building and obj_roof and obj_base:
    # เลือกทั้งสองออบเจกต์
    bpy.ops.object.select_all(action='DESELECT')
    obj_building.select_set(True)
    obj_roof.select_set(True)
    obj_base.select_set(True)
    
    bpy.context.view_layer.objects.active = obj_building  # set active object เป็นตึก (หลัก)
    
    bpy.ops.object.join()  # รวมเข้าด้วยกัน!
    
    print("✅ รวมตึกและหลังคาสำเร็จแล้ว!")

bpy.ops.object.editmode_toggle()
bpy.ops.mesh.remove_doubles(threshold=0.0001)
bpy.ops.object.editmode_toggle()
    
#------------------------------------------------------------------------------#

#Modify Building

obj = bpy.context.active_object
mesh = obj.data

bm = bmesh.new()
bm.from_mesh(mesh)

# --- Parameters ---
use_wave = True
amplitude = 15
frequency = 0.1
falloff_power = 0.8

layer_height = 10 
offset_x = 0.3            
alternate = True         

# --- คำนวณความสูงของวัตถุ ---
y_vals = [v.co.y for v in bm.verts]
min_y = min(y_vals)
max_y = max(y_vals)
height = max_y - min_y if max_y != min_y else 1  # ป้องกันหาร 0

for v in bm.verts:
    x = v.co.x
    layer = int(x / layer_height)
    
    direction = -1
    v.co.y += direction * offset_x * layer

    if use_wave:
        # แรงดัดตามความสูง (ฐานโดน 0, ยอดโดนเต็ม)
        influence = (v.co.y - min_y) / height

        wave = math.sin(x * frequency)
        wave *= abs(wave) ** falloff_power
        wave *= 0.25 * amplitude

        v.co.y += wave * influence  # ดัดเฉพาะส่วนบน

bm.to_mesh(mesh)
bm.free()

#------------------------------------------------------------------------------#

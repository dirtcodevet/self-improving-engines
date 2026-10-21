# Blender-side: apply a fit_camera.py solution to the scene camera. Expects CAM_JSON.
import bpy, json
from mathutils import Matrix, Vector

c = json.load(open(CAM_JSON))
cam = bpy.context.scene.camera
cam.data.lens = c["lens"]
cam.data.sensor_width = c["sensor_width"]
cam.data.sensor_fit = 'HORIZONTAL'
cam.matrix_world = Matrix.Translation(Vector(c["location"])) @ Matrix(c["rot_matrix"]).to_4x4()
print("camera set: lens", c["lens"], "loc", [round(v, 3) for v in c["location"]])

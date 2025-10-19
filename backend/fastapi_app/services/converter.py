import subprocess
import os
from fastapi import HTTPException

def convert_glb_to_usdz(glb_path: str, output_dir: str = "models") -> str:
    """
    Converts a .glb file to .usdz using Blender's command-line interface.
    Requires Blender to be installed and in your PATH.
    """
    usdz_path = os.path.splitext(glb_path)[0] + ".usdz"
    os.makedirs(output_dir, exist_ok=True)

    try:
        subprocess.run([
            "blender",
            "--background",
            "--python-expr",
            f"import bpy; bpy.ops.import_scene.gltf(filepath='{glb_path}'); bpy.ops.export_scene.usdz(filepath='{usdz_path}')"
        ], check=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"USDZ conversion failed: {str(e)}")

    return usdz_path
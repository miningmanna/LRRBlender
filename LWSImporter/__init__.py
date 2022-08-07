
bl_info = {
    "name": "LRR LWS/LWO Importer",
    "author": "miningmanna",
    "version": (0, 0, 1),
    "blender": (3, 2, 1),
    "location": "Files -> Import-Export",
    "description": "Plugin for importing LightWave Scenes (LWS) and LightWave Objects (LWO) for Lego Rock Raiders",
    "warning": "",
    "doc_url": "",
    "category": "Import-Export"
}

import bpy

from .operators import LWSImporter
from .operators import LWOImporter


def menu_func_import(self, context):
    self.layout.operator(LWOImporter.LWOImporter.bl_idname,
                         text="LRR LightWave Object (.lwo)")
    self.layout.operator(LWSImporter.LWSImporter.bl_idname,
                         text="LRR LightWave Scene (.lws)")

def register():
    bpy.utils.register_class(LWOImporter.LWOImporter)
    bpy.utils.register_class(LWSImporter.LWSImporter)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.utils.unregister_class(LWSImporter.LWSImporter)
    bpy.utils.unregister_class(LWOImporter.LWOImporter)


if __name__ == "__main__":
    register()
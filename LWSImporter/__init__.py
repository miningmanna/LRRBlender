
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

classes = (
    LWOImporter.LWOImporter,
    LWOImporter.LRRLWO_PT_import_settings,
    LWSImporter.LWSImporter,
    LWSImporter.LRRLWS_PT_import_settings
    )

def menu_func_import(self, context):
    self.layout.operator(LWOImporter.LWOImporter.bl_idname,
                         text="LRR LightWave Object (.lwo)")
    self.layout.operator(LWSImporter.LWSImporter.bl_idname,
                         text="LRR LightWave Scene (.lws)")

def register():
    for c in classes:
        bpy.utils.register_class(c)
    
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
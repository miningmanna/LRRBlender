import bpy
from bpy_extras.io_utils import ImportHelper
from bpy.props import (
        BoolProperty,
        EnumProperty,
        FloatProperty,
        StringProperty,
        )

class LRRLWS_PT_import_settings(bpy.types.Panel):
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOL_PROPS"
    bl_label = "Settings"
    bl_parent_id = "FILE_PT_operator"
    
    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        
        return operator.bl_idname == "IMPORT_SCENE_OT_lrrlws"
    
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        sfile = context.space_data
        operator = sfile.active_operator
        
        layout.prop(operator, "shared_path")
        layout.prop(operator, "reuse_assets")
        layout.prop(operator, "use_uv_files")

from .. import LwsLoad
from pathlib import Path
class LWSImporter(bpy.types.Operator, ImportHelper):
    """LRR LWS Importer"""
    bl_idname = "import_scene.lrrlws"
    bl_label = "Import LRR LWS"
    filename_ext = ".lws"
    filter_glob: StringProperty(default="*.lws", options={'HIDDEN'})
    
    shared_path: StringProperty(
        name = "Shared asset folder",
        description = "Path to the folder with assets shared between multiple models",
        default = "",
        subtype = "DIR_PATH"
        )
    
    reuse_assets: BoolProperty(
        name = "Reuse materials and textures",
        description = "Reuse materials and texture if they already have been loaded into blender",
        default = True
        )
    
    use_uv_files: BoolProperty(
        name = "Use UV files",
        description = "Applies UV coordiantes from UV file if present",
        default = True
        )
    
    
    
    def execute(self, context):
        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "filter_glob",
                                            ))
        
        path = Path(keywords["filepath"])
        dir = path.parent
        
        lws_anim = LwsLoad.load_lws(str(path))
        
        # Create base to put stuff into
        base = bpy.data.objects.new(path.name, None)
        collection = bpy.context.collection
        if not collection:
            collection = bpy.data.collections.new(path.name)
            bpy.context.scene.collection.children.link(collection)
        collection.objects.link(base)
        
        
        # Create the objects
        objects = []
        for x in lws_anim.objects:
            
            obj = None
            if x.filepath:
                # Load lwo
                raw_lwo_path = Path(x.filepath)
                lwo_path = dir.joinpath(raw_lwo_path.name)
                
                if not lwo_path.exists():
                    if keywords["shared_path"] != "":
                        lwo_path = Path(keywords["shared_path"]).joinpath(raw_lwo_path.name)
                
                status = None
                try:
                    status = bpy.ops.import_mesh.lrrlwo(filepath = str(lwo_path), shared_path = keywords["shared_path"], reuse_assets = keywords["reuse_assets"], use_uv_files = keywords["use_uv_files"])
                except Exception as e:
                    print("Failed to load {lwo_path} :")
                    print(e)
                
                if status != {"FINISHED"}:
                    # Create empty
                    obj = bpy.data.objects.new(x.name, None)
                    collection.objects.link(obj)
                else:
                    obj = bpy.context.object
                    obj.name = x.name
            else:
                # Create empty
                obj = bpy.data.objects.new(x.name, None)
                collection.objects.link(obj)
            
            # Set rotation mode
            obj.rotation_mode = "ZYX"
            
            # Set keyframe data
            for frame in x.keyframes:
                fdata = x.keyframes[frame]
                
                obj.location = fdata[0]
                obj.keyframe_insert("location", frame = frame)
                
                rot = fdata[1]
                # Weird conversion
                obj.rotation_euler = (rot[1], rot[0], rot[2])
                obj.keyframe_insert("rotation_euler", frame = frame)
                
                obj.scale = fdata[2]
                obj.keyframe_insert("scale", frame = frame)
            
            # Set alpha keyframes
            for frame in x.alphaKeyframes:
                obj["Alpha"] = 1.0 - float(x.alphaKeyframes[frame])
                obj.keyframe_insert("[\"Alpha\"]", frame = frame)
            
            # Make sure the keyframes interpolate linear
            action = obj.id_data.animation_data.action
            for fcurve in action.fcurves:
                for keyframe in fcurve.keyframe_points:
                    keyframe.interpolation = "LINEAR"
            
            # Update data to make keyframes work, but only if we have data
            if obj.data:
                obj.data.update()
            
            objects.append(obj)
        
        # Parent the objects
        for i in range(len(lws_anim.objects)):
            obj_data = lws_anim.objects[i]
            if obj_data.parent == -1:
                objects[i].parent = base
            else:
                objects[i].parent = objects[obj_data.parent - 1]
        
        for odata in lws_anim.objects:
            print(odata.name, f"Parent: {odata.parent}")
        
        # Set frames
        bpy.context.scene.frame_start = lws_anim.firstFrame
        bpy.context.scene.frame_end = lws_anim.lastFrame
        bpy.context.scene.frame_set(bpy.context.scene.frame_start)
        
        # Flip normals if they have been scaled with -1
        for obj in objects:
            if obj.matrix_world.determinant() < 0 and obj.data:
                print(f"Flipping normals of {obj.name}")
                bpy.ops.object.select_all(action='DESELECT')
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode = "EDIT")
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.flip_normals()
                bpy.ops.object.mode_set(mode = "OBJECT")
        
        return {"FINISHED"}
    
    def draw(self, context):
        pass

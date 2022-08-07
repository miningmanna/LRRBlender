import bpy
from bpy_extras.io_utils import ImportHelper
from bpy.props import (
        BoolProperty,
        EnumProperty,
        FloatProperty,
        StringProperty,
        )

from .. import LwsLoad
from pathlib import Path
class LWSImporter(bpy.types.Operator, ImportHelper):
    """LRR LWS Importer"""
    bl_idname = "import_scene.lws"
    bl_label = "Import LWS"
    filename_ext = ".lws"
    filter_glob: StringProperty(default="*.lws", options={'HIDDEN'})
    
    def execute(self, context):
        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "filter_glob",
                                            ))
        
        path = Path(keywords["filepath"])
        dir = path.parent
        
        lws_anim = LwsLoad.load_lws(str(path))
        LwsLoad.print_anim(lws_anim)
        
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
                lwo_path = str(dir.joinpath(raw_lwo_path.name))
                
                status = None
                try:
                    status = bpy.ops.import_mesh.lwo(filepath = lwo_path)
                except Exception as e:
                    print("Failed to load {lwo_path} :")
                    print(e)
                
                if status != {"FINISHED"}:
                    # Create empty
                    obj = bpy.data.objects.new(x.name, None)
                    collection.objects.link(obj)
                else:
                    obj = bpy.context.object
                    print(obj.name, x.name)
                    obj.name = x.name
            else:
                # Create empty
                obj = bpy.data.objects.new(x.name, None)
                collection.objects.link(obj)
            
            print(x.keyframes)
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
                obj["Alpha"] = float(x.alphaKeyframes[frame])
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
        
        print(keywords)
        return {"FINISHED"}
    
    def draw(self, context):
        pass

import bpy
from bpy_extras.io_utils import ImportHelper
from bpy.props import (
        BoolProperty,
        EnumProperty,
        FloatProperty,
        StringProperty,
        )

from .. import LwoLoad
from pathlib import Path
class LWOImporter(bpy.types.Operator, ImportHelper):
    """LRR LWO Importer"""
    bl_idname = "import_mesh.lwo"
    bl_label = "Import LWO"
    filename_ext = ".lwo"
    filter_glob: StringProperty(default="*.lwo", options={'HIDDEN'})
    
    def execute(self, context):
        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "filter_glob",
                                            ))
        
        path = Path(keywords["filepath"])
        dir = path.parent
        
        lwo_data = LwoLoad.load_lwo(keywords["filepath"])
        
        mesh = bpy.data.meshes.new(f"{path.stem} mesh")
        faces = []
        offset = 0
        for size in lwo_data.polVertCount:
            faces.append(tuple(lwo_data.polVerts[offset:offset + size]))
            offset += size
        
        mesh.from_pydata(lwo_data.verts, [], faces)
        
        # Set materials for polygons
        for i in range(len(lwo_data.polSurfId)):
            mesh.polygons[i].material_index = lwo_data.polSurfId[i] - 1
        
        """ Create new uv layer """
        uvd = mesh.uv_layers.new().data
        
        index = 0
        """ Generate materials """
        for surfName in lwo_data.surfNames:
            surf = lwo_data.surfs[surfName]
            
            """ Add new material """
            mat = bpy.data.materials.new(name=surfName)
            mat.blend_method = "BLEND"
            mat.shadow_method = "NONE"
            mat.show_transparent_back = False
            mat.use_backface_culling = not surf.doubleSided
            
            mesh.materials.append(mat)
            mat.use_nodes = True
            tree = mat.node_tree
            index += 1
            
            positions = {
                "Principled BSDF": (10, 300),
                "Transparent BSDF": (10, 400),
                "Geometry": (10, 650),
                "Mix Shader": (300, 400),
                "Material Output": (500, 300),
                "Image Texture": (-540, 300),
                "Attribute": (-440, -150),
                "Math": (-190, -150)
                }
            
            out = tree.nodes["Material Output"]
            
            bsdf = tree.nodes["Principled BSDF"]
            bsdf.inputs["Base Color"].default_value = (*surf.color, 1)
            bsdf.inputs["Specular"].default_value = 0
            
            geom = tree.nodes.new("ShaderNodeNewGeometry")
            
            trans = tree.nodes.new("ShaderNodeBsdfTransparent")
            
            mix = tree.nodes.new("ShaderNodeMixShader")
            mix.inputs[0].default_value = 0.0 # Default no face culling
            
            tree.links.new(mix.outputs[0], out.inputs[0])
            tree.links.new(trans.outputs[0], mix.inputs[2])
            tree.links.new(bsdf.outputs[0], mix.inputs[1])
            
            if not surf.doubleSided:
                tree.links.new(mix.inputs[0], geom.outputs["Backfacing"])
            
            math = tree.nodes.new("ShaderNodeMath")
            math.operation = "MULTIPLY"
            math.inputs[0].default_value = 1.0
            math.use_clamp = True
            
            alpha = tree.nodes.new("ShaderNodeAttribute")
            alpha.attribute_name = "Alpha"
            alpha.attribute_type = "OBJECT"
            
            tree.links.new(alpha.outputs[2], math.inputs[1])
            tree.links.new(math.outputs[0], bsdf.inputs[21])
            
            """ Add texture if present """
            if surf.ctex:
                ctex = surf.ctex
                tex = tree.nodes.new("ShaderNodeTexImage")
                
                """ Load and set image """
                imgpath = dir.joinpath(Path(ctex.filepath).name)
                img = load_texture(imgpath)
                tex.image = img
                tex.extension = "REPEAT"
                
                if ctex.interpolate:
                    tex.interpolation = "Linear"
                else:
                    tex.interpolation = "Closest"
                
                tree.links.new(tex.outputs[0], bsdf.inputs[0])
                tree.links.new(tex.outputs[1], math.inputs[0])
            
            """ Apply positions """
            for node in tree.nodes:
                loc = node.location
                loc.x, loc.y = positions[node.name]
            
            """ Set uv """
            k = 0
            for i in range(len(lwo_data.polSurfId)):
                if lwo_data.polSurfId[i] == index and surf.ctex:
                    """ Map and set uvs """
                    inds = faces[i]
                    for j in range(len(inds)):
                        uvd[k+j].uv = LwoLoad.planar_project(surf.ctex, lwo_data.verts[inds[j]])
                k += lwo_data.polVertCount[i]
            
        
        # Create object
        obj = bpy.data.objects.new(path.stem, mesh)
        """ Create Alpha property """
        obj["Alpha"] = 1.0
        
        # Disable shadows, since LRR does not have shadows
        obj.visible_shadow = False
        
        collection = bpy.context.collection
        if not collection:
            collection = bpy.data.collections.new(path.name)
            bpy.context.scene.collection.children.link(collection)
        collection.objects.link(obj)
        
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        
        return {"FINISHED"}
    
    def draw(self, context):
        pass

import re
from .. import BmpLoad
def load_texture(path):
    
    # if the image is a BMP image with AXXX_ as prefix, use custom loader, otherwise use in-built
    # See if it matches
    match = re.match(r"^[Aa](\d{3})_.*$", path.name)
    if path.suffix.lower() == ".bmp" and not match is None:
        
        # Get the index for the transparent color
        alphaIndex = int(match.group(1))
        
        # Load BMP color table and pixels
        bmp_data = BmpLoad.load_bmp(str(path))
        
        w = bmp_data.width
        h = bmp_data.height
        img = bpy.data.images.new(path.name, w, h)
        
        for y in range(h):
            for x in range(w):
                i = y * w + x
                ind = bmp_data.pixels[i]
                col = bmp_data.colors[ind]
                img.pixels[i*4 + 0] = col[0]
                img.pixels[i*4 + 1] = col[1]
                img.pixels[i*4 + 2] = col[2]
                
                # Set alpha
                if ind == alphaIndex:
                    img.pixels[i*4 + 3] = 0
                else:
                    img.pixels[i*4 + 3] = 1
        
        return img
    else:
        return bpy.data.images.load(str(path))
    

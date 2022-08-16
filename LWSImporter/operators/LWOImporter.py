import bpy
from bpy_extras.io_utils import ImportHelper
from bpy.props import (
        BoolProperty,
        EnumProperty,
        FloatProperty,
        StringProperty,
        )

class LRRLWO_PT_import_settings(bpy.types.Panel):
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOL_PROPS"
    bl_label = "Settings"
    bl_parent_id = "FILE_PT_operator"
    
    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        
        return operator.bl_idname == "IMPORT_MESH_OT_lrrlwo"
    
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        sfile = context.space_data
        operator = sfile.active_operator
        
        layout.prop(operator, "shared_path")
        layout.prop(operator, "reuse_assets")
        layout.prop(operator, "use_uv_files")

import re
from .. import LwoLoad
from .. import UvLoad
from pathlib import Path
class LWOImporter(bpy.types.Operator, ImportHelper):
    """LRR LWO Importer"""
    bl_idname = "import_mesh.lrrlwo"
    bl_label = "Import LWO"
    filename_ext = ".lwo"
    filter_glob: StringProperty(default="*.lwo", options={'HIDDEN'})
    
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
        
        lwo_data = LwoLoad.load_lwo(keywords["filepath"])
        
        # Check if we should find a UV file and load it
        uv_data = None
        uv_file_path = Path(dir.joinpath(path.stem + ".uv"))
        
        # If the file does not exist, try to get one from the shared folder
        if not uv_file_path.exists() and keywords["shared_path"] != "":
            uv_file_path = Path(Path(keywords["shared_path"]).joinpath(uv_file_name))
        
        if uv_file_path.exists():
            uv_data = UvLoad.load_uv(str(uv_file_path))
        
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
        
        # Apply UV file if present and setting is ticked
        if keywords["use_uv_files"] and uv_data:
            k = 0
            for i in range(len(mesh.polygons)):
                polygon = mesh.polygons[i]
                for j in range(len(polygon.vertices)):
                    uvd[polygon.loop_start + j].uv = uv_data.uvs[k + j]
                k += len(polygon.vertices)
        
        index = 0
        """ Generate materials """
        for surfName in lwo_data.surfNames:
            surf = lwo_data.surfs[surfName]
            
            use_uv = keywords["use_uv_files"] and uv_data and surfName in uv_data.material_tex
            
            index += 1
            mat = None
            matname = f"{path.stem}_{surfName}"
            
            # Check if we should reuse assets
            if keywords["reuse_assets"]:
                if matname in bpy.data.materials:
                    mat = bpy.data.materials[matname]
            
            # Create material if not found/used
            if not mat:
                """ Add new material """
                mat = bpy.data.materials.new(name = matname)
                mat.blend_method = "BLEND"
                mat.shadow_method = "NONE"
                mat.show_transparent_back = False
                mat.use_backface_culling = not surf.doubleSided
                
                mat.use_nodes = True
                tree = mat.node_tree
                
                positions = {
                    "Principled BSDF": (10, 300),
                    "Transparent BSDF": (10, 400),
                    "Geometry": (10, 650),
                    "Mix Shader": (300, 400),
                    "Material Output": (500, 300),
                    "Image Texture": (-540, 300),
                    "Attribute": (-440, -150),
                    "Math": (-190, -150),
                    "Mix Shader.001": (10, 850),
                    "Combine HSV": (-440, 700),
                    "Separate HSV": (-440, 500),
                    "Emission": (-190, 650),
                    "Math.001": (-190, 500)
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
                if surf.ctex or use_uv:
                    ctex = surf.ctex
                    tex = tree.nodes.new("ShaderNodeTexImage")
                    
                    """ Load and set image """
                    imgpath = None
                    if use_uv:
                        imgpath = Path(uv_data.material_tex[surfName])
                    elif ctex:
                        imgpath = Path(ctex.filepath)
                    
                    imgname = imgpath.name
                    imgpath = Path(dir.joinpath(imgname))
                    
                    # If the file does not exist, try to get one from the shared folder
                    if not imgpath.exists() and keywords["shared_path"] != "":
                        imgpath = Path(Path(keywords["shared_path"]).joinpath(imgname))
                    
                    sequence_match = re.match(r"^.*[^\d]+(\d{3,})\..*$", imgpath.name)
                    
                    if sequence_match:
                        
                        if keywords["reuse_assets"] and imgname in bpy.data.images:
                            img = bpy.data.images[imgname]
                            tex.image = img
                        else:
                            img = bpy.data.images.load(str(imgpath))
                            img.source = "SEQUENCE"
                            tex.image = img
                        
                        startFrame = int(sequence_match.group(1))
                        stopFrame = startFrame
                        digitSpan = sequence_match.span(1)
                        pad = digitSpan[1] - digitSpan[0]
                        
                        imgdir = imgpath.parent
                        seqImgPrefix = imgname[:digitSpan[0]]
                        seqImgPostfix = imgname[digitSpan[1]:]
                        
                        seqImg = Path(imgdir.joinpath(f"{seqImgPrefix}{str(stopFrame).zfill(pad)}{seqImgPostfix}"))
                        
                        while seqImg.exists():
                            stopFrame += 1
                            seqImg = Path(imgdir.joinpath(f"{seqImgPrefix}{str(stopFrame).zfill(pad)}{seqImgPostfix}"))
                        
                        user = tex.image_user
                        user.use_auto_refresh = True
                        user.use_cyclic = True
                        user.frame_duration = stopFrame - startFrame
                        
                    else:
                        if keywords["reuse_assets"] and imgname in bpy.data.images:
                            # Use existing image
                            img = bpy.data.images[imgname]
                            tex.image = img
                        else:
                            # Load image
                            img = load_texture(imgpath)
                            tex.image = img
                    
                    
                    tex.extension = "REPEAT"
                    
                    if use_uv or ctex.interpolate:
                        tex.interpolation = "Linear"
                    else:
                        tex.interpolation = "Closest"
                    
                    if surf.additive:
                        
                        # Modify shader to display additive
                        mix2 = tree.nodes.new("ShaderNodeMixShader")
                        emission = tree.nodes.new("ShaderNodeEmission")
                        math2 = tree.nodes.new("ShaderNodeMath")
                        sep = tree.nodes.new("ShaderNodeSeparateHSV")
                        comb = tree.nodes.new("ShaderNodeCombineHSV")
                        
                        # Configure default values and settings
                        math2.operation = "MULTIPLY"
                        math2.inputs[0].default_value = 1.0
                        math2.use_clamp = True
                        
                        comb.inputs[2].default_value = 1.0
                        
                        # Create links
                        links = tree.links
                        
                        # Tex -> seperate HSV
                        links.new(tex.outputs[0], sep.inputs[0])
                        
                        # Sep HSV -> Comb HSV
                        links.new(sep.outputs[0], comb.inputs[0])
                        links.new(sep.outputs[1], comb.inputs[1])
                        
                        # Math 2
                        links.new(sep.outputs[2], math2.inputs[0])
                        links.new(math.outputs[0], math2.inputs[1])
                        links.new(math2.outputs[0], mix2.inputs[0])
                        
                        # Emission
                        links.new(comb.outputs[0], emission.inputs[0])
                        
                        # Mix 2
                        links.new(math2.outputs[0], mix2.inputs[0])
                        links.new(trans.outputs[0], mix2.inputs[1])
                        links.new(emission.outputs[0], mix2.inputs[2])
                        links.new(mix2.outputs[0], mix.inputs[1])
                        
                    else:
                        tree.links.new(tex.outputs[0], bsdf.inputs[0])
                        tree.links.new(tex.outputs[1], math.inputs[0])
                
                """ Apply positions """
                for node in tree.nodes:
                    loc = node.location
                    loc.x, loc.y = positions[node.name]
            
            mesh.materials.append(mat)
            """ Set uv """
            k = 0
            for i in range(len(lwo_data.polSurfId)):
                inds = faces[i]
                
                # Set UV
                polygon = mesh.polygons[i]
                if lwo_data.polSurfId[i] == index and surf.ctex:
                    for j in range(len(polygon.vertices)):
                        vertex = mesh.vertices[polygon.vertices[j]].co
                        uvd[polygon.loop_start + j].uv = LwoLoad.planar_project(surf.ctex, vertex)
                
                
                
                k += lwo_data.polVertCount[i]
        
        mesh.calc_normals_split()
        mesh.calc_normals()
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
    


class UvData:
    
    def __init__(self):
        self.material_tex = {}
        self.uvs = []

def load_uv(filepath):
    
    lines = None
    with open(filepath, "r") as f:
        lines = [x.rstrip("\r\n") for x in f.readlines()]
    lines = [x for x in lines if x != ""]
    
    data = UvData()
    
    if int(lines[0]) != 2:
        raise Exception("Invalid magic")
    
    material_count = int(lines[1])
    materials = lines[2:2+material_count]
    paths = lines[2+material_count:2+2*material_count]
    
    for i in range(material_count):
        data.material_tex[materials[i]] = paths[i]
    
    polygons = int(lines[2+2*material_count])
    
    j = 3+2*material_count
    for i in range(polygons):
        uv_count = int(lines[j].split(" ")[1])
        j += 1
        for k in range(uv_count):
            split = lines[j].split(" ")
            j += 1
            coords = [float(split[x]) for x in range(2)]
            data.uvs.append((coords[0], 1 - coords[1]))
    
    return data

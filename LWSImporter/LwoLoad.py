
class LwoTexture:
    
    def __init__(self):
        self.filepath = None
        self.sequenced = False
        
        """ Only relevant settings have been included """
        self.interpolate = False
        self.projAxis = "X"
        self.size = (1, 1, 1)
        self.center = (0, 0, 0)

class LwoSurface:
    
    def __init__(self):
        self.name = ""
        
        """ Most important ones. doubleSided -> Backface Culling, self.additive -> additive color blending 
        self.luminous = False
        self.outline = False
        self.smoothing = False
        self.colorHighlights = False
        self.colorFilter = False
        self.opaqueEdge = False
        self.transparentEdge = False
        self.sharpTerminator = False
        """
        self.doubleSided = False
        self.additive = False
        
        """ Only consider color maps """
        self.color = (1, 1, 1)
        self.ctex = None
        self.__lastTex = None
        

class LwoData:
    
    def __init__(self):
        self.surfNames = []
        self.surfs = {}
        self.verts = []
        self.polVerts = []
        self.polVertCount = []
        self.polSurfId = []

def planar_project(tex, vec):
    
    xoff = 0
    yoff = 0
    if tex.projAxis == "X":
        xoff = 2
        yoff = 1
    elif tex.projAxis == "Y":
        xoff = 0
        yoff = 2
    else:
        xoff = 0
        yoff = 1
    
    x = 0.5 + ((vec[xoff] - tex.center[xoff]) / tex.size[xoff])
    y = 0.5 + ((vec[yoff] - tex.center[yoff]) / tex.size[yoff])
    
    return (x, y)




""" Map from name to parser function """
chunk_parsers = {}
subchunk_parsers = {}

def parse_chunk(data, raw, i):
    if (len(raw) - i) < 8:
        raise Exception("Chunk header too short")
    name = raw[i:i+4].decode("ASCII")
    size = int.from_bytes(raw[i+4:i+8], "big")
    
    parser = None
    try:
        parser = chunk_parsers[name]
    except:
        print(f"No parser for chunk \"{name}\" known.")
    
    if parser:
        parser(data, raw, i+8, size)
    
    return 8 + size

def parse_subchunk(data, raw, i):
    if (len(raw) - i) < 6:
        raise Exception("Subchunk header too short")
    name = raw[i:i+4].decode("ASCII")
    size = int.from_bytes(raw[i+4:i+6], "big")
    
    parser = None
    try:
        parser = subchunk_parsers[name]
    except:
        print(f"No parser for subchunk \"{name}\" known.")
    
    if parser:
        parser(data, raw, i+6, size)
    
    return 6 + size

def load_lwo(filepath):
    
    data = LwoData()
    
    raw = None
    with open(filepath, "rb+") as f:
        raw = f.read()
    
    if len(raw) < 12:
        raise Exception("File is too short")
    if raw[0:4].decode("ASCII") != "FORM":
        raise Exception("File does not start with FORM")
    if raw[8:12].decode("ASCII") != "LWOB":
        raise Exception("File is not an LWO B file")
    
    offset = 12
    while offset < len(raw):
        offset += parse_chunk(data, raw, offset)
    
    return data


""" Parser functions """
def parse_vec(raw, i, dimension):
    import struct
    return tuple(struct.unpack(">f", raw[i+x*4:i+(x+1)*4])[0] for x in range(dimension))



def parse_PNTS(data, raw, i, size):
    vecs = size // 12
    data.verts = [parse_vec(raw, i + x*12, 3) for x in range(vecs)]

chunk_parsers["PNTS"] = parse_PNTS



def parse_POLS(data, raw, i, size):
    shorts = [int.from_bytes(raw[i+x*2:i+(x+1)*2], "big") for x in range(size // 2)]
    
    j = 0
    while j < len(shorts):
        vertCount = shorts[j]
        data.polVertCount.append(vertCount)
        j += 1
        for x in range(vertCount):
            data.polVerts.append(shorts[j+x])
        j += vertCount
        data.polSurfId.append(shorts[j])
        j += 1

chunk_parsers["POLS"] = parse_POLS


def parse_SRFS(data, raw, i, size):
    
    j = 0
    while j < size:
        lname = 0
        k = i + j
        rem = size - j
        while raw[k+lname] != 0 and lname < rem:
            lname += 1
        if lname >= rem:
            raise Exception("Missing null termination")
        elif lname == 0:
            raise Exception("Misformed string")
        
        name = raw[k:k+lname].decode("ASCII")
        data.surfNames.append(name)
        
        if lname % 2 == 0:
            j += lname + 2
        else:
            j += lname + 1
        
chunk_parsers["SRFS"] = parse_SRFS



def parse_SURF(data, raw, i, size):
    
    surf = LwoSurface()
    """ Parse name """
    lname = 0
    while raw[i+lname] != 0 and lname < size:
        lname += 1
    if lname >= size:
        raise Exception("Missing null termination")
    
    surf.name = raw[i:i+lname].decode("ASCII")
    
    """ Continue and ensure alignment """
    j = 0
    if lname % 2 == 0:
        j += lname + 2
    else:
        j += lname + 1
    
    """ Parse subchunks """
    while j < size:
        j += parse_subchunk(surf, raw, i+j)
    
    data.surfs[surf.name] = surf
    
chunk_parsers["SURF"] = parse_SURF



def parse_COLR(surf, raw, i, size):
    if size != 4:
        raise Exception("COLR has the wrong length")
    surf.color = tuple(raw[i+j] / 255 for j in range(3))

subchunk_parsers["COLR"] = parse_COLR



def parse_FLAG(surf, raw, i, size):
    if size != 2:
        raise Exception("FLAG has the wrong length")
    flags = int.from_bytes(raw[i:i+2], "big")
    
    surf.doubleSided = (flags & (1 << 8)) != 0
    surf.additive = (flags & (1 << 9)) != 0

subchunk_parsers["FLAG"] = parse_FLAG



def parse_CTEX(surf, raw, i, size):
    """ Parse type string """
    ltype = 0
    while raw[i+ltype] != 0 and ltype < size:
        ltype += 1
    if ltype >= size:
        raise Exception("Missing null termination")
    
    type = raw[i:i+ltype].decode("ASCII")
    
    if type != "Planar Image Map":
        raise Exception("Unknown texture mapping type")
    
    surf.ctex = LwoTexture()
    surf.__lastTex = surf.ctex

subchunk_parsers["CTEX"] = parse_CTEX



def parse_DTEX(surf, raw, i, size):
    surf.__lastTex = LwoTexture()
subchunk_parsers["DTEX"] = parse_DTEX



def parse_DTEX(surf, raw, i, size):
    surf.__lastTex = LwoTexture()
subchunk_parsers["DTEX"] = parse_DTEX


def parse_STEX(surf, raw, i, size):
    surf.__lastTex = LwoTexture()
subchunk_parsers["STEX"] = parse_STEX


def parse_RTEX(surf, raw, i, size):
    surf.__lastTex = LwoTexture()
subchunk_parsers["RTEX"] = parse_RTEX


def parse_TTEX(surf, raw, i, size):
    surf.__lastTex = LwoTexture()
subchunk_parsers["TTEX"] = parse_TTEX


def parse_BTEX(surf, raw, i, size):
    surf.__lastTex = LwoTexture()
subchunk_parsers["BTEX"] = parse_BTEX



def parse_TIMG(surf, raw, i, size):
    if not surf.__lastTex:
        raise Exception("Missing TEX subchunk before this subchunk.")
    tex = surf.__lastTex
    
    """ Parse filepath """
    lpath = 0
    while raw[i+lpath] != 0 and lpath < size:
        lpath += 1
    if lpath >= size:
        raise Exception("Missing null termination")
    
    filename = raw[i:i+lpath].decode("ASCII")
    if filename.endswith(" (sequence)"):
        tex.filepath = filename[:-len(" (sequence)")]
        tex.sequcned = True
    else:
        tex.filepath = filename
        tex.sequenced = False

subchunk_parsers["TIMG"] = parse_TIMG



def parse_TFLG(surf, raw, i, size):
    if not surf.__lastTex:
        raise Exception("Missing TEX subchunk before this subchunk.")
    tex = surf.__lastTex
    
    if size != 2:
        raise Exception("TFLG has the wrong length")
    
    flags = int.from_bytes(raw[i:i+2], "big")
    
    """ Parse axis """
    if flags & (1 << 0) != 0:
        tex.projAxis = "X"
    elif flags & (1 << 1) != 0:
        tex.projAxis = "Y"
    elif flags & (1 << 2) != 0:
        tex.projAxis = "Z"
    
    tex.interpolate = flags & (1 << 5) != 0

subchunk_parsers["TFLG"] = parse_TFLG


def parse_TSIZ(surf, raw, i, size):
    if not surf.__lastTex:
        raise Exception("Missing TEX subchunk before this subchunk.")
    tex = surf.__lastTex
    
    if size != 12:
        raise Exception("TSIZ has the wrong length")
    
    tex.size = parse_vec(raw, i, 3)

subchunk_parsers["TSIZ"] = parse_TSIZ



def parse_TCTR(surf, raw, i, size):
    if not surf.__lastTex:
        raise Exception("Missing TEX subchunk before this subchunk.")
    tex = surf.__lastTex
    
    if size != 12:
        raise Exception("TCTR has the wrong length")
    
    tex.center = parse_vec(raw, i, 3)

subchunk_parsers["TCTR"] = parse_TCTR

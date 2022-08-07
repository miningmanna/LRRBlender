

class BmpData:
    
    def __init__(self):
        self.width = 0
        self.height = 0
        self.colors = []
        self.pixels = []

def get_int(raw, i, size = 4):
    return int.from_bytes(raw[i:i+size], "little")

def flatten(l):
    nl = []
    for sl in l:
        for x in sl:
            nl.append(x)
    return nl

def load_bmp(path):
    
    data = BmpData()
    
    raw = None
    with open(path, "rb+") as f:
        raw = f.read()
    
    if raw[0:2].decode("ASCII") != "BM":
        raise Exception("Invalid magic")
    
    pixel_offset = get_int(raw, 10)
    
    # Check that we have a BITMAPINFOHEADER
    if get_int(raw, 0x0E) != 40:
        raise Exception("Invalid info header")
    
    data.width = get_int(raw, 0x12)
    data.height = get_int(raw, 0x16)
    
    # Check that we only have one color plane
    if get_int(raw, 0x1A, 2) != 1:
        raise Exception("Invalid color plane count")
    
    pix_bits = get_int(raw, 0x1C, 2)
    # Check pixel size
    if pix_bits != 8:
        raise Exception("Expected pixels to be 8 bits big")
    
    palette_size = get_int(raw, 0x2E)
    if palette_size == 0:
        palette_size = 2**pix_bits
    
    off = 54
    # Get color palette
    for i in range(palette_size):
        bytes = raw[off:off+4]
        rgb = (bytes[2], bytes[1], bytes[0])
        color = tuple(x / 255 for x in rgb)
        data.colors.append(color)
        off += 4
    
    off = pixel_offset
    rows = []
    for y in range(data.height):
        row = []
        for i in range(data.width):
            row.append(int(raw[off]))
            off += 1
        rows.append(row)
    
    data.pixels = flatten(rows)
    
    return data
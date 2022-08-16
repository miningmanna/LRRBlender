
class LwsObject:
	
	def __init__(self):
		self.keyframes = {}
		self.alphaKeyframes = {}
		
		self.name = None
		self.filepath = None
		self.parent = -1
		self.pivot = (0, 0, 0)

class LwsAnimation:
	
	def __init__(self):
		self.firstFrame = 0
		self.lastFrame = 0
		self.framesPerSecond = 25.0
		
		self.objects = []

import math
def parse_keyframes(lines, i):
	oldi = i
	frames = {}
	entries = int(lines[i+2])
	i += 3
	
	for j in range(entries):
		lineA = lines[i]
		if (i+1) >= len(lines):
			break
		lineB = lines[i+1]
		
		frame = int(lineB.strip().split(" ")[0])
		floats = [float(x) for x in lineA.strip().split(" ")]
		if len(floats) != 9:
			raise Exception("Too few floats for keyframe.")
		
		""" Position, Rotation, Scale """
		frames[frame] = (tuple(floats[0:3]), tuple([(x*math.pi / 180.0) for x in floats[3:6]]), tuple(floats[6:9]))
		
		i += 2
	
	if lines[i].startswith("EndBehavior"):
		return i - oldi, frames
		
		

	raise Exception("Unexpected end of keyframes.")

def parse_alpha_keyframes(lines, i):
	oldi = i
	frames = {}
	entries = int(lines[i+2])
	i += 3
	
	for j in range(entries):
		lineA = lines[i]
		if (i+1) >= len(lines):
			break
		lineB = lines[i+1]
		
		frame = int(lineB.strip().split(" ")[0])
		value = float(lineA.strip())
		
		frames[frame] = value
		
		i += 2
	
	if lines[i].startswith("EndBehavior"):
		return i - oldi, frames
	
	
	raise Exception("Unexpected end of alpha keyframes.")

def load_lws(filepath):
	
	lines = None
	with open(filepath, "r") as f:
		lines = [x.rstrip("\r\n") for x in f.readlines()]
	lines = [x for x in lines if x != ""]
	
	""" Check magic """
	if lines[0] != "LWSC":
		raise Exception("File does not start with \"LWSC\".")
	
	import re
	import os
	
	""" Create instance to be returned after parsing """
	anim = LwsAnimation()
	curObji = -1
	objectPause = True
	
	lineskips = 0
	for i in range(len(lines)):
		''' Skip lines if needed '''
		if lineskips > 0:
			lineskips -= 1
			continue
		
		line = lines[i]
		""" Parse line """
		if line.startswith("FirstFrame"):
			anim.firstFrame = int(line.split(" ")[1])
			continue
		if line.startswith("LastFrame"):
			anim.lastFrame = int(line.split(" ")[1])
			continue
		if line.startswith("FramesPerSecond"):
			anim.framesPerSecond = float(line.split(" ")[1])
			continue
		
		if line.startswith("AddNullObject"):
			objectPause = False
			
			""" Add new object """
			curObji += 1
			anim.objects.append(LwsObject())
			
			""" Set name of new object """
			anim.objects[curObji].name = line.split(" ")[1]
			continue
		
		if line.startswith("LoadObject"):
			objectPause = False
			
			filepath = line[(line.index(" ") + 1):]
			filename = os.path.basename(filepath)
			""" Remove file extension if present """
			if filename.rfind(".") >= 0:
				filename = filename[0:filename.rfind(".")]
			
			""" Add new object """
			curObji += 1
			anim.objects.append(LwsObject())
			
			""" Set name and filepath of new object """
			anim.objects[curObji].name = filename
			anim.objects[curObji].filepath = filepath
			continue
		
		if objectPause:
			continue
		
		if line.startswith("ParentObject"):
			anim.objects[curObji].parent = int(line.split(" ")[1])
			continue
		
		if line.startswith("PivotPoint"):
			anim.objects[curObji].pivot = tuple(float(x) for x in line.split(" ")[1:4])
			continue
		
		
		""" Object transform keyframes """
		if line.startswith("ObjectMotion"):
			lineskips, anim.objects[curObji].keyframes = parse_keyframes(lines, i)
			continue
		
		""" Object transparency keyframes """
		if line.startswith("ObjDissolve (envelope)"):
			lineskips, anim.objects[curObji].alphaKeyframes = parse_alpha_keyframes(lines, i)
			continue
		
		if line.startswith("AddLight") or line.startswith("ShowCamera"):
			objectPause = True
			continue
		
	
	return anim

def print_anim(anim):
	if anim:
		print("Animation:")
		print(f"  {anim.firstFrame}")
		print(f"  {anim.lastFrame}")
		print(f"  {anim.framesPerSecond}")
		print("  Objects:")
		for o in anim.objects:
			print(f"    " + o.name)
			print(f"      File: {o.filepath}")
			print(f"      Parent: {o.parent}")
			print(f"      Pivot: {o.pivot}")
			print(f"      Keyframes: {o.keyframes}")
			print(f"      Alpha Keyframes: {o.alphaKeyframes}")
	else:
		print("Given \"None\"")

if __name__ == "__main__":
	import sys
	anim = load_lws(*sys.argv[1:])
	print_anim(anim)
import os, time, json
import numpy as np
from PIL import Image
from toy3d import *
from assets import *

os.makedirs("sprites", exist_ok=True)
S = 512
CAM = Cam(yaw=0.60, pitch=0.28, scale=132, ox=S/2, oy=S*0.86)

SHAPES = {
    "seat":      seat_parts(),
    "char_idle": char_parts("idle"),
    "char_walkA":char_parts("walk", phase= 1.15),
    "char_walkB":char_parts("walk", phase=-1.15),
    "char_sit":  char_parts("sit"),
}

t0 = time.time(); cache = {}
for name, parts in SHAPES.items():
    t = time.time()
    cache[name] = bake(parts, CAM, S, S)
    cache[name]["shadow"] = contact_shadow(parts, CAM, S, S, blur=6, alpha=110)
    print(f"  baked {name:11s} {time.time()-t:5.1f}s")
print(f"total bake {time.time()-t0:.1f}s")

np.save("cache_meta.npy", np.array([S]))
import pickle
pickle.dump(cache, open("cache.pkl","wb"))

for name in SHAPES:
    for cname, col in PALETTE.items():
        im = colorize(cache[name], col)
        im.save(f"sprites/{name}__{cname}.png")
print("sprites:", len(os.listdir("sprites")))

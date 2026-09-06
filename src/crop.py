from PIL import Image
im = Image.open("shot_light.png")
print("light", im.size)
w = 900
im.crop((0, 280, 1320, 1560)).resize((w, int(1280 * w / 1320))).save("crop_a.png")
im.crop((0, 1500, 1320, 2380)).resize((w, int(880 * w / 1320))).save("crop_b.png")
dk = Image.open("shot_dark.png")
dk.crop((0, 280, 1320, 1560)).resize((w, int(1280 * w / 1320))).save("crop_dark.png")
print("ok")

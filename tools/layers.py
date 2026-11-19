"""Colour-separate line layers and reproject map image to Web Mercator for Leaflet overlay."""
import json, numpy as np, math
from PIL import Image
from scipy import ndimage
Image.MAX_IMAGE_PIXELS = None
OUT = '/home/claude/site/data'
import os; os.makedirs(OUT, exist_ok=True)
src = np.array(Image.open('/home/claude/pdf/full-000.jpg').convert('RGB')).astype(int)
x0, y0, sx, sy, rot = json.load(open('/home/claude/geo/transform.json'))
# crop to inner frame
X0, Y0, X1, Y1 = 100, 100, 4928, 3512
img = src[Y0:Y1, X0:X1]
R, G, B = img[..., 0], img[..., 1], img[..., 2]
lon = lambda x: 85.5 + (x - x0) / sx
lat = lambda y: 26.0 - (y - y0) / sy
west, east = lon(X0), lon(X1)
north, south = lat(Y0), lat(Y1)
blank = np.zeros(R.shape, bool)
# title text & legend area
blank[0:200, 1300:3700] = True
blank[2680:, 3400:] = True
masks = {
    'l765': (R > 90) & (R < 170) & (G > 40) & (G < 110) & (B > 15) & (B < 80) & (R - G > 35) & (G - B > 15),
    'l400': (R > 170) & (G < 120) & (B < 120) & (R - G > 90),
    'l220': (G > 120) & (R < 140) & (B < 170) & (G - R > 45) & (G - B > 10),
    'l132': (B > 120) & (R < 120) & (B - R > 60) & (B - G > 20),
}
colours = {'l765': (122, 72, 40), 'l400': (220, 38, 38), 'l220': (22, 160, 74), 'l132': (37, 99, 200)}

def merc(lat_):
    return math.log(math.tan(math.pi / 4 + math.radians(lat_) / 2))

H, W = R.shape
scale = 0.7
OW = int(W * scale)
mN, mS = merc(north), merc(south)
OH = int(round(H * scale * (mN - mS) / math.radians(north - south)))
# for each output row find source row
rows = []
for j in range(OH):
    m = mN - (j + 0.5) / OH * (mN - mS)
    la = math.degrees(2 * math.atan(math.exp(m)) - math.pi / 2)
    rows.append((north - la) / (north - south) * H)
rows = np.clip(np.array(rows), 0, H - 1)
cols = np.clip((np.arange(OW) + 0.5) / scale, 0, W - 1)

def warp(arr):
    return ndimage.map_coordinates(arr.astype(float), np.meshgrid(rows, cols, indexing='ij'), order=1)

for k, m in masks.items():
    m = m & ~blank
    m = ndimage.binary_opening(m, np.ones((2, 2)))
    m = ndimage.binary_dilation(m, iterations=1)
    a = warp(m.astype(float))
    a = np.clip(a * 1.6, 0, 1)
    out = np.zeros((OH, OW, 4), np.uint8)
    out[..., :3] = colours[k]
    out[..., 3] = (a * 255).astype(np.uint8)
    im = Image.fromarray(out, 'RGBA')
    im.save(f'{OUT}/{k}.png', optimize=True)
    print(k, m.sum(), os.path.getsize(f'{OUT}/{k}.png'))
# original map, reprojected, JPEG
rgb = np.stack([warp(img[..., c]) for c in range(3)], -1).clip(0, 255).astype(np.uint8)
Image.fromarray(rgb).save(f'{OUT}/original_map.jpg', quality=72, optimize=True)
print('orig', os.path.getsize(f'{OUT}/original_map.jpg'))
json.dump({'south': south, 'west': west, 'north': north, 'east': east}, open(f'{OUT}/overlay_bounds.json', 'w'))
print(south, west, north, east, OW, OH)

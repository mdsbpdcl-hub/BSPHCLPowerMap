import json, numpy as np
from PIL import Image
from scipy import ndimage, optimize
from shapely.geometry import shape
from shapely.ops import unary_union
Image.MAX_IMAGE_PIXELS = None
im = np.array(Image.open('/home/claude/pdf/full-000.jpg')).astype(int)
R, G, B = im[..., 0], im[..., 1], im[..., 2]
mask = (R > 100) & (R < 190) & (G > 40) & (G < 125) & (B > 120) & (B < 210) & (B - G > 40) & (R - G > 25)
mask[:100] = 0; mask[3512:] = 0; mask[:, :100] = 0; mask[:, 4928:] = 0
mask[2800:, 3500:] = 0  # legend
Image.fromarray((mask * 255).astype(np.uint8)).resize((1278, 910)).save('/home/claude/geo/mask.png')
dt = ndimage.distance_transform_edt(~mask)
d = json.load(open('/home/claude/geo/bihar.geojson'))
st = unary_union([shape(f['geometry']).buffer(0) for f in d['features']])
polys = [st] if st.geom_type == 'Polygon' else list(st.geoms)
pts = []
for p in polys:
    c = np.array(p.exterior.coords)
    # densify
    for a, b in zip(c[:-1], c[1:]):
        n = max(1, int(np.hypot(*(b - a)) / 0.005))
        for t in np.linspace(0, 1, n, endpoint=False):
            pts.append(a + (b - a) * t)
pts = np.array(pts)
print('pts', len(pts))

def proj(p, P):
    x0, y0, sx, sy, rot = P
    lon, lat = p[:, 0] - 85.5, p[:, 1] - 26.0
    u = lon * sx; v = -lat * sy
    cr, sr = np.cos(rot), np.sin(rot)
    return x0 + u * cr - v * sr, y0 + u * sr + v * cr

def cost(P):
    x, y = proj(pts, P)
    xi = np.clip(x, 0, dt.shape[1] - 1).astype(int); yi = np.clip(y, 0, dt.shape[0] - 1).astype(int)
    dd = dt[yi, xi]
    return np.mean(np.minimum(dd, 40) ** 2)

# initial from graticule
x0 = 296 + (85.5 - 83.5) * 959.7; y0 = 270 + (27.5 - 26.0) * 959.7
P0 = [x0, y0, 959.7, 959.7, 0.0]
print('init cost', cost(P0))
best = None
for dx in range(-150, 151, 30):
    for dy in range(-150, 151, 30):
        P = [x0 + dx, y0 + dy, 959.7, 959.7, 0]
        c = cost(P)
        if best is None or c < best[0]: best = (c, P)
print('grid best', best)
r = optimize.minimize(cost, best[1], method='Nelder-Mead', options={'maxiter': 4000, 'xatol': 0.01, 'fatol': 0.01})
print(r.x, r.fun)
r = optimize.minimize(cost, r.x, method='Nelder-Mead', options={'maxiter': 4000})
print(r.x, r.fun)
x, y = proj(pts, r.x)
dd = dt[np.clip(y, 0, 3639).astype(int), np.clip(x, 0, 5111).astype(int)]
print('median px err', np.median(dd), 'p90', np.percentile(dd, 90))
json.dump(list(r.x), open('/home/claude/geo/transform.json', 'w'))
# overlay check
ov = Image.open('/home/claude/pdf/full-000.jpg').convert('RGB')
from PIL import ImageDraw
dr = ImageDraw.Draw(ov)
for f in d['features']:
    g = shape(f['geometry'])
    for p in ([g] if g.geom_type == 'Polygon' else g.geoms):
        c = np.array(p.exterior.coords)
        X, Y = proj(c, r.x)
        dr.line(list(zip(X, Y)), fill=(0, 200, 0), width=4)
ov.resize((1600, 1139)).save('/home/claude/geo/overlay.jpg', quality=85)

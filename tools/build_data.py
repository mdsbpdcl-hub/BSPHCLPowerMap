import sys, json, numpy as np
sys.path.insert(0, 'tools')
from entries import E
from shapely.geometry import shape, Point
x0, y0, sx, sy, rot = json.load(open('tools/src/transform.json'))

def px2geo(x, y):
    u, v = x - x0, y - y0
    cr, sr = np.cos(-rot), np.sin(-rot)
    uu, vv = u * cr - v * sr, u * sr + v * cr
    return 85.5 + uu / sx, 26.0 - vv / sy

gj = json.load(open('tools/src/bihar.geojson'))
NB = {'West Champaran', 'East Champaran', 'Sheohar', 'Sitamarhi', 'Muzaffarpur', 'Vaishali', 'Saran', 'Siwan',
      'Gopalganj', 'Darbhanga', 'Madhubani', 'Samastipur', 'Supaul', 'Saharsa', 'Madhepura', 'Purnia', 'Araria',
      'Kishanganj', 'Katihar', 'Begusarai', 'Khagaria'}
dists = [(f['properties']['district'], shape(f['geometry'])) for f in gj['features']]
out = []
OVR = {('Bihta', '132'): 'Patna', ('Teghra', '132'): 'Begusarai'}
for i, (name, kv, st, own, x, y, note) in enumerate(E):
    lon, lat = px2geo(x, y)
    p = Point(lon, lat)
    d = [n for n, g in dists if g.contains(p)]
    if not d:
        d = [min(dists, key=lambda t: t[1].distance(p))[0]]
    d = [OVR.get((name, kv), d[0])]
    out.append(dict(id=i + 1, name=name, kv=kv, status=st, owner=own, lat=round(lat, 5), lon=round(lon, 5),
                    district=d[0], discom='NBPDCL' if d[0] in NB else 'SBPDCL', note=note, px=[x, y]))
for o in out:
    print(f"{o['name']:<28}{o['kv']:<8}{o['status']:<9}{o['district']:<16}{o['lat']:.3f},{o['lon']:.3f}")
json.dump(out, open('tools/src/substations.json', 'w'), indent=1)

import json, csv, math, numpy as np
from shapely.geometry import shape, Point, mapping
OUT = 'data'
S = json.load(open('tools/src/substations.json'))
gj = json.load(open('tools/src/bihar.geojson'))
pop = {}
for r in csv.DictReader(open('tools/src/census.csv')):
    if r['State name'] == 'BIHAR':
        pop[r['District code']] = int(r['Population'])
NB = {'West Champaran', 'East Champaran', 'Sheohar', 'Sitamarhi', 'Muzaffarpur', 'Vaishali', 'Saran', 'Siwan',
      'Gopalganj', 'Darbhanga', 'Madhubani', 'Samastipur', 'Supaul', 'Saharsa', 'Madhepura', 'Purnia', 'Araria',
      'Kishanganj', 'Katihar', 'Begusarai', 'Khagaria'}

def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))

grid_kv = {'765', '400', '220', '132'}
exist = [s for s in S if s['kv'] in grid_kv and s['status'] == 'Existing']
src220 = [s for s in S if s['kv'] in {'765', '400', '220'} and s['status'] == 'Existing']
allplanned = [s for s in S if s['kv'] in grid_kv]
EX = np.array([[s['lat'], s['lon']] for s in exist])
EXP = np.array([[s['lat'], s['lon']] for s in allplanned])

def nearest_km(lat, lon, arr):
    la, lo = np.radians(arr[:, 0]), np.radians(arr[:, 1])
    a = np.sin((la - math.radians(lat)) / 2) ** 2 + math.cos(math.radians(lat)) * np.cos(la) * np.sin((lo - math.radians(lon)) / 2) ** 2
    return float(np.min(6371 * 2 * np.arcsin(np.sqrt(a))))

districts = []
feats = []
for f in gj['features']:
    name = f['properties']['district']; code = f['properties']['dt_code']
    g = shape(f['geometry']).buffer(0)
    # area km2 (equal-area approx)
    c = g.centroid
    kx = 111.32 * math.cos(math.radians(c.y)); ky = 110.57
    area = g.area * kx * ky
    ss = [s for s in S if s['district'] == name]
    cnt = lambda kv, st=None: sum(1 for s in ss if s['kv'] == kv and (st is None or s['status'] == st))
    # coverage: sample grid points within district
    minx, miny, maxx, maxy = g.bounds
    pts = [(y, x) for x in np.arange(minx, maxx, 0.02) for y in np.arange(miny, maxy, 0.02) if g.contains(Point(x, y))]
    d_now = [nearest_km(p[0], p[1], EX) for p in pts]
    d_plan = [nearest_km(p[0], p[1], EXP) for p in pts]
    cov20 = 100 * sum(d <= 20 for d in d_now) / len(pts)
    cov20p = 100 * sum(d <= 20 for d in d_plan) / len(pts)
    gss_ex = sum(1 for s in ss if s['kv'] in grid_kv and s['status'] == 'Existing')
    gss_uc = sum(1 for s in ss if s['kv'] in grid_kv and s['status'] != 'Existing')
    p = pop.get(code)
    near220 = min(hav((c.y, c.x), (s['lat'], s['lon'])) for s in src220)
    rec = dict(district=name, code=code, discom='NBPDCL' if name in NB else 'SBPDCL', area_km2=round(area),
               population_2011=p,
               kv765=cnt('765'), kv400=cnt('400', 'Existing'), kv400_uc=cnt('400') - cnt('400', 'Existing'),
               kv220=cnt('220', 'Existing'), kv220_uc=cnt('220') - cnt('220', 'Existing'),
               kv132=cnt('132', 'Existing'), kv132_uc=cnt('132') - cnt('132', 'Existing'),
               gen=sum(1 for s in ss if s['kv'] in ('Thermal', 'Hydro')),
               other=sum(1 for s in ss if s['kv'] in ('HVDC', 'TSS')),
               gss_existing=gss_ex, gss_planned=gss_uc,
               area_per_gss=round(area / gss_ex) if gss_ex else None,
               pop_lakh_per_gss=round(p / 1e5 / gss_ex, 1) if gss_ex and p else None,
               mean_dist_km=round(float(np.mean(d_now)), 1), max_dist_km=round(float(np.max(d_now)), 1),
               cov20=round(cov20), cov20_planned=round(cov20p),
               has_ehv=(cnt('220', 'Existing') + cnt('400', 'Existing') + cnt('765')) > 0,
               centroid_to_220_km=round(near220, 1))
    districts.append(rec)
    gs = g.simplify(0.003, preserve_topology=True)
    feats.append(dict(type='Feature', properties=dict(district=name, code=code), geometry=mapping(gs)))
# ranking/flags
for d in districts:
    flags = []
    if not d['has_ehv']: flags.append('No 220 kV or higher GSS in district')
    if d['cov20'] < 70: flags.append(f"Only {d['cov20']}% of area within 20 km of a grid sub-station")
    if d['area_per_gss'] and d['area_per_gss'] > 900: flags.append(f"Large area per GSS ({d['area_per_gss']} km²)")
    if d['pop_lakh_per_gss'] and d['pop_lakh_per_gss'] > 7: flags.append(f"High load-base: {d['pop_lakh_per_gss']} lakh people per GSS (2011)")
    if d['gss_planned']: flags.append(f"{d['gss_planned']} GSS under construction / proposed on map")
    d['flags'] = flags
    # simple status score 0-100
    s = 0
    s += min(d['cov20'], 100) * 0.45
    s += (25 if d['has_ehv'] else 0)
    s += max(0, 30 - (d['pop_lakh_per_gss'] or 30) * 3) if d['pop_lakh_per_gss'] else 0
    d['score'] = round(s)
    d['band'] = 'Good' if d['score'] >= 70 else ('Watch' if d['score'] >= 50 else 'Weak')
json.dump(dict(type='FeatureCollection', features=feats), open(f'{OUT}/districts.geojson', 'w'), separators=(',', ':'))
json.dump(sorted(districts, key=lambda d: d['district']), open(f'{OUT}/district_stats.json', 'w'), indent=1)
pub = [{k: v for k, v in s.items() if k != 'px'} for s in S]
json.dump(pub, open(f'{OUT}/substations.json', 'w'), indent=1)
with open(f'{OUT}/substations.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(pub[0].keys())); w.writeheader(); w.writerows(pub)
for d in sorted(districts, key=lambda d: d['score']):
    print(f"{d['district']:<16}{d['discom']:<8}{d['area_km2']:>6}{d['gss_existing']:>4}{d['gss_planned']:>3} cov{d['cov20']:>4} mean{d['mean_dist_km']:>5} plk{d['pop_lakh_per_gss']} ehv{int(d['has_ehv'])} score{d['score']} {d['band']}")

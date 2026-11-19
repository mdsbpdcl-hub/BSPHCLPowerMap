# Bihar Power Map – interactive

An interactive, district-wise version of the BSPHCL **Comprehensive Bihar Map** (13th Plan edition, revised Aug 2020).

Open `index.html` (or the GitHub Pages site) to:

- pan and zoom the transmission network with 765 / 400 / 220 / 132 kV line layers that switch on and off;
- click any of the 196 sub-stations, generating stations, HVDC and traction points for voltage, status, owner, district and DISCOM;
- shade districts by overall status, area within 20 km of a grid sub-station, number of sub-stations, people per sub-station or DISCOM;
- view the 20 km reach of every existing sub-station to see coverage gaps;
- open any district for its figures, points to note and list of sub-stations;
- compare SBPDCL and NBPDCL, see rankings, and search, filter and copy the full sub-station register.

## Files

| Path | What it is |
|---|---|
| `index.html` | The app (built from `src/index.src.html` with Leaflet CSS inlined) |
| `data/substations.csv` / `.json` | Sub-station register – **edit this to update status** (e.g. UC → Existing) |
| `data/district_stats.json` | District-wise figures and status score |
| `data/districts.geojson` | District boundaries (Census 2011, 38 districts) |
| `data/l765.png … l132.png` | Line layers traced from the original map |
| `data/original_map.jpg` | The original BSPHCL map, re-projected to overlay exactly |
| `tools/` | Python pipeline used to georeference the PDF, trace layers and compute the analysis |

## Updating

1. Edit `tools/entries.py` (name, voltage, status, owner, pixel position on the original map).
2. Run `python3 tools/build_data.py && python3 tools/analyse.py` (needs `shapely`, `numpy`, `scipy`), with outputs written to `data/`.
3. Commit and push.

## Method notes

- The map was georeferenced by fitting the district/state boundaries on the PDF to Census 2011 boundaries (median error under 1 px ≈ 0.1 km).
- Status reflects the map's 2020 edition; many projects then under construction have since been commissioned.
- The map is partly schematic, so positions are approximate (1–3 km).
- Overall status score (0–100) = area within 20 km × 0.45 + 25 if the district has a 220 kV-or-higher sub-station + up to 30 for people per sub-station. Good ≥ 70, Watch 50–69, Weak < 50.
- Population: Census 2011.

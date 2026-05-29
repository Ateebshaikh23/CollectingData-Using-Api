import requests
import json

API_URL = ( "https://api.data.stats.govt.nz/rest/data/" "STATSNZ,CEN18_HAD_001/" "1+2+3.DHB9999.1+2+3.1+2+3.1+2.2018" "?format=jsondata" )

HEADERS = {
    "Ocp-Apim-Subscription-Key": "4438fa53f1e54ed093d06793b131e0b8",
    "Accept": "application/vnd.sdmx.data+json"
}

response = requests.get(API_URL, headers=HEADERS, timeout=60)
data = response.json()

root      = data['data']
dataset   = root['dataSets'][0]
structure = root['structures'][0]

# ── How many entries in dimensionGroupAttributes? ──
dga = dataset.get('dimensionGroupAttributes', {})
print(f"\n--- dimensionGroupAttributes total entries: {len(dga)} ---")

# ── Print first 10 keys + values ──
print("\n--- First 10 dimensionGroupAttributes entries ---")
for i, (k, v) in enumerate(dga.items()):
    print(f"  {k}  →  {v}")
    if i >= 9:
        break

# ── Check structures[0]['dataSets'] ──
print("\n--- structures[0]['dataSets'] ---")
struct_datasets = structure.get('dataSets', [])
print(f"  Count: {len(struct_datasets)}")
if struct_datasets:
    print(f"  First item keys: {list(struct_datasets[0].keys())}")
    print(f"  First item (trimmed): {json.dumps(struct_datasets[0])[:500]}")

# ── Print all dimension levels and their values ──
for level in ['dataSet', 'series', 'observation']:
    dims = structure['dimensions'].get(level, [])
    print(f"\n--- dimensions['{level}'] ({len(dims)} dims) ---")
    for dim in dims:
        vals = dim.get('values', [])
        print(f"  id={dim['id']}  |  {len(vals)} values  |  first={vals[0] if vals else 'N/A'}")

# ── Print attributes keys ──
print("\n--- structures[0]['attributes'] keys ---")
print(list(structure.get('attributes', {}).keys()))
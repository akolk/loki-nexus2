---
name: pdok-locatieserver
description: Use this skill whenever the user wants to geocode Dutch addresses, find coordinates for locations in the Netherlands, look up BAG objects (addresses, buildings, parcels) by ID, search for cadastral data, postcodes, municipalities, or any other Dutch geo-reference objects via PDOK. Trigger when the user mentions PDOK, Locatieserver, BAG lookup, Dutch address geocoding, finding Dutch coordinates, BAG IDs, cadastral parcel lookup, or building object IDs. Also trigger for any task involving querying, calling, or integrating the PDOK location API in code — even if the user just says "look up this Dutch address" or "find the coordinates of this location in the Netherlands".
---

# PDOK Locatieserver Skill

The PDOK Locatieserver is the **official Dutch geocoding service** (Kadaster/BZK). It is **free** and requires **no API key**.

**Base URL:** `https://api.pdok.nl/bzk/locatieserver/search/v3_1/`  
**Interactive docs:** `https://api.pdok.nl/bzk/locatieserver/search/v3_1/ui/`

Datasets covered: BAG (addresses, buildings), Kadaster (cadastral parcels), NWB (roads), CBS (municipalities/districts), Bestuurlijke Grenzen (administrative boundaries).

---

## Primary Use Cases

### 1. Geocoding: Address string → coordinates (`/free`)

```
GET /free?q=<address>&rows=<n>&fq=type:adres
```

**Key parameters:**

| Parameter | Description |
|-----------|-------------|
| `q` | Search string (required) |
| `rows` | Max results (default 10) |
| `fq` | Filter query, e.g. `fq=type:adres` |
| `fl` | Fields to return (comma-separated) |
| `lat` + `lon` | Bias/sort by proximity (WGS84) |
| `start` | Pagination offset (zero-based) |

**Example request:**
```
GET https://api.pdok.nl/bzk/locatieserver/search/v3_1/free?q=Binnenhof+1+Den+Haag&rows=1&fq=type:adres
```

**Raw response (abbreviated):**
```json
{
  "response": {
    "numFound": 1,
    "start": 0,
    "docs": [
      {
        "id": "adr-a8b3c2d1e4f5a6b7c8d9e0f1a2b3c4d5",
        "weergavenaam": "Binnenhof 1, 2513AA 's-Gravenhage",
        "type": "adres",
        "score": 15.24,
        "straatnaam": "Binnenhof",
        "huisnummer": 1,
        "postcode": "2513AA",
        "woonplaatsnaam": "'s-Gravenhage",
        "gemeentenaam": "'s-Gravenhage",
        "provincienaam": "Zuid-Holland",
        "centroide_ll": "POINT(4.31317 52.07987)",
        "centroide_rd": "POINT(85104.8 446476.2)"
      }
    ]
  }
}
```

> ⚠️ **`centroide_ll` format is `POINT(longitude latitude)`** — longitude comes first!

---

### 2. Lookup by Object ID (`/lookup`)

Best for: retrieving the complete record for a known object. The `id` comes from `/free` or `/suggest` results, or can be derived from a BAG identifier (see below).

```
GET /lookup?id=<object-id>
```

**Example request:**
```
GET https://api.pdok.nl/bzk/locatieserver/search/v3_1/lookup?id=adr-a8b3c2d1e4f5a6b7c8d9e0f1a2b3c4d5
```

**Raw response:**
```json
{
  "response": {
    "numFound": 1,
    "docs": [
      {
        "id": "adr-a8b3c2d1e4f5a6b7c8d9e0f1a2b3c4d5",
        "weergavenaam": "Binnenhof 1, 2513AA 's-Gravenhage",
        "type": "adres",
        "straatnaam": "Binnenhof",
        "huisnummer": 1,
        "huisletter": null,
        "huisnummertoevoeging": null,
        "postcode": "2513AA",
        "woonplaatsnaam": "'s-Gravenhage",
        "gemeentecode": "0518",
        "gemeentenaam": "'s-Gravenhage",
        "wijkcode": "WK051800",
        "buurtcode": "BU05180000",
        "provincienaam": "Zuid-Holland",
        "nummeraanduiding_id": "0518200000000001",
        "adresseerbaarobject_id": "0518010000000001",
        "centroide_ll": "POINT(4.31317 52.07987)",
        "centroide_rd": "POINT(85104.8 446476.2)"
      }
    ]
  }
}
```

#### BAG Object IDs

BAG IDs are 16-digit numeric codes. The Locatieserver uses its own hex-prefixed IDs, but you can search by BAG ID using `fq`:

| BAG object type | Locatieserver `type` | BAG field to filter on |
|-----------------|----------------------|------------------------|
| Nummeraanduiding (address) | `adres` | `nummeraanduiding_id` |
| Verblijfsobject (building unit) | `adres` | `adresseerbaarobject_id` |
| Perceel (cadastral parcel) | `perceel` | `perceelnummer` |

**Example: find address by BAG nummeraanduiding ID:**
```
GET https://api.pdok.nl/bzk/locatieserver/search/v3_1/free?fq=nummeraanduiding_id:0518200000000001&rows=1
```

---

## Object Types Reference

| `type` value | Description |
|--------------|-------------|
| `adres` | Full address (straat + huisnummer + woonplaats) |
| `weg` | Street / road segment |
| `postcode` | Postcode (4-digit) area |
| `woonplaats` | City / place name |
| `gemeente` | Municipality |
| `provincie` | Province |
| `perceel` | Cadastral parcel |
| `appartementsrecht` | Apartment right (VVE) |
| `buurt` | Neighbourhood |
| `wijk` | District |
| `waterschap` | Water board |

Filter by one type: `fq=type:adres`  
Filter by multiple: `fq=type:(adres OR postcode)`

---

## Key Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Locatieserver ID (use for `/lookup`) |
| `weergavenaam` | string | Human-readable display name |
| `type` | string | Object type |
| `score` | float | Relevance score |
| `centroide_ll` | WKT | Center as `POINT(lon lat)` in WGS84 |
| `centroide_rd` | WKT | Center as `POINT(x y)` in RD/EPSG:28992 |
| `straatnaam` | string | Street name |
| `huisnummer` | int | House number |
| `huisletter` | string | House letter (e.g. "A") |
| `huisnummertoevoeging` | string | House number addition (e.g. "bis") |
| `postcode` | string | Dutch postcode (e.g. "1234AB") |
| `woonplaatsnaam` | string | City/place name |
| `gemeentenaam` | string | Municipality name |
| `gemeentecode` | string | CBS municipality code |
| `provincienaam` | string | Province name |
| `nummeraanduiding_id` | string | BAG nummeraanduiding ID (16 digits) |
| `adresseerbaarobject_id` | string | BAG verblijfsobject/standplaats/ligplaats ID |

---

## Code Examples

### Python — Geocode an address (raw response)

```python
import requests

BASE = "https://api.pdok.nl/bzk/locatieserver/search/v3_1"

def geocode_raw(address: str, rows: int = 5) -> dict:
    """Returns the full raw API response."""
    r = requests.get(f"{BASE}/free", params={
        "q": address,
        "rows": rows,
        "fq": "type:adres",
    })
    r.raise_for_status()
    return r.json()

response = geocode_raw("Kalverstraat 1 Amsterdam")
# Access docs: response["response"]["docs"]
# First hit:   response["response"]["docs"][0]
# Coordinates: response["response"]["docs"][0]["centroide_ll"]  → "POINT(4.892 52.372)"
```

### Python — Lookup by Locatieserver ID (raw response)

```python
def lookup_raw(object_id: str) -> dict:
    """Look up a full object record by its Locatieserver ID."""
    r = requests.get(f"{BASE}/lookup", params={"id": object_id})
    r.raise_for_status()
    return r.json()

response = lookup_raw("adr-a8b3c2d1e4f5a6b7c8d9e0f1a2b3c4d5")
doc = response["response"]["docs"][0]
```

### Python — Lookup by BAG nummeraanduiding ID

```python
def lookup_by_bag_id(nummeraanduiding_id: str) -> dict:
    """Find address record by its BAG nummeraanduiding ID."""
    r = requests.get(f"{BASE}/free", params={
        "fq": f"nummeraanduiding_id:{nummeraanduiding_id}",
        "rows": 1,
    })
    r.raise_for_status()
    return r.json()

response = lookup_by_bag_id("0518200000000001")
```

### Python — Batch geocode a list of addresses

```python
import time

def batch_geocode(addresses: list[str], delay: float = 0.1) -> list[dict]:
    results = []
    for addr in addresses:
        raw = geocode_raw(addr, rows=1)
        docs = raw["response"]["docs"]
        results.append({
            "input": addr,
            "found": len(docs) > 0,
            "raw": docs[0] if docs else None,
        })
        time.sleep(delay)  # be polite to the API
    return results
```

### Python — Parse coordinates from raw response

```python
import re

def parse_centroide_ll(wkt: str) -> tuple[float, float]:
    """Parse 'POINT(lon lat)' → (lat, lon). Note: lon comes first in WKT!"""
    lon, lat = map(float, re.search(r"POINT\(([^ ]+) ([^ ]+)\)", wkt).groups())
    return lat, lon

doc = response["response"]["docs"][0]
lat, lon = parse_centroide_ll(doc["centroide_ll"])
```

### JavaScript — Geocode an address (raw response)

```javascript
const BASE = "https://api.pdok.nl/bzk/locatieserver/search/v3_1";

async function geocodeRaw(address, rows = 5) {
  const url = new URL(`${BASE}/free`);
  url.searchParams.set("q", address);
  url.searchParams.set("rows", String(rows));
  url.searchParams.set("fq", "type:adres");
  const res = await fetch(url);
  if (!res.ok) throw new Error(`PDOK error: ${res.status}`);
  return res.json(); // full raw response
}

const data = await geocodeRaw("Kalverstraat 1 Amsterdam");
const docs = data.response.docs;
console.log(docs[0].weergavenaam);        // "Kalverstraat 1, 1012NX Amsterdam"
console.log(docs[0].centroide_ll);        // "POINT(4.892 52.372)"
console.log(docs[0].nummeraanduiding_id); // BAG nummeraanduiding ID
```

### JavaScript — Lookup by ID

```javascript
async function lookupRaw(id) {
  const url = new URL(`${BASE}/lookup`);
  url.searchParams.set("id", id);
  const res = await fetch(url);
  if (!res.ok) throw new Error(`PDOK error: ${res.status}`);
  return res.json();
}

const data = await lookupRaw("adr-a8b3c2d1e4f5a6b7c8d9e0f1a2b3c4d5");
const doc = data.response.docs[0];
```

---

## Coordinate Systems

| System | Used in | Notes |
|--------|---------|-------|
| WGS84 (EPSG:4326) | `centroide_ll`, `lat`/`lon` params | Standard GPS. Format: `POINT(lon lat)` |
| RD (EPSG:28992) | `centroide_rd`, `X`/`Y` params | Dutch national grid. X: 0–280000, Y: 300000–625000 |

Convert RD ↔ WGS84 in Python:
```python
from pyproj import Transformer

rd2wgs = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=False)
lat, lon = rd2wgs.transform(85105, 446476)  # → (52.0799, 4.3113)
```

---

## Tips & Gotchas

- **No API key required** — fully open, no auth headers needed
- **`centroide_ll` is `POINT(lon lat)`** — longitude first, latitude second (WKT convention)
- **Only use documented parameters** — undocumented query params cause HTTP 400 errors
- **BAG IDs vs Locatieserver IDs**: the `id` field in responses is a Locatieserver hex ID (e.g. `adr-abc...`), not the BAG ID. Use `nummeraanduiding_id` or `adresseerbaarobject_id` response fields to get the actual BAG IDs
- **No rate limit documented** — add `time.sleep(0.1)` for batch jobs to be safe
- **Pagination**: use `start` (offset) + `rows` (page size)
- **`fl` parameter** limits which fields are returned — useful to reduce response payload size
- **CORS**: API supports browser requests directly; no server-side proxy needed

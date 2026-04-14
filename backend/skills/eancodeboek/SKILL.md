---
name: eancodeboek
description: Use this skill whenever the user wants to look up EAN codes for Dutch electricity or gas connections, find grid operators (netbeheerders) for a Dutch address or postcode, search metering points by address, postcode or city, or integrate with the EDSN EAN Codeboek API. Trigger when the user mentions EAN codeboek, EAN code opzoeken, netbeheerder opzoeken, EDSN API, aansluitingen register, transformator (huisjes), metering points, ELK/GAS aansluitingen, gasaansluiting, electriciteitsmeter, or any task involving the Dutch energy connection register. 
---

# IMPORTANT: Always use this exact base URL in your code:
**`BASE_URL = "https://gateway.edsn.nl/eancodeboek/v1"`**

# EAN Codeboek (EDSN) Skill

Het **EAN Codeboek** is het centrale Nederlandse aansluitingenregister beheerd door **EDSN** (Energie Data Services Nederland). Het bevat alle elektriciteit- en gasaansluitingen in Nederland, inclusief EAN-codes, netbeheerder-informatie en adresgegevens.

**Swagger UI:** `https://gateway.edsn.nl/eancodeboek/swagger-ui/index.html?configUrl=../v3/api-docs/swagger-config`  
**Base URL:** `https://gateway.edsn.nl/eancodeboek/v1/`

---

## Twee hoofdservices

### 1. `/ecbinfoset` — Zoek aansluitpunten 

Zoek meetpunten (aansluitingen) op basis van adresgegevens. Retourneert EAN-codes, netbeheerder, product (ELK/GAS) en adresdetails.

**Toegestane parametercombinaties:**

| Combinatie | Parameters |
|------------|------------|
| Postcode | `product` + `postalCode` |
| Postcode + huisnummer | `product` + `postalCode` + `streetNumber` |
| Postcode + huisnummer + toevoeging | `product` + `postalCode` + `streetNumber` + `streetNumberAddition` |
| Stad + bijzonder meetpunt | `product` + `city` + `specialMeteringPoint` |
| Stad + straat + huisnummer | `product` + `city` + `street` + `streetNumber` |
| Stad + straat + huisnummer + toevoeging | `product` + `city` + `street` + `streetNumber` + `streetNumberAddition` |

**Verplichte parameters:**
- `product`: `ELK` (elektriciteit) of `GAS`

**Paginering:**
- `limit`: aantal resultaten per pagina (default 100, max 100)
- `offset`: startpositie (default 0)

**Voorbeeld request:**
```
GET https://gateway.edsn.nl/eancodeboek/v1/ecbinfoset?product=ELK&postalCode=7339AB&limit=100&offset=0
```

**Raw response:**
```json
{
  "meteringPoints": [
    {
      "ean": "871687940000000001",
      "product": "ELK",
      "address": {
        "postalCode": "3010CK",
        "streetNumber": "1",
        "streetNumberAddition": null,
        "street": "Voorbeeldstraat",
        "city": "Rotterdam",
      },
      "organisation": "Stedin Netbeheer B.V.",
      "gridOperatorEan": "8716867000009",
      "gridArea": "8716870000009",
      "specialMeteringPoint": false,
      "bagId": "0599010000000001"
    }
  ]
}
```

---

### 2. `/gridoperators` — Netbeheerder(s) per postcode

Geeft een lijst van alle netbeheerders die actief zijn op een postcode, inclusief welke producten (ELK en/of GAS) zij leveren.

```
GET https://gateway.edsn.nl/eancodeboek/v1/gridoperators?postalCode=<postcode>
```

**Verplichte parameters:**
- `postalCode`: Nederlandse postcode (bijv. `3010CK` of `3010 CK`)

**Voorbeeld request:**
```
GET https://gateway.edsn.nl/eancodeboek/v1/gridoperators?postalCode=1012NX
```

**Raw response:**
```json
[
  {
    "ean": "8716867000009",
    "name": "Stedin Netbeheer B.V.",
    "products": ["ELK", "GAS"]
  }
]
```

## Veldverklaring response (`/ecbinfoset`)

| Veld | Type | Beschrijving |
|------|------|-------------|
| `ean` | string (18 cijfers) | EAN-code van de aansluiting (begint met `871687...` voor NL) |
| `product` | string | `ELK` = elektriciteit, `GAS` = gas |
| `postalCode` | string | Postcode van het adres |
| `streetNumber` | string | Huisnummer |
| `streetNumberAddition` | string\|null | Toevoeging (bijv. `B`, `bis`) |
| `street` | string | Straatnaam |
| `city` | string | Plaatsnaam |
| `gridOperator.ean` | string | EAN-code van de netbeheerder |
| `gridOperator.name` | string | Naam van de netbeheerder |
| `specialMeteringPoint` | boolean | Zie definitie hieronder |
| `bagId` | string\|null | BAG-ID van het verblijfsobject (leeg = bijzonder meetpunt) |

**Definitie `specialMeteringPoint`:**
- `bagId` aanwezig → `false`
- `bagId` leeg + secundair allocatiepunt → `false`
- `bagId` leeg + geen secundair allocatiepunt → `true`

---

## Nederlandse netbeheerders (EAN-codes)

| Naam | EAN-code | Gebied |
|------|----------|--------|
| Liander (Alliander) | `8716867000009` | Noord-Holland, Gelderland, Friesland e.a. |
| Stedin Netbeheer | `8716867000016` | Zuid-Holland, Utrecht, Zeeland |
| Enexis | `8716867000023` | Noord-Brabant, Groningen, Drenthe, Overijssel, Limburg |
| Westland Infra | `8716867000030` | Westland |
| Coteq | `8716867000047` | Twente |
| Rendo | `8716867000054` | Zuidwest Drenthe, Kop van Overijssel |

> Tip: gebruik `/gridoperators?postalCode=<postcode>` om de exacte netbeheerder voor een postcode op te vragen.

---

## Code Examples

### Python — Zoek EAN-codes op postcode + huisnummer

```python
import requests

BASE = "https://gateway.edsn.nl/eancodeboek/v1"

def get_ean_codes(postal_code: str, street_number: str, product: str = "ELK") -> dict:
    """Zoek EAN-codes op postcode + huisnummer. product = 'ELK' of 'GAS'."""
    r = requests.get(
        f"{BASE}/ecbinfoset",
        params={
            "product": product,
            "postalCode": postal_code.replace(" ", ""),
            "streetNumber": street_number,
        }
    )
    r.raise_for_status()
    return r.json()  # raw response

# Zoek elektriciteitsaansluiting
response = get_ean_codes("3010CK", "1")
print(response)
# response["results"][0]["ean"]          → EAN-code
# response["results"][0]["gridOperator"] → netbeheerder info
# response["count"]                      → aantal gevonden aansluitingen
```

### Python — Zoek netbeheerder op postcode

```python
def get_grid_operator(postal_code: str) -> list:
    """Geeft lijst van netbeheerders voor een postcode."""
    r = requests.get(
        f"{BASE}/gridoperators",
        params={"postalCode": postal_code.replace(" ", "")}
    )
    r.raise_for_status()
    return r.json()  # lijst van netbeheerders

operators = get_grid_operator("1012NX")
# [{"ean": "...", "name": "Liander", "products": ["ELK", "GAS"]}]
```

### Python — Zoek zowel elektriciteit als gas voor een adres

```python
def get_all_connections(postal_code: str, street_number: str,
                        addition: str = None) -> dict:
    """Haal ELK én GAS aansluitingen op voor een adres."""
    results = {}
    for product in ["ELK", "GAS"]:
        params = {
            "product": product,
            "postalCode": postal_code.replace(" ", ""),
            "streetNumber": street_number,
        }
        if addition:
            params["streetNumberAddition"] = addition
        r = requests.get(f"{BASE}/ecbinfoset", params=params)
        r.raise_for_status()
        results[product] = r.json()
    return results

all_connections = get_all_connections("1071XX", "1", "A")
```

### Python — Batch geocoding lijst adressen

```python
import time

def batch_lookup(addresses: list[dict], delay: float = 0.2) -> list[dict]:
    """
    addresses = [{"postalCode": "1234AB", "streetNumber": "10", "product": "ELK"}, ...]
    """
    results = []
    for addr in addresses:
        params = {k: v for k, v in addr.items()}
        params["postalCode"] = params["postalCode"].replace(" ", "")
        r = requests.get(f"{BASE}/ecbinfoset", params=params)
        results.append({
            "input": addr,
            "status": r.status_code,
            "raw": r.json() if r.ok else None,
        })
        time.sleep(delay)
    return results
```

### JavaScript — EAN-codes opzoeken

```javascript
const BASE = "https://gateway.edsn.nl/eancodeboek/v1";
const TOKEN = process.env.EDSN_TOKEN;

async function getEanCodes(postalCode, streetNumber, product = "ELK") {
  const url = new URL(`${BASE}/ecbinfoset`);
  url.searchParams.set("product", product);
  url.searchParams.set("postalCode", postalCode.replace(/\s/g, ""));
  url.searchParams.set("streetNumber", streetNumber);

  const res = await fetch(url);
  if (!res.ok) throw new Error(`EDSN fout: ${res.status}`);
  return res.json(); // raw response
}

const data = await getEanCodes("3010CK", "1");
console.log(data.results[0].ean);              // EAN-code
console.log(data.results[0].gridOperator.name); // Netbeheerder
```

### JavaScript — Netbeheerder per postcode

```javascript
async function getGridOperator(postalCode) {
  const url = new URL(`${BASE}/gridoperators`);
  url.searchParams.set("postalCode", postalCode.replace(/\s/g, ""));
  const res = await fetch(url);
  if (!res.ok) throw new Error(`EDSN fout: ${res.status}`);
  return res.json();
}

const operators = await getGridOperator("1012NX");
// [{ean: "...", name: "Liander", products: ["ELK", "GAS"]}]
```

---

## Tips & Valkuilen

- **Transformator = bijzonder meetpunt** — transformatorstations hebben geen BAG-ID en worden als `specialMeteringPoint: true` geretourneerd  en kunnen niet op adres worden gezocht, alleen op stad + bijzonder meetpunt. 
- **Postcode zonder spatie** — geef altijd in als `3010CK`, niet `3010 CK` (of strip de spatie in code)
- **Product verplicht bij `/ecbinfoset`** — altijd `ELK` of `GAS` meegeven
- **Alleen gedocumenteerde parametercombinaties** — andere combinaties geven een foutmelding
- **Paginering** — gebruik `limit` + `offset` bij grote resultaatsets (bijv. heel Rotterdam)
- **EAN-code formaat NL**: 18 cijfers, begint altijd met `871687...`
- **`specialMeteringPoint`**: bijzondere meetpunten (o.a. garages, schuren, transformatoren) hebben geen BAG-ID
- **Geen scripts nodig** — roep de API direct aan met `requests` of `fetch`, geen helper scripts

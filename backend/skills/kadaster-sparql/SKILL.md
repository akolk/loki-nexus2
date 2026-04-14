---
name: kadaster-sparql
description: >
  Generates a valid SPARQL query against the Kadaster Knowledge Graph (KKG) based on a natural language question.
  Use this skill whenever the user asks about Dutch geodata such as parcels, buildings, addresses, municipalities,
  neighbourhoods (buurt/wijk), roads, or cadastral information — and wants a SPARQL query or structured data back.
  Also trigger when the user asks: "hoe groot is het perceel?", "welke gebouwen zijn voor 1900 gebouwd?",
  "geef mij alle kerken in Amsterdam", "wat is het bouwjaar van dit pand?", or any question that could be
  answered by querying the Kadaster KKG endpoint. Always use this skill before writing any SPARQL by hand.
---

# Kadaster SPARQL Skill

Generates a SPARQL query for the Kadaster Knowledge Graph (KKG) based on a natural language question about Dutch
geodata (parcels, buildings, addresses, municipalities, roads, etc.).

## Endpoint

```
https://api.labs.kadaster.nl/datasets/kadaster/kkg/services/kkg/sparql
```

Send as HTTP POST with header `Content-Type: application/sparql-query` and the raw query as the body.

---

## Data Model

Read the full data model from `references/data-model.md` before writing any query.

Key classes:

| Class | Key Properties |
|---|---|
| `imx:Adres` | `imx:straatnaam`, `imx:huisnummer`, `imx:postcode`, `imx:plaatsnaam`, `imx-ext:vloerOppervlakte`, `imx:isAdresVanGebouw` |
| `imx:Gebouw` | `imx:bouwjaar`, `imx:gebruiksdoel`, `imx:status`, `imx-ext:gebouwType`, `imx:heeftAlsAdres`, `imx:bevindtZichOpPerceel` |
| `imx:Perceel` | `geo:hasMetricArea`, `imx-ext:perceelnummer`, `imx:ligtInRegistratieveRuimte` |
| `imx:Buurt` | `imx:naam`, `imx:buurtcode`, `geo:sfWithin` → `imx:Wijk` |
| `imx:Wijk` | `imx:naam`, `imx:wijkcode`, `geo:sfWithin` → `imx:Gemeentegebied` |
| `imx:Gemeentegebied` | `imx:naam`, `nen3610:identificatie`, `geo:sfWithin` → `imx:Provincie` |
| `imx:Provincie` | `imx:naam`, `nen3610:identificatie` |
| `imx:Weg` | `imx:functie`, `imx:fysiekVoorkomen`, `geo:hasGeometry` |

---

## Location Placeholders

Use **only** these placeholders for location filtering. They are substituted at runtime by the calling system
with the actual identifier for the requested location.

| Placeholder | Meaning |
|---|---|
| `#nummeraanduiding_id` | `imx:Adres` → `nen3610:identificatie` (specific address) |
| `#straatnaam` | `imx:Adres` → `imx:straatnaam` (street filter) |
| `#buurtcode` | `imx:Buurt` → `nen3610:identificatie` |
| `#wijkcode` | `imx:Wijk` → `nen3610:identificatie` |
| `#woonplaatscode` | `imx:Woonplaats` → `nen3610:identificatie` |
| `#gemeentecode` | `imx:Gemeentegebied` → `nen3610:identificatie` (format: `GM0344`) |
| `#provinciecode` | `imx:Provincie` → `nen3610:identificatie` |

> Never hard-code actual IDs. Always use placeholders.

---

## Prefix Handling

Do include PREFIX declarations in the query. Just use the short prefixes:
```json
{
    "imx:":"<http://modellen.geostandaarden.nl/def/imx-geo#>",
    "nen3610:": "<http://modellen.geostandaarden.nl/def/nen3610#>",
    "geo:": "<http://www.opengis.net/ont/geosparql#>",
    "rdf:": "<http://www.w3.org/1999/02/22-rdf-syntax-ns#>",
    "rdfs:": "<http://www.w3.org/2000/01/rdf-schema#>",
    "geof:": "<http://www.opengis.net/def/function/geosparql/>",
    "uom:": "<http://www.opengis.net/def/uom/OGC/1.0/>",
    "imx-ext:": "<https://modellen.kkg.kadaster.nl/def/imxgeo-ext#>",
    "sh:": "<http://www.w3.org/ns/shacl#>",
    "xsd:": "<http://www.w3.org/2001/XMLSchema#>",
}
```
---

## Query Writing Rules

1. **Use only the properties in the data model** — do not invent predicates.
2. **Filter on `xsd:gYear`** with: `FILTER(xsd:integer(str(?bouwjaar)) >= 1800)`
3. **Optional properties** (`imx:huisletter`, `imx:huisnummertoevoeging`) must be wrapped in `OPTIONAL { }`.
4. **Geometry** (`geo:hasGeometry`, `imx-ext:bovenaanzichtgeometrie`) is expensive — only request it when the user explicitly needs coordinates or spatial data.
5. **Always add a `LIMIT`** (default 100) unless the user asks for all results.
6. For counting, use `SELECT (COUNT(?x) AS ?count)`.
7. Connect buildings to addresses via `imx:heeftAlsAdres` / `imx:isAdresVanGebouw`.
8. Connect parcels to neighbourhoods via `imx:ligtInRegistratieveRuimte`.

---

## Workflow

### Step 1 — Understand the question

Identify:
- **What** is asked (area, count, list, attribute lookup, spatial filter)
- **Which class(es)** are involved
- **What location scope** is implied (address / street / neighbourhood / municipality / province / all of NL)

### Step 2 — Choose the right placeholder

| Scope | Placeholder |
|---|---|
| Specific address | `#nummeraanduiding_id` |
| Street | `#straatnaam` |
| Neighbourhood (buurt) | `#buurtcode` |
| District (wijk) | `#wijkcode` |
| City / woonplaats | `#woonplaatscode` |
| Municipality | `#gemeentecode` |
| Province | `#provinciecode` |
| All of NL | No placeholder needed |

### Step 3 — Draft the query

Follow the rules above. Use the example patterns in `references/query-examples.md` for guidance.

### Step 4 — Output

Return **only** the raw SPARQL query — no markdown fences, no explanation, unless the question cannot be answered
with the available data model, in which case reply exactly:

```
Ik heb geen data om deze vraag te beantwoorden.
```

---

## Examples (inline quick reference)

**Parcel area for an address:**
```sparql
SELECT ?oppervlakte WHERE {
  ?adres a imx:Adres ;
         nen3610:identificatie "#nummeraanduiding_id" ;
         imx:isAdresVanGebouw ?gebouw .
  ?gebouw imx:bevindtZichOpPerceel ?perceel .
  ?perceel geo:hasMetricArea ?oppervlakte .
}
```

**Buildings built before 1900 in a municipality:**
```sparql
SELECT ?identificatie ?bouwjaar WHERE {
  ?gebouw a imx:Gebouw ;
          nen3610:identificatie ?identificatie ;
          imx:bouwjaar ?bouwjaar ;
          imx:heeftAlsAdres ?adres .
  ?adres imx:plaatsnaam ?plaats .
  ?gemeente a imx:Gemeentegebied ;
            nen3610:identificatie "#gemeentecode" .
  ?adres geo:sfWithin ?gemeente .
  FILTER(xsd:integer(str(?bouwjaar)) < 1900)
}
LIMIT 100
```

**Count churches in a city:**
```sparql
SELECT (COUNT(?gebouw) AS ?aantalKerken) WHERE {
  ?gebouw a imx:Gebouw ;
          imx-ext:gebouwType "kerk" ;
          imx:heeftAlsAdres ?adres .
  ?adres imx:plaatsnaam ?plaats .
  ?woonplaats a imx:Woonplaats ;
              nen3610:identificatie "#woonplaatscode" .
  ?adres geo:sfWithin ?woonplaats .
}
```

For more patterns, see `references/query-examples.md`.
For full property details, see `references/data-model.md`.

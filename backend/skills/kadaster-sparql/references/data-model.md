# Kadaster KKG Data Model Reference

Full property listing per class. Use this when the quick reference in SKILL.md is insufficient.

---

## imx:Adres

| Property | Type | Notes |
|---|---|---|
| `nen3610:identificatie` | `xsd:string` | BAG nummeraanduiding ID |
| `imx:straatnaam` | `xsd:string` | |
| `imx:huisnummer` | `xsd:integer` | |
| `imx:huisletter` | `xsd:string` | **optional** |
| `imx:huisnummertoevoeging` | `xsd:string` | **optional** |
| `imx:postcode` | `xsd:string` | |
| `imx:plaatsnaam` | `xsd:string` | |
| `imx:omschrijving` | `xsd:string` | Full address string |
| `imx:isHoofdadres` | `xsd:boolean` | |
| `imx:isAdresVanGebouw` | `imx:Gebouw` | Link to building |
| `imx-ext:straat` | `imx-ext:Straat` | Link to street object |
| `imx-ext:vloerOppervlakte` | `xsd:integer` | Floor area in m² |
| `geo:hasGeometry` | `geo:Geometry` | Point geometry |

---

## imx:Gebouw

| Property | Type | Notes |
|---|---|---|
| `nen3610:identificatie` | `xsd:string` | BAG pand ID |
| `imx:bouwjaar` | `xsd:gYear` | Filter: `xsd:integer(str(?bouwjaar))` |
| `imx:gebruiksdoel` | `xsd:string` | See enum below |
| `imx:status` | `xsd:string` | See enum below |
| `imx-ext:gebouwType` | `xsd:string` | See enum below |
| `imx:heeftAlsAdres` | `imx:Adres` | Link to address(es) |
| `imx:bevindtZichOpPerceel` | `imx:Perceel` | Link to parcel |
| `imx-ext:bovenaanzichtgeometrie` | `geo:Geometry` | Top-down polygon |
| `imx-ext:maaiveldgeometrie` | `geo:Geometry` | Ground-level geometry |

**gebruiksdoel enum:** bijeenkomstfunctie / celfunctie / gezondheidszorgfunctie / industriefunctie /
kantoorfunctie / logiesfunctie / onderwijsfunctie / overige gebruiksfunctie / sportfunctie /
winkelfunctie / woonfunctie

**status enum:** Bouw gestart / Bouwvergunning verleend / Niet gerealiseerd pand / Pand buiten gebruik /
Pand gesloopt / Pand in gebruik / Pand in gebruik (niet ingemeten) / Pand ten onrechte opgevoerd /
Sloopvergunning verleend / Verbouwing pand / bestaand

**gebouwType enum (partial):** bezoekerscentrum / brandweerkazerne / bunker / crematorium /
elektriciteitscentrale / fabriek / fort / gemaal / gemeentehuis / gevangenis / hotel / huizenblok /
kapel / kas, warenhuis / kasteel / kerk / kliniek, inrichting, sanatorium / klokkentoren /
klooster, abdij / koepel / kunstijsbaan / manege / moskee / museum / overig / politiebureau /
pompstation / postkantoor / school / schoorsteen / sporthal / stadion / stationsgebouw / synagoge /
tank / tankstation / toren / uitzichttoren / universiteit / vuurtoren / watertoren / windmolen /
ziekenhuis / zwembad

---

## imx:Perceel

| Property | Type | Notes |
|---|---|---|
| `nen3610:identificatie` | `xsd:string` | |
| `geo:hasMetricArea` | `xsd:decimal` | Area in m² |
| `imx-ext:perceelnummer` | `xsd:integer` | |
| `imx-ext:plaatscoordinaten` | `geo:Geometry` | Centroid point |
| `geo:hasGeometry` | `geo:Geometry` | Polygon |
| `imx:ligtInRegistratieveRuimte` | `imx:Buurt` | Link to neighbourhood |

---

## imx:Buurt

| Property | Type | Notes |
|---|---|---|
| `nen3610:identificatie` | `xsd:string` | Buurtcode with prefix, e.g. `BU03440000` |
| `imx:naam` | `xsd:string` | |
| `imx:buurtcode` | `xsd:string` | |
| `geo:hasGeometry` | `http://www.opengis.net/ont/gml#Surface` | |
| `geo:sfWithin` | `imx:Wijk` | |
| `imx:bevatPerceel` | `imx:Perceel` | |

---

## imx:Wijk

| Property | Type | Notes |
|---|---|---|
| `nen3610:identificatie` | `xsd:string` | |
| `imx:naam` | `xsd:string` | |
| `imx:wijkcode` | `xsd:string` | |
| `geo:hasGeometry` | `http://www.opengis.net/ont/gml#Surface` | |
| `geo:sfWithin` | `imx:Gemeentegebied` | |

---

## imx:Gemeentegebied

| Property | Type | Notes |
|---|---|---|
| `nen3610:identificatie` | `xsd:string` | Format: `GM0344` |
| `imx:naam` | `xsd:string` | |
| `geo:hasGeometry` | `geo:Geometry` | |
| `geo:sfWithin` | `imx:Provincie` | |
| `imx:wordtBestuurdDoorGemeente` | `imx:Gemeente` | |

---

## imx:Gemeente

| Property | Type | Notes |
|---|---|---|
| `nen3610:identificatie` | `xsd:string` | |
| `imx:naam` | `xsd:string` | |
| `imx:bestuurdGebied` | `imx:Gemeentegebied` | |

---

## imx:Woonplaats

| Property | Type | Notes |
|---|---|---|
| `nen3610:identificatie` | `xsd:string` | |
| `imx:naam` | `xsd:string` | |
| `geo:hasGeometry` | `geo:Geometry` | |
| `imx:bevatPerceel` | `imx:Perceel` | |

---

## imx:Provincie

| Property | Type | Notes |
|---|---|---|
| `nen3610:identificatie` | `xsd:string` | |
| `imx:naam` | `xsd:string` | |
| `geo:hasGeometry` | `geo:Geometry` | |

---

## imx:Weg

| Property | Type | Notes |
|---|---|---|
| `nen3610:identificatie` | `xsd:string` | |
| `imx:functie` | `xsd:string` | |
| `imx:fysiekVoorkomen` | `xsd:string` | |
| `geo:hasGeometry` | `geo:Geometry` | |

---

## imx-ext:Straat

| Property | Type | Notes |
|---|---|---|
| `nen3610:identificatie` | `xsd:string` | |
| `imx-ext:bestaatUit` | `imx:Weg` | Links to road segments |

---

## imx:Bouwwerk

Non-building structures (bridges, walls, etc.)

| Property | Type | Notes |
|---|---|---|
| `nen3610:identificatie` | `xsd:string` | |
| `imx:type` | `xsd:string` | |
| `imx:status` | `xsd:string` | |
| `imx:bevindtZichOpPerceel` | `imx:Perceel` | |
| `imx-ext:maaiveldgeometrie` | `geo:Geometry` | |

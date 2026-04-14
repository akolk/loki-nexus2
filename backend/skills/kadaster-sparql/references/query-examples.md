# SPARQL Query Examples for Kadaster KKG

A collection of proven patterns. Use as inspiration — adapt placeholders and filters to match the question.

---

## 1. Parcel area for a specific address

**Question:** Hoe groot is het perceel van [adres]?

```sparql
SELECT ?oppervlakte WHERE {
  ?adres a imx:Adres ;
         nen3610:identificatie "#nummeraanduiding_id" ;
         imx:isAdresVanGebouw ?gebouw .
  ?gebouw imx:bevindtZichOpPerceel ?perceel .
  ?perceel geo:hasMetricArea ?oppervlakte .
}
```

---

## 2. Floor area (vloeroppervlakte) for a specific address

**Question:** Hoe groot is de woning op [adres]?

```sparql
SELECT ?vloerOppervlakte WHERE {
  ?adres a imx:Adres ;
         nen3610:identificatie "#nummeraanduiding_id" ;
         imx-ext:vloerOppervlakte ?vloerOppervlakte .
}
```

---

## 3. Construction year of a building

**Question:** Wanneer is het pand op [adres] gebouwd?

```sparql
SELECT ?bouwjaar WHERE {
  ?adres a imx:Adres ;
         nen3610:identificatie "#nummeraanduiding_id" ;
         imx:isAdresVanGebouw ?gebouw .
  ?gebouw imx:bouwjaar ?bouwjaar .
}
```

---

## 4. All buildings built before 1900 in a municipality

**Question:** Welke gebouwen zijn voor 1900 gebouwd in [gemeente]?

```sparql
SELECT ?identificatie ?bouwjaar ?omschrijving WHERE {
  ?gebouw a imx:Gebouw ;
          nen3610:identificatie ?identificatie ;
          imx:bouwjaar ?bouwjaar ;
          imx:heeftAlsAdres ?adres .
  ?adres imx:omschrijving ?omschrijving .
  ?gemeentegebied a imx:Gemeentegebied ;
                  nen3610:identificatie "#gemeentecode" .
  ?adres geo:sfWithin ?gemeentegebied .
  FILTER(xsd:integer(str(?bouwjaar)) < 1900)
}
LIMIT 100
```

---

## 5. Count churches in a city

**Question:** Hoeveel kerken zijn er in [woonplaats]?

```sparql
SELECT (COUNT(?gebouw) AS ?aantalKerken) WHERE {
  ?gebouw a imx:Gebouw ;
          imx-ext:gebouwType "kerk" ;
          imx:heeftAlsAdres ?adres .
  ?woonplaats a imx:Woonplaats ;
              nen3610:identificatie "#woonplaatscode" .
  ?adres geo:sfWithin ?woonplaats .
}
```

---

## 6. List all hospitals in a province

**Question:** Geef alle ziekenhuizen in [provincie].

```sparql
SELECT ?identificatie ?omschrijving WHERE {
  ?gebouw a imx:Gebouw ;
          nen3610:identificatie ?identificatie ;
          imx-ext:gebouwType "ziekenhuis" ;
          imx:heeftAlsAdres ?adres .
  ?adres imx:omschrijving ?omschrijving .
  ?provincie a imx:Provincie ;
             nen3610:identificatie "#provinciecode" .
  ?adres geo:sfWithin ?provincie .
}
LIMIT 100
```

---

## 7. Parcel number and area for a neighbourhood

**Question:** Geef de percelen in buurt [buurt] met hun oppervlakte.

```sparql
SELECT ?identificatie ?perceelnummer ?oppervlakte WHERE {
  ?perceel a imx:Perceel ;
           nen3610:identificatie ?identificatie ;
           imx-ext:perceelnummer ?perceelnummer ;
           geo:hasMetricArea ?oppervlakte ;
           imx:ligtInRegistratieveRuimte ?buurt .
  ?buurt nen3610:identificatie "#buurtcode" .
}
LIMIT 100
```

---

## 8. Buildings with a specific use (gebruiksdoel)

**Question:** Geef alle kantoorgebouwen in [gemeente].

```sparql
SELECT ?identificatie ?omschrijving WHERE {
  ?gebouw a imx:Gebouw ;
          nen3610:identificatie ?identificatie ;
          imx:gebruiksdoel "kantoorfunctie" ;
          imx:heeftAlsAdres ?adres .
  ?adres imx:omschrijving ?omschrijving .
  ?gemeentegebied a imx:Gemeentegebied ;
                  nen3610:identificatie "#gemeentecode" .
  ?adres geo:sfWithin ?gemeentegebied .
}
LIMIT 100
```

---

## 9. Address details for a specific postcode + house number

**Question:** Wat is het adres bij postcode [X] huisnummer [Y]?

```sparql
SELECT ?omschrijving ?plaatsnaam ?straatnaam WHERE {
  ?adres a imx:Adres ;
         imx:postcode "1234AB" ;
         imx:huisnummer 10 ;
         imx:omschrijving ?omschrijving ;
         imx:plaatsnaam ?plaatsnaam ;
         imx:straatnaam ?straatnaam .
}
```

---

## 10. All neighbourhoods in a municipality with their names

**Question:** Welke buurten zijn er in [gemeente]?

```sparql
SELECT ?naam ?buurtcode WHERE {
  ?buurt a imx:Buurt ;
         imx:naam ?naam ;
         imx:buurtcode ?buurtcode ;
         geo:sfWithin ?wijk .
  ?wijk geo:sfWithin ?gemeentegebied .
  ?gemeentegebied nen3610:identificatie "#gemeentecode" .
}
ORDER BY ?naam
```

---

## 11. Status of a building

**Question:** Wat is de status van het pand op [adres]?

```sparql
SELECT ?status WHERE {
  ?adres a imx:Adres ;
         nen3610:identificatie "#nummeraanduiding_id" ;
         imx:isAdresVanGebouw ?gebouw .
  ?gebouw imx:status ?status .
}
```

---

## 12. Buildings built between two years in a wijk

**Question:** Welke woningen zijn gebouwd tussen 1950 en 1980 in wijk [X]?

```sparql
SELECT ?identificatie ?bouwjaar ?omschrijving WHERE {
  ?gebouw a imx:Gebouw ;
          nen3610:identificatie ?identificatie ;
          imx:bouwjaar ?bouwjaar ;
          imx:gebruiksdoel "woonfunctie" ;
          imx:heeftAlsAdres ?adres .
  ?adres imx:omschrijving ?omschrijving .
  ?wijk a imx:Wijk ;
        nen3610:identificatie "#wijkcode" .
  ?adres geo:sfWithin ?wijk .
  FILTER(xsd:integer(str(?bouwjaar)) >= 1950 && xsd:integer(str(?bouwjaar)) <= 1980)
}
LIMIT 100
```

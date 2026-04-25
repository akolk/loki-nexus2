import json
import logging
import requests

cbs_apis = [
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/03747",
        "displaytitle": "Overledenen; geslacht, leeftijd, burgerlijke staat, regio",
        "ObservationCount": 2937178,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/03759ned",
        "displaytitle": "Bevolking op 1 januari en gemiddeld; geslacht, leeftijd en regio",
        "ObservationCount": 97851795,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/37201",
        "displaytitle": "Geboorte; kerncijfers vruchtbaarheid, leeftijd moeder, regio",
        "ObservationCount": 759046,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/37230ned",
        "displaytitle": "Bevolkingsontwikkeling; regio per maand",
        "ObservationCount": 2831951,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/37259ned",
        "displaytitle": "Bevolkingsontwikkeling; levend geborenen, overledenen en migratie per regio",
        "ObservationCount": 4400636,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/37890",
        "displaytitle": "Huwen en huwelijksontbinding; geslacht, leeftijd (31 december), regio",
        "ObservationCount": 2729175,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/60048ned",
        "displaytitle": "Verhuisde personen; binnen gemeenten, tussen gemeenten, regio",
        "ObservationCount": 6724205,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/70077NED",
        "displaytitle": "Professionele podiumkunsten; capaciteit, voorstellingen, bezoekers, regio",
        "ObservationCount": 10963,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/70262ned",
        "displaytitle": "Bodemgebruik; uitgebreide gebruiksvorm, per gemeente",
        "ObservationCount": 332442,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/70806ned",
        "displaytitle": "Lengte van wegen; wegkenmerken, regio",
        "ObservationCount": 292920,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/71231ned",
        "displaytitle": "Gemeenterekeningen; balans naar regio en grootteklasse",
        "ObservationCount": 78648,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/71476ned",
        "displaytitle": "Zuivering van stedelijk afvalwater; per regionale waterkwaliteitsbeheerder",
        "ObservationCount": 52319,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/71478ned",
        "displaytitle": "(Speciaal) basisonderwijs en speciale scholen; leerlingen, schoolregio",
        "ObservationCount": 2532150,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/71486ned",
        "displaytitle": "Huishoudens; samenstelling, grootte, regio, 1 januari",
        "ObservationCount": 8365030,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/71487ned",
        "displaytitle": "Huishoudens; kindertal, leeftijdsklasse kind, regio, 1 januari",
        "ObservationCount": 4992000,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/71488ned",
        "displaytitle": "Huishoudens; personen naar geslacht, leeftijd en regio, 1 januari",
        "ObservationCount": 13012272,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/71531ned",
        "displaytitle": "Lengte van vaarwegen; vaarwegkenmerken, regio, 2005 t/m 2018",
        "ObservationCount": 9282,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/71536ned",
        "displaytitle": "Provincierekeningen; balansposten, regio",
        "ObservationCount": 22780,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/80142ned",
        "displaytitle": "Overledenen; doodsoorzaak (4 hoofdgroepen), regio",
        "ObservationCount": 127716,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/80202ned",
        "displaytitle": "Overledenen; belangrijke doodsoorzaken (korte lijst), regio",
        "ObservationCount": 6699913,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/80305ned",
        "displaytitle": "Nabijheid voorzieningen; afstand locatie, regionale cijfers",
        "ObservationCount": 1045790,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/80780ned",
        "displaytitle": "Landbouw; gewassen, dieren en grondgebruik naar regio",
        "ObservationCount": 445470,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/80781ned",
        "displaytitle": "Landbouw; gewassen, dieren en grondgebruik naar gemeente",
        "ObservationCount": 2642624,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/80783ned",
        "displaytitle": "Landbouw; gewassen, dieren en grondgebruik naar hoofdbedrijfstype, regio",
        "ObservationCount": 4349431,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/80784ned",
        "displaytitle": "Landbouw; arbeidskrachten naar regio",
        "ObservationCount": 196540,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/80786ned",
        "displaytitle": "Landbouw; economische omvang naar omvangsklasse, hoofdbedrijfstype, regio",
        "ObservationCount": 103275,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/80787ned",
        "displaytitle": "Landbouw; gewassen, dieren en grondgebruik naar omvangsklasse en regio",
        "ObservationCount": 447578,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/80794ned",
        "displaytitle": "Personen met een uitkering; uitkeringsontvangers per regio",
        "ObservationCount": 1422744,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/80807ned",
        "displaytitle": "Landbouw; bedrijven met verbredingsactiviteiten, hoofdbedrijfstype, regio",
        "ObservationCount": 24480,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/81064ned",
        "displaytitle": "Betalingsachterstand zorgpremie; regio per 31 december",
        "ObservationCount": 15570,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/81206NED",
        "displaytitle": "Gemeentefinanciën vanaf 1900",
        "ObservationCount": 1488,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/81333ned",
        "displaytitle": "Verhuisde personen tussen gemeenten, 2010",
        "ObservationCount": 281963,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/81351ned",
        "displaytitle": "Investering in materiële vaste activa; bedrijfstak, regio ",
        "ObservationCount": 291213,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/81528NED",
        "displaytitle": "Energieverbruik particuliere woningen; woningtype en regio's",
        "ObservationCount": 218311,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/81575NED",
        "displaytitle": "Vestigingen van bedrijven; bedrijfstak, gemeente",
        "ObservationCount": 222124,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/81578NED",
        "displaytitle": "Vestigingen van bedrijven; bedrijfstak, regio",
        "ObservationCount": 2719684,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/81644NED",
        "displaytitle": "Vestigingen van bedrijven; grootte, rechtsvorm, bedrijfstak, regio",
        "ObservationCount": 206910,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/81734NED",
        "displaytitle": "Tussen gemeenten verhuisde personen",
        "ObservationCount": 3528056,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/81996NED",
        "displaytitle": "Vestigingen van bedrijven; zeggenschap, bedrijfstak, regio",
        "ObservationCount": 39820,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/82015NED",
        "displaytitle": "Bijstandsuitkeringen; uitkeringsgrondslag, regio's",
        "ObservationCount": 1109651,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/82020NED",
        "displaytitle": "Bijstand; bijstandsvorderingen naar ontstaansgrond en regio",
        "ObservationCount": 1026704,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/82056NED",
        "displaytitle": "Levend geboren kinderen; huishoudenssamenstelling, regio",
        "ObservationCount": 38995,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/82059NED",
        "displaytitle": "Logiesaccommodaties; gasten, nachten, woonland, logiesvorm, regio",
        "ObservationCount": 764331,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/82061NED",
        "displaytitle": "Hotels; gasten, overnachtingen, woonland, regio ",
        "ObservationCount": 812078,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/82062NED",
        "displaytitle": "Logiesaccommodaties; capaciteit, accommodaties, bedden, regio",
        "ObservationCount": 324118,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/82211NED",
        "displaytitle": "Woningen en niet-woningen in de pijplijn; gebruiksfunctie, regio",
        "ObservationCount": 2334150,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/82243NED",
        "displaytitle": "Faillissementen; natuurlijke personen, regio",
        "ObservationCount": 51300,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/82522NED",
        "displaytitle": "Faillissementen; bedrijven en instellingen, regio",
        "ObservationCount": 51300,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/82538NED",
        "displaytitle": "Levering aardgas, elektriciteit via openbaar net; bedrijven, SBI2008, regio",
        "ObservationCount": 340772,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/82550NED",
        "displaytitle": "Voorraad woningen; gemiddeld oppervlak; woningtype, bouwjaarklasse, regio",
        "ObservationCount": 594690,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/82557NED",
        "displaytitle": "Caribisch Nederland; overlast in buurt, persoonskenmerken",
        "ObservationCount": 8022,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/82621NED",
        "displaytitle": "Hotels; zakelijke overnachtingen, regio",
        "ObservationCount": 6672,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/82900NED",
        "displaytitle": "Voorraad woningen; eigendom, type verhuurder, bewoning, regio",
        "ObservationCount": 125496,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/82975NED",
        "displaytitle": "Jeugdbeschermingstrajecten; regio",
        "ObservationCount": 194123,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/82977NED",
        "displaytitle": "Jeugdreclasseringstrajecten; regio",
        "ObservationCount": 51530,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83162NED",
        "displaytitle": "Huurverhoging woningen; regio",
        "ObservationCount": 462,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83246NED",
        "displaytitle": "Personen; afstand tot ouder; persoonskenmerken, regio 2014",
        "ObservationCount": 5365440,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83250NED",
        "displaytitle": "Personen met verstrekte geneesmiddelen; regio (GGD)",
        "ObservationCount": 13679697,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83251NED",
        "displaytitle": "Personen met verstrekte geneesmiddelen; regio (gemeente)",
        "ObservationCount": 51835626,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83434NED",
        "displaytitle": "Zuivering van stedelijk afvalwater; afzet zuiveringsslib, regio ",
        "ObservationCount": 68544,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83440NED",
        "displaytitle": "Maatstaven gemeentefonds; Sociaal domein; diverse peildata; regio 2016",
        "ObservationCount": 22639,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83452NED",
        "displaytitle": "Huishoudelijk afval per gemeente per inwoner",
        "ObservationCount": 482531,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83454NED",
        "displaytitle": "Gemeentelijke kosten; jeugdzorg, regio",
        "ObservationCount": 41523,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83488NED",
        "displaytitle": "Personen met een rijbewijs; rijbewijscategorie, leeftijd, regio, 1 januari",
        "ObservationCount": 32604,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83502NED",
        "displaytitle": "Bevolking; geslacht, leeftijd en viercijferige postcode, 1 januari",
        "ObservationCount": 7193592,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83504NED",
        "displaytitle": "Bevolking; geslacht, positie huishouden, viercijferige postcode, 1 januari",
        "ObservationCount": 3082968,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83505NED",
        "displaytitle": "Huishoudens; huishoudenssamenstelling en viercijferige postcode, 1 januari",
        "ObservationCount": 709481,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83558NED",
        "displaytitle": "Gemeentelijke afvalstoffen; hoeveelheden",
        "ObservationCount": 177872,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83582NED",
        "displaytitle": "Banen van werknemers in december; economische activiteit (SBI2008), regio",
        "ObservationCount": 166646,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83599NED",
        "displaytitle": "Openstaande vacatures; SBI 2008, regio",
        "ObservationCount": 24072,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83614NED",
        "displaytitle": "Gemeentebegrotingen; heffingen naar regio en grootteklasse",
        "ObservationCount": 16380,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83616NED",
        "displaytitle": "Kerncijfers gemeentebegrotingen, heffingen naar regio en grootteklasse",
        "ObservationCount": 20020,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83625NED",
        "displaytitle": "Bestaande koopwoningen; gemiddelde verkoopprijzen, regio",
        "ObservationCount": 22350,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83631NED",
        "displaytitle": "Vestigingen van bedrijven; oprichtingen, bedrijfstak, regio",
        "ObservationCount": 137020,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83635NED",
        "displaytitle": "Vestigingen van bedrijven; opheffingen, bedrijfstak, regio",
        "ObservationCount": 137020,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83641NED",
        "displaytitle": "Gemeentebegrotingen; baten en lasten naar regio en grootteklasse  ",
        "ObservationCount": 161460,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83642NED",
        "displaytitle": "Gemeentebegrotingen; heffingen per gemeente",
        "ObservationCount": 101780,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83643NED",
        "displaytitle": "Kerncijfers gemeentebegrotingen, heffingen per gemeente",
        "ObservationCount": 146977,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83648NED",
        "displaytitle": "Geregistreerde criminaliteit; soort misdrijf, regio",
        "ObservationCount": 3149616,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83651NED",
        "displaytitle": "Geregistreerde diefstallen; diefstallen en verdachten, regio",
        "ObservationCount": 3175243,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83671NED",
        "displaytitle": "Bouwvergunningen woonruimten; type, opdrachtgever, eigendom, gemeente",
        "ObservationCount": 1051452,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83672NED",
        "displaytitle": "Bouwvergunningen; bedrijfsgebouwen, bedrijfstak, regio",
        "ObservationCount": 118596,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83673NED",
        "displaytitle": "Bouwvergunningen; kerncijfers nieuwbouwwoningen; bouwkosten, inhoud, regio",
        "ObservationCount": 2550,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83674NED",
        "displaytitle": "Gezondheidsmonitor; bevolking 19 jaar of ouder, regio, 2016",
        "ObservationCount": 76179,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83704NED",
        "displaytitle": "Voorraad woningen; woningtype, oppervlakteklasse, regio",
        "ObservationCount": 210840,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83707NED",
        "displaytitle": "Bouw; bouwkosten nieuwbouw naar bestemming, bouwfase, regio",
        "ObservationCount": 181150,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83718NED",
        "displaytitle": "Maatstaven gemeentefonds; Sociaal domein; diverse peildata; regio 2017",
        "ObservationCount": 23301,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83978NED",
        "displaytitle": "Consumentenvertrouwen; regionale kenmerken",
        "ObservationCount": 74290,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83982NED",
        "displaytitle": "Dierlijke mest; productie en mineralenuitscheiding, diercategorie, regio ",
        "ObservationCount": 452640,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83983NED",
        "displaytitle": "Dierlijke mest; productie en mineralenuitscheiding; bedrijfstype, regio ",
        "ObservationCount": 206080,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/83997NED",
        "displaytitle": "Maatstaven gemeentefonds: Sociaal domein: diverse peildata; regio 2018",
        "ObservationCount": 21297,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84071NED",
        "displaytitle": "Dierlijke mest en mineralen; productie, transport en gebruik per regio",
        "ObservationCount": 38130,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84413NED",
        "displaytitle": "Gemeenterekeningen; gemeentelijke taakvelden, gemeentegrootteklasse, regio",
        "ObservationCount": 125580,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84415NED",
        "displaytitle": "Gemeenterekeningen; gemeentelijke heffingen, gemeentegrootteklasse, regio",
        "ObservationCount": 12740,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84488NED",
        "displaytitle": "Woonlasten huishoudens; kenmerken woning, regio",
        "ObservationCount": 422376,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84521NED",
        "displaytitle": "Ziekenhuisopnamen; diagnose-indeling ISHMT, regio",
        "ObservationCount": 122163717,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84523NED",
        "displaytitle": "Ziekenhuisopnamen; diagnose-indeling VTV, regio",
        "ObservationCount": 18020178,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84525NED",
        "displaytitle": "Regionale prognose 2020-2050; bevolking, regio-indeling 2018",
        "ObservationCount": 4123,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84527NED",
        "displaytitle": "Regionale prognose 2020-2050; bevolking, intervallen, regio-indeling 2018 ",
        "ObservationCount": 40269,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84547NED",
        "displaytitle": "Verhuisde personen; geslacht, leeftijd en regio per maand",
        "ObservationCount": 122200704,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84570NED",
        "displaytitle": "Woontevredenheid; kenmerken huishouden, regio's",
        "ObservationCount": 342174,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84571NED",
        "displaytitle": "Woontevredenheid; kenmerken woning, regio's",
        "ObservationCount": 369078,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84580NED",
        "displaytitle": "Gemeentelijke uitgaven Wmo-maatwerkvoorzieningen; type voorziening, regio",
        "ObservationCount": 66192,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84590NED",
        "displaytitle": "Maatstaven gemeentefonds; diverse indicatoren; regio-indeling 2019",
        "ObservationCount": 11392,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84687NED",
        "displaytitle": "Totale vervoersprestatie in Nederland; vervoerwijzen, regio's",
        "ObservationCount": 6024,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84702NED",
        "displaytitle": "Mobiliteit; per persoon, verplaatsingskenmerken, reismotieven, regio's ",
        "ObservationCount": 1306278,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84703NED",
        "displaytitle": "Arbeidsdeelname; regionale indeling 2019",
        "ObservationCount": 1513084,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84708NED",
        "displaytitle": "Mobiliteit; per persoon, verplaatsingskenmerken, vervoerwijzen en regio's",
        "ObservationCount": 989982,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84709NED",
        "displaytitle": "Mobiliteit; per persoon, persoonskenmerken, vervoerwijzen en regio's",
        "ObservationCount": 2250300,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84710NED",
        "displaytitle": "Mobiliteit; per persoon, vervoerwijzen, motieven, regio's",
        "ObservationCount": 237042,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84711NED",
        "displaytitle": "Mobiliteit; per verplaatsing, vervoerwijzen, motieven, regio's",
        "ObservationCount": 79296,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84713NED",
        "displaytitle": "Mobiliteit; per persoon, persoonskenmerken, motieven en regio's",
        "ObservationCount": 2891310,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84777NED",
        "displaytitle": "Medisch geschoolden; specialisme, arbeidspositie, sector, woonregio",
        "ObservationCount": 11009760,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84779NED",
        "displaytitle": "Medisch geschoolden; specialisme, arbeidspositie, leeftijd, woonregio",
        "ObservationCount": 7805952,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84780NED",
        "displaytitle": "Voortijdig schoolverlaters; geslacht, woonregio",
        "ObservationCount": 70271,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84847NED",
        "displaytitle": "Huiselijk geweld; kerncijfers Veilig Thuis, regio",
        "ObservationCount": 129362,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84848NED",
        "displaytitle": "Huiselijk geweld; rol/functie, organisatie, duur geweld, Veilig Thuis-regio",
        "ObservationCount": 242982,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84849NED",
        "displaytitle": "Huiselijk geweld; rol/functie, organisatie, duur geweld, regio",
        "ObservationCount": 479402,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84850NED",
        "displaytitle": "Huiselijk geweld; aard geweld, aanvullende informatie, Veilig Thuis-regio",
        "ObservationCount": 237994,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84851NED",
        "displaytitle": "Huiselijk geweld; aard geweld, aanvullende informatie, regio",
        "ObservationCount": 871602,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84852NED",
        "displaytitle": "Huiselijk geweld; veiligheidsbeoordeling en -taxatie Veilig Thuis, regio",
        "ObservationCount": 252130,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84853NED",
        "displaytitle": "Huiselijk geweld; uitkomsten onderzoeken Veilig Thuis, Veilig Thuis-regio",
        "ObservationCount": 13950,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84854NED",
        "displaytitle": "Huiselijk geweld; organisatie van overdracht, type hulp, Veilig Thuis-regio",
        "ObservationCount": 99840,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84855NED",
        "displaytitle": "Huiselijk geweld; organisatie van overdracht, type hulp, regio",
        "ObservationCount": 155760,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84860NED",
        "displaytitle": "Maatstaven gemeentefonds; diverse indicatoren; regio-indeling 2020",
        "ObservationCount": 10324,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84924NED",
        "displaytitle": "Personen met uitgesproken schuldsanering; jaar uitspraak, regio",
        "ObservationCount": 6432,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84926NED",
        "displaytitle": "Personen in de schuldsanering op 31 december; regio",
        "ObservationCount": 9639,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/84928NED",
        "displaytitle": "Personen met beëindigde schuldsanering; regio, wijze beëindiging",
        "ObservationCount": 23255,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85004NED",
        "displaytitle": "Hernieuwbare energie; zonnestroom, windenergie, RES-regio",
        "ObservationCount": 7090,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85005NED",
        "displaytitle": "Zonnestroom; vermogen en vermogensklasse, bedrijven en woningen, regio",
        "ObservationCount": 78963,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85012NED",
        "displaytitle": "Gezondheidsmonitor; bevolking 18 jaar of ouder, regio, 2020",
        "ObservationCount": 67827,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85020NED",
        "displaytitle": "Lengte van fietsnetwerk; fietswegkenmerken, regio ",
        "ObservationCount": 15246,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85035NED",
        "displaytitle": "Woningvoorraad; woningtype op 1 januari, regio",
        "ObservationCount": 13568,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85036NED",
        "displaytitle": "Gemiddelde WOZ-waarde van woningen; eigendom, regio ",
        "ObservationCount": 11523,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85052NED",
        "displaytitle": "Maatstaven gemeentefonds; diverse indicatoren; regio-indeling 2021",
        "ObservationCount": 10237,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85055NED",
        "displaytitle": "Mobiliteit: per verplaatsing, verplaatsingskenmerken, motieven, regio's",
        "ObservationCount": 437241,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85056NED",
        "displaytitle": "Mobiliteit; per verplaatsing, verplaatsingskenmerken, vervoerwijzen, regio",
        "ObservationCount": 330606,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85094NED",
        "displaytitle": "Trajecten jeugdzorg in natura; regio (gemeente), op peildatum",
        "ObservationCount": 67344,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85097NED",
        "displaytitle": "Jeugdhulptrajecten in natura; verwijzer, regio (gemeente)",
        "ObservationCount": 1744741,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85098NED",
        "displaytitle": "Indicatoren jeugdzorg in natura; gemeenten",
        "ObservationCount": 23734,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85118NED",
        "displaytitle": "Arbeidsdeelname; wijken en buurten, 2019",
        "ObservationCount": 1718461,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85146NED",
        "displaytitle": "Veiligheidsmonitor; kerncijfers, regio",
        "ObservationCount": 261909,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85150NED",
        "displaytitle": "Zorgwoonruimten; type zorgwoonruimte, regio",
        "ObservationCount": 5472,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85171NED",
        "displaytitle": "Regionale prognose 2023-2050; bevolking, regio-indeling 2021",
        "ObservationCount": 3948,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85173NED",
        "displaytitle": "Regionale prognose 2023-2050; bevolking, intervallen, regio-indeling 2021",
        "ObservationCount": 34020,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85175NED",
        "displaytitle": "Arbeidsdeelname; wijken en buurten, 2020",
        "ObservationCount": 1735993,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85235NED",
        "displaytitle": "Motorvoertuigenpark actief; inwoners, type, regio, 1 januari",
        "ObservationCount": 2380,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85237NED",
        "displaytitle": "Personenauto's actief; voertuigkenmerken, regio's, 1 januari ",
        "ObservationCount": 70035,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85238NED",
        "displaytitle": "Motorfietsen actief; voertuigkenmerken, regio's, 1 januari",
        "ObservationCount": 44100,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85239NED",
        "displaytitle": "Bedrijfsvoertuigen actief; voertuigkenmerken, regio's, 1 januari",
        "ObservationCount": 801752,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85240NED",
        "displaytitle": "Bromfietsen actief; voertuigsoort, bouwjaar, leeftijd, regio, 1 januari",
        "ObservationCount": 114660,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85242NED",
        "displaytitle": "Bromfietsen actief; aantal (per 1000 inwoners), voertuig, regio, 1 januari",
        "ObservationCount": 21336,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85249NED",
        "displaytitle": "Motorvoertuigen actief; sloop, export en overige uitval, regio's",
        "ObservationCount": 10080,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85269NED",
        "displaytitle": "Arbeidsdeelname; regionale indeling 2021",
        "ObservationCount": 796893,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85303NED",
        "displaytitle": "Weidegang van melkvee; bedrijfsgrootte, regio",
        "ObservationCount": 45078,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85309NED",
        "displaytitle": "Maatstaven gemeentefonds; diverse indicatoren; regio-indeling 2022",
        "ObservationCount": 10033,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85322NED",
        "displaytitle": "Slachtofferschap traditionele criminaliteit; regio",
        "ObservationCount": 252606,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85353NED",
        "displaytitle": "Mbo; studenten, niveau, leerweg, studierichting, regiokenmerken",
        "ObservationCount": 1980000,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85356NED",
        "displaytitle": "Mbo; gediplomeerden, niveau, leerweg, studierichting, regiokenmerken",
        "ObservationCount": 1782000,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85361NED",
        "displaytitle": "Huiselijk geweld; meldingen naar eerdere betrokkenheid Veilig Thuis, regio",
        "ObservationCount": 54204,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85380NED",
        "displaytitle": "Vo; leerlingen, onderwijssoort, leerjaar, woonregio",
        "ObservationCount": 103194,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85382NED",
        "displaytitle": "Vo; examenkandidaten en gediplomeerden, onderwijssoort, woonregio",
        "ObservationCount": 27290,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85451NED",
        "displaytitle": "Immi- en emigratie; geslacht, leeftijd, nationaliteit, regio",
        "ObservationCount": 111168288,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85458NED",
        "displaytitle": "Bevolking; herkomstland, geboorteland, leeftijd, regio, 1 januari",
        "ObservationCount": 20746440,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85468NED",
        "displaytitle": "Immigratie en emigratie; geslacht, leeftijd, geboorteland, regio",
        "ObservationCount": 141486912,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85472NED",
        "displaytitle": "Slachtofferschap online criminaliteit; regio",
        "ObservationCount": 189577,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85481NED",
        "displaytitle": "Werknemersbanen en reisafstand; woon- en werkregio",
        "ObservationCount": 1041161,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85482NED",
        "displaytitle": "Werknemersbanen en reisafstand; SBI (2008), arbeidsduur, woon- en werkregio",
        "ObservationCount": 500224,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85483NED",
        "displaytitle": "Werknemersbanen en reisafstand; geslacht, leeftijd, woon- en werkregio",
        "ObservationCount": 454104,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85485NED",
        "displaytitle": "Arbeidsdeelname; wijken en buurten, 2021",
        "ObservationCount": 1766474,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85489NED",
        "displaytitle": "Leerlingen in (speciaal) basisonderwijs; herkomst, woonregio",
        "ObservationCount": 170100,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85490NED",
        "displaytitle": "Leerlingen op speciale scholen; herkomst, woonregio",
        "ObservationCount": 680400,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85494NED",
        "displaytitle": "Arbeidsdeelname; regionale indeling 2022",
        "ObservationCount": 631479,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85525NED",
        "displaytitle": "Bevolking; hoogstbehaald onderwijsniveau en regio",
        "ObservationCount": 2062880,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85554NED",
        "displaytitle": "Personen met WW-uitkering, seizoengecorrigeerd; persoonskenmerken en regio",
        "ObservationCount": 290016,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85563NED",
        "displaytitle": "Gezondheidsmonitor; bevolking 18 jaar of ouder, regio, 2022",
        "ObservationCount": 54992,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85588NED",
        "displaytitle": "Re-integratie-/participatievoorzieningen; type, status voorziening en regio",
        "ObservationCount": 1781136,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85610NED",
        "displaytitle": "Conjunctuurenquête Nederland; regio",
        "ObservationCount": 526664,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85614NED",
        "displaytitle": "Ondernemersvertrouwen; regio",
        "ObservationCount": 19396,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85619NED",
        "displaytitle": "Bestelauto's; gemiddelde leeftijd, leeftijdsklasse, hoofdgebruiker, regio's",
        "ObservationCount": 104328,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85636NED",
        "displaytitle": "Akkerbouwgewassen; productie, regio",
        "ObservationCount": 43058,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85644NED",
        "displaytitle": "Bevolking; geslacht, leeftijd, nationaliteit en regio, 1 januari",
        "ObservationCount": 23369472,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85655NED",
        "displaytitle": "Verdachten; delict, leeftijd, geslacht en woongemeente",
        "ObservationCount": 2462687,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85701NED",
        "displaytitle": "Leerlingen en studenten; onderwijssoort, woonregio",
        "ObservationCount": 514080,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85702NED",
        "displaytitle": "Gediplomeerden; onderwijssoort, woonregio",
        "ObservationCount": 397800,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85761NED",
        "displaytitle": "Lengte van vaarwegen; vaarwegvaktype, regio",
        "ObservationCount": 408,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85792NED",
        "displaytitle": "Bestaande koopwoningen; verkoopprijzen, prijsindex 2020=100, regio",
        "ObservationCount": 25704,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85814NED",
        "displaytitle": "Arbeidsdeelname; wijken en buurten, 2022",
        "ObservationCount": 2120850,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85819NED",
        "displaytitle": "Bestaande koopwoningen; verkoopprijzen prijsindex 2020=100, regio (COROP)",
        "ObservationCount": 49200,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85896NED",
        "displaytitle": "Wmo-cliënten; type maatwerkvoorziening, persoonskenmerken, regio",
        "ObservationCount": 4383672,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85922NED",
        "displaytitle": "Investeringen in vaste activa; type en regio, nationale rekeningen",
        "ObservationCount": 23716,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85923NED",
        "displaytitle": "Investeringen in vaste activa; bedrijfstak en regio, nationale rekeningen",
        "ObservationCount": 28980,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85924NED",
        "displaytitle": "Regionale kerncijfers; nationale rekeningen",
        "ObservationCount": 33337,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85925NED",
        "displaytitle": "Productieproces; bedrijfstak en regio, nationale rekeningen",
        "ObservationCount": 494172,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85926NED",
        "displaytitle": "Economische groei; bedrijfstak en regio, nationale rekeningen",
        "ObservationCount": 61129,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85927NED",
        "displaytitle": "Inkomensrekening sector huishoudens naar regio; nationale rekeningen",
        "ObservationCount": 3264,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85950NED",
        "displaytitle": "Woonlasten huishoudens; kenmerken huishouden, woning, gemeente",
        "ObservationCount": 2522517,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85955NED",
        "displaytitle": "Ondervonden delicten traditionele criminaliteit; regio",
        "ObservationCount": 89257,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85967NED",
        "displaytitle": "Inkomsten uit eigen bijdragen Wmo excl. verblijf en opvang; inkomen, regio",
        "ObservationCount": 127817,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85971NED",
        "displaytitle": "Donorregistratie (18 jaar of ouder); regio (indeling 2024)",
        "ObservationCount": 10773,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/85980NED",
        "displaytitle": "Aandachtsgroepen volkshuisvesting; regio, 1 januari en 31 december",
        "ObservationCount": 32331535,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86008NED",
        "displaytitle": "Arbeidsdeelname; gemeenten (regio-indeling 2024)",
        "ObservationCount": 26065407,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86050NED",
        "displaytitle": "Wmo-cliënten; type maatwerkvoorziening (detail), regio",
        "ObservationCount": 185146,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86051NED",
        "displaytitle": "Wmo-voorzieningen; stand, instroom, uitstroom, regio",
        "ObservationCount": 123465,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86053NED",
        "displaytitle": "Huishoudelijk restafval; nascheiding per gemeente",
        "ObservationCount": 22988,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86054NED",
        "displaytitle": "Voorraad woningen; overige toevoegingen en onttrekkingen (detail), regio",
        "ObservationCount": 50040,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86060NED",
        "displaytitle": "Wmo-gebruik; aantal maatwerkvoorzieningen, regio",
        "ObservationCount": 195058,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86061NED",
        "displaytitle": "Wmo-cliënten; reden beëindiging ondersteuning, regio",
        "ObservationCount": 53930,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86063NED",
        "displaytitle": "Particuliere huishoudens; soort woonruimte, regio, 31 december",
        "ObservationCount": 202055,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86064NED",
        "displaytitle": "Personen; soort woonruimte, positie huishouden, regio, 31 december",
        "ObservationCount": 392599,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86065NED",
        "displaytitle": "Bewoonde woningen; kenmerken woning en huishouden, regio, 31 december",
        "ObservationCount": 2500086,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86070NED",
        "displaytitle": "Bewoonde woonruimten; type woonruimte en huishouden, regio, 31 december",
        "ObservationCount": 61308,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86079NED",
        "displaytitle": "Woningvoorraad; kenmerken woning en bewoning op 31 december, regio",
        "ObservationCount": 2161259,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86088NED",
        "displaytitle": "Arbeidsdeelname; regionale indeling 2024",
        "ObservationCount": 751926,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86089NED",
        "displaytitle": "Arbeidsdeelname; wijken en buurten, 2023",
        "ObservationCount": 2142056,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86098NED",
        "displaytitle": "Levensloop van woningen en niet-woningen; gebruiksfunctie, regio",
        "ObservationCount": 26438763,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86109NED",
        "displaytitle": "Rijksmonumenten; regio (indeling 2025), 1965-2024",
        "ObservationCount": 335160,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86111NED",
        "displaytitle": "Arbeidsdeelname; binding arbeidsmarkt; regio (indeling 2024)",
        "ObservationCount": 170208,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86112NED",
        "displaytitle": "Werkzame beroepsbevolking; beroep en regio's (indeling 2024)",
        "ObservationCount": 52008,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86131NED",
        "displaytitle": "Armoede van personen; persoons- en huishoudenskenmerken, regio (2025)",
        "ObservationCount": 6531480,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86132NED",
        "displaytitle": "Armoede van kinderen; persoons- en huishoudenskenmerken, regio (2025)",
        "ObservationCount": 345710,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86137NED",
        "displaytitle": "Gezondheidsmonitor; bevolking 18 jaar of ouder, regio, 2024",
        "ObservationCount": 61187,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86153NED",
        "displaytitle": "Donorregistratie (18 jaar of ouder); regio (indeling 2025)",
        "ObservationCount": 14364,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86160NED",
        "displaytitle": "Vermogen van huishoudens; huishoudenskenmerken, regio (indeling 2025)",
        "ObservationCount": 1896215,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86161NED",
        "displaytitle": "Inkomen van huishoudens; huishoudenskenmerken, regio (indeling 2025)",
        "ObservationCount": 4088988,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86162NED",
        "displaytitle": "Inkomen van personen; persoonskenmerken, regio (indeling 2025)",
        "ObservationCount": 2884816,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86163NED",
        "displaytitle": "Zelfstandigen; inkomen, vermogen, regio (indeling 2025)",
        "ObservationCount": 29883903,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86219NED",
        "displaytitle": "Arbeidsverleden bevolking afgelopen 4 jaar; regio (indeling 2025)",
        "ObservationCount": 12196737,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86223NED",
        "displaytitle": "Arbeidsmarktsituatie jongeren (15 tot 27 jaar); regio (indeling 2025)",
        "ObservationCount": 796824,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86235NED",
        "displaytitle": "Aanbod van ecosysteemdiensten; fysiek en monetair, regio",
        "ObservationCount": 87240,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/86242NED",
        "displaytitle": "Ecosysteemomvang; ecosysteemtypen, regio",
        "ObservationCount": 4352,
    },
    {
        "url": "https://opendata.cbs.nl/ODataApi/odata/900001NED",
        "displaytitle": "Energielevering aan woningen en bedrijven; postcode 6, 2017",
        "ObservationCount": 1219456,
    },
]

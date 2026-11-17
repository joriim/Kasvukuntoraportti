"""Raportin osio «Termit ja ilmiöt»: lukijalle kirjoitetut selitykset.

Kaksi osaa:

- **ilmiöt**: miksi kartta tai käyrä näyttää siltä kuin näyttää (mitä näkyy, mistä johtuu, miten tulkita)
- **termit**: lyhenteet ja mittarit yhdellä virkkeellä

Jokaisella kohdalla on ``osiot``: raportin osiot, joissa asia esiintyy. Raporttiin tulevat vain ne
kohdat, joiden osio on mukana (esim. hiilivuotermit vain, jos hiilivuot on laskettu). Täysi
lyhenneluettelo kehittäjälle on ``docs/lyhenteet.md``.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

# "n2o" on tulevaa N2O-riski-indeksiä varten; sen termit näkyvät vasta, kun osio on raportissa.
OSIOT = ("aina", "vaihtelu", "kausi", "planet", "vuo", "maapera", "vertailu", "talvi", "n2o")


@dataclass(frozen=True)
class Termi:
    tunnus: str
    nimi: str
    selitys: str
    ryhma: str
    osiot: tuple[str, ...] = ("aina",)
    pitka: str = ""  # lyhenteen aukikirjoitus
    haku: tuple[str, ...] = field(default=())  # tekstimuodot, jotka linkitetään; oletus: nimi


@dataclass(frozen=True)
class Ilmio:
    tunnus: str
    otsikko: str
    nakyy: str
    johtuu: str
    tulkinta: str
    osiot: tuple[str, ...] = ("aina",)


RYHMAT = (
    "Kasvuston mittarit",
    "Vaihtelu lohkon sisällä",
    "Vertailu ja indeksit",
    "Maaperä ja maasto",
    "Hiilivuot ja säteily",
    "Talvi",
    "Typpioksiduuli",
    "Aineistot",
)

TERMIT: tuple[Termi, ...] = (
    # --- Kasvuston mittarit ---
    Termi(
        "ndvi",
        "NDVI",
        "Kasvuston vihreyden mittari asteikolla 0–1. Lasketaan punaisen ja lähi-infrapunan heijastuksesta: "
        "paljas maa on noin 0,1–0,2 ja tiheä, terve kasvusto 0,8–0,9.",
        "Kasvuston mittarit",
        pitka="normalisoitu kasvillisuusindeksi",
    ),
    Termi(
        "ndre",
        "NDRE",
        "Kuten NDVI, mutta käyttää punaisen reunan aallonpituutta. Erottelee eroja vielä tiheässä "
        "kasvustossa, jossa NDVI ei enää nouse, ja kertoo lehtivihreän ja typen tilasta.",
        "Kasvuston mittarit",
        ("vaihtelu",),
        pitka="normalisoitu punaisen reunan indeksi",
    ),
    Termi(
        "kasvipeittavyys",
        "Kasvipeittävyys",
        "Arvio siitä, kuinka suuren osan maan pinnasta vihreä kasvusto peittää (0–100 %). "
        "Johdetaan NDVI:stä.",
        "Kasvuston mittarit",
        ("talvi",),
        haku=("kasvipeittävyys", "Kasvipeittävyys"),
    ),
    Termi(
        "ndvi-integraali",
        "NDVI-integraali",
        "NDVI-käyrän alle jäävä pinta-ala touko–elokuussa. Kuvaa koko kauden kasvua yhdellä luvulla: "
        "mitä aikaisemmin ja pidempään lohko on vihreä, sitä suurempi luku.",
        "Kasvuston mittarit",
        ("vertailu",),
    ),
    Termi(
        "peltotyo-luottamus",
        "Luottamus",
        "Peltotyön tunnistuksen varmuus asteikolla 0–1. Yli 0,6 on todennäköinen tapahtuma; sitä "
        "pienemmät ovat mahdollisia ja näkyvät kuvaajassa vaaleampina.",
        "Kasvuston mittarit",
        ("kausi",),
        haku=("luottamus", "Luottamus"),
    ),
    Termi(
        "alustava",
        "Alustava",
        "Sääntö tai luokkaraja, jota ei ole vielä kalibroitu suomalaisella maastoaineistolla. "
        "Tulos on suuntaa antava.",
        "Kasvuston mittarit",
        haku=("alustava", "Alustava"),
    ),
    # --- Vaihtelu ---
    Termi(
        "suhteellinen-kasvu",
        "Suhteellinen kasvu",
        "Solun arvo prosentteina lohkon saman päivän mediaanista. 100 = lohkon keskitaso, 90 = kymmenen "
        "prosenttia heikompi. Kertoo vaihtelun lohkon sisällä, ei satotasoa.",
        "Vaihtelu lohkon sisällä",
        ("vaihtelu",),
        haku=("Suhteellinen kasvu", "suhteellinen kasvu", "Suhteellinen NDVI"),
    ),
    Termi(
        "mediaani",
        "Mediaani, P10 ja P90",
        "Mediaani on keskimmäinen arvo: puolet soluista on sen alla ja puolet yllä. P10 on raja, jonka "
        "alle jää 10 % soluista, ja P90 raja, jonka alle jää 90 %. Väli P10–P90 kattaa siis lohkon "
        "tavallisen vaihtelun ilman ääripäitä.",
        "Vaihtelu lohkon sisällä",
        haku=("mediaani", "Mediaani", "P10–P90", "P90–P10", "P95"),
    ),
    Termi(
        "cv",
        "Variaatiokerroin (CV)",
        "Hajonta suhteessa keskiarvoon prosentteina. Mitä pienempi, sitä tasaisempi kasvusto: "
        "alle 3 % on tasainen.",
        "Vaihtelu lohkon sisällä",
        ("vaihtelu", "vertailu"),
        haku=("Variaatiokerroin", "variaatiokerroin", "CV"),
    ),
    Termi(
        "heikko-alue",
        "Heikko alue",
        "Osuus lohkon alasta, jolla kasvu jää alle 90 prosenttiin lohkon mediaanista.",
        "Vaihtelu lohkon sisällä",
        ("vaihtelu",),
        haku=("Heikko alue",),
    ),
    Termi(
        "pysyvyysluokka",
        "Pysyvyysluokka",
        "Solun luokka usean kuvauspäivän perusteella: vakaasti heikko, keskimääräinen, vakaasti hyvä tai "
        "epävakaa (hyvä yhtenä päivänä, heikko toisena).",
        "Vaihtelu lohkon sisällä",
        ("vaihtelu",),
        haku=("Pysyvyysluokka", "Pysyvyys"),
    ),
    Termi(
        "moran",
        "Moranin I",
        "Laikuittaisuuden mitta. Lähellä 1: heikot ja hyvät kohdat ovat yhtenäisinä alueina, joihin "
        "toimenpiteet voi kohdentaa. Lähellä 0: vaihtelu on satunnaista pilkkua.",
        "Vaihtelu lohkon sisällä",
        ("vaihtelu",),
        haku=("Moranin I",),
    ),
    Termi(
        "erotuskyky",
        "Erotuskyky",
        "Satelliittikuvan yhden pikselin koko maastossa. 10 m tarkoittaa, että pienin erottuva kohde on "
        "noin aarin kokoinen; kapeat ojanvarret ja ajourat sekoittuvat ympäristöönsä.",
        "Vaihtelu lohkon sisällä",
        haku=("erotuskyky", "Erotuskyky"),
    ),
    # --- Vertailu ---
    Termi(
        "vertailulohko",
        "Vertailulohko",
        "Lähialueen lohko, jolla on samana vuonna sama kasviryhmä ja mahdollisimman samanlainen maalaji, "
        "koko ja märkyys. Vertailu samana vuonna vakioi sään vaikutuksen.",
        "Vertailu ja indeksit",
        ("vertailu",),
        haku=("Vertailulohkoja", "vertailulohkoja", "Vertailulohkot", "vertailulohkot"),
    ),
    Termi(
        "kasvukuntoindeksi",
        "Kasvukuntoindeksi",
        "Lohkon sijoitus vertailulohkojen joukossa kauden kasvun (NDVI-integraali) mukaan, 0–100. "
        "50 = keskitaso, 80 = parempi kuin 80 % vertailulohkoista. Ei ole satotaso.",
        "Vertailu ja indeksit",
        ("vertailu",),
        haku=("Kasvukuntoindeksi", "Kasvukuntoindeksin", "kasvukuntoindeksi"),
    ),
    Termi(
        "tasaisuusindeksi",
        "Tasaisuusindeksi",
        "Lohkon sijoitus vertailulohkojen joukossa sisäisen tasaisuuden mukaan, 0–100. "
        "Suuri luku = kasvusto on tasaisempi kuin useimmilla vertailulohkoilla.",
        "Vertailu ja indeksit",
        ("vertailu",),
        haku=("Tasaisuusindeksi", "tasaisuusindeksi"),
    ),
    Termi(
        "hoitoindeksi",
        "Hoitoindeksi",
        "Kasvukuntoindeksi, kun märkien alueiden osuus on vakioitu. Kertoo, miten lohko kasvaa "
        "olosuhteisiinsa nähden: märkää lohkoa ei rangaista märkyydestä.",
        "Vertailu ja indeksit",
        ("vertailu",),
        haku=("Hoitoindeksi", "hoitoindeksi"),
    ),
    Termi(
        "persentiili",
        "Persentiili",
        "Sijoitus sadasosina: persentiili 70 tarkoittaa, että 70 % joukosta jää alle.",
        "Vertailu ja indeksit",
        ("vertailu",),
        haku=("persentiilejä", "persentiili", "Persentiili"),
    ),
    Termi(
        "tasapaino",
        "Vertailulohkojen tasapaino",
        "Tarkistus siitä, kuinka samanlaisia vertailulohkot ovat kohteen kanssa. Jos standardoitu ero "
        "on jossakin ominaisuudessa yli 1, indeksi on vain suuntaa antava.",
        "Vertailu ja indeksit",
        ("vertailu",),
        haku=("tasapaino",),
    ),
    # --- Maaperä ja maasto ---
    Termi(
        "dtw",
        "DTW",
        "Laskennallinen korkeusero lähimpään veden kerääntymiskohtaan metreinä (Luke). Alle 0,5 m = "
        "todennäköisesti märkä kohta. 1 ha ja 4 ha kertovat, kuinka suuri valuma-alue uoman "
        "syntymiseen vaaditaan: 1 ha kuvaa märkää kautta, 4 ha kuivempaa.",
        "Maaperä ja maasto",
        ("maapera", "vertailu"),
        pitka="depth-to-water, märkyysindeksi",
    ),
    Termi(
        "twi",
        "TWI",
        "Kuvaa, kuinka paljon vettä maaston muoto ohjaa kohtaan ja kuinka hitaasti se poistuu. "
        "Suuri arvo = vettä kertyvä kohta.",
        "Maaperä ja maasto",
        ("maapera",),
        pitka="topografinen kosteusindeksi",
    ),
    Termi(
        "tpi",
        "TPI",
        "Kohdan korkeus suhteessa ympäristöönsä. Negatiivinen = painanne, positiivinen = kumpare.",
        "Maaperä ja maasto",
        ("maapera",),
        pitka="topografinen sijainti-indeksi",
    ),
    Termi(
        "rinnevarjostus",
        "Rinnevarjostus",
        "Korkeusmallista laskettu varjokuva, josta maaston muodot, ojat ja painanteet erottuvat.",
        "Maaperä ja maasto",
        ("maapera",),
        haku=("Rinnevarjostus",),
    ),
    Termi(
        "hasu",
        "Happamat sulfaattimaat",
        "Rannikon vanhaa merenpohjaa, jonka sulfidit hapettuvat kuivatuksen jälkeen ja happamoittavat "
        "maata ja valumavesiä. GTK:n kartta antaa esiintymisen todennäköisyyden.",
        "Maaperä ja maasto",
        ("maapera",),
        pitka="HASU",
        haku=("Happamat sulfaattimaat",),
    ),
    Termi(
        "eroosioherkkyys",
        "Eroosioherkkyys",
        "Arvio siitä, kuinka herkästi pintamaa lähtee veden mukana; kasvaa rinteen pituuden ja "
        "jyrkkyyden myötä.",
        "Maaperä ja maasto",
        ("maapera",),
        haku=("Eroosioherkkyys",),
    ),
    # --- Hiilivuot ---
    Termi(
        "par",
        "PAR ja IPAR",
        "PAR on auringon säteilyn osa, jota kasvit käyttävät yhteyttämiseen. IPAR on se osa PAR:sta, "
        "jonka kasvusto sieppaa; loppu osuu maahan.",
        "Hiilivuot ja säteily",
        ("vuo",),
        pitka="fotosynteettisesti aktiivinen säteily",
        haku=("PAR", "IPAR"),
    ),
    Termi(
        "gpp",
        "GPP",
        "Bruttosidonta: hiili, jonka kasvusto sitoo ilmasta yhteyttämällä. Yksikkö g C/m².",
        "Hiilivuot ja säteily",
        ("vuo",),
        pitka="bruttoperustuotanto",
    ),
    Termi(
        "npp",
        "NPP",
        "Kasvien nettotuotanto: sidonnasta jäljelle jäävä osa, kun kasvin oma hengitys on vähennetty. "
        "Noin puolet GPP:stä.",
        "Hiilivuot ja säteily",
        ("vuo",),
        pitka="nettoperustuotanto",
    ),
    Termi(
        "reco",
        "Reco",
        "Ekosysteemin hengitys: hiili, joka palaa ilmaan kasvien ja maaperän eliöiden hengityksessä.",
        "Hiilivuot ja säteily",
        ("vuo",),
        pitka="ekosysteemin kokonaishengitys",
    ),
    Termi(
        "nee",
        "NEE",
        "Nettovaihto = hengitys − sidonta. Negatiivinen luku tarkoittaa, että pelto sitoi kaudella "
        "enemmän hiiltä kuin vapautti. Ei sisällä sadon mukana poistuvaa hiiltä eikä talvea.",
        "Hiilivuot ja säteily",
        ("vuo",),
        pitka="ekosysteemin nettohiilivaihto",
    ),
    Termi(
        "rue",
        "RUE",
        "Säteilyn käytön tehokkuus: kuinka monta grammaa kuiva-ainesatoa syntyi siepattua säteilyä "
        "kohden. Lasketaan vain, jos sato on annettu.",
        "Hiilivuot ja säteily",
        ("vuo",),
        pitka="radiation use efficiency",
    ),
    Termi(
        "gcm2",
        "g C/m²",
        "Grammaa hiiltä neliömetrillä. 100 g C/m² = 1 t hiiltä hehtaarilla ≈ 3,67 t CO₂/ha.",
        "Hiilivuot ja säteily",
        ("vuo",),
    ),
    # --- Talvi ---
    Termi(
        "viherpeite",
        "Viherpeite",
        "Talviaikainen kasvipeite. Arvio kertoo, oliko lohko kasvin tai sängen peitossa säilytysjaksolla "
        "31.10.–31.3. niinä päivinä, joina maa näkyi.",
        "Talvi",
        ("talvi",),
        haku=("Viherpeite", "viherpeite"),
    ),
    Termi(
        "talvehtiminen",
        "Talvehtiminen",
        "Syyskylvöisen kasvin tai nurmen selviäminen talvesta. Arvioidaan vertaamalla kevään "
        "vihertymistä syksyn kasvustoon: hyvä, kohtalainen, heikko tai tuhoutunut.",
        "Talvi",
        ("talvi",),
        haku=("Talvehtiminen",),
    ),
    Termi(
        "pakkassumma",
        "Pakkassumma",
        "Talven pakkasvuorokausien keskilämpötilojen summa (°Cvrk). Mitä suurempi, sitä ankarampi talvi.",
        "Talvi",
        ("talvi",),
        haku=("pakkassumma", "Pakkassumma"),
    ),
    # --- Aineistot ---
    Termi(
        "sentinel-2",
        "Sentinel-2",
        "EU:n Copernicus-ohjelman optinen satelliittipari. Kuvaa saman kohdan 2–5 päivän välein "
        "10–20 metrin erotuskyvyllä. Ei näe pilvien läpi.",
        "Aineistot",
        haku=("Sentinel-2",),
    ),
    Termi(
        "hls",
        "HLS",
        "NASAn aineisto, jossa Sentinel-2:n ja Landsatin kuvat on yhdenmukaistettu samaksi 30 metrin "
        "aikasarjaksi. Antaa enemmän kuvauspäiviä, mutta karkeamman kuvan.",
        "Aineistot",
        pitka="Harmonized Landsat Sentinel-2",
    ),
    Termi(
        "sentinel-1",
        "Sentinel-1",
        "Tutkasatelliitti, joka näkee pilvien läpi ja pimeällä. Reagoi kasvuston rakenteeseen ja "
        "kosteuteen; käytetään peltotöiden ajoituksen tukena.",
        "Aineistot",
        ("kausi",),
        haku=("Sentinel-1",),
    ),
    Termi(
        "planetscope",
        "PlanetScope",
        "Kaupallinen satelliittiparvi, joka kuvaa lähes päivittäin 3 metrin erotuskyvyllä. "
        "Käytetään tarkentamaan peltotöiden ajoitusta ja kapeiden lohkojen vaihtelua.",
        "Aineistot",
        ("planet",),
        haku=("PlanetScope",),
    ),
    Termi(
        "era5",
        "ERA5-Land",
        "Euroopan sääennustekeskuksen säähistoria-aineisto (9 km ruutu): säteily, lämpötila, sade ja "
        "haihdunta lohkon kohdalta.",
        "Aineistot",
        ("vuo",),
    ),
    # --- Typpioksiduuli (tuleva N2O-riski-indeksi) ---
    Termi(
        "n2o",
        "N2O",
        "Typpioksiduuli eli dityppioksidi, voimakas kasvihuonekaasu. Pellolla sitä syntyy, kun maan "
        "mikrobit muuttavat typpeä, eniten märässä, lämpimässä ja typpipitoisessa maassa.",
        "Typpioksiduuli",
        ("n2o",),
        pitka="typpioksiduuli",
        haku=("N2O", "N₂O"),
    ),
    Termi(
        "hot-spot",
        "Hot spot",
        "Pieni alue, jolta päästöt ovat muuhun lohkoon nähden suhteettoman suuret, "
        "esimerkiksi märkä painanne.",
        "Typpioksiduuli",
        ("n2o",),
        haku=("hot spot", "Hot spot"),
    ),
    Termi(
        "hot-moment",
        "Hot moment",
        "Lyhyt jakso, jolloin päästöt ovat suhteettoman suuret, esimerkiksi roudan sulamisen, rankkasateen "
        "tai lannoituksen jälkeen.",
        "Typpioksiduuli",
        ("n2o",),
        haku=("hot moment", "Hot moment"),
    ),
    Termi(
        "n2o-riski",
        "N2O-riski-indeksi",
        "Arvio 0–1 siitä, missä ja milloin päästöjen riski on suuri. Yhdistää hot spot -alueet ja hot moment "
        "-jaksot. Riski, ei mitattu päästö. Väri on aina vaaleanpunainen.",
        "Typpioksiduuli",
        ("n2o",),
        haku=("N2O-riski-indeksi", "riski-indeksi"),
    ),
)

ILMIOT: tuple[Ilmio, ...] = (
    Ilmio(
        "pilvet",
        "Pilvet, varjot ja usva",
        "Aikasarjassa on aukkoja, tai yksittäinen piste notkahtaa ja palaa seuraavassa kuvassa ennalleen.",
        "Optinen satelliitti ei näe pilven läpi. Pilviset kuvat hylätään, mutta ohut usva tai pilven "
        "varjo voi jäädä huomaamatta ja painaa NDVI:tä hetkellisesti.",
        "Yksittäinen kuoppa ei ole muutos kasvustossa. Raportti käyttää vain päiviä, joina lohkosta "
        "näkyi vähintään 80 %, ja peltotyö hyväksytään vasta, kun muutos pysyy seuraavassakin kuvassa.",
    ),
    Ilmio(
        "kyllastyminen",
        "NDVI ei enää nouse tiheässä kasvustossa",
        "Keskikesällä NDVI-käyrä tasaantuu 0,85–0,9:n tuntumaan ja kartta näyttää tasaiselta, vaikka "
        "kasvustossa olisi silmin nähtäviä eroja.",
        "Kun lehtiala on suuri, lisälehdet eivät enää muuta punaisen valon heijastusta. NDVI kyllästyy.",
        "Katso tiheän kasvuston eroja NDRE-kartasta, joka erottelee pidemmälle. Alkukesän ja "
        "loppukauden kartat näyttävät vaihtelun selvimmin.",
        ("vaihtelu",),
    ),
    Ilmio(
        "reunat",
        "Reunat ja sekapikselit",
        "Lohkon reunoilla, ojien varsilla ja saarekkeiden ympärillä näkyy heikompi kaistale.",
        "10–30 metrin pikseli ulottuu reunalla osin pientareelle, ojaan tai metsän varjoon. Osa "
        "heikkoudesta on todellista (varjostus, tiivistymä päisteessä), osa pelkkää sekoittumista.",
        "Laskennassa lohkoa kutistetaan reunoilta, jotta sekapikselit jäävät pois. Kapealla lohkolla "
        "soluja jää vähän ja tunnusluvut ovat epävarmempia; 3 metrin PlanetScope-kuva erottaa reunat.",
        ("vaihtelu",),
    ),
    Ilmio(
        "pysyva-vaihtelu",
        "Pysyvä ja satunnainen vaihtelu",
        "Sama kohta on heikko kuvasta ja vuodesta toiseen, tai kohta on välillä hyvä ja välillä heikko.",
        "Pysyvästi heikko kohta viittaa kasvupaikkaan: märkyyteen, tiivistymään, happamuuteen tai "
        "maalajin vaihtumiseen. Epävakaa kohta reagoi säähän: kuivana kesänä kärsii kumpare, märkänä "
        "painanne.",
        "Vakaasti heikot, yhtenäiset alueet ovat ensimmäinen paikka maanäytteelle, ojituksen "
        "tarkistukselle tai kalkitukselle. Satunnaiseen pilkkuun toimenpiteitä ei kannata kohdentaa.",
        ("vaihtelu",),
    ),
    Ilmio(
        "niitto",
        "Niitto ja jälkikasvu",
        "Nurmen NDVI putoaa jyrkästi muutamassa päivässä ja palaa 2–4 viikossa lähelle lähtötasoa.",
        "Niitto poistaa vihreän lehtimassan, ja sänki ja karhot heijastavat kuin paljas maa. "
        "Jälkikasvu vihertää lohkon uudelleen.",
        "Putoamisen ja palautumisen väli kertoo niiton ajankohdan. Jos selkeiden kuvien väli on yli "
        "kaksi viikkoa, niitto voi jäädä kokonaan näkemättä, koska nurmi ehtii vihertyä.",
        ("kausi",),
    ),
    Ilmio(
        "tuleentuminen",
        "Tuleentuminen ei ole heikkoa kasvua",
        "Viljan ja öljykasvien NDVI laskee tasaisesti heinä–elokuussa viikkojen ajan ennen puintia.",
        "Kasvusto kellastuu kypsyessään, kun lehtivihreä hajoaa. Lasku on hidas, toisin kuin niitossa "
        "tai puinnissa.",
        "Hidas lasku kuuluu kasvin kehitykseen. Aikaisemmin tuleentuvat laikut voivat silti kertoa "
        "kuivuudesta tai kevyemmästä maasta, ja ne erottuvat loppukauden kartoissa.",
        ("kausi",),
    ),
    Ilmio(
        "sensorierot",
        "Eri satelliittien käyrät kulkevat hieman eri tasolla",
        "HLS:n, Sentinel-2:n ja PlanetScopen pisteet eivät osu täsmälleen samalle käyrälle.",
        "Satelliittien kaistat, pikselikoko ja pilvimaskit eroavat. 30 metrin pikseliin mahtuu "
        "enemmän reunaa kuin 10 tai 3 metrin pikseliin.",
        "Vertaa muutoksia saman lähteen sisällä. Peltotyöt tunnistetaan lähteittäin erikseen, ja usean "
        "lähteen yhtäaikainen havainto nostaa luottamusta.",
        ("kausi",),
    ),
    Ilmio(
        "tutka",
        "Tutka reagoi kosteuteen",
        "Sentinel-1:n signaali heilahtaa sateen jälkeen, vaikka kasvusto ei muuttunut.",
        "Tutkan takaisinsironta riippuu kasvuston rakenteen lisäksi maan ja lehtien kosteudesta.",
        "Tutka yksin ei riitä peltotyön toteamiseen. Se tukee optista havaintoa ja tarkentaa "
        "ajoitusta pilvisinä jaksoina.",
        ("kausi",),
    ),
    Ilmio(
        "markyys-kuivuus",
        "Märkyys ja kuivuus näkyvät eri paikoissa",
        "Heikot kohdat osuvat painanteisiin ja ojien latvoille, tai päinvastoin kumpareille ja "
        "karkeille maille.",
        "Painanteissa vesi seisoo ja juuristo kärsii hapenpuutteesta; kylvö myöhästyy ja maa tiivistyy. "
        "Kuivana kautena taas kärsivät kohdat, joissa maa pidättää vähiten vettä.",
        "Vertaa vaihtelukarttaa märkyys- ja korkeuskarttoihin. Yhteys ei todista syytä, mutta kertoo, "
        "mistä maastokäynti kannattaa aloittaa: salaojien toiminta, pintavesien poisto, maan rakenne.",
        ("maapera",),
    ),
    Ilmio(
        "saa-ja-vertailu",
        "Hyvä ja huono vuosi",
        "Lohkon NDVI on jonakin vuonna selvästi matalampi, mutta kasvukuntoindeksi ei juuri muutu.",
        "Sää vaikuttaa koko alueen lohkoihin samalla tavalla. Indeksi vertaa lohkoa saman vuoden "
        "vertailulohkoihin, joten yhteinen sään vaikutus kumoutuu.",
        "Indeksin muutos vuodesta toiseen kertoo lohkon omasta kehityksestä suhteessa muihin. "
        "Yhden vuoden luku on altis sattumalle; katso useamman vuoden vaihteluväliä.",
        ("vertailu",),
    ),
    Ilmio(
        "hiili",
        "Sidonta, hengitys ja niiden erotus",
        "Kesällä sidonta (GPP) on suurempi kuin hengitys (Reco), keväällä ja syksyllä päinvastoin.",
        "Kasvusto sitoo hiiltä vain yhteyttäessään, mutta maaperä ja kasvit hengittävät koko ajan, "
        "sitä enemmän mitä lämpimämpi maa on.",
        "Kauden nettovaihto on kahden suuren luvun pieni erotus ja siksi epävarma (asemilla virhe "
        "jopa ±400 g C/m²). Se ei ole pellon vuoden hiilitase: sadon mukana poistuva hiili ja talven "
        "hengitys puuttuvat.",
        ("vuo",),
    ),
    Ilmio(
        "lumi",
        "Talvella on vähän havaintoja",
        "Marras–maaliskuulta on vain muutama kuva tai ei yhtään.",
        "Lumi peittää kasvuston, aurinko on matalalla ja pilvisyys on runsasta. Lumiset ja hämärät "
        "kuvat hylätään.",
        "Viherpeitteen arvio kertoo, mikä osa jaksosta oli havaittavissa. Lumen tulo ja lähtö "
        "rajaavat jakson, jolta tietoa ei voi olla.",
        ("talvi",),
    ),
    Ilmio(
        "talvituho",
        "Talvituhot",
        "Keväällä osa lohkosta ei verty, vaikka syksyllä kasvusto oli tasainen.",
        "Jääpolte syntyy, kun vesi jäätyy painanteeseen ja kasvusto tukehtuu jään alle. Lumihome "
        "viihtyy paksun lumen alla roudattomassa maassa. Pakkanen vioittaa kasvustoa, jos lunta ei ole "
        "suojana.",
        "Tuhokartta näyttää kohdat, joissa vihreää ei keväällä ollut. Painanteisiin osuva tuho viittaa "
        "jääpoltteeseen ja pintavesien poiston tarpeeseen. Myöhäinen kevät voi näyttää tuholta, joten "
        "arvio tarkentuu toukokuun kuvilla.",
        ("talvi",),
    ),
)


def valitse(osiot) -> tuple[list[Termi], list[Ilmio]]:
    """Kohdat, joiden jokin osio on raportissa (``aina`` on mukana aina)."""
    o = set(osiot) | {"aina"}
    return [t for t in TERMIT if o & set(t.osiot)], [i for i in ILMIOT if o & set(i.osiot)]


class Linkittaja:
    """Linkittää tekstissä esiintyvät termit sanastoon. Sama termi linkitetään kerran osiota kohden."""

    def __init__(self, termit: list[Termi]):
        self._kohteet = {}
        for t in termit:
            for h in t.haku or (t.nimi,):
                self._kohteet[h] = t
        sanat = sorted(self._kohteet, key=len, reverse=True)
        self._re = (
            re.compile(
                r"(?<![\wäöåÄÖÅ])(" + "|".join(re.escape(html.escape(s)) for s in sanat) + r")(?![\wäöå])"
            )
            if sanat
            else None
        )
        self._tehty: set[str] = set()

    def uusi_osio(self) -> None:
        self._tehty = set()

    def __call__(self, teksti: str) -> str:
        """``teksti`` on jo HTML-suojattua tekstiä ilman tageja."""
        if self._re is None:
            return teksti

        def korvaa(m):
            t = self._kohteet[html.unescape(m.group(1))]
            if t.tunnus in self._tehty:
                return m.group(1)
            self._tehty.add(t.tunnus)
            return f'<a class="termi" href="#t-{t.tunnus}">{m.group(1)}</a>'

        return self._re.sub(korvaa, teksti)


def osiot_html(termit: list[Termi], ilmiot: list[Ilmio]) -> tuple[str, str]:
    """(ilmiösivun HTML, termisivun HTML)."""
    e = html.escape
    o = []
    if ilmiot:
        o.append(
            "<p class='selite'>Jokaisesta ilmiöstä kolme asiaa: mitä näkyy, mistä se johtuu ja miten se "
            "luetaan.</p><div class='ilmiot'>"
        )
        for i in ilmiot:
            o.append(
                f"<article class='ilmio' id='i-{i.tunnus}'><h4>{e(i.otsikko)}</h4><dl>"
                f"<dt>Mitä näkyy</dt><dd>{e(i.nakyy)}</dd>"
                f"<dt>Mistä johtuu</dt><dd>{e(i.johtuu)}</dd>"
                f"<dt>Miten tulkita</dt><dd>{e(i.tulkinta)}</dd></dl></article>"
            )
        o.append("</div>")
    t_html = [
        "<p class='selite'>Raportissa esiintyvät termit. Katkoviivalla alleviivattu sana raportissa tuo "
        "tänne.</p>"
    ]
    for ryhma in RYHMAT:
        rt = [t for t in termit if t.ryhma == ryhma]
        if not rt:
            continue
        t_html.append(f"<h3 class='ryhma'>{e(ryhma)}</h3><dl class='sanasto'>")
        for t in rt:
            pitka = f" <span>· {e(t.pitka)}</span>" if t.pitka else ""
            t_html.append(f"<div id='t-{t.tunnus}'><dt>{e(t.nimi)}{pitka}</dt><dd>{e(t.selitys)}</dd></div>")
        t_html.append("</dl>")
    return "".join(o), "".join(t_html)

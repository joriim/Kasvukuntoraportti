# Satotaso, satovaje ja maahan päätyvä hiili lohkon sisällä

Suunnitelma ja toteutuksen tila. Moduuli `src/kasvukunto/sato.py`, raportin osio `raportti._sato_osio`
(sisältösivu "Satotaso ja satovaje lohkon sisällä"), testit `tests/test_sato.py`.

## Lähtötieto: satokartta

Satokartta on 10 m ruudukossa, samassa kuin analyysi (`solukko`, EPSG:3067). Ruudulla on sato t/ha
korjuukosteudessa, lähde ja koko kartalle kosteus.

| Lähde | Koodi | Esitys |
|---|---|---|
| mitattu | 1 | täysi väri |
| kuvamallista | 2 | läpikuultava |
| naapureista | 3 | rengas |
| puimatta | 4 | ei satoa; GPP-pylväs jää seisomaan |
| ei tietoa | 0 | piste |

Satokartan voi tuoda kahdella tavalla:

- **Beanstalk Growth Space -puintinäkymä** (`sato.katselimesta(data)`). Datan avain `sato` sisältää
  arvot (`arvo`, uint16 × `skaala`), lähteet (`lahde`), varmimman ruutukoon ryhmät (`varma`: koko_m,
  toistuvuus, epävarmuus) ja puimurin ajon (`ajot[ajo]`: kello, pöytä, kaista, kosteus). Esimerkkinä on
  lohkon 1641431471 puinti 28.8.2026: 1 923 ruutua, mitattu 89 %, naapureista 10 %, kuvamallista 0,4 %.
  Sato on keskimäärin 11,5 t/ha kosteudessa 13,3 % (kuivana 10,0 t/ha), CV 15,6 %. Varmin ruutukoko on
  40 m, toistuvuus 0,81 ja ruudun epävarmuus ±0,79 t/ha.
- **Satokartoituksen tietueet** (`sato.ruudukkoon(x, y, sato, transform, shape, vuosi, kosteus)`).
  Ruudun arvo on pisteiden mediaani, ja ruutu tarvitsee vähintään 3 pistettä. Täydennys (kuvamalli,
  naapurit) on erillinen vaihe Yield-Data-Suitessa.

## Raportoitavat suureet

| Suure | Laskenta | Tila |
|---|---|---|
| Satotaso | keskiarvo, mediaani, P10–P90, CV, osuus alle 90 % mediaanista, kuiva-aine kosteudesta | toteutettu |
| Suhteellinen sato | sato / lohkon mediaani × 100 | toteutettu |
| Vaje lohkon parhaisiin | lohkon P90 − ruutu, ≥ 0 | toteutettu |
| Vaje ruudun omaan maksimiin | ruudun paras suhteellinen sato vuosilta × tämän vuoden mediaani − ruutu | toteutettu; vaatii ≥ 3 satokarttavuotta, muuten varaus |
| Vaje samankaltaisiin ruutuihin | samankaltaisuusryhmän P90 mitatuista ruuduista − ruutu | toteutettu; vaatii maaston ja märkyyden samassa ruudukossa |
| Vajeen jako: vesitalous ja muu | vesitalous = lohkon P90 − märkyysluokan P90; muu = märkyysluokan P90 − ruutu | toteutettu |
| Maahan päätynyt hiili sadosta | sänki + juuret + juurieritteet (`maahiili.jako_sadosta`) kuiva-ainesadosta | toteutettu, mutta raportissa varaus: kasvikohtaiset kertoimet puuttuvat |
| Salaojitus | etäisyys salaojaan ja ojitusluokka ryhmittelyyn | varaus (`Salaojakartta`, `salaoja_rasteri`) |

### Miksi kolme viitettä

- **Lohkon P90** vastaa kysymykseen, paljonko lohko jää omista parhaista kohdistaan samana vuonna.
  Se on helppo ymmärtää, mutta se rankaisee kohtia, jotka eivät voi koskaan yltää parhaisiin
  (esimerkiksi märkä painanne).
- **Ruudun oma maksimi** vastaa kysymykseen, jääkö ruutu tänä vuonna siitä, mihin se on itse pystynyt.
  Suhteellisena (% mediaanista) se on vertailukelpoinen eri kasvien ja vuosien välillä. Yksi poikkeuksellisen
  hyvä vuosi nostaa maksimia, joten myöhemmin kannattaa käyttää toiseksi parasta tai P80:aa, kun vuosia
  on viisi tai enemmän.
- **Samankaltaiset ruudut** vastaa kysymykseen, jääkö ruutu sellaisista ruuduista, joilla on sama märkyys,
  kosteusindeksi ja korkeus (ja salaojitus, kun kartta on). Tämä erottaa korjattavan vajeen (hoito, tiivistyminen,
  rikkakasvit, kalkitus) olosuhteista johtuvasta.

## Märkyys (DTW) vajeen selittäjänä

Luken DTW (syvyys pohjaveteen, 1 ha kynnys) luokitellaan kolmeen luokkaan: märkä alle 0,5 m, kostea
0,5–1,0 m ja kuiva yli 1,0 m (`sato.DTW_LUOKAT`).

1. **Ryhmittely.** Märkyysluokka on samankaltaisuusryhmien ensimmäinen piirre, jolloin märkää ruutua
   verrataan märkiin ruutuihin.
2. **Vajeen jako.** Vaje lohkon parhaisiin = vesitalous + muu. Vesitaloudella selittyvä osa on
   ruudun märkyysluokan parhaiden ja lohkon parhaiden ruutujen ero. Kuva "Sato ja märkyys" näyttää
   jokaisen ruudun pisteenä, luokkien P90-tasot vihreinä viivoina ja lohkon P90:n katkoviivana.
3. **Suunta vaihtelee vuosittain.** Kuivana kesänä märkä luokka voi olla paras ja märkänä huonoin.
   Siksi jako tehdään vuosittain eikä vesitaloudelle anneta kiinteää kerrointa. Lohkolla 7290727639 kasvu
   oli parempi kosteissa kohdissa (DTW ρ = −0,56).
4. **Jatkokehitys** (suunnitelma): vesipotentiaali kauden säästä. DTW on staattinen maastomalli. Kauden
   sademäärä ja haihdunta (FMI, ERA5-Land ET0) siirtävät rajaa: märkänä vuonna kostea luokka käyttäytyy
   kuin märkä. Tavoitteena on vuosikohtainen tehollinen märkyys = DTW − sadetta ja haihduntaa kuvaava
   korjaus, kalibroituna monen vuoden satokartoista.

### Salaojakartan varaus

Salaojakartan rakenne on `sato.Salaojakartta`:

| Kenttä | Sisältö |
|---|---|
| `geometria` | salaojat viivoina tai ojitettu ala alueina (shapely, EPSG:3067) |
| `ominaisuudet` | asennusvuosi `vuosi`, ojaväli `vali_m` (oletus 16 m), syvyys `syvyys_m`, kunto `kunto`: toimiva, heikko tai tukossa |
| `lahde` | esimerkiksi "tilan salaojakartta 1987" |

`salaoja_rasteri` laskee jokaiselle ruudulle etäisyyden lähimpään salaojaan sekä ojitusluokan:
0 ojittamaton, 1 ojitettu (enintään puolen ojavälin päässä), 2 ojitettu mutta heikko tai tukossa.

Suunniteltu käyttö:

1. Ojitusluokka on samankaltaisuusryhmien piirre (toteutettu, kun kartta annetaan).
2. Märkyysluokan korjaus: ojitetulla alalla tehollinen DTW kasvaa noin salaojasyvyyteen asti.
   Toimimaton salaoja (luokka 2) jätetään korjaamatta, ja sen vaje raportoidaan omana rivinään:
   ojituksen kunnostustarve.
3. Kartta 3D:ssä: salaojat ohuina viivoina maan alla salaojasyvyydellä, heikot meripihkana.
4. Sisääntulot: GeoPackage tai GeoJSON (`kasvukunto analysoi --salaojat polku.gpkg`, suunniteltu
   CLI-vipu). Skannattu paperikartta digitoidaan ensin.

## Maahan päätynyt hiili

Satokartasta (kuiva-aine) lasketaan ruuduittain korjattu hiili, sänki, juuret ja juurieritteet
(`maahiili.jako_sadosta`). Oletuskertoimet ovat nurmille. Viljoille tarvitaan oma korjuuindeksi,
verso:juuri-suhde ja eriteosuus, joten ne ovat raportissa varauksena (`sato.maahan_hiili(k, kertoimet)`).

Satokartta parantaa maanalaista arviota GPP:hen verrattuna: syöte tulee mitatusta sadosta, ei GPP:n
skaalauksesta. Rajoitukset ovat samat kuin docs/3d-pylvaat.md:ssä: arvio on jälkikäteinen ja kertoimien
epävarmuus on suuri.

## Visualisointi

### Raportti (2D)

Sisältösivulla "Satotaso ja satovaje lohkon sisällä" on:

- tunnuslukukortti
- kartat: sato (t/ha), sato % mediaanista, vaje lohkon parhaisiin, vaje ruudun omaan maksimiin,
  vaje samankaltaisiin ruutuihin ja vajeesta vesitalous
- kuva "Sato ja märkyys": ruudut pisteinä, märkyysluokkien P90 ja lohkon P90
- ilman satokarttaa varauskortti, jossa kerrotaan, mitä kukin luku vaatii

Asteikot ovat Signaali-ilmeen: sato `maara` (pimeä → vihreä), suhteellinen `signaali` (meripihka →
pimeä → vihreä), vaje `vaje` (pimeä → meripihka) ja vesitalous `markyys` (syaani).

### 4D (Beanstalk Growth Space, puintinäkymä)

Puintinäkymä (design-kanvaasi "Harvest timelapse in Beanstalk Space" ja lohkon 1641431471 toteutus)
näyttää puinnin näin:

1. **Puintipäivä avautuu tunneiksi.** Puimuri ajaa kaistoittain kellon mukaan. Leikkuupöydän tila
   näkyy (alhaalla, ylhäällä, vajaa leveys, tyhjennys). Kasvupylväs kaatuu sängeksi, ja mitattu sato
   nousee noin 12 sekunnin viiveellä.
2. **Asettuminen ja paikkaus.** Raaka lukema asettuu varmimpaan ruutukokoon (40 m). Leveät aukot
   täytetään kuvamallista läpikuultavina ja kapeat naapureista renkaina. Puimatta jäänyt ala jää siniseksi.
3. **Pysäytyskuva.** Koko kauden toistossa kamera pysähtyy jokaiseen puintiin (10,5 s, 150° kierto).

Satovajeen lisäykset näkymään (suunnitelma):

- **Vaje pylvään päälle.** Satopylvään päälle tulee läpikuultava meripihkainen osa, jonka korkeus on
  vaje valittuun viitteeseen. Viitteen voi vaihtaa: lohkon P90, oma maksimi tai samankaltaiset ruudut.
  Sama periaate kuin GPP:n käyttämättömässä potentiaalissa.
- **Vesitalous erikseen.** Vesitaloudella selittyvä osa on syaani ja muu vaje meripihka. Lukija näkee,
  mikä osa vajeesta on korjattavissa hoidolla ja mikä vaatii vesitalouden korjausta.
- **Maan alla.** Sänki (puinnissa kaatuva kasvupylväs) painuu maahan. Juuret ja juurieritteet tulevat
  satokartasta, kun kasvin kertoimet ovat. Salaojat näkyvät viivoina salaojasyvyydellä.
- **Ryhmän valinta.** Ruutua napautettaessa korostuvat sen samankaltaiset ruudut, ja kortti kertoo
  ryhmän P90:n, ruudun vajeen ja märkyysluokan.
- **Varmuus.** Vaje lasketaan mitatuista ruuduista. Täydennetyt ruudut näkyvät, mutta niiden vaje on
  läpikuultava, kuten itse satokin.

## Avoimet kysymykset

1. Viljojen kertoimet (korjuuindeksi, verso:juuri-suhde, eriteosuus): suomalainen lähde tarvitaan,
   ennen kuin maanalainen hiili sadosta esitetään arviona.
2. Oman maksimin määritelmä: maksimi, toiseksi paras vai P80? Päätös, kun vuosia on vähintään viisi.
3. Samankaltaisuusryhmien piirteet: lisätäänkö maalaji (GTK 1:20 000 on harvoin riittävän tarkka) ja
   viljavuusnäytteet?
4. Puintinäkymän tuottava koodi ei ole näissä repoissa (näkymässä on `sato`-avain, jota
   `beanstalk4d`:n julkinen versio ei vielä tuota). Tuodaanko se `beanstalk4d`:hen vai analyysiin?

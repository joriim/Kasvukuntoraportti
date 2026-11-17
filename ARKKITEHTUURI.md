# Kasvukuntoraportin arkkitehtuuri

Kasvukuntoraportti on yksi itsenäinen HTML-tiedosto: interaktiivinen kirjanen (Signaali-ilme), jonka kansi
on Helle yöllä -tyylinen pistekuva ja jonka uusimman kauden hiilisivulla on upotettu Beanstalk Growth
Space -näkymä. Raportti ei laske mitään itse: analyysi tuottaa tulokset, raporttikerros esittää ne.

Raporttikerros erotetaan omaksi paketikseen repoon
[joriim/Kasvukuntoraportti](https://github.com/joriim/Kasvukuntoraportti). Siihen asti se asuu tässä repossa.

## Kerrokset

```
analyysi (kasvukunto)                 raportti (tuleva paketti kasvukuntoraportti)
───────────────────────               ─────────────────────────────────────────────
analyysi.analysoi  ── osat (dict) ──▶ raportti.kirjoita ──▶ raportti.html
  vuo.kartat (aikasarja)                kirja      sivutyypit: kansi, aukeama, sisältösivu, pavunvarsi
  maahiili.maanalainen (varaus)         ilme       värit, asteikot, fontit, CSS, JS, kuvaajien teema
  vaihtelu, vertailu, maapera, talvi    sanasto    termit ja ilmiöt
                                        kasvu3d_osio ──▶ pylvaat3d (sovitin) ──▶ beanstalk4d (katselin)
```

| Moduuli | Vastuu | Riippuu |
|---|---|---|
| `raportti.py` | sivukartta (`kirjoita`), osiot, kuvaajat (matplotlib, upotettu PNG) | `ilme`, `kirja`, `sanasto` |
| `kirja.py` | sivutyypit, pistekartat SVG:nä, sataruudukko, pino, merkit, pavunvarsi | `ilme` |
| `ilme.py` | Signaali-värit, asteikot (`signaali`, `maara`, `markyys`, `ipar`, `vaje`, `helle`, varattu `n2o-riski`), fontit, CSS, selaus-JS | – |
| `sanasto.py` | termit ja ilmiöt valitaan mukana olevien osioiden mukaan | – |
| `sato.py` | satokartta ruudukkoon, satotaso, vaje kolmeen viitteeseen, DTW-jako, salaojavaraus, maahan päätyvä hiili | `maahiili` |
| `pylvaat3d.py` | analyysin tulokset Beanstalk Growth Space -dataksi (kerrokset, vertailu, tila) | `beanstalk4d` (valinnainen) |

## Datasopimus: `osat`

`raportti.kirjoita(polku, osat)` saa kaiken sanakirjana. Avaimet:

| Avain | Sisältö |
|---|---|
| `lohko` | `tunnus`, `ala_ha`, `geometria` (shapely, EPSG:3067), `kasvi`, `leveys_m` |
| `historia` | kasvihistoria (DataFrame) |
| `vuodet` | `{vuosi: {optinen, peltotyot, kasvi, vuo, planet, yhteenveto}}` |
| `vaihtelu` | `{ndvi: Vaihtelu, ndre: Vaihtelu}` |
| `maapera` | maaperä ja maasto (`kerrokset_2m`, `transform_2m`, tunnusluvut, selittäjät) |
| `vertailu`, `vertailualue` | vertailulohkot ja indeksit; alueen korkeusmalli ja DTW 3D-näkymään |
| `talvi` | talvet (viherpeite, talvehtiminen) |
| `pilvisyys`, `koko_vuosi`, `ajot` | 3D-näkymän sää, koko vuoden tila ja koneajot (puimurin reitti `GT/puintireitti`) |
| `sato` | `{vuosi: sato.Satokartta}` analyysiruudukossa (10 m), luettu varastosta `GT/satokartta` (puinti: `maastotosi --puimuri`); ilman sitä satosivu on varaus |
| `salaojat` | `sato.Salaojakartta` (varaus); ruudut ryhmitellään ojitusluokan mukaan, kun annettu |
| `lahteet`, `huomiot` | tietolähteet ja huomiot |

### Vuon tulos (`vuodet[v]["vuo"]`)

| Kenttä | Sisältö |
|---|---|
| `paivat` | päivätaulukko: `pvm`, `par_mj`, `ipar_mj`, `gpp`, `gpp_vira_p05/p95`, `npp`, `reco`, `nee` |
| `summat` | kauden summat (GPP, IPAR, NPP, Reco, NEE, potentiaalin viite) |
| `kartat` | kauden kartat: `gpp_g_c`, `ipar_mj`, `kayttamaton_sisainen_g_c`, `kayttamaton_lohko_g_c` |
| `aikasarja` | kertymät soluittain (T, ny, nx): `gpp_g_c`, `ipar_mj`, `gpp_pot_paiva_g_c`, `gpp_pot_g_c` |
| `transform` | ruudukon affiini muunnos |

**Vaje referenssimaksimiin** = `gpp_pot_g_c − gpp_g_c`: se GPP, joka jäi saamatta, kun ruutu ei kasvanut
viitetason mukaan samassa säässä. Kaksi osaa: lohkon sisäinen (ruutu jäi lohkon saman päivän parhaista
kohdista) ja koko lohkon taso (lohkon paras taso jäi viitteestä).

### Maanalainen hiili (varaus)

`maahiili.maanalainen(paivat, gpp_kertyma, sato_kuiva_g_m2=None)` palauttaa soluittain (T, ny, nx), g C/m²:

| Kenttä | Sisältö |
|---|---|
| `syote_g_c` | maahan mennyt kertyvä syöte (juuret + juurieritteet) |
| `juuret_g_c` | juurten hajoamaton hiili |
| `eritteet_g_c` | juurieritteiden hajoamaton hiili |
| `kiintea_g_c` | humifioitunut (ICBM) |
| `palanut_g_c` | hajotessa ilmakehään palanut (ei summaan) |

Raportti näyttää nämä 3D-näkymässä maan alla ja hiilisivun varauskortissa. Ilman syötettä kerrokset ovat
varauksia (laatu `varaus`, ei arvoja). Oletuskertoimet ovat nurmille. Kevätviljoille tarvitaan oma
verso:juuri-suhde ja eriteosuus, tai satokartta.

## Sivukartta

1. Kansi (Helle yöllä: lohkon pistekuva lohkon omasta vaihteluvälistä, kultainen leijona)
2. Yhdellä silmäyksellä · 3. Pavunvarsi · 4. Lohko
5. Kasvuvaihtelu (aukeama + sisältö)
6. Kaudet uusimmasta: kausi (aukeama + sisältö), hiili (aukeama + sisältö)
7. Satotaso ja satovaje (`_sato_osio`, ks. docs/sato-ja-satovaje.md)
8. Maaperä · 9. Vertailu · 10. Talvi · 11. Ilmiöt · 12. Termit · 13. Takakansi

### Hiilisivu (kausittain)

| Osa | Lähde | Huom |
|---|---|---|
| Hiilivuot päivittäin ja kertymä | `vuo_kuva` | GPP 90 % väli, Reco, −NEE |
| Tunnusluvut | `_vuo_osio` | sis. säteilyn käytön tehokkuus kaudelta (GPP / IPAR) |
| Säteilyn käytön tehokkuus viikoittain | `rue_kuva` | viikon GPP / viikon IPAR, g C/MJ; taustalla IPAR |
| Kertymät ruuduittain | `kertyma_kuva` | rivit GPP, IPAR, vaje; sarakkeet kuukausien loput |
| Kartat | `kartta_kuva` | GPP, IPAR, vaje lohkon parhaisiin kohtiin, vaje koko lohkon viitteeseen |
| Maan alle menevä hiili (varaus) | `_vuo_osio` | juuret, juurieritteet, kiinteä, palanut |
| Beanstalk Growth Space (uusin kausi) | `kasvu3d_osio` | ks. alla |

### Beanstalk Growth Space -näkymä

Ylös: GPP-kertymä (pylväs), vaje lohkon parhaisiin kohtiin ja vaje koko lohkon viitteeseen. Alas:
juuret, juurieritteet, kiinteä ja palanut (varaus). Lohkon vieressä kertyvä lämpösumma ja sadanta vuoden
alusta (FMI:n lähin asema), maasto (MML 2 m, väri Luken DTW), vertailulohkot, aurinko, satelliittihavainnot,
pilvet ja sade, koko vuoden tila (lumi, kasviton, viherpeite) ja viirit. IPAR on eri yksikössä (MJ/m²), joten
se on raportin kartta eikä pylväskerros.

## Paketiksi erottaminen

1. Kasvukuntoraportti-repoon paketti `kasvukuntoraportti`: `raportti`, `kirja`, `ilme`, `sanasto`, fontit,
   ja `kasvu3d_osio` valinnaisena (`[nakyma3d]` → `beanstalk4d`).
2. `pylvaat3d` jää analyysiin (laskee kerrokset), tai siirtyy raporttipakettiin sovittimena; päätetään
   erotettaessa.
3. Analyysi kutsuu `kasvukuntoraportti.kirjoita(polku, osat)`; datasopimus yllä on rajapinta.
4. Testit: `test_raportti*.py` ja `raportti_esimerkki.py` siirtyvät pakettiin.

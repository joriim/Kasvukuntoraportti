"""Raportin graafinen ilme: värit, fontit, kuvaajien teema ja kirjasen tyylit yhdessä paikassa.

Signaali: raportti on viesti data-avaruudesta. Musta pohja, kannen kentät indigo, meripihka ja
petrooli (Rothko). Kartoissa keskitaso häviää pimeään: heikko hehkuu meripihkana, kasvu vihreänä.
Tuloste on paperilla. Periaatteet: ``docs/graafinen-ilme.md``.
"""

from __future__ import annotations

import base64
from contextlib import contextmanager
from functools import lru_cache
from importlib import resources

# --- Kentät ja signaalit ---
INDIGO = "#1b2a6b"
MERIPIHKA = "#f5a524"  # heikko, varoitus, Sentinel-2
PETROOLI = "#0e4a52"
SYAANI = "#2ec4d6"  # vesi, märkyys, HLS, datalähteet
VIHREA = "#3fd07a"  # kasvu: hyvä, sidonta, kasvusto
# Varattu: tulevan N2O-riski-indeksin (hot spot, hot moment) väri. Ei muuhun käyttöön.
PINKKI = "#f4a3bd"
# Helle yöllä -kannet (oma-design, luonnos 5): Toikan pinkki ja taivaansininen mustalla, kultainen merkki.
# Huom: oma-designin päätösloki varaa vaaleanpunaisen N2O-riskille; kansi käyttää eri sävyä ja vain kannessa.
HELLE_PINKKI = "#e86a92"
HELLE_TAIVAS = "#3aa7d6"
HELLE_KULTA = "#f0b429"
VIOLETTI = "#b48cff"  # epävakaa, PlanetScope
MUSTE = "#efeae0"
HILJAINEN = "#8d93a0"
AVARUUS = "#050505"
PINTA = "#0d1016"
VIIVA = "#232833"
TYHJA = "#1a1f27"  # ei tietoa, tyhjä piste
PAPERI = "#f3efe6"

# --- Ruutu (musta) ja tuloste (paperi) ---
AVARUUS_TEEMA = {
    "tausta": AVARUUS,
    "pinta": PINTA,
    "pinta2": "#141821",
    "muste": MUSTE,
    "hiljainen": HILJAINEN,
    "viiva": VIIVA,
    "korostus": MUSTE,
    "korostus-pehmea": "#141a33",
    "varoitus": MERIPIHKA,
    "varoitus-pehmea": "#231a08",
    "linkki": SYAANI,
}
PAPERI_TEEMA = {
    "tausta": "#ffffff",
    "pinta": "#ffffff",
    "pinta2": "#f1efe9",
    "muste": "#111111",
    "hiljainen": "#5b5f68",
    "viiva": "#d6d3cb",
    "korostus": "#111111",
    "korostus-pehmea": "#eef0f7",
    "varoitus": "#8a5a00",
    "varoitus-pehmea": "#fbf1dc",
    "linkki": "#111111",
}
# Kuvaajat piirretään avaruuteen; nämä nimet säilyvät vanhoille kutsuille.
VAALEA = {"muste": MUSTE, "hiljainen": HILJAINEN, "korostus": MUSTE}

# --- Kuvaajien värit. Tarkistettu värinäön poikkeamille (ΔE ≥ 8 kaikilla pareilla). ---
LAHDEVARIT = {
    "hls2-s30": SYAANI,
    "hls2-l30": SYAANI,
    "sentinel-2-l2a": MERIPIHKA,
    "planetscope": VIOLETTI,
}
LAHDEMERKIT = {"hls2-s30": "o", "hls2-l30": "s", "sentinel-2-l2a": "o", "planetscope": "D"}
LAHDENIMET = {
    "hls2-s30": "HLS (Sentinel-2), 30 m",
    "hls2-l30": "HLS (Landsat), 30 m",
    "sentinel-2-l2a": "Sentinel-2, 10 m",
    "planetscope": "PlanetScope, 3 m",
}
TAPAHTUMAVARIT = {
    "niitto": MUSTE,
    "sadonkorjuu": MUSTE,
    "kynto_tai_muokkaus": HILJAINEN,
    "kypsyys": HILJAINEN,
    "oraalle_tulo": MUSTE,
    "talvipeite": "#4a505c",
}
TAPAHTUMANIMET = {
    "niitto": "niitto",
    "sadonkorjuu": "sadonkorjuu",
    "kynto_tai_muokkaus": "kyntö tai muokkaus",
    "kypsyys": "kypsyys",
    "oraalle_tulo": "oraalle tulo",
    "talvipeite": "talvipeite",
}
# Hiilivuot: sidonta vihreä, hengitys meripihka, nettotase muste.
VUOVARIT = {"gpp": VIHREA, "npp": "#9ee6b6", "reco": MERIPIHKA, "nee": MUSTE}
# Pysyvyysluokat 0–4: ei tietoa, vakaasti heikko, keskimääräinen, vakaasti hyvä, epävakaa.
PYSYVYYSVARIT = [TYHJA, MERIPIHKA, "#2a303b", VIHREA, VIOLETTI]
# Talvituho: kasvustoa / ei vihreää.
TUHOVARIT = {"kasvustoa": VIHREA, "ei vihreää": MERIPIHKA}

# Väriasteikot: omat nimet rakennetaan pysäytysväreistä, muut ovat matplotlibin.
ASTEIKOT = {
    # kaksisuuntainen: meripihka heikko, keskitaso pimeä, vihreä hyvä
    "signaali": [MERIPIHKA, "#7a5716", "#121619", "#1f6b3f", VIHREA],
    # yksisuuntainen kasvu: pimeä vähän, vihreä paljon
    "maara": ["#121619", "#163c26", "#26804a", VIHREA],
    # varattu: N2O-riski-indeksi 0–1, pimeä matala, vaaleanpunainen korkea (hot spot kartalla, hot moment ajassa)
    "n2o-riski": ["#121619", "#4a2a37", "#9c5a74", PINKKI],
    # märkyys: syaani märkä (DTW 0 m), pimeä kuiva
    "markyys": [SYAANI, "#175a66", "#121619"],
    # kasvuston sieppaama säteily (IPAR): pimeä vähän, muste paljon (valo, ei kasvu eikä varoitus)
    "ipar": ["#121619", "#34383f", "#8d93a0", MUSTE],
    # vaje referenssimaksimiin: pimeä ei vajetta, meripihka suuri vaje (heikko)
    "vaje": ["#121619", "#4a3810", "#a8711a", MERIPIHKA],
    # Helle yöllä -kansi: pinkki heikko, yönsininen keskitaso, taivaansininen hyvä (vain kansi, ei mittaustietoa)
    "helle": [HELLE_PINKKI, "#7a4466", "#2c3c70", "#2f6f9a", HELLE_TAIVAS],
}
KARTTA_SUHTEELLINEN = "signaali"
KARTTA_MAARA = "maara"
KARTTA_MARKYYS = "markyys"
KARTTA_KORKEUS = "cividis"
VANHAT_ASTEIKOT = {
    "RdYlGn": KARTTA_SUHTEELLINEN,
    "BrBG": KARTTA_SUHTEELLINEN,
    "maa-vesi": KARTTA_SUHTEELLINEN,
    "YlGn": KARTTA_MAARA,
    "Blues_r": KARTTA_MARKYYS,
}


def asteikko(nimi):
    """Matplotlibin väriasteikko nimestä; vanhat nimet ohjataan uusiin."""
    nimi = VANHAT_ASTEIKOT.get(nimi, nimi)
    if nimi in ASTEIKOT:
        from matplotlib.colors import LinearSegmentedColormap

        cm = LinearSegmentedColormap.from_list(nimi, ASTEIKOT[nimi])
        cm.set_bad("#00000000")
        return cm
    return nimi


def _rgb(h: str) -> tuple[int, int, int]:
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def vari(nimi: str, t: float) -> str:
    """Asteikon ``nimi`` väri kohdassa t (0–1) heksana; upotettaviin SVG-kuvioihin ilman matplotlibia."""
    p = [_rgb(h) for h in ASTEIKOT[VANHAT_ASTEIKOT.get(nimi, nimi)]]
    x = min(1.0, max(0.0, float(t))) * (len(p) - 1)
    i = min(len(p) - 2, int(x))
    f = x - i
    return "#" + "".join(f"{round(a + (b - a) * f):02x}" for a, b in zip(p[i], p[i + 1], strict=True))


_RC = {
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "text.color": MUSTE,
    "axes.labelcolor": HILJAINEN,
    "axes.edgecolor": "#3a4150",
    "axes.linewidth": 0.8,
    "axes.titlesize": 10,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.titlepad": 8,
    "axes.titlecolor": MUSTE,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": VIIVA,
    "grid.linewidth": 0.6,
    "xtick.color": HILJAINEN,
    "ytick.color": HILJAINEN,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.frameon": False,
    "legend.fontsize": 8,
    "legend.labelcolor": MUSTE,
    "figure.facecolor": PINTA,
    "axes.facecolor": PINTA,
    "savefig.facecolor": PINTA,
    "lines.linewidth": 1.6,
    "lines.markersize": 4,
}
KUVAN_DPI = 150


@contextmanager
def teema():
    """Kuvaajien yhteinen ulkoasu: ``with teema(): fig, ax = plt.subplots(...)``."""
    import matplotlib

    matplotlib.use("Agg")
    with matplotlib.rc_context(_RC):
        yield


# --- Fontit: upotetaan raporttiin, jotta se avautuu ilman verkkoa (SIL OFL 1.1) ---
FONTIT = (
    ("League Spartan", 800, "league-spartan-latin-800-normal.woff2"),
    ("Jost", 400, "jost-latin-400-normal.woff2"),
    ("Jost", 600, "jost-latin-600-normal.woff2"),
)


@lru_cache
def fontti_css() -> str:
    o = []
    for perhe, paino, tiedosto in FONTIT:
        try:
            data = resources.files("kasvukuntoraportti").joinpath("data", "fontit", tiedosto).read_bytes()
        except (FileNotFoundError, ModuleNotFoundError):
            continue  # ilman fonttitiedostoa selain käyttää varafonttia
        b64 = base64.b64encode(data).decode("ascii")
        o.append(
            f"@font-face{{font-family:'{perhe}';font-weight:{paino};font-style:normal;font-display:swap;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}"
        )
    return "".join(o)


def _muuttujat(v: dict) -> str:
    return "".join(f"--{k}:{a};" for k, a in v.items())


_KENTAT = (
    f"--indigo:{INDIGO};--meripihka:{MERIPIHKA};--petrooli:{PETROOLI};--syaani:{SYAANI};"
    f"--violetti:{VIOLETTI};--vihrea:{VIHREA};--pinkki:{PINKKI};--tyhja:{TYHJA};"
)

CSS = (
    ":root{" + _muuttujat(AVARUUS_TEEMA) + _KENTAT + "color-scheme:dark;"
    "--otsikko:'League Spartan','Jost',Futura,'Century Gothic',sans-serif;"
    "--teksti:'Jost',Futura,'Century Gothic',system-ui,sans-serif;--palkki:56px;--varsi:0px}"
    + """
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--tausta);color:var(--muste);font:17px/1.5 var(--teksti)}
a{color:var(--linkki)}
h1,h2,.iso{font-family:var(--otsikko);font-weight:800;letter-spacing:-.025em;text-wrap:balance}
h1{font-size:clamp(40px,8vw,92px);line-height:.9;margin:0}
h2{font-size:clamp(28px,4.5vw,44px);line-height:1;margin:0 0 18px}
h3{font-size:19px;font-weight:600;margin:26px 0 8px}
p{margin:0 0 12px}
.tunniste{font-size:13px;font-weight:600;letter-spacing:.12em;text-transform:uppercase}
.hiljainen{color:var(--hiljainen)}
.pieni,.selite{font-size:15px}
.selite{color:var(--hiljainen);max-width:68ch}

/* ---- Kirja: sivu kerrallaan, kun skripti on käytössä; ilman skriptiä sivut ovat allekkain ---- */
.sivu{min-height:calc(100dvh - var(--palkki));padding:40px max(16px,env(safe-area-inset-right,0px)) 48px max(16px,env(safe-area-inset-left,0px))}
.sivu>.sisus{max-width:1080px;margin:0 auto}
.js .sivu:not(.nyt){display:none}
.kirja{overflow-x:clip}
.js .sivu.nyt{display:block;animation:sisaan .28s ease-out}
.js .sivu.aukeama.nyt,.js .sivu.kansi.nyt{display:grid}
@keyframes sisaan{from{opacity:0;transform:translateX(var(--suunta,14px))}to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){.js .sivu.nyt{animation:none}}
body{padding-bottom:var(--palkki)}

/* Kansi: Rothkon kentät */
.sivu.kansi{display:grid;grid-template-rows:1fr auto 1fr;gap:14px;padding:18px;color:var(--muste);position:relative}
.kansi .k{border-radius:4px;filter:blur(.6px)}
.kansi .k1{background:var(--indigo)}.kansi .k2{background:var(--meripihka);height:clamp(40px,9vh,90px)}.kansi .k3{background:var(--petrooli)}
.kansi.taka .k1{background:var(--petrooli)}.kansi.taka .k2{background:var(--syaani)}.kansi.taka .k3{background:var(--indigo)}
.kansi .paalla{position:absolute;inset:18px;padding:clamp(20px,5vw,56px);display:flex;flex-direction:column;justify-content:space-between;gap:20px}
.kansi .ala{font-size:clamp(18px,2.4vw,24px);margin:14px 0 0;max-width:30ch}
.kansi .tiedot{font-size:14px;opacity:.9;max-width:60ch}
.kansi .tiedot a{color:inherit}
.kansi svg{max-height:34vh;width:auto;max-width:100%;align-self:flex-end}
iframe.kasvu3d{width:100%;height:min(78vh,680px);border:1px solid var(--viiva);border-radius:4px;background:var(--avaruus);display:block}
.tulostehuom{display:none}
@media print{iframe.kasvu3d{display:none}.tulostehuom{display:block}}
.kansi.helle{background:var(--avaruus)}.kansi.helle .k{display:none}
.kansi.helle .paalla{inset:0}.kansi.helle svg.pk{position:absolute;right:4%;bottom:6%;max-height:74%;max-width:62%;z-index:-1}
.kansi.helle .paalla{z-index:1}.kansi.helle .merkki{color:#f0b429}
.kansi ul{margin:0;padding-left:18px}
.kansi button.avaa{align-self:flex-start;font:600 16px var(--teksti);color:#050505;background:var(--muste);border:0;border-radius:999px;padding:12px 22px;cursor:pointer}

/* Aukeama: värikenttä ja kuvio */
.sivu.aukeama{display:grid;grid-template-columns:minmax(0,1fr);gap:14px;padding:18px}
@media(min-width:900px){.sivu.aukeama{grid-template-columns:minmax(0,5fr) minmax(0,6fr)}}
.kentta{border-radius:4px;padding:clamp(22px,4vw,48px);display:flex;flex-direction:column;justify-content:space-between;gap:28px;color:var(--muste);background:var(--indigo);min-width:0}
.kentta.petrooli{background:var(--petrooli)}.kentta.tumma{background:var(--avaruus);border:1px solid var(--viiva)}
.kentta.meripihka{background:var(--meripihka);color:#050505}
.kentta .iso{font-size:clamp(34px,5.4vw,68px);line-height:.95;margin:0;overflow-wrap:anywhere}
.kentta .iso b{font-size:1.7em;display:block;line-height:.85;margin-bottom:.08em}
.kentta p{font-size:18px;max-width:34ch;margin:0}
.kentta a{color:inherit}
.kuvio{background:var(--pinta);border-radius:4px;padding:clamp(18px,3vw,36px);display:flex;flex-direction:column;justify-content:center;gap:22px;min-width:0}
.kuvio svg{display:block;width:100%;height:auto;max-height:62vh}
.kuvio .kt{font-size:14px;color:var(--hiljainen);margin:0}
.kuvio h3{margin:0}
.pk circle{transition:r .12s}
.pk circle:hover{stroke:var(--muste);stroke-width:1.5}
.asteikko{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--hiljainen)}
.asteikko i{flex:1;height:8px;border-radius:4px}
.osuudet{display:flex;height:44px;gap:2px}
.osuudet i{display:block;border-radius:3px;min-width:3px}
.selitteet{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:14px;margin:0;padding:0;list-style:none}
.selitteet i{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:6px}
.selitteet b{font-weight:600;font-variant-numeric:tabular-nums}
.pino{display:flex;flex-direction:column;gap:6px;height:min(52vh,420px)}
.pino div{border-radius:4px;padding:12px 16px;color:#050505;display:flex;justify-content:space-between;align-items:flex-end;min-height:44px;font-size:15px}
.pino b{font:800 clamp(22px,3vw,34px)/1 var(--otsikko)}
.luvut{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:18px}
.luvut div{border-top:3px solid var(--muste);padding-top:8px;font-size:14px;color:var(--hiljainen)}
.luvut b{display:block;font:800 clamp(28px,3.4vw,40px)/1 var(--otsikko);color:var(--muste);letter-spacing:-.02em}
.luvut b small{font:600 15px var(--teksti);letter-spacing:0;color:var(--hiljainen)}
.sadat{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:22px}
.sadat figure{margin:0}
.sadat figcaption{font-size:14px;color:var(--hiljainen);margin-top:8px}
.sadat figcaption b{display:block;font:800 30px/1 var(--otsikko);color:var(--muste)}

/* Sisältösivut */
.kortti{background:var(--pinta);border:1px solid var(--viiva);border-radius:6px;padding:16px 20px;margin:0 0 14px}
.huomio{border-left:6px solid var(--meripihka);background:var(--varoitus-pehmea);padding:12px 16px;margin:0 0 14px;font-size:16px}
.huomio.ohje{border-color:var(--vihrea);background:var(--korostus-pehmea)}
dl.tiedot{display:grid;grid-template-columns:minmax(150px,300px) minmax(0,1fr);margin:0;font-size:16px}
dl.tiedot dt,dl.tiedot dd{margin:0;padding:7px 0;border-top:1px solid var(--viiva)}
dl.tiedot dt{color:var(--hiljainen);padding-right:16px}
dl.tiedot dt:first-of-type,dl.tiedot dt:first-of-type+dd{border-top:0}
dl.tiedot dd{font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
@media(max-width:560px){dl.tiedot{grid-template-columns:1fr}dl.tiedot dd{border-top:0;padding-top:0;font-weight:600}}
.vierita{overflow-x:auto}
table.t{border-collapse:collapse;width:100%;font-size:15px}
table.t th,table.t td{text-align:left;padding:7px 10px 7px 0;border-top:1px solid var(--viiva);vertical-align:top}
table.t thead th{border-top:0;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--hiljainen);font-weight:600;white-space:nowrap}
table.t td{font-variant-numeric:tabular-nums}
.kuvat{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;margin:0 0 14px}
figure{margin:0 0 14px}
.kuvat figure{margin:0}
figure img{display:block;width:100%;height:auto;background:#fff;border:1px solid var(--viiva);border-radius:4px}
figcaption{font-size:14px;color:var(--hiljainen);margin-top:6px}
ul.lista{margin:0;padding-left:20px}
ul.lista li{margin-bottom:6px}

/* Termit ja ilmiöt */
a.termi{color:inherit;text-decoration:underline dotted;text-underline-offset:3px;text-decoration-color:var(--hiljainen)}
.ilmiot{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px;margin:0 0 14px}
.ilmio{background:var(--pinta);border-top:4px solid var(--muste);padding:14px 18px;font-size:16px}
.ilmio h4{font-size:18px;font-weight:600;margin:0 0 8px}
.ilmio dl{margin:0}
.ilmio dt{font-size:12px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--korostus);margin-top:8px}
.ilmio dd{margin:2px 0 0}
.sanasto{columns:2 340px;column-gap:32px;margin:0}
.sanasto div{break-inside:avoid;padding:8px 0;border-top:1px solid var(--viiva);font-size:16px}
.sanasto dt{font-weight:600}
.sanasto dt span{font-weight:400;color:var(--hiljainen)}
.sanasto dd{margin:2px 0 0;color:var(--hiljainen)}
.sanasto div:target,.ilmio:target{outline:3px solid var(--syaani);outline-offset:4px}
h3.ryhma{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:var(--korostus);margin:22px 0 4px}

/* Pavunvarsi-sivu */
.sivu.varsi .sisus{max-width:1180px}
.sivu.varsi .tunniste{color:var(--hiljainen);margin-bottom:10px}
.varsikuva{overflow-x:auto}
.varsikuva svg{min-width:760px;width:100%;max-width:1000px;height:auto}
.varsikuva text{font-family:var(--teksti)}
.varsikuva .lahde,.varsikuva .tuote{cursor:pointer}
.varsikuva .reuna{fill:none;stroke-width:1.4;transition:opacity .15s,stroke-width .15s}
.varsikuva.valittu .reuna{opacity:.08!important}
.varsikuva.valittu .reuna.on{opacity:1!important;stroke-width:2.4}
.varsikuva.valittu .lahde,.varsikuva.valittu .tuote{opacity:.25;transition:opacity .15s}
.varsikuva.valittu .lahde.on,.varsikuva.valittu .tuote.on{opacity:1}
.ohjeet{display:flex;flex-wrap:wrap;gap:8px 22px;font-size:14px;color:var(--hiljainen);margin:0 0 12px;padding:0;list-style:none}

/* Köysi marginaalissa: sivun lähteet syttyvät omalle korkeudelleen */
.varsi-reuna{display:none}
@media(min-width:960px){
  .js body{--varsi:64px}
  .js .varsi-reuna{display:block;position:fixed;left:0;top:0;bottom:var(--palkki);width:var(--varsi);z-index:10;pointer-events:none}
  .js .sivu{padding-left:calc(var(--varsi) + 16px)}
  .js .sivu.aukeama,.js .sivu.kansi{padding-left:calc(var(--varsi) + 4px)}
  .js .kansi .paalla{left:calc(var(--varsi) + 4px)}
}
.varsi-reuna svg{width:100%;height:100%}
.varsi-reuna line.koysi{stroke:var(--muste);stroke-width:1;opacity:.35}
.varsi-reuna .m line{stroke:var(--hiljainen);stroke-width:1;opacity:.5}
.varsi-reuna .m text{fill:var(--muste);font:600 10px var(--teksti);opacity:0;transition:opacity .2s}
.varsi-reuna .m.on line{stroke:var(--muste);stroke-width:2;opacity:1}
.varsi-reuna .m.on text{opacity:1}
.varsi-reuna .maa{stroke:var(--meripihka);stroke-width:2}

/* Kolme merkkiä, kukin kerran */
.merkki{display:inline-block;vertical-align:middle;width:11px;height:11px;margin-left:8px;opacity:.75}
.merkki svg{display:block;width:100%;height:100%}
.ilmio{position:relative}
.ilmio .merkki{position:absolute;right:12px;top:14px;margin:0}

/* Selauspalkki */
.palkki{position:fixed;left:0;right:0;bottom:0;z-index:20;height:var(--palkki);background:var(--tausta);border-top:1px solid var(--viiva);
  display:flex;align-items:center;gap:10px;padding:0 max(12px,env(safe-area-inset-right,0px)) 0 max(12px,env(safe-area-inset-left,0px))}
.palkki button{font:600 15px var(--teksti);color:var(--muste);background:var(--pinta);border:1px solid var(--viiva);border-radius:999px;min-width:44px;height:40px;padding:0 14px;cursor:pointer}
.palkki button:disabled{opacity:.35;cursor:default}
.palkki button:focus-visible,.sis a:focus-visible{outline:3px solid var(--syaani);outline-offset:2px}
.palkki .missa{flex:1;min-width:0;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.palkki .missa b{font-weight:600}
.palkki .jana{position:absolute;left:0;top:-3px;height:3px;background:var(--muste);transition:width .2s}
.sis{position:fixed;left:0;right:0;bottom:var(--palkki);z-index:19;max-height:70dvh;overflow:auto;background:var(--pinta);border-top:1px solid var(--viiva);
  padding:14px max(16px,env(safe-area-inset-right,0px)) 14px max(16px,env(safe-area-inset-left,0px));columns:3 220px;column-gap:28px}
.sis a{display:flex;gap:10px;padding:6px 0;color:var(--muste);text-decoration:none;font-size:15px;break-inside:avoid}
.sis a span{color:var(--hiljainen);font-variant-numeric:tabular-nums;min-width:2ch}
.sis a.paa{font-weight:600}
.sis a[aria-current]{color:var(--varoitus)}
html:not(.js) .palkki,html:not(.js) .sis{display:none}

/* Tuloste: A4, sivu kerrallaan, kentät ohuina raitoina (säästää mustetta) */
@page{size:A4;margin:16mm 14mm}
@media print{
  :root{"""
    + _muuttujat(PAPERI_TEEMA)
    + "color-scheme:light"
    + """}
  body{background:#fff;font-size:10.5pt;padding:0}
  .palkki,.sis,.kansi button.avaa{display:none!important}
  .js .sivu,.sivu{display:block!important;min-height:0;padding:0;break-before:page;animation:none}
  .sivu:first-child{break-before:auto}
  .sivu.aukeama,.sivu.kansi{display:block!important}
  .kentta,.kentta.meripihka,.kentta.petrooli,.kentta.tumma{background:none;color:#111;border:0;border-left:8px solid var(--indigo);border-radius:0;padding:0 0 0 14px;margin-bottom:18px}
  .kentta.petrooli{border-color:var(--petrooli)}.kentta.meripihka{border-color:var(--meripihka)}.kentta.tumma{border-color:#111}
  .varsi-reuna{display:none!important}
  /* kuviot ovat tulosteessakin ikkunoita data-avaruuteen */
  .kuvio,.varsikuva{background:#0d1016!important;padding:5mm;border-radius:0;-webkit-print-color-adjust:exact;print-color-adjust:exact;
    --muste:#efeae0;--hiljainen:#8d93a0;--viiva:#232833;color:#efeae0}
  .kuvio .kt,.kuvio .asteikko{color:#8d93a0}
  .varsikuva{overflow:visible}.varsikuva svg{min-width:0}
  .kuvio svg{max-height:120mm}
  .kansi{color:#1c1a17}
  .kansi .k{height:6mm;filter:none}
  .kansi .paalla{position:static;padding:10mm 0}
  h2,h3{break-after:avoid}
  figure,.kortti,.ilmio,.huomio,tr{break-inside:avoid}
  .kuvat{grid-template-columns:repeat(3,1fr)}
  a{color:inherit;text-decoration:none}
  a.termi{text-decoration:none}
}
"""
)

# Selaus: nuolinäppäimet, painikkeet, pyyhkäisy, sisällys ja #ankkuri. Ilman skriptiä sivut ovat allekkain.
JS = """
(function(){
  var d=document, sivut=[].slice.call(d.querySelectorAll('.sivu')), nyt=0;
  if(!sivut.length) return;
  d.documentElement.classList.add('js');
  var ed=d.getElementById('ed'), se=d.getElementById('se'), missa=d.getElementById('missa'), jana=d.getElementById('jana');
  var sis=d.getElementById('sis'), sb=d.getElementById('sisb');
  function nayta(i,vieri){
    i=Math.max(0,Math.min(sivut.length-1,i));
    d.documentElement.style.setProperty('--suunta',(i<nyt?-14:14)+'px');
    sivut.forEach(function(s,k){s.classList.toggle('nyt',k===i)});
    nyt=i; ed.disabled=i===0; se.disabled=i===sivut.length-1;
    missa.innerHTML='<b>'+(i+1)+' / '+sivut.length+'</b> · '+(sivut[i].dataset.nimi||'');
    jana.style.width=((i+1)/sivut.length*100)+'%';
    var lv=(sivut[i].getAttribute('data-lahteet')||'').split(' ');
    [].forEach.call(d.querySelectorAll('.varsi-reuna .m'),function(g){g.classList.toggle('on',lv.indexOf(g.getAttribute('data-k'))>=0)});
    [].forEach.call(sis.querySelectorAll('a'),function(a){if(a.getAttribute('href')==='#'+sivut[i].id)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current')});
    sis.hidden=true; sb.setAttribute('aria-expanded','false');
    if(vieri!==false) window.scrollTo(0,0);
    try{history.replaceState(null,'','#'+sivut[i].id)}catch(e){}
  }
  function kohde(h){
    var el=h&&d.getElementById(h.slice(1)); if(!el) return false;
    var s=el.closest('.sivu'); if(!s) return false;
    nayta(sivut.indexOf(s), el===s); if(el!==s) el.scrollIntoView();
    return true;
  }
  ed.onclick=function(){nayta(nyt-1)}; se.onclick=function(){nayta(nyt+1)};
  sb.onclick=function(){sis.hidden=!sis.hidden; sb.setAttribute('aria-expanded',String(!sis.hidden))};
  d.addEventListener('click',function(e){
    var a=e.target.closest&&e.target.closest('a[href^="#"]');
    if(a&&kohde(a.getAttribute('href'))) e.preventDefault();
    else if(e.target.closest&&e.target.closest('[data-seuraava]')) nayta(nyt+1);
  });
  d.addEventListener('keydown',function(e){
    if(e.altKey||e.ctrlKey||e.metaKey||/INPUT|SELECT|TEXTAREA/.test(e.target.tagName)) return;
    if(e.key==='ArrowRight'||e.key==='PageDown') nayta(nyt+1);
    else if(e.key==='ArrowLeft'||e.key==='PageUp') nayta(nyt-1);
    else if(e.key==='Home') nayta(0); else if(e.key==='End') nayta(sivut.length-1);
    else if(e.key==='Escape') {sis.hidden=true; sb.setAttribute('aria-expanded','false')}
  });
  var x0=null,y0=null;
  d.addEventListener('touchstart',function(e){var t=e.touches[0];x0=t.clientX;y0=t.clientY},{passive:true});
  d.addEventListener('touchend',function(e){
    if(x0===null) return; var t=e.changedTouches[0], dx=t.clientX-x0, dy=t.clientY-y0; x0=null;
    if(Math.abs(dx)>70&&Math.abs(dx)>2*Math.abs(dy)&&!(e.target.closest&&e.target.closest('.vierita'))) nayta(nyt+(dx<0?1:-1));
  },{passive:true});
  // Pavunvarsi: tuloksen tai lähteen suhteet korostuvat
  [].forEach.call(d.querySelectorAll('.varsikuva'),function(v){
    function k(e,a){return (e.getAttribute(a)||'').split(' ').filter(Boolean)}
    function valitse(ts,ls){v.classList.add('valittu');
      [].forEach.call(v.querySelectorAll('.tuote'),function(e){e.classList.toggle('on',ts.indexOf(e.getAttribute('data-t'))>=0)});
      [].forEach.call(v.querySelectorAll('.lahde'),function(e){e.classList.toggle('on',ls.indexOf(e.getAttribute('data-k'))>=0)});
      [].forEach.call(v.querySelectorAll('.reuna'),function(e){var t=e.getAttribute('data-t'),kk=k(e,'data-k');
        e.classList.toggle('on',t?ts.indexOf(t)>=0&&kk.some(function(x){return ls.indexOf(x)>=0}):kk.every(function(x){return ls.indexOf(x)>=0}))})}
    function pois(){v.classList.remove('valittu')}
    [].forEach.call(v.querySelectorAll('.tuote'),function(e){function on(){valitse([e.getAttribute('data-t')],k(e,'data-l'))}
      e.addEventListener('mouseenter',on);e.addEventListener('focus',on);e.addEventListener('mouseleave',pois);e.addEventListener('blur',pois)});
    [].forEach.call(v.querySelectorAll('.lahde'),function(e){var key=e.getAttribute('data-k');
      function on(){var ts=[].filter.call(v.querySelectorAll('.tuote'),function(t){return k(t,'data-l').indexOf(key)>=0}).map(function(t){return t.getAttribute('data-t')});
        var ls=[key];[].forEach.call(v.querySelectorAll('.reuna:not([data-t])'),function(r){var kk=k(r,'data-k');if(kk.indexOf(key)>=0)kk.forEach(function(x){if(ls.indexOf(x)<0)ls.push(x)})});
        valitse(ts,ls)}
      e.addEventListener('mouseenter',on);e.addEventListener('focus',on);e.addEventListener('mouseleave',pois);e.addEventListener('blur',pois)});
  });
  window.addEventListener('hashchange',function(){kohde(location.hash)});
  if(!kohde(location.hash)) nayta(0,false);
})();
"""

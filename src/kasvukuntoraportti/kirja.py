"""Kirjasen infografiikka: upotettavat SVG- ja HTML-kuviot aukeamille (ei matplotlibia).

Jokainen kuvio kertoo yhden asian: pistekartta (yksi piste = yksi solu), sataruudukko
(persentiili sadasta pisteestä), osuuspalkki, kausinauha ja pinta-alaltaan verrannolliset kentät.
"""

from __future__ import annotations

import html
import warnings
from datetime import date

import numpy as np
import pandas as pd

from . import ilme

e = html.escape


def fi(x, desimaalit: int = 1) -> str:
    """Luku suomalaisittain: desimaalipilkku, turhat nollat pois."""
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "–"
    s = f"{float(x):.{desimaalit}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s.replace(".", ",").replace("-", "−")


def pvm(p) -> str:
    """2025-06-12 -> 12.6.2025; muu jätetään ennalleen."""
    try:
        d = date.fromisoformat(str(p)[:10])
        return f"{d.day}.{d.month}.{d.year}"
    except ValueError:
        return str(p)


def _harvenna(a: np.ndarray, enintaan: int) -> tuple[np.ndarray, int]:
    """Lohkokeskiarvo, kunnes kelvollisia soluja on enintään ``enintaan``."""
    k = 1
    b = a
    while np.isfinite(b).sum() > enintaan:
        k += 1
        h, w = (a.shape[0] // k) * k, (a.shape[1] // k) * k
        if h == 0 or w == 0:
            break
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)  # kokonaan tyhjät lohkot jäävät NaN:ksi
            b = np.nanmean(a[:h, :w].reshape(h // k, k, w // k, k), axis=(1, 3))
    return b, k


def pistekartta(
    arr: np.ndarray,
    asteikko: str = "signaali",
    vmin: float = 85,
    vmax: float = 115,
    yksikko: str = " % lohkon mediaanista",
    enintaan: int = 1500,
    yksivari: str | None = None,
    otsikko: str = "Pistekartta",
) -> str:
    """Rasteri pisteinä: yksi piste = yksi solu, väri = arvo. ``yksivari``: väri sama, koko = arvo (kansi)."""
    a, _ = _harvenna(np.asarray(arr, dtype=float), enintaan)
    ok = np.isfinite(a)
    if not ok.any():
        return ""
    rivit, sarakkeet = np.where(ok)
    r0, r1, c0, c1 = rivit.min(), rivit.max(), sarakkeet.min(), sarakkeet.max()
    w, h = (c1 - c0 + 1) * 10, (r1 - r0 + 1) * 10
    o = [f'<svg class="pk" viewBox="0 0 {w} {h}" role="img" aria-label="{e(otsikko)}">']
    for r, c in zip(rivit, sarakkeet, strict=True):
        v = float(a[r, c])
        t = (v - vmin) / (vmax - vmin)
        x, y = (c - c0) * 10 + 5, (r - r0) * 10 + 5
        if yksivari:
            sade = 1.6 + 3.0 * min(1.0, max(0.0, t))
            o.append(f'<circle cx="{x}" cy="{y}" r="{sade:.1f}" fill="{yksivari}"/>')
        else:
            o.append(
                f'<circle cx="{x}" cy="{y}" r="4.3" fill="{ilme.vari(asteikko, t)}">'
                f"<title>{fi(v, 0)}{e(yksikko)}</title></circle>"
            )
    o.append("</svg>")
    return "".join(o)


def asteikkoselite(asteikko: str, vasen: str, oikea: str) -> str:
    vv = ",".join(ilme.ASTEIKOT[asteikko])
    return (
        f'<div class="asteikko"><span>{e(vasen)}</span>'
        f'<i style="background:linear-gradient(90deg,{vv})"></i><span>{e(oikea)}</span></div>'
    )


def sataruudukko(arvo: float, vari: str = ilme.VIHREA, otsikko: str = "") -> str:
    """10 × 10 pistettä, joista ``arvo`` on täytetty: persentiili luettavana kuvana."""
    n = int(round(min(100, max(0, arvo))))
    o = [f'<svg viewBox="0 0 100 100" role="img" aria-label="{e(otsikko)}: {n} sadasta">']
    for i in range(100):
        r, c = 9 - i // 10, i % 10  # täyttö alhaalta ylös
        taysi = i < n
        o.append(
            f'<circle cx="{c * 10 + 5}" cy="{r * 10 + 5}" r="3.6" '
            + (
                f'fill="{vari}"/>'
                if taysi
                else f'fill="none" stroke="{ilme.HILJAINEN}" stroke-opacity=".5" stroke-width="1"/>'
            )
        )
    o.append("</svg>")
    return "".join(o)


def osuuspalkki(osuudet: list[tuple[str, float, str]]) -> str:
    """Vaakapalkki osuuksista ja selite: [(nimi, prosentti, väri)]."""
    osat = [(n, p, c) for n, p, c in osuudet if p and p > 0]
    if not osat:
        return ""
    palkki = "".join(
        f'<i style="flex:{p:.1f};background:{c}" title="{e(n)} {fi(p)} %"></i>' for n, p, c in osat
    )
    selite = "".join(f'<li><i style="background:{c}"></i>{e(n)} <b>{fi(p)} %</b></li>' for n, p, c in osat)
    return f'<div class="osuudet">{palkki}</div><ul class="selitteet">{selite}</ul>'


def pino(osat: list[tuple[str, float, str, str]]) -> str:
    """Rothko-pino: kenttien korkeus on verrannollinen arvoon. [(nimi, arvo, yksikkö, väri)]."""
    osat = [x for x in osat if x[1] and x[1] > 0]
    if not osat:
        return ""
    return (
        '<div class="pino">'
        + "".join(
            f'<div style="flex:{a:.0f};background:{c}"><span>{e(n)}</span><b>{fi(a, 0)} {e(y)}</b></div>'
            for n, a, y, c in osat
        )
        + "</div>"
    )


def luvut(rivit: list[tuple[str, str, str]]) -> str:
    """Isot luvut rinnakkain: [(arvo, yksikkö, selite)]."""
    return (
        '<div class="luvut">'
        + "".join(
            f"<div><b>{e(a)}{' <small>' + e(y) + '</small>' if y else ''}</b>{e(s)}</div>"
            for a, y, s in rivit
        )
        + "</div>"
    )


def kausinauha(optinen: pd.DataFrame | None, peltotyot: pd.DataFrame | None, vuosi: int) -> tuple[str, dict]:
    """Kasvukausi nauhana 1.4.–31.10.: viikon väri = NDVI, merkit = peltotyöt. Palauttaa (svg, tiedot)."""
    tiedot: dict = {}
    if optinen is None or not len(optinen):
        return "", tiedot
    d = optinen[optinen["kelvollinen_pct"] >= 80]
    if not len(d):
        return "", tiedot
    s = d.assign(t=pd.to_datetime(d["pvm"])).groupby("t")["ndvi_p50"].median().sort_index()
    alku, loppu = pd.Timestamp(f"{vuosi}-04-01"), pd.Timestamp(f"{vuosi}-10-31")
    huippu = s[(s.index >= alku) & (s.index <= loppu)]
    if len(huippu):
        tiedot["huippu_pvm"] = huippu.idxmax().strftime("%Y-%m-%d")
        tiedot["huippu_ndvi"] = float(huippu.max())
    tiedot["kuvia"] = int(len(s))
    viikot = pd.date_range(alku, loppu, freq="7D")
    x = (s.index - alku).days.to_numpy(dtype=float)
    paivia = (loppu - alku).days + 1
    lev, kork, yla = 1000.0, 230.0, 76.0
    o = [
        f'<svg viewBox="0 0 {lev:.0f} {yla + kork + 44:.0f}" role="img" aria-label="Kasvukausi {vuosi} viikoittain">'
    ]
    for v in viikot:
        k = (v - alku).days + 3.5
        if k < x.min() - 10 or k > x.max() + 10:
            vari, arvo = ilme.TYHJA, None  # ei havaintoa lähellä
        else:
            arvo = float(np.interp(k, x, s.to_numpy()))
            vari = ilme.vari("maara", (arvo - 0.15) / 0.75)
        x0 = (v - alku).days / paivia * lev
        w = 7 / paivia * lev - 2
        nimi = f"vko {v.isocalendar().week}: " + (
            f"NDVI {fi(arvo, 2)}" if arvo is not None else "ei selkeää kuvaa"
        )
        o.append(
            f'<rect x="{x0:.1f}" y="{yla}" width="{w:.1f}" height="{kork}" rx="3" fill="{vari}"><title>{nimi}</title></rect>'
        )
    for kk in range(4, 11):
        x0 = (pd.Timestamp(f"{vuosi}-{kk:02d}-01") - alku).days / paivia * lev
        nimi = ["huhti", "touko", "kesä", "heinä", "elo", "syys", "loka"][kk - 4]
        o.append(
            f'<text x="{x0 + 2:.1f}" y="{yla + kork + 32}" font-size="24" fill="{ilme.HILJAINEN}">{nimi}</text>'
        )
    n = 0
    if peltotyot is not None:
        for r in peltotyot.itertuples(index=False):
            if r.tyyppi == "talvipeite":
                continue
            a, b = pd.to_datetime(r.alku), pd.to_datetime(r.loppu)
            if b < alku or a > loppu:
                continue
            xa = max(0.0, (a - alku).days / paivia * lev)
            xb = min(lev, ((b - alku).days + 1) / paivia * lev)
            varma = r.luottamus >= 0.6
            katko = "" if varma else ' stroke-dasharray="6 5"'
            nimi = ilme.TAPAHTUMANIMET.get(r.tyyppi, str(r.tyyppi).replace("_", " ")) + (
                "" if varma else " ?"
            )
            y = 26 + 30 * (n % 2)
            ankkuri = "end" if xa > lev * 0.8 else "start"
            o.append(
                f'<rect x="{xa:.1f}" y="{yla - 6}" width="{max(4.0, xb - xa):.1f}" height="{kork + 12}" rx="2" fill="none" '
                f'stroke="{ilme.MUSTE}" stroke-width="3"{katko}/>'
                f'<text x="{xa if ankkuri == "start" else xb:.1f}" y="{y}" font-size="24" font-weight="600" '
                f'text-anchor="{ankkuri}" fill="{ilme.MUSTE}">{e(nimi)}</text>'
            )
            n += 1
    o.append("</svg>")
    return "".join(o), tiedot


def vuosijana(vuodet: dict[int, float | None], otsikko: str = "Indeksi vuosittain") -> str:
    """Indeksi vuosittain janalla 0–100; pystyviiva = vertailulohkojen keskitaso."""
    rivit = [(v, x) for v, x in sorted(vuodet.items()) if x is not None]
    if not rivit:
        return ""
    rk = 30
    h = len(rivit) * rk + 30
    o = [f'<svg viewBox="0 0 520 {h}" role="img" aria-label="{e(otsikko)}">']
    o.append(
        f'<line x1="280" y1="4" x2="280" y2="{h - 26}" stroke="{ilme.HILJAINEN}" stroke-width="1" stroke-dasharray="3 4"/>'
    )
    o.append(
        f'<text x="280" y="{h - 8}" font-size="13" text-anchor="middle" fill="{ilme.HILJAINEN}">50 = keskitaso</text>'
    )
    for i, (v, x) in enumerate(rivit):
        y = i * rk + 18
        cx = 80 + 4 * min(100, max(0, x))
        o.append(
            f'<text x="0" y="{y + 5}" font-size="15" fill="{ilme.HILJAINEN}">{v}</text>'
            f'<line x1="80" y1="{y}" x2="480" y2="{y}" stroke="{ilme.VIIVA}" stroke-width="2"/>'
            f'<line x1="280" y1="{y}" x2="{cx:.0f}" y2="{y}" stroke="{ilme.VIHREA if x >= 50 else ilme.MERIPIHKA}" stroke-width="6" stroke-linecap="round"/>'
            f'<circle cx="{cx:.0f}" cy="{y}" r="8" fill="{ilme.VIHREA if x >= 50 else ilme.MERIPIHKA}"><title>{v}: {fi(x, 0)}</title></circle>'
            f'<text x="{cx + 14:.0f}" y="{y + 5}" font-size="15" font-weight="600" fill="currentColor">{fi(x, 0)}</text>'
        )
    o.append("</svg>")
    return "".join(o)


def aukeama(
    ankkuri: str, nimi: str, tunniste: str, iso: str, alla: str, kuvio: str, vari: str = "", lahteet: str = ""
) -> str:
    """Aukeama: vasemmalla värikenttä ja yksi väite, oikealla kuvio. ``iso`` ja ``kuvio`` ovat HTML:ää.
    ``lahteet``: välilyönnein erotetut lähdeavaimet (``LAHTEET``), jotka syttyvät marginaalin köydessä."""
    return (
        f'<section class="sivu aukeama" id="{ankkuri}" data-nimi="{e(nimi)}" data-lahteet="{lahteet}">'
        f'<div class="kentta {vari}"><div class="tunniste">{e(tunniste)}</div>'
        f'<div><p class="iso">{iso}</p></div><p>{alla}</p></div>'
        f'<div class="kuvio">{kuvio}</div></section>'
    )


def sisaltosivu(ankkuri: str, nimi: str, otsikko: str, sisalto: str, lahteet: str = "") -> str:
    return (
        f'<section class="sivu sisalto" id="{ankkuri}" data-nimi="{e(nimi)}" data-lahteet="{lahteet}"><div class="sisus">'
        f"<h2>{e(otsikko)}</h2>{sisalto}</div></section>"
    )


# ---------- Pavunvarsi: datalähteet korkeutensa mukaan ----------

# korkeus metreinä (negatiivinen = maan alla), pikselikoko metreinä (0 = ei rasteria)
LAHTEET = {
    "geo": {
        "nimi": "Geostationaarinen rata",
        "lyhyt": "GEO",
        "h": 35_786e3,
        "px": 0,
        "kuvaus": "köyden pää, ei dataa",
        "ankkuri": True,
    },
    "s2": {
        "nimi": "Sentinel-2",
        "lyhyt": "S2",
        "h": 786e3,
        "px": 10,
        "kuvaus": "10 m · 5 vrk, Suomessa tiheämmin",
    },
    "hls": {
        "nimi": "HLS",
        "lyhyt": "HLS",
        "h": 745e3,
        "px": 30,
        "kuvaus": "30 m · Landsat ja Sentinel-2 yhdenmukaistettuna",
        "johdettu": True,
    },
    "ls": {
        "nimi": "Landsat 8/9",
        "lyhyt": "Landsat",
        "h": 705e3,
        "px": 30,
        "kuvaus": "30 m · 8 vrk kahdella satelliitilla",
    },
    "s1": {"nimi": "Sentinel-1", "lyhyt": "S1", "h": 693e3, "px": 10, "kuvaus": "tutka · näkee pilven läpi"},
    "pl": {
        "nimi": "PlanetScope",
        "lyhyt": "Planet",
        "h": 500e3,
        "px": 3,
        "kuvaus": "3 m · lähes päivittäin · noin 500 km",
    },
    "era": {
        "nimi": "ERA5-Land",
        "lyhyt": "ERA5",
        "h": 1e4,
        "px": 9000,
        "kuvaus": "säteily, lämpö, vesi · 9 km ruutu",
    },
    "mml": {
        "nimi": "MML laserkeilaus",
        "lyhyt": "MML",
        "h": 2e3,
        "px": 2,
        "kuvaus": "korkeusmalli 2 m · lentokoneesta",
    },
    "fmi": {
        "nimi": "FMI sääasemat",
        "lyhyt": "FMI",
        "h": 2,
        "px": 0,
        "kuvaus": "lumi, lämpö, sade · 2 m",
        "asema": True,
    },
    "lpis": {
        "nimi": "Ruokavirasto",
        "lyhyt": "lohkot",
        "h": 0,
        "px": 0,
        "kuvaus": "lohkorajat ja kasvit",
        "rajat": True,
    },
    "dtw": {
        "nimi": "Luke DTW",
        "lyhyt": "DTW",
        "h": 0,
        "px": 2,
        "kuvaus": "märkyys korkeusmallista",
        "johdettu": True,
    },
    "gtk": {
        "nimi": "GTK maaperä",
        "lyhyt": "GTK",
        "h": -0.3,
        "px": 0,
        "kuvaus": "pintamaan maalaji",
        "rajat": True,
    },
    "turve": {
        "nimi": "Turve",
        "lyhyt": "turve",
        "h": -0.6,
        "px": 0,
        "kuvaus": "≥ 30 cm ja > 60 cm (OmaMaatu)",
        "rajat": True,
    },
}
JOHDANNAISET = (("ls", "hls"), ("s2", "hls"), ("mml", "dtw"), ("pl", "s2"))


def korkeus_y(h: float, ylin: float = 60, maa: float = 600) -> float:
    """Katkaistu asteikko: GEO | 450–850 km venytettynä | ≈ | 1 m – 10 km logaritminen | maa | juuret."""
    k = (maa - ylin) / 540
    if h > 2e7:
        return ylin
    if h >= 450e3:
        return ylin + k * (270 - (h - 450e3) / 400e3 * 260)
    if h >= 1:
        return ylin + k * (530 - np.log10(h) / 4 * 190)
    if h >= 0:
        return maa
    return maa - h * 150 * k


def _sade(lahde: dict) -> float:
    return 3 + 2.4 * np.log10(max(1, lahde["px"])) if lahde["px"] else 3.5


def pavunvarsi(kaytossa: list[str], tulokset: list[tuple[str, str, list[str]]]) -> str:
    """Koko sivun kuvio: lähteet köydellä ja raportin tulokset (pavut) maassa, suhteet kaarina.
    ``tulokset``: [(tunnus, nimi, [lähdeavaimet])]."""
    avaimet = ["geo"] + [k for k in LAHTEET if k in kaytossa and k != "geo"]
    avaimet.sort(key=lambda k: korkeus_y(LAHTEET[k]["h"]))
    AX, NX, M, HL = 250, 580, ilme.MUSTE, ilme.HILJAINEN
    o = [
        '<svg viewBox="0 0 1000 780" role="img" aria-label="Datalähteet korkeutensa mukaan ja niistä lasketut tulokset">'
    ]
    o.append(f'<rect x="0" y="600" width="1000" height="180" fill="{ilme.PETROOLI}" opacity=".35"/>')
    o.append(f'<line x1="0" y1="600" x2="1000" y2="600" stroke="{ilme.MERIPIHKA}" stroke-width="2"/>')
    o.append(
        f'<text x="{AX - 12}" y="596" font-size="12" text-anchor="end" fill="{ilme.MERIPIHKA}">pelto 0 m</text>'
    )
    o.append(f'<line x1="{AX}" y1="52" x2="{AX}" y2="700" stroke="{M}" stroke-width="1.2" opacity=".55"/>')
    for yy in (92, 355):
        o.append(
            f'<rect x="{AX - 8}" y="{yy - 6}" width="16" height="12" fill="{ilme.AVARUUS}"/>'
            f'<text x="{AX}" y="{yy + 5}" font-size="16" text-anchor="middle" fill="{M}">≈</text>'
        )
    for h, t in (
        (35_786e3, "35 786 km"),
        (800e3, "800 km"),
        (700e3, "700 km"),
        (600e3, "600 km"),
        (500e3, "500 km"),
        (1e4, "10 km"),
        (1e3, "1 km"),
        (10, "10 m"),
        (-0.3, "−30 cm"),
        (-0.6, "−60 cm"),
    ):
        yy = korkeus_y(h)
        o.append(
            f'<line x1="{AX - 6}" y1="{yy:.1f}" x2="{AX}" y2="{yy:.1f}" stroke="{HL}"/>'
            f'<text x="{AX - 12}" y="{yy + 4:.1f}" font-size="12" text-anchor="end" fill="{HL}">{t}</text>'
        )
    o.append(f'<text x="{AX - 12}" y="470" font-size="12" text-anchor="end" fill="{HL}">ilmakehä</text>')
    # tarrat erilleen, viiva köyteen
    P, ly = {}, -1e9
    for k in avaimet:
        t = korkeus_y(LAHTEET[k]["h"])
        ty = max(t, ly + 34)
        if k == "dtw":
            ty = max(ty, 618)
        ly = ty
        P[k] = (t, ty)
    TX, TY = 650, 700
    pavut = [(tid, n, [k for k in ll if k in P], TX + i * 64) for i, (tid, n, ll) in enumerate(tulokset)]
    o.append('<g class="reunat">')
    for tid, _, ll, x in pavut:
        for k in ll:
            x1, y1 = NX + _sade(LAHTEET[k]) + 2, P[k][1]
            o.append(
                f'<path class="reuna" data-k="{k}" data-t="{tid}" d="M{x1:.1f} {y1:.1f} C{x1 + 120:.1f} {y1:.1f} {x} {y1 + (TY - 16 - y1) * 0.4:.1f} {x} {TY - 16}" '
                f'stroke="{ilme.SYAANI}" opacity=".5"/>'
            )
    for a, b in JOHDANNAISET:
        if a in P and b in P:
            ya, yb = P[a][1], P[b][1]
            o.append(
                f'<path class="reuna" data-k="{a} {b}" d="M{NX + _sade(LAHTEET[a]) + 3:.1f} {ya:.1f} C{NX + 46} {ya:.1f} {NX + 46} {yb:.1f} {NX + _sade(LAHTEET[b]) + 3:.1f} {yb:.1f}" '
                f'stroke="{HL}" stroke-dasharray="5 4" opacity=".8"/>'
            )
    o.append("</g>")
    halo = f'paint-order="stroke" stroke="{ilme.AVARUUS}" stroke-width="5" stroke-linejoin="round"'
    for k in avaimet:
        lv, (t, ty) = LAHTEET[k], P[k]
        r = _sade(lv)
        o.append(f'<g class="lahde" data-k="{k}" tabindex="0">')
        o.append(
            f'<line x1="{AX}" y1="{t:.1f}" x2="{NX - r - 4:.1f}" y2="{ty:.1f}" stroke="{HL}" stroke-width=".8" opacity=".6"/>'
        )
        o.append(f'<circle cx="{AX}" cy="{t:.1f}" r="2.5" fill="{M}"/>')
        if lv.get("asema"):
            o.append(f'<rect x="{NX - 4}" y="{ty - 4:.1f}" width="8" height="8" fill="{M}"/>')
        elif lv.get("rajat"):
            o.append(
                f'<rect x="{NX - 6}" y="{ty - 5:.1f}" width="12" height="10" rx="1" fill="none" stroke="{M}" stroke-width="1.4"/>'
            )
        elif lv.get("ankkuri"):
            o.append(
                f'<circle cx="{NX}" cy="{ty:.1f}" r="6" fill="none" stroke="{HL}" stroke-dasharray="2 2"/>'
            )
        elif lv.get("johdettu"):
            o.append(
                f'<circle cx="{NX}" cy="{ty:.1f}" r="{r:.1f}" fill="none" stroke="{ilme.SYAANI}" stroke-width="2"/>'
            )
        else:
            o.append(f'<circle cx="{NX}" cy="{ty:.1f}" r="{r:.1f}" fill="{ilme.SYAANI}"/>')
        o.append(
            f'<text x="{NX - 18}" y="{ty + 1:.1f}" font-size="15" font-weight="600" text-anchor="end" fill="{M}" {halo}>{e(lv["nimi"])}</text>'
            f'<text x="{NX - 18}" y="{ty + 16:.1f}" font-size="12" text-anchor="end" fill="{HL}" {halo}>{e(lv["kuvaus"])}</text></g>'
        )
    for i, (tid, n, ll, x) in enumerate(pavut):
        o.append(
            f'<g class="tuote" data-t="{tid}" data-l="{" ".join(ll)}" tabindex="0">'
            f'<ellipse cx="{x}" cy="{TY}" rx="26" ry="15" fill="{ilme.MERIPIHKA}"/>'
            f'<text x="{x}" y="{TY + 5}" font-size="13" font-weight="600" text-anchor="middle" fill="#050505">{len(ll)}</text>'
            f'<text x="{x}" y="{TY + (44 if i % 2 else 30)}" font-size="13" font-weight="600" text-anchor="middle" fill="{M}">{e(n)}</text></g>'
        )
    o.append(
        f'<text x="{TX - 26}" y="{TY + 66}" font-size="12" fill="{HL}">raportin tulokset · luku = lähteiden määrä</text>'
    )
    o.append("</svg>")
    return "".join(o)


def varsi_reuna() -> str:
    """Marginaalin köysi: sama asteikko pienenä; JS sytyttää sivun ``data-lahteet``-lähteet."""
    o = [
        '<div class="varsi-reuna" aria-hidden="true"><svg viewBox="0 0 64 640" preserveAspectRatio="xMidYMid meet">'
    ]
    o.append('<line class="koysi" x1="14" y1="24" x2="14" y2="600"/>')
    o.append('<line class="maa" x1="4" y1="540" x2="24" y2="540"/>')
    ty = -1e9
    for k, lv in sorted(LAHTEET.items(), key=lambda x: korkeus_y(x[1]["h"])):
        yy = korkeus_y(lv["h"], ylin=24, maa=540)
        ty = max(yy, ty + 12)  # tarrat erilleen, merkki pysyy oikealla korkeudella
        o.append(
            f'<g class="m" data-k="{k}"><line x1="9" y1="{yy:.1f}" x2="19" y2="{yy:.1f}"/>'
            f'<text x="23" y="{ty + 3.5:.1f}">{e(lv["lyhyt"])}</text></g>'
        )
    o.append("</svg></div>")
    return "".join(o)


# ---------- Kolme merkkiä: omat geometriset muodot, kukin kerran kirjasessa ----------


def merkki(nimi: str, vari: str = ilme.MUSTE) -> str:
    """Pieni merkki (leijona, tiikeri, karhu). Ei linkki, ei selitystä."""
    c = vari
    if nimi == "leijona":
        sade = "".join(
            f'<line x1="{12 + np.cos(a) * 7.4:.2f}" y1="{12 + np.sin(a) * 7.4:.2f}" x2="{12 + np.cos(a) * 11:.2f}" y2="{12 + np.sin(a) * 11:.2f}" stroke="{c}" stroke-width="1.6" stroke-linecap="round"/>'
            for a in np.linspace(0, 2 * np.pi, 12, endpoint=False)
        )
        sisus = f'<circle cx="12" cy="12" r="5.2" fill="{c}"/>' + sade
    elif nimi == "tiikeri":
        sisus = "".join(
            f'<line x1="{5 + d}" y1="21" x2="{13 + d}" y2="3" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
            for d in (-5, 1, 7)
        )
    else:
        sisus = (
            f'<rect x="3" y="7" width="18" height="15" rx="4" fill="{c}"/>'
            f'<circle cx="6.5" cy="5.5" r="2.6" fill="{c}"/><circle cx="17.5" cy="5.5" r="2.6" fill="{c}"/>'
        )
    return f'<span class="merkki {nimi}" aria-hidden="true"><svg viewBox="0 0 24 24">{sisus}</svg></span>'

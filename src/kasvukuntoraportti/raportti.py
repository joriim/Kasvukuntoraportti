"""Lohkoraportti interaktiivisena kirjasena: yksi itsenäinen HTML-tiedosto, avautuu ilman verkkoa.

Taitto: etukansi, aukeamat (värikenttä + yksi väite + yksi kuvio) rytmittämässä sisältösivuja,
Termit ja ilmiöt, takakansi. Selaus nuolilla, painikkeilla, pyyhkäisemällä tai sisällyksestä; tuloste
A4 sivu kerrallaan. Ulkoasu: ``ilme``; aukeamien kuviot: ``kirja``; selitykset: ``sanasto``.
Ks. docs/graafinen-ilme.md.
"""

from __future__ import annotations

import base64
import html
import io
from datetime import date

import numpy as np
import pandas as pd

from . import __version__, ilme, kirja, sanasto
from .ilme import LAHDEVARIT as VARIT
from .ilme import TAPAHTUMAVARIT, teema

# Pysyvyysluokat (analyysin vaihtelu.LUOKAT): koodit ovat datasopimusta, nimet raportin
LUOKAT = {0: "ei tietoa", 1: "vakaasti heikko", 2: "keskimääräinen", 3: "vakaasti hyvä", 4: "epävakaa"}
MIN_SATOVUODET = 3  # vaje ruudun omaan maksimiin vaatii vähintään näin monta satokarttavuotta


def _png(fig) -> str:
    import matplotlib.pyplot as plt

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=ilme.KUVAN_DPI, bbox_inches="tight")
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def aikasarja_kuva(optinen: pd.DataFrame, peltotyot: pd.DataFrame | None, otsikko: str) -> str | None:
    if optinen is None or not len(optinen):
        return None
    with teema():
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt

        d = optinen[optinen["kelvollinen_pct"] >= 80].copy()
        d["t"] = pd.to_datetime(d["pvm"])
        fig, ax = plt.subplots(figsize=(10, 3.6))
        for lahde, g in d.groupby("lahde"):
            vari = VARIT.get(lahde, ilme.HILJAINEN)
            ax.fill_between(g["t"], g["ndvi_p10"], g["ndvi_p90"], color=vari, alpha=0.10, lw=0)
            ax.plot(
                g["t"],
                g["ndvi_p50"],
                marker=ilme.LAHDEMERKIT.get(lahde, "o"),
                ms=4.5,
                mec=ilme.PINTA,
                mew=0.8,
                ls="--" if lahde == "hls2-l30" else "-",
                color=vari,
                label=ilme.LAHDENIMET.get(lahde, lahde),
            )
        if peltotyot is not None:
            n = 0
            for r in peltotyot.itertuples(index=False):
                if r.tyyppi == "talvipeite":
                    continue
                a, b = pd.to_datetime(r.alku), pd.to_datetime(r.loppu)
                vari = TAPAHTUMAVARIT.get(r.tyyppi, ilme.HILJAINEN)
                varma = r.luottamus >= 0.6
                ax.axvspan(a, b + pd.Timedelta(days=1), color=vari, alpha=0.28 if varma else 0.12, lw=0)
                ax.text(
                    a,
                    1.02 + 0.075 * (n % 2),
                    ilme.TAPAHTUMANIMET.get(r.tyyppi, r.tyyppi.replace("_", " ")) + ("" if varma else " ?"),
                    fontsize=7.5,
                    color=ilme.VAALEA["muste"],
                    va="bottom",
                    transform=ax.get_xaxis_transform(),
                )
                n += 1
        ax.set_ylim(0, 1)
        ax.set_ylabel("NDVI (mediaani ja väli P10–P90)")
        ax.set_title(otsikko, pad=30)
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(_kk_akseli(mdates))
        ax.grid(axis="x", visible=False)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=4)
        return _png(fig)


def kartta_kuva(
    arr: np.ndarray, otsikko: str, vmin=None, vmax=None, cmap="RdYlGn", luokat=None, transform=None, raja=None
) -> str:
    """``transform`` (a, b, c, d, e, f, EPSG:3067) ja ``raja`` (shapely) piirtävät lohkon rajan.
    ``luokat``: {arvo: (nimi, väri)} piirtää luokkakartan selitteineen."""
    with teema():
        import matplotlib.pyplot as plt
        from matplotlib.colors import BoundaryNorm, ListedColormap
        from matplotlib.patches import Patch

        cmap = ilme.asteikko(cmap)
        fig, ax = plt.subplots(figsize=(4.6, 4.3))
        ext = None
        if transform is not None:
            a, _, c, _, e, f = transform[:6]
            ext = [c, c + arr.shape[1] * a, f + arr.shape[0] * e, f]
        if luokat:
            varit = [v for _, (_, v) in sorted(luokat.items())]
            cm = ListedColormap(varit)
            ax.imshow(
                np.where(np.isfinite(arr), arr, np.nan),
                cmap=cm,
                norm=BoundaryNorm(np.arange(-0.5, len(varit) + 0.5), cm.N),
                interpolation="nearest",
                extent=ext,
            )
            ax.legend(
                handles=[Patch(fc=v, ec="#3a4150", lw=0.5, label=n) for _, (n, v) in sorted(luokat.items())],
                loc="upper center",
                bbox_to_anchor=(0.5, -0.02),
                ncol=2,
                handlelength=1.2,
                columnspacing=1.2,
            )
        else:
            im = ax.imshow(arr, cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest", extent=ext)
            cb = fig.colorbar(im, ax=ax, orientation="horizontal", fraction=0.04, pad=0.03, aspect=32)
            cb.outline.set_visible(False)
            cb.ax.tick_params(length=0)
        if raja is not None and ext is not None:
            for g in getattr(raja, "geoms", [raja]):
                x, y = g.exterior.xy
                ax.plot(x, y, color=ilme.VAALEA["muste"], lw=1.1)
        ax.set_title(otsikko, fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.grid(False)
        for s in ax.spines.values():
            s.set_visible(False)
        return _png(fig)


def vertailu_kuva(vert, vuosi: int) -> str | None:
    """Hajontakuva: kauden NDVI-integraali (taso) vs. CV huipulla (tasaisuus); kohde korostettuna."""
    df = vert.vertailulohkot
    kx, ky = f"cv_{vuosi}", f"integraali_{vuosi}"
    if kx not in df or ky not in df:
        return None
    d = df[[kx, ky]].apply(pd.to_numeric, errors="coerce").dropna()
    km = vert.kohde_mittarit.get(vuosi) or {}
    if len(d) < 3 or km.get("ndvi_integraali") is None or km.get("cv_huippu_pct") is None:
        return None
    with teema():
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(5.2, 3.9))
        ax.axvline(d[kx].median(), color="#3a4150", lw=0.8, ls="--")
        ax.axhline(d[ky].median(), color="#3a4150", lw=0.8, ls="--")
        ax.scatter(d[kx], d[ky], s=30, color="#4a505c", ec=ilme.PINTA, lw=0.8, label="vertailulohkot")
        x, y = km["cv_huippu_pct"], km["ndvi_integraali"]
        ax.scatter([x], [y], s=110, color=ilme.VIHREA, ec=ilme.PINTA, lw=1.2, zorder=3, label="tämä lohko")
        ax.annotate(
            "tämä lohko", (x, y), xytext=(8, 6), textcoords="offset points", fontsize=8, fontweight="bold"
        )
        ax.set_xlabel("Lohkon sisäinen vaihtelu huipulla, CV % (pienempi = tasaisempi)")
        ax.set_ylabel("NDVI-integraali touko–elokuu")
        ax.set_title(f"{vuosi}: taso ja tasaisuus vertailulohkoihin nähden")
        ax.text(
            0.99,
            0.02,
            "katkoviivat: vertailulohkojen mediaanit",
            transform=ax.transAxes,
            ha="right",
            fontsize=7,
            color=ilme.VAALEA["hiljainen"],
        )
        return _png(fig)


def vuo_kuva(t, vuosi: int) -> str:
    c = ilme.VUOVARIT
    with teema():
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt

        d = t.paivat
        x = pd.to_datetime(d["pvm"])
        fig, (a1, a2) = plt.subplots(
            2, 1, figsize=(9, 4.8), sharex=True, gridspec_kw={"height_ratios": [2, 1], "hspace": 0.12}
        )
        vira = (
            "gpp_vira_p05" in d
            and d["gpp_vira_p05"].notna().any()
            and t.summat.get("gpp_malli") == "vira2025"
        )
        if vira:
            a1.fill_between(
                x,
                d["gpp_vira_p05"],
                d["gpp_vira_p95"],
                color=c["gpp"],
                alpha=0.15,
                lw=0,
                label="GPP 90 % väli",
            )
        else:
            a1.fill_between(x, d["gpp"], color=c["gpp"], alpha=0.15, lw=0)
        a1.plot(x, d["gpp"], color=c["gpp"], label="GPP (sidonta)")
        turve = t.summat.get("maa") == "turvemaa"
        if turve:
            a1.plot(x, d["npp"], color=c["npp"], ls="--", label="NPP (kasvien nettotuotanto)")
        else:
            a1.plot(x, d["reco"], color=c["reco"], label="Reco (hengitys)")
            a1.plot(x, -d["nee"], color=c["nee"], lw=1.2, label="−NEE (nettosidonta)")
        a1.axhline(0, color="#3a4150", lw=0.8)
        a1.set_ylabel("g C/m²/vrk")
        a1.legend(ncol=4, loc="lower left", bbox_to_anchor=(0, 1.0), borderaxespad=0.2)
        nimi = "GPP: Vira ym. 2025" if t.summat.get("gpp_malli") == "vira2025" else "GPP: valontehokkuusmalli"
        lisa = "maaperän vuot eivät mukana (turvemaa)" if turve else "Reco kalibroitu"
        a1.set_title(f"Hiilivuot {vuosi} ({nimi}; {lisa})", pad=26)
        if turve:
            a2.plot(x, d["gpp"].cumsum(), color=c["gpp"], label="GPP")
            a2.plot(x, d["npp"].cumsum(), color=c["npp"], ls="--", label="NPP")
            a2.legend(loc="upper left")
            a2.set_ylabel("kertymä\ng C/m²")
        else:
            a2.plot(x, d["nee"].cumsum(), color=c["nee"])
            a2.axhline(0, color="#3a4150", lw=0.8)
            a2.set_ylabel("NEE kertymä\ng C/m²")
        a2.xaxis.set_major_locator(mdates.MonthLocator())
        a2.xaxis.set_major_formatter(_kk_akseli(mdates))
        for a in (a1, a2):
            a.grid(axis="x", visible=False)
        return _png(fig)


def _askeleet(paivat: list[str], n: int = 5) -> list[int]:
    """Kertymäkuvien hetket: kuukausien loput kauden sisällä ja viimeinen päivä, enintään ``n``."""
    pv = pd.to_datetime(pd.Series(paivat))
    i = [int(np.nonzero((pv.dt.month == m).to_numpy())[0][-1]) for m in sorted(set(pv.dt.month))]
    i = sorted(set(i) | {len(pv) - 1})
    if len(i) > n:
        i = [i[round(k * (len(i) - 1) / (n - 1))] for k in range(n)]
    return i


def kertyma_kuva(t, vuosi: int, raja=None) -> str | None:
    """Kertyvä GPP, IPAR ja vaje referenssimaksimiin ruuduittain: rivit suureittain, sarakkeet hetkittäin.
    Vaje = referenssimaksimi (koko lohkon viite) − GPP, eli kummankin käyttämättömän osan summa."""
    a = getattr(t, "aikasarja", None)
    if not a or "gpp_g_c" not in a or t.transform is None:
        return None
    rivit = [("GPP, g C/m²", a["gpp_g_c"], ilme.KARTTA_MAARA)]
    if "ipar_mj" in a:
        rivit.append(("IPAR, MJ/m²", a["ipar_mj"], "ipar"))
    if "gpp_pot_g_c" in a:
        rivit.append(("Vaje, g C/m²", np.maximum(a["gpp_pot_g_c"] - a["gpp_g_c"], 0), "vaje"))
    ii = _askeleet(a["paivat"])
    with teema():
        import matplotlib.pyplot as plt

        fig, axs = plt.subplots(
            len(rivit), len(ii), figsize=(1.75 * len(ii) + 0.9, 1.9 * len(rivit) + 0.4), squeeze=False
        )
        ta, _, tc, _, te, tf = t.transform[:6]
        h, w = rivit[0][1].shape[1:]
        ext = [tc, tc + w * ta, tf + h * te, tf]
        for r, (nimi, x, cm) in enumerate(rivit):
            hi = float(np.nanmax(x[ii[-1]])) if np.isfinite(x[ii[-1]]).any() else 1.0
            for c, i in enumerate(ii):
                ax = axs[r, c]
                im = ax.imshow(
                    x[i], cmap=ilme.asteikko(cm), vmin=0, vmax=hi, interpolation="nearest", extent=ext
                )
                if raja is not None:
                    for g in getattr(raja, "geoms", [raja]):
                        gx, gy = g.exterior.xy
                        ax.plot(gx, gy, color=ilme.VAALEA["muste"], lw=0.5)
                ax.set_xticks([])
                ax.set_yticks([])
                ax.grid(False)
                for sp in ax.spines.values():
                    sp.set_visible(False)
                if r == 0:
                    ax.set_title(_pvm(a["paivat"][i]), fontsize=9)
                if c == 0:
                    ax.set_ylabel(nimi, fontsize=9)
            cb = fig.colorbar(im, ax=list(axs[r]), fraction=0.02, pad=0.01)
            cb.outline.set_visible(False)
            cb.ax.tick_params(length=0, labelsize=7)
        fig.suptitle(f"Kertymät ruuduittain {vuosi}", x=0.01, ha="left", fontsize=10)
        return _png(fig)


def rue_kuva(t, vuosi: int) -> str | None:
    """Säteilyn käytön tehokkuus kasvukauden aikana: viikon GPP / viikon IPAR (g C/MJ), taustalla viikon IPAR."""
    d = getattr(t, "paivat", None)
    if d is None or not {"gpp", "ipar_mj", "pvm"} <= set(d.columns):
        return None
    v = (
        d.assign(t=pd.to_datetime(d["pvm"]))
        .set_index("t")[["gpp", "ipar_mj"]]
        .resample("W-SUN")
        .sum(min_count=4)
    )
    # harva tai kuivuva kasvusto: pieni IPAR tekee osamäärästä epävakaan, joten vain viikot,
    # joilla IPAR on vähintään 15 % kauden huippuviikosta
    v = v[v["ipar_mj"] >= 0.15 * v["ipar_mj"].max()]
    if len(v) < 3:
        return None
    rue = v["gpp"] / v["ipar_mj"]
    kausi = float(d["gpp"].sum() / d["ipar_mj"].sum()) if d["ipar_mj"].sum() > 0 else np.nan
    with teema():
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(9, 3.2))
        a2 = ax.twinx()
        a2.bar(
            v.index - pd.Timedelta(days=3), v["ipar_mj"], width=5.5, color=ilme.HILJAINEN, alpha=0.28, lw=0
        )
        a2.set_ylabel("IPAR, MJ/m²/vko", color=ilme.HILJAINEN)
        a2.grid(False)
        a2.tick_params(axis="y", colors=ilme.HILJAINEN)
        ax.set_zorder(a2.get_zorder() + 1)
        ax.patch.set_visible(False)
        x = v.index - pd.Timedelta(days=3)
        ax.plot(x, rue, color=ilme.VIHREA, marker="o", ms=3.5, label="RUE (GPP / IPAR)")
        if np.isfinite(kausi):
            ax.axhline(kausi, color=ilme.MUSTE, lw=0.8, ls="--")
            ax.text(
                x[0], kausi, f" kausi {kirja.fi(kausi, 2)} g C/MJ", va="bottom", fontsize=8, color=ilme.MUSTE
            )
        j = int(np.nanargmax(rue.to_numpy()))
        ax.annotate(
            f"huippu {kirja.fi(float(rue.iloc[j]), 2)}",
            (x[j], rue.iloc[j]),
            xytext=(6, 6),
            textcoords="offset points",
            fontsize=8,
            color=ilme.VIHREA,
        )
        ax.set_ylabel("RUE, g C/MJ IPAR")
        ax.set_ylim(bottom=0)
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(_kk_akseli(mdates))
        ax.grid(axis="x", visible=False)
        ax.set_title(f"Säteilyn käytön tehokkuus {vuosi} (viikoittain)", loc="left")
        return _png(fig)


def _pysyvyysluokat() -> dict:

    return {i: (LUOKAT[i], c) for i, c in zip(range(5), ilme.PYSYVYYSVARIT, strict=True)}


def paivakartat_kuva(vp, raja=None, sarakkeita: int = 5) -> str | None:
    """Pienet päiväkartat (suhteellinen NDVI, % lohkon mediaanista) samalla asteikolla."""
    kartat = sorted((vp.paivakartat or {}).items())
    if not kartat:
        return None
    with teema():
        import matplotlib.pyplot as plt

        n = len(kartat)
        rivit = -(-n // sarakkeita)
        fig, axs = plt.subplots(
            rivit, min(n, sarakkeita), figsize=(2.3 * min(n, sarakkeita), 2.4 * rivit), squeeze=False
        )
        ta, _, tc, _, te, tf = tuple(vp.transform)[:6]  # affiini tai (a, b, c, d, e, f)
        for ax in axs.flat:
            ax.axis("off")
        for ax, (pvm, k) in zip(axs.flat, kartat, strict=False):
            h, w = k.shape
            ext = (tc, tc + w * ta, tf + h * te, tf)
            im = ax.imshow(k, cmap=ilme.asteikko(ilme.KARTTA_SUHTEELLINEN), vmin=80, vmax=120, extent=ext)
            if raja is not None:
                for geom in getattr(raja, "geoms", [raja]):
                    x, y = geom.exterior.xy
                    ax.plot(x, y, color=ilme.VAALEA["muste"], lw=0.6)
            ax.set_title(_pvm(pvm), fontsize=8, loc="center", fontweight="normal")
        cb = fig.colorbar(im, ax=axs, shrink=0.6, label="% lohkon mediaanista")
        cb.outline.set_visible(False)
        return _png(fig)


def _pvm(p) -> str:
    """2025-06-12 -> 12.6.2025; muu jätetään ennalleen."""
    try:
        d = date.fromisoformat(str(p)[:10])
        return f"{d.day}.{d.month}.{d.year}"
    except ValueError:
        return str(p)


def _gpp_teksti(s: dict) -> str:
    if s.get("gpp_malli") == "vira2025":
        p05, p95 = s.get("gpp_vira_p05_p95") or (None, None)
        return (
            f"{s.get('gpp_g_c_m2'):.0f} g C/m² (90 % väli {p05:.0f}–{p95:.0f}; Vira ym. 2025, "
            f"CIre {s.get('cire_lahde')}); valontehokkuusmalli {s.get('gpp_lue_g_c_m2'):.0f}"
        )
    return f"{s.get('gpp_g_c_m2'):.0f} g C/m² (valontehokkuusmalli)"


def _kk_akseli(mdates):
    from matplotlib.ticker import FuncFormatter

    return FuncFormatter(lambda x, _: "{0.day}.{0.month}.".format(mdates.num2date(x)))


# Sanastolinkittäjä; ``kirjoita`` asettaa sen raportin ajaksi.
_linkita = lambda teksti: teksti  # noqa: E731

SARAKKEET = {
    "tyyppi": "Tyyppi",
    "alku": "Alku",
    "loppu": "Loppu",
    "luottamus": "Luottamus",
    "lahteet": "Lähteet",
    "alustava": "Alustava",
    "huom": "Huomautus",
    "alku_tarkka": "Alku (tarkennettu)",
    "loppu_tarkka": "Loppu (tarkennettu)",
    "tarkennus": "Tarkennus",
    "vuosi": "Vuosi",
    "kasvi": "Kasvi",
    "kasviryhmä": "Kasviryhmä",
    "esikasvi": "Esikasvi",
    "kasvukunto": "Kasvukunto",
    "tasaisuus": "Tasaisuus",
    "hoito": "Hoito",
    "vertailulohkoja": "Vertailulohkoja",
    "tunnus": "Tunnus",
    "ala_ha": "Ala (ha)",
    "etaisyys_km": "Etäisyys (km)",
    "maalaji": "Maalaji",
    "hasu": "HASU",
    "marka_pct": "Märkää (%)",
}


def _otsikko(sarake) -> str:
    s = str(sarake)
    if s in SARAKKEET:
        return SARAKKEET[s]
    for etu, nimi in (
        ("integraali_", "NDVI-integr. "),
        ("cv_", "CV % "),
        ("esikasvi_", "Esikasvi "),
        ("kasvi_", "Kasvi "),
    ):
        if s.startswith(etu):
            return nimi + s[len(etu) :]
    return s[:1].upper() + s[1:].replace("_", " ")


def _taulukko(df: pd.DataFrame | None, sarakkeet: list[str] | None = None) -> str:
    if df is None or not len(df):
        return "<p class='hiljainen'>Ei tietoja.</p>"
    d = (df[sarakkeet] if sarakkeet else df).rename(columns=_otsikko)
    return (
        "<div class='vierita'>"
        + d.to_html(index=False, border=0, classes="t", na_rep="–", escape=True)
        + "</div>"
    )


def _ind(x) -> str:
    return "–" if x is None else f"{x:.0f}"


def _avainarvot(rivit: list[tuple[str, str]]) -> str:
    return (
        "<dl class='tiedot'>"
        + "".join(f"<dt>{_linkita(html.escape(str(k)))}</dt><dd>{html.escape(str(v))}</dd>" for k, v in rivit)
        + "</dl>"
    )


def _kortti(sisalto: str) -> str:
    return f"<div class='kortti'>{sisalto}</div>"


def _selite(teksti: str) -> str:
    return f"<p class='selite'>{_linkita(html.escape(teksti))}</p>"


def _kuva(src: str | None, kuvateksti: str = "") -> str:
    if not src:
        return ""
    alt = html.escape(kuvateksti or "Kuva")
    kt = f"<figcaption>{_linkita(html.escape(kuvateksti))}</figcaption>" if kuvateksti else ""
    return f"<figure><img src='{src}' alt='{alt}'>{kt}</figure>"


def _kuvat(*kuvat: str) -> str:
    k = [x for x in kuvat if x]
    return "<div class='kuvat'>" + "".join(k) + "</div>" if k else ""


def _vuo_osio(t, vuosi: int, raja) -> str:
    s = t.summat
    o = [
        _kuva(
            vuo_kuva(t, vuosi),
            "Päivittäinen sidonta (GPP), hengitys (Reco) ja nettosidonta sekä kauden kertymä.",
        ),
    ]
    rivit = [
        ("Jakso", s.get("jakso")),
        ("Säteilyn lähde", s.get("sateilyn_lahde")),
        ("PAR, kausi", f"{s.get('par_mj_m2'):.0f} MJ/m²"),
        ("Kasvuston sieppaama PAR (IPAR)", f"{s.get('ipar_mj_m2'):.0f} MJ/m² ({s.get('ipar_osuus_pct')} %)"),
        ("GPP (bruttosidonta)", _gpp_teksti(s)),
        ("NPP (kasvien nettotuotanto ≈ 0,5 × GPP)", f"{s.get('npp_g_c_m2'):.0f} g C/m²"),
        (
            "Kasvuston sitoma energia",
            f"{s.get('sidottu_energia_mj_m2')} MJ/m² ({s.get('fotosynteesin_hyotysuhde_pct')} % IPAR:sta)",
        ),
    ]
    if s.get("maa") == "turvemaa":
        rivit.append(
            ("Reco ja NEE", "ei mallinneta turvemaalla (maaperän hengitys ja hiilitase rajattu pois)")
        )
    else:
        rivit += [
            ("Reco (ekosysteemin hengitys)", f"{s.get('reco_g_c_m2'):.0f} g C/m²"),
            ("NEE (nettovaihto)", f"{s.get('nee_g_c_m2'):.0f} g C/m² ≈ {s.get('nee_t_co2_ha')} t CO₂/ha"),
        ]
    rivit += [
        ("GPP-huippu", f"{s.get('gpp_huippu_g_c_m2_vrk')} g C/m²/vrk ({s.get('gpp_huippupaiva')})"),
    ]
    if s.get("gpp_solut_p10_p90"):
        p10, p90 = s["gpp_solut_p10_p90"]
        rivit.append(
            ("GPP 10 m soluissa P10–P90", f"{p10:.0f}–{p90:.0f} g C/m² (CV {s.get('gpp_solut_cv_pct')} %)")
        )
    if s.get("ipar_mj_m2"):
        rivit.append(
            (
                "Säteilyn käytön tehokkuus, kausi",
                f"{kirja.fi(s['gpp_g_c_m2'] / s['ipar_mj_m2'], 2)} g C/MJ IPAR (GPP / IPAR)",
            )
        )
    if s.get("rue_g_mj"):
        rivit.append(("RUE sadosta", f"{s['rue_g_mj']} g/MJ IPAR ({s.get('rue_oletukset')})"))
    o.append(_kortti(_avainarvot(rivit)))
    o.append(
        _kuva(
            rue_kuva(t, vuosi),
            "Viikon GPP jaettuna viikon kasvuston sieppaamalla säteilyllä (IPAR). Mukana viikot, joilla IPAR on "
            "vähintään 15 % huippuviikosta; harvassa kasvustossa osamäärä on epävakaa. Malliarvio, alustava.",
        )
    )
    o.append(
        _kuva(
            kertyma_kuva(t, vuosi, raja),
            "Kertynyt GPP, kasvuston sieppaama säteily (IPAR) ja vaje referenssimaksimiin ruuduittain. Vaje on "
            "se osa, joka jäi saamatta, jos ruutu olisi kasvanut viitetason mukaan samassa säässä "
            f"({html.escape(str(s.get('potentiaalin_viite', 'lohkon viite')))}). Asteikko kunkin rivin lopputilanteesta.",
        )
    )
    if t.kartat:
        o.append(
            _kuvat(
                *(
                    _kuva(
                        kartta_kuva(
                            t.kartat[k],
                            n,
                            cmap="vaje" if k.startswith("kayttamaton") else ilme.KARTTA_MAARA,
                            transform=t.transform,
                            raja=raja,
                        )
                    )
                    for k, n in (
                        (
                            "gpp_g_c",
                            f"GPP {vuosi} (g C/m²; erotuskyky {s.get('gpp_kartan_erotuskyky_m', 10)} m)",
                        ),
                        (
                            "ipar_mj",
                            f"IPAR {vuosi} (MJ/m²; erotuskyky {s.get('ipar_kartan_erotuskyky_m', 10)} m)",
                        ),
                        ("kayttamaton_sisainen_g_c", f"Vaje lohkon parhaisiin kohtiin {vuosi} (g C/m²)"),
                        ("kayttamaton_lohko_g_c", f"Vaje koko lohkon viitteeseen {vuosi} (g C/m²)"),
                    )
                    if k in t.kartat
                )
            )
        )
    o.append(
        "<p class='selite'>GPP: Vira ym. (2025) GPP = a·x/(b+x), x = CIre × PAR, parametrit viiden "
        "suomalaisen vuomittausaseman posteriorista (90 % väli sisältää lohkojen välisen vaihtelun); "
        "jos CIre-havaintoja ei ole, valontehokkuusmalli GPP = ε × fAPAR × PAR × f(T) × f(VPD). "
        "Reco = (R0 + k × GPP₁₄) × Q10^((T_maa − 10)/10), kalibroitu samojen asemien mitattuun "
        "hengitykseen (docs/validointi-vuo.md); NEE = Reco − GPP (negatiivinen = sidonta). NEE ei sisällä "
        "sadon mukana poistuvaa hiiltä eikä talven hengitystä. RUE lasketaan vain, jos sato annetaan.</p>"
    )
    o.append(
        "<h3>Maan alle menevä hiili (varaus)</h3>"
        + _kortti(
            _avainarvot(
                [
                    ("Juurissa", "ei laskettu"),
                    ("Juurieritteissä", "ei laskettu"),
                    ("Humifioitunut (kiinteä)", "ei laskettu"),
                    ("Palanut ilmakehään", "ei laskettu"),
                ]
            )
        )
        + "<p class='selite'>Varaus: kerrokset näkyvät 3D-näkymässä maan alla, kun syöte on. Juuret = "
        "maanpäällinen hiili / verso:juuri-suhde, juurieritteet = eriteosuus × juuret (Bolinder ym. 2007), kohtalo "
        "ICBM-tyyppisesti (Andrén ja Kätterer 1997). Tarvitaan satokartta tai kasvilajille kalibroidut kertoimet; "
        "nykyiset oletukset ovat nurmille.</p>"
    )
    return "".join(o)


def _lohko_osio(lohko: dict, osat: dict) -> str:
    return (
        _kortti(
            _avainarvot(
                [
                    ("Tunnus", lohko["tunnus"]),
                    ("Pinta-ala", f"{lohko['ala_ha']:.2f} ha"),
                    ("Leveys", f"{lohko.get('leveys_m', 0):.0f} m"),
                    ("Kasvi (viimeisin)", lohko.get("kasvi") or "–"),
                    ("Analysoidut vuodet", ", ".join(map(str, sorted(osat["vuodet"])))),
                ]
            )
        )
        + "<h3>Kasvihistoria</h3>"
        + _kortti(_taulukko(osat.get("historia")))
    )


def _vaihtelu_osio(v: dict, lohko: dict) -> str:
    vn = v.get("ndvi")
    if vn is None or not vn.paivat:
        return "<p class='hiljainen'>Ei kasvukauden selkeitä 10 m karttoja.</p>"
    t = vn.tunnusluvut
    raja = lohko.get("geometria")
    ndre = v.get("ndre") if v.get("ndre") is not None and v["ndre"].paivat else None
    o = [
        _selite(
            "Kartat näyttävät, missä lohkon osissa kasvu on ollut lohkon omaa keskitasoa parempaa tai "
            "heikompaa. Meripihka on mediaania heikompi, vihreä parempi; keskitaso on tumma. Suhteellinen kasvu ei kerro satotasoa."
        ),
        _kuvat(
            _kuva(
                kartta_kuva(
                    vn.keskiarvo,
                    "Suhteellinen kasvu, NDVI (% mediaanista; 10 m)",
                    85,
                    115,
                    cmap=ilme.KARTTA_SUHTEELLINEN,
                    transform=vn.transform,
                    raja=raja,
                ),
                "Selkeiden päivien keskiarvo.",
            ),
            _kuva(
                kartta_kuva(
                    ndre.keskiarvo,
                    "Suhteellinen kasvu, NDRE (%; 20 m)",
                    85,
                    115,
                    cmap=ilme.KARTTA_SUHTEELLINEN,
                    transform=ndre.transform,
                    raja=raja,
                ),
                "NDRE erottelee tiheän kasvuston eroja.",
            )
            if ndre is not None
            else "",
            _kuva(
                kartta_kuva(
                    vn.luokka.astype(float),
                    "Pysyvyysluokka (NDVI; 10 m)",
                    luokat=_pysyvyysluokat(),
                    transform=vn.transform,
                    raja=raja,
                ),
                "Toistuuko heikko tai hyvä kasvu samassa kohdassa.",
            ),
        ),
    ]
    rivit = [
        (
            "Kuvia (10 m)",
            f"{t['paivia']} ({', '.join(_pvm(p) for p in vn.paivat[:6])}{'…' if len(vn.paivat) > 6 else ''})",
        ),
        ("Variaatiokerroin", f"{t['cv_pct']} %"),
        ("Kvantiiliväli P90–P10", f"{t['kvantiilivali_pct']} %-yks."),
        ("Heikko alue (< 90 % mediaanista)", f"{t['heikko_osuus_pct']} %"),
        ("Laikuittaisuus (Moranin I)", t["morans_i"]),
        ("Päivien välinen hajonta (mediaani)", t["paivien_hajonta_mediaani"]),
    ]
    rivit += [(f"Pysyvyys: {k}", f"{x} %") for k, x in t["luokat_pct"].items()]
    if ndre is not None:
        tr = ndre.tunnusluvut
        rivit.append(
            ("NDRE: variaatiokerroin / heikko alue", f"{tr['cv_pct']} % / {tr['heikko_osuus_pct']} %")
        )
    o.append(_kortti(_avainarvot(rivit)))
    return "".join(o)


def _kausi_osio(y: dict, vuosi: int, lohko: dict) -> str:
    o = []
    opt_kuva = y.get("optinen")
    pl = y.get("planet")
    if pl is not None and len(pl.get("planet_havainnot", [])):
        opt_kuva = pd.concat([opt_kuva, pl["planet_havainnot"]], ignore_index=True)
    o.append(
        _kuva(
            aikasarja_kuva(opt_kuva, y.get("peltotyot"), f"Kasvuston vihreys {vuosi}"),
            "Viiva on lohkon NDVI-mediaani ja varjostus väli P10–P90. Väripalkit ovat tunnistettuja "
            "peltotöitä; kysymysmerkki tarkoittaa, että luottamus on alle 0,6.",
        )
    )
    o.append("<h3>Peltotyöt</h3>")
    pt = y.get("peltotyot")
    if pt is not None and len(pt):
        pt = pt.assign(
            alustava=pt["alustava"].map({True: "kyllä", False: "ei"}),
            tyyppi=pt["tyyppi"].map(lambda x: ilme.TAPAHTUMANIMET.get(x, str(x).replace("_", " "))),
            alku=pt["alku"].map(_pvm),
            loppu=pt["loppu"].map(_pvm),
        )
    o.append(
        _kortti(
            _taulukko(
                pt,
                ["tyyppi", "alku", "loppu", "luottamus", "lahteet", "alustava", "huom"]
                if pt is not None and len(pt)
                else None,
            )
        )
    )
    if pl is not None and pl.get("tarkennetut") is not None:
        tk = pl["tarkennetut"]
        tk = tk[tk["tarkennus"].notna()]
        n = int((pl["planet_havainnot"]["kelvollinen_pct"] >= 80).sum()) if len(pl["planet_havainnot"]) else 0
        o.append(
            f"<h3>PlanetScope-tarkennus</h3><p>{len(pl['planet_havainnot'])} kuvaa, joista {n} lohkon "
            "kohdalta selkeitä (3 m, harmonisoitu Sentinel-2:een).</p>"
        )
        o.append(
            _kortti(_taulukko(tk, ["tyyppi", "alku", "loppu", "alku_tarkka", "loppu_tarkka", "tarkennus"]))
            if len(tk)
            else "<p class='hiljainen'>Planet-havainnot eivät muuttaneet peltotöiden ajoitusta.</p>"
        )
    vp = (pl or {}).get("vaihtelu") if pl is not None else None
    if vp is not None:
        raja = lohko.get("geometria")
        o.append("<h3>Lohkon sisäinen vaihtelu PlanetScopella (3 m)</h3>")
        o.append(
            _kuvat(
                _kuva(
                    kartta_kuva(
                        vp.keskiarvo,
                        f"Suhteellinen NDVI {vuosi}, PlanetScope (%; 3 m)",
                        85,
                        115,
                        cmap=ilme.KARTTA_SUHTEELLINEN,
                        transform=vp.transform,
                        raja=raja,
                    )
                ),
                _kuva(
                    kartta_kuva(
                        vp.luokka.astype(float),
                        f"Pysyvyysluokka {vuosi} (PlanetScope; 3 m)",
                        luokat=_pysyvyysluokat(),
                        transform=vp.transform,
                        raja=raja,
                    )
                ),
            )
        )
        o.append(_kuva(paivakartat_kuva(vp, raja), "Selkeät PlanetScope-päivät samalla asteikolla."))
        tl = vp.tunnusluvut
        o.append(
            _kortti(
                _avainarvot(
                    [
                        (
                            "Selkeitä Planet-päiviä",
                            f"{tl.get('paivia')} ({', '.join(_pvm(p) for p in vp.paivat)})",
                        ),
                        ("Soluja (3 m)", tl.get("soluja")),
                        ("Variaatiokerroin", f"{tl.get('cv_pct')} %"),
                        ("Heikko alue (< 90 % mediaanista)", f"{tl.get('heikko_osuus_pct')} %"),
                        ("Moranin I", tl.get("morans_i")),
                    ]
                )
            )
        )
        o.append(
            "<p class='selite'>PlanetScope 3 m, harmonisoitu Sentinel-2:een; vain lohkon kohdalta selkeät "
            "päivät (UDM2). Kapealla lohkolla 3 m solukko erottaa reuna-alueet, ojanvarret ja ajourat, jotka "
            "10 m Sentinel-2-solussa sekoittuvat. Suhteellinen kartta, ei satotaso; kesä- ja heinäkuun niiton "
            "jälkeiset päivät kuvaavat sängen ja jälkikasvun vaihtelua.</p>"
        )
    if y.get("yhteenveto"):
        o.append(_kortti(_avainarvot(y["yhteenveto"])))
    return "".join(o)


def _maapera_osio(maa, lohko: dict) -> str:
    o = []
    raja = lohko.get("geometria")
    k2 = maa.kerrokset_2m
    o.append(
        _kuvat(
            _kuva(
                kartta_kuva(
                    k2["rinnevarjostus"],
                    "Rinnevarjostus (MML 2 m)",
                    0,
                    1,
                    cmap="gray",
                    transform=maa.transform_2m,
                    raja=raja,
                ),
                "Maaston muodot, ojat ja painanteet.",
            )
            if "rinnevarjostus" in k2
            else "",
            _kuva(
                kartta_kuva(
                    np.clip(k2["dtw4_m"], 0, 2),
                    "Märkyys, DTW 4 ha (m)",
                    0,
                    2,
                    cmap=ilme.KARTTA_MARKYYS,
                    transform=maa.transform_2m,
                    raja=raja,
                ),
                "Kirkas = märkä: pieni korkeusero veden kerääntymiskohtaan.",
            )
            if "dtw4_m" in k2
            else "",
            _kuva(
                kartta_kuva(
                    k2["korkeus_m"],
                    "Korkeus (m)",
                    cmap=ilme.KARTTA_KORKEUS,
                    transform=maa.transform_2m,
                    raja=raja,
                ),
                "Korkeus merenpinnasta.",
            )
            if "korkeus_m" in k2
            else "",
        )
    )
    ml = maa.maalajit or {}
    rivit = [
        (
            "Maalajit (GTK " + str(ml.get("mittakaava") or "?") + ")",
            ", ".join(f"{k} {v} %" for k, v in (ml.get("pintamaalajit") or {}).items()) or "–",
        )
    ]
    if ml.get("happamat_sulfaattimaat"):
        rivit.append(
            (
                "Happamat sulfaattimaat (todennäköisyys)",
                ", ".join(f"{k} {v} %" for k, v in ml["happamat_sulfaattimaat"].items()),
            )
        )
    tm = ml.get("omamaatu")
    if tm:
        op = tm.get("osuus_pct") or {}
        rivit.append(
            (
                "Turvetta, OmaMaatu-malli (alustava)",
                f"≥ 30 cm: {op.get(30)} % alasta, > 60 cm: {op.get(60)} % alasta; "
                f"turvepeltolohko: {'kyllä' if tm.get('turvepelto') else 'ei'} "
                f"(puiden yksimielisyys {(tm.get('yksimielisyys') or {}).get(30)})",
            )
        )
    nimet = {
        "korkeusero_m": "Korkeusero (P95–P5)",
        "kaltevuus_p50_deg": "Kaltevuus, mediaani (°)",
        "kaltevuus_p95_deg": "Kaltevuus, P95 (°)",
        "painanteita_pct": "Painanteita (TPI < −0,3 m) %",
        "marka_pct_dtw1": "Märkää (DTW 1 ha < 0,5 m) %",
        "marka_pct_dtw4": "Märkää (DTW 4 ha < 0,5 m) %",
        "dtw4_p50_m": "DTW 4 ha, mediaani (m)",
        "twi_p50": "TWI, mediaani",
        "eroosio_p50": "Eroosioherkkyys, mediaani",
        "eroosio_p95": "Eroosioherkkyys, P95",
    }
    rivit += [(nimet.get(k, k), v) for k, v in maa.tunnusluvut.items() if k in nimet]
    o.append(_kortti(_avainarvot(rivit)))
    if maa.selittajat:
        o.append("<h3>Vaihtelun ja talvituhon selittäjät (alustava)</h3>")
        o.append(_kortti(_taulukko(pd.DataFrame(maa.selittajat).fillna(""))))
    if maa.tulkinta:
        o.append(
            "<div class='huomio ohje'><ul class='lista'>"
            + "".join(f"<li>{html.escape(x)}</li>" for x in maa.tulkinta)
            + "</ul></div>"
        )
    o.append(
        "<p class='selite'>Korrelaatio ei osoita syy-yhteyttä. Märkyys: Luken DTW-indeksi "
        "(etäisyys laskennalliseen pohjaveden pintaan).</p>"
    )
    return "".join(o)


def _vertailu_osio(vert) -> str:
    o = []
    ind = vert.indeksit
    vv = ind.get("vertailuvuodet") or sorted(ind.get("vuodet", {}))
    jakso = f"{min(vv)}–{max(vv)}" if vv else ""
    an = ind.get("analysoidut") or {}
    av = ind.get("analysoidut_vuodet") or []
    ajakso = f"{min(av)}–{max(av)}" if av else ""
    rivit = []
    for nimi, avain in (
        ("Kasvukuntoindeksi", "kasvukuntoindeksi"),
        ("Tasaisuusindeksi", "tasaisuusindeksi"),
        ("Hoitoindeksi (märkyys huomioitu)", "hoitoindeksi"),
    ):
        arvo = f"{_ind(ind.get(avain))} ({jakso})"
        if an and set(av) != set(vv):
            arvo += f"; analysoidut vuodet {ajakso}: {_ind(an.get(avain))}"
        rivit.append((f"{nimi} (0–100)", arvo))
    tt = ind.get("toistuvuus")
    if tt:
        rivit.append(
            (
                "Kasvukuntoindeksin vaihtelu vuosittain",
                f"{tt['kki_min']:.0f}–{tt['kki_max']:.0f} (hajonta {tt['kki_hajonta']:.0f}); "
                f"keskitason yläpuolella {tt['vuosia_yli_keskitason']}/{tt['vuosia']} vuotena",
            )
        )
    rivit += [
        ("Kasviryhmä (viimeisin)", vert.kasviryhma),
        ("Vertailulohkoja yhteensä", len(vert.vertailulohkot)),
    ]
    o.append(_kortti(_avainarvot(rivit)))
    o.append(
        _selite(
            "Indeksit ovat persentiilejä: 50 = vertailulohkojen keskitaso, 80 = parempi "
            "kuin 80 % vertailulohkoista. Kasvukunto = kauden NDVI-integraali; tasaisuus = lohkon sisäinen "
            "vaihtelu kasvun huipulla (pienempi parempi); hoito = kasvukunto, kun märkien alueiden (DTW) osuus "
            "on vakioitu. Vuosittain mukana vain lohkot, joilla oli sama kasviryhmä kuin kohteella; "
            "samankaltaisuudessa myös viljelykierto (esikasvi ja nurmivuodet kolmelta edeltävältä vuodelta). "
            "Vertailu kattaa kaikki lohkorekisterin vuodet, vaikka kuva-analyysi tehdään valituille vuosille."
        )
    )
    vrivit = [
        {
            "vuosi": v,
            "kasviryhmä": x.get("kasviryhma"),
            "esikasvi": x.get("esikasvi"),
            "kasvukunto": x.get("kasvukuntoindeksi"),
            "tasaisuus": x.get("tasaisuusindeksi"),
            "hoito": x.get("hoitoindeksi"),
            "vertailulohkoja": x.get("vertailulohkoja_tiedoin"),
            "NDVI-integraali": (vert.kohde_mittarit.get(v) or {}).get("ndvi_integraali"),
            "CV huipulla %": (vert.kohde_mittarit.get(v) or {}).get("cv_huippu_pct"),
        }
        for v, x in sorted(ind.get("vuodet", {}).items())
    ]
    o.append("<h3>Indeksit vuosittain</h3>" + _kortti(_taulukko(pd.DataFrame(vrivit))))
    o.append(_kuvat(*(_kuva(vertailu_kuva(vert, v)) for v in sorted(ind.get("vuodet", {})))))
    o.append("<h3>Vertailulohkojen tasapaino</h3>")
    o.append(_kortti(_taulukko(pd.DataFrame(vert.tasapaino))))
    o.append("<h3>Vertailulohkot</h3>")
    vl = vert.vertailulohkot
    sar = [
        c
        for c in vl.columns
        if c in ("tunnus", "ala_ha", "etaisyys_km", "maalaji", "hasu", "marka_pct")
        or c.startswith(("kasvi_", "esikasvi_", "integraali_", "cv_"))
    ]
    o.append(_kortti(_taulukko(vl[sar].round(2))))
    return "".join(o)


def _talvi_osio(t: dict) -> str:
    vp = t["viherpeite"]
    rivit = [
        ("Viherpeite (säilytysjakso 31.10.–31.3.)", vp.arvio),
        ("Lumi", f"tulo {vp.lumen_tulo or '?'}, lähtö {vp.lumen_lahto or '?'}"),
    ]
    rivit += [("Huom", h) for h in vp.huom]
    ts = t.get("saa") or {}
    if ts.get("pakkassumma") is not None:
        rivit += [
            (
                "Talven sää (FMI)",
                f"pakkassumma {ts['pakkassumma']} °Cvrk, lumipeite {ts['lumipaivia']} vrk, "
                f"lunta enintään {ts['lumi_max_cm']} cm ({ts['lumen_tulo']}–{ts['lumen_lahto']})",
            )
        ]
        rivit += [("Talvituhoriski (alustava)", r) for r in ts.get("riskit", [])]
    tal = t.get("talvehtiminen")
    if tal is not None:
        rivit += [
            (
                "Talvehtiminen",
                f"{tal.luokka}"
                + (f", tuhoala {tal.tuhoala_pct:.0f} %" if tal.tuhoala_pct is not None else ""),
            ),
            ("Syksy", f"kasvipeittävyys {tal.syksy_peitto_pct} % (NDVI {tal.syksy_ndvi})"),
            (
                "Kevät",
                f"{tal.kevat_eka_pvm} → {tal.kevat_vertailu_pvm}: kasvipeittävyys {tal.kevat_peitto_pct} %",
            ),
        ]
        if tal.uusintakylvo:
            rivit.append(("Kevät", tal.uusintakylvo))
        rivit += [("Huom", h) for h in tal.huom]
    return _kortti(_avainarvot(rivit)) + _kuvat(
        _kuva(t.get("tuhokuva"), "Kohdat, joissa vihreää kasvustoa ei keväällä havaittu.")
    )


# ---------- Kirjanen: kannet ja aukeamat ----------


def _kansi(lohko: dict, osat: dict, ala: str) -> str:
    e = html.escape
    vn = (osat.get("vaihtelu") or {}).get("ndvi")
    kuvio = ""
    if vn is not None and vn.paivat:
        # Helle yöllä D2: lohkon pistekuva, väri lohkon omasta vaihteluvälistä (P5–P95)
        k = np.asarray(vn.keskiarvo, float)
        ok = k[np.isfinite(k)]
        lo, hi = (float(np.percentile(ok, 5)), float(np.percentile(ok, 95))) if len(ok) else (85.0, 115.0)
        kuvio = kirja.pistekartta(
            k, asteikko="helle", vmin=lo, vmax=max(hi, lo + 1), enintaan=1400, otsikko="Lohkon kasvu pisteinä"
        )
    tanaan = date.today()
    return (
        '<section class="sivu kansi helle" id="kansi" data-nimi="Kansi">'
        '<div class="k k1"></div><div class="k k2"></div><div class="k k3"></div>'
        '<div class="paalla"><div><div class="tunniste">Kasvukuntoraportti · peltolohko</div>'
        f"<h1>Lohko {e(lohko['tunnus'])}</h1><p class='ala'>{e(ala)}</p></div>"
        f"{kuvio}"
        f"<div><div style='text-align:right'>{kirja.merkki('leijona')}</div><button class='avaa' type='button' data-seuraava>Avaa raportti →</button>"
        f"<p class='tiedot' style='margin:14px 0 0'>Laadittu {tanaan.day}.{tanaan.month}.{tanaan.year} · kasvukunto {e(osat.get('versio') or __version__)} · "
        "arvio satelliittiaineistosta"
        + (" · pisteet: kasvu lohkon sisällä, pinkki heikompi, sininen parempi" if kuvio else "")
        + "</p></div>"
        "</div></section>"
    )


def _takakansi(osat: dict) -> str:
    e = html.escape
    lahteet = "".join(f"<li>{e(x)}</li>" for x in osat.get("lahteet", []))
    lahteet += f"<li>… ja muut{kirja.merkki('karhu')}</li>"
    huomiot = "".join(f"<li>{e(x)}</li>" for x in osat.get("huomiot") or [])
    return (
        '<section class="sivu kansi taka" id="lahteet" data-nimi="Tietolähteet">'
        '<div class="k k1"></div><div class="k k2"></div><div class="k k3"></div>'
        '<div class="paalla"><div><div class="tunniste">Tietolähteet ja menetelmät</div>'
        f"<ul class='tiedot' style='margin-top:14px'>{lahteet}</ul>"
        + (
            f"<div class='tunniste' style='margin-top:22px'>Huomiot</div><ul class='tiedot' style='margin-top:10px'>{huomiot}</ul>"
            if huomiot
            else ""
        )
        + "</div>"
        f"<p class='tiedot'>Kasvukuntoraportti · lohko {e(osat['lohko']['tunnus'])} · kasvukunto {e(osat.get('versio') or __version__)}. "
        "Satelliittiaineistot: NASA HLS, ESA Copernicus Sentinel, Planet. Lohkorajat © Ruokavirasto (CC BY 4.0). "
        "Fontit: League Spartan ja Jost (SIL OFL 1.1).</p>"
        "</div></section>"
    )


def _silmays(osat: dict) -> str:
    """Toinen sivu: lohko yhdellä silmäyksellä."""
    lohko = osat["lohko"]
    vert = osat.get("vertailu")
    vn = (osat.get("vaihtelu") or {}).get("ndvi")
    rivit = [(kirja.fi(lohko["ala_ha"], 2), "ha", "pinta-ala")]
    if vn is not None and vn.paivat:
        t = vn.tunnusluvut
        rivit += [
            (kirja.fi(t["cv_pct"]), "%", "vaihtelu lohkon sisällä (CV)"),
            (kirja.fi(t["heikko_osuus_pct"]), "%", "alasta kasvaa heikosti"),
        ]
    rivit.append((str(len(osat["vuodet"])), "", "kautta analysoitu"))
    ohje = (
        "<div class='huomio ohje'><strong>Näin luet raporttia.</strong> Kartta näyttää erot lohkon sisällä. "
        "Se ei näytä satoa. Indeksi vertaa lohkoa samankaltaisiin lähilohkoihin samana vuonna. "
        "Alustava sääntö on suuntaa antava. Sanat: <a href='#ilmiot'>Termit ja ilmiöt</a>.</div>"
    )
    kki = vert.indeksit.get("kasvukuntoindeksi") if vert is not None else None
    if kki is not None:
        ind = vert.indeksit
        ruudut = "".join(
            f"<figure>{kirja.sataruudukko(ind[a], v, n)}<figcaption><b>{kirja.fi(ind[a], 0)}</b>{_linkita(html.escape(n))}</figcaption></figure>"
            for n, a, v in (
                ("Kasvukuntoindeksi", "kasvukuntoindeksi", ilme.VIHREA),
                ("Tasaisuusindeksi", "tasaisuusindeksi", ilme.MUSTE),
                ("Hoitoindeksi", "hoitoindeksi", ilme.VIOLETTI),
            )
            if ind.get(a) is not None
        )
        iso = f"<b>{kirja.fi(kki, 0)}</b>Parempi kuin {kirja.fi(kki, 0)} lohkoa sadasta."
        alla = "Kasvu verrattuna samankaltaisiin lähilohkoihin. 50 on keskitaso."
        kuvio = f"<div class='sadat'>{ruudut}</div>{kirja.luvut(rivit)}{ohje}"
    else:
        iso = f"<b>{kirja.fi(lohko['ala_ha'], 1)}</b>hehtaaria."
        alla = html.escape(lohko.get("kasvi") or "Vertailulohkoja ei haettu, joten indeksejä ei ole.")
        kuvio = kirja.luvut(rivit) + ohje
    return kirja.aukeama("silmays", "Yhdellä silmäyksellä", "Yhdellä silmäyksellä", iso, alla, kuvio)


def _vaihtelu_aukeama(v: dict) -> str | None:
    vn = v.get("ndvi")
    if vn is None or not vn.paivat:
        return None
    t = vn.tunnusluvut
    lu = t["luokat_pct"]
    nimet = _pysyvyysluokat()
    palkki = kirja.osuuspalkki([(nimet[i][0], lu.get(nimet[i][0], 0), nimet[i][1]) for i in (1, 2, 3, 4)])
    kuvio = (
        kirja.pistekartta(vn.keskiarvo, otsikko="Suhteellinen kasvu pisteinä")
        + kirja.asteikkoselite("signaali", "85 % heikompi", "parempi 115 %")
        + f"<p class='kt'>Yksi piste on yksi mittaussolu. Väri: kasvu suhteessa lohkon mediaaniin, {t['paivia']} selkeän päivän keskiarvo. Vie osoitin pisteen päälle.</p>"
        + "<h3>Toistuuko sama kuvio?</h3>"
        + palkki
    )
    return kirja.aukeama(
        "vaihtelu",
        "Kasvuvaihtelu",
        "Kasvuvaihtelu lohkon sisällä",
        f"<b>{kirja.fi(t['heikko_osuus_pct'])} %</b>lohkosta kasvaa heikosti.",
        f"Heikko = alle 90 % lohkon mediaanista. Vaihtelu (CV) {kirja.fi(t['cv_pct'])} %. Kartta ei näytä satoa.",
        kuvio,
        "petrooli",
    )


def _kausi_aukeama(y: dict, vuosi: int) -> str | None:
    opt = y.get("optinen")
    pl = y.get("planet")
    if pl is not None and len(pl.get("planet_havainnot", [])):
        opt = pd.concat([opt, pl["planet_havainnot"]], ignore_index=True)
    nauha, tiedot = kirja.kausinauha(opt, y.get("peltotyot"), vuosi)
    if not nauha:
        return None
    pt = y.get("peltotyot")
    varmat = (
        pt[(pt["luottamus"] >= 0.6) & (pt["tyyppi"] != "talvipeite")] if pt is not None and len(pt) else None
    )
    if varmat is not None and len(varmat):
        maarat = varmat["tyyppi"].value_counts()
        tyyppi, n = maarat.index[0], int(maarat.iloc[0])
        monikko = {"niitto": "niittoa", "sadonkorjuu": "sadonkorjuuta", "kynto_tai_muokkaus": "muokkausta"}
        yksikko = {"niitto": "niitto", "sadonkorjuu": "sadonkorjuu", "kynto_tai_muokkaus": "muokkaus"}
        sana = (yksikko if n == 1 else monikko).get(tyyppi, ilme.TAPAHTUMANIMET.get(tyyppi, tyyppi))
        iso = f"<b>{n}</b>{html.escape(sana)} tunnistettu."
    else:
        iso = f"<b>{tiedot.get('kuvia', 0)}</b>selkeää kuvaa."
    alla = (
        f"Vihrein {kirja.pvm(tiedot['huippu_pvm'])[:-4]} (NDVI {kirja.fi(tiedot['huippu_ndvi'], 2)}). {tiedot.get('kuvia', 0)} selkeää kuvauspäivää."
        if tiedot.get("huippu_pvm")
        else ""
    )
    kuvio = (
        f"<h3>Kasvukausi {vuosi} viikoittain</h3>{nauha}"
        + kirja.asteikkoselite("maara", "paljas maa", "tiheä kasvusto")
        + "<p class='kt'>Viikon kirkkaus on lohkon NDVI. Valkoinen kehys on tunnistettu peltotyö; katkoviiva ja kysymysmerkki = epävarma (luottamus alle 0,6). Tyhjä viikko: ei selkeää kuvaa.</p>"
    )
    kasvi = y.get("kasvi")
    return kirja.aukeama(
        f"kausi-{vuosi}",
        f"Kausi {vuosi}",
        f"Kausi {vuosi}" + (f" · {kasvi}" if kasvi else ""),
        iso,
        html.escape(alla),
        kuvio,
        "meripihka",
    )


def _hiili_aukeama(t, vuosi: int) -> str:
    s = t.summat
    gpp = s.get("gpp_g_c_m2") or 0
    if s.get("maa") == "turvemaa":
        kuvio = kirja.pino(
            [
                ("Sidonta (GPP)", gpp, "g C/m²", ilme.VIHREA),
                ("Kasvien nettotuotanto (NPP)", s.get("npp_g_c_m2") or 0, "g C/m²", "#9ee6b6"),
            ]
        )
        alla = "Turvemaalla maaperän hengitystä ja hiilitasetta ei mallinneta."
    else:
        reco = s.get("reco_g_c_m2") or 0
        kuvio = kirja.pino(
            [
                ("Sidonta (GPP)", gpp, "g C/m²", ilme.VIHREA),
                ("Hengitys (Reco)", reco, "g C/m²", ilme.MERIPIHKA),
            ]
        )
        nee = s.get("nee_g_c_m2")
        alla = (
            f"Hengitys vei {kirja.fi(reco, 0)}. Nettovaihto {kirja.fi(nee, 0)} g C/m²: virhe enintään ±400, lue suuntana. "
            "Sadon mukana poistuva hiili ja talvi puuttuvat."
        )
    kuvio += f"<p class='kt'>Kentän korkeus on verrannollinen hiilimäärään. Jakso {html.escape(str(s.get('jakso')))}. Alustava malli.</p>"
    return kirja.aukeama(
        f"hiili-{vuosi}",
        f"Hiili {vuosi}",
        f"Hiili {vuosi}",
        f"<b>{kirja.fi(gpp, 0)}</b>g hiiltä sitoutui neliömetrille.",
        alla,
        kuvio,
        "",
    )


def _maapera_aukeama(maa) -> str | None:
    ml = (maa.maalajit or {}).get("pintamaalajit") or {}
    if not ml:
        return None
    varit = [ilme.MERIPIHKA, "#c3842a", "#8f6630", "#5e4a2e", "#3a3329"]  # osuusjärjestyksessä
    lajit = sorted(ml.items(), key=lambda x: -x[1])
    palkki = kirja.osuuspalkki([(n, p, varit[min(i, len(varit) - 1)]) for i, (n, p) in enumerate(lajit)])
    tl = maa.tunnusluvut
    marka = tl.get("marka_pct_dtw4")
    rivit = []
    if marka is not None:
        rivit.append((kirja.fi(marka), "%", "alasta märkää (DTW alle 0,5 m)"))
    if tl.get("korkeusero_m") is not None:
        rivit.append((kirja.fi(tl["korkeusero_m"]), "m", "korkeusero"))
    if tl.get("painanteita_pct") is not None:
        rivit.append((kirja.fi(tl["painanteita_pct"]), "%", "painanteita"))
    kuvio = "<h3>Pintamaa</h3>" + palkki + (kirja.luvut(rivit) if rivit else "")
    if marka is not None:
        kuvio += "<h3>Märkä ala</h3>" + kirja.osuuspalkki(
            [("märkää", marka, ilme.SYAANI), ("kuivempaa", 100 - marka, ilme.TYHJA)]
        )
    nimi, pct = lajit[0]
    return kirja.aukeama(
        "maapera",
        "Maaperä ja maasto",
        "Maaperä, maasto ja vesi",
        f"<b>{kirja.fi(pct, 0)} %</b>{html.escape(nimi)}a.",
        ("Märkää " + kirja.fi(marka) + " % alasta. " if marka is not None else "")
        + "Maalaji: GTK:n kartta. Märkyys: Luken laskennallinen indeksi.",
        kuvio,
        "petrooli",
    )


def _vertailu_aukeama(vert) -> str | None:
    ind = vert.indeksit
    vuodet = {v: x.get("kasvukuntoindeksi") for v, x in (ind.get("vuodet") or {}).items()}
    jana = kirja.vuosijana(vuodet, "Kasvukuntoindeksi vuosittain")
    if not jana:
        return None
    arvot = [x for x in vuodet.values() if x is not None]
    yli = sum(1 for x in arvot if x > 50)
    return kirja.aukeama(
        "vertailu",
        "Vertailu ja indeksit",
        "Vertailulohkot ja indeksit",
        f"<b>{yli} / {len(arvot)}</b>vuotena keskitason yläpuolella.",
        f"{len(vert.vertailulohkot)} vertailulohkoa, kasviryhmä {html.escape(str(vert.kasviryhma))}. Sama vuosi, joten sää on sama kaikilla.",
        f"<h3>Kasvukuntoindeksi vuosittain</h3>{jana}<p class='kt'>0–100. Vihreä: keskitason yläpuolella. Meripihka: alapuolella.</p>",
    )


def _talvi_aukeama(t: dict) -> str | None:
    tal = t.get("talvehtiminen")
    if tal is None or tal.tuhoala_pct is None:
        return None
    tuho = float(tal.tuhoala_pct)
    kuvio = (
        "<div class='sadat'><figure>"
        + kirja.sataruudukko(100 - tuho, ilme.VIHREA, "Kasvustoa keväällä")
        + f"<figcaption><b>{kirja.fi(100 - tuho, 0)} %</b>alasta vihersi keväällä</figcaption></figure></div>"
        + f"<p class='kt'>Sata pistettä = koko lohko. Tyhjä piste: ei vihreää kasvustoa keväällä. Kevään vertailukuva {kirja.pvm(tal.kevat_vertailu_pvm)}. Luokkarajat alustavia.</p>"
    )
    return kirja.aukeama(
        f"talvi-{t['talvi']}",
        f"Talvi {t['talvi']}–{t['talvi'] + 1}",
        f"Talvi {t['talvi']}–{t['talvi'] + 1}",
        f"<b>{kirja.fi(tuho, 0)} %</b>kasvustosta tuhoutui.",
        f"Talvehtiminen: {html.escape(str(tal.luokka))}.",
        kuvio,
        "tumma",
    )


# ---------- Pavunvarsi: mitkä lähteet tässä raportissa on ja millä sivulla ----------


def _kaytetyt_lahteet(osat: dict) -> dict:
    """Lähdeavaimet (``kirja.LAHTEET``) vuosittain ja koko raportille."""
    vuosittain: dict[int, set] = {}
    for vuosi, y in osat["vuodet"].items():
        k = set()
        opt = y.get("optinen")
        if opt is not None and len(opt):
            lahteet = set(opt["lahde"])
            if "hls2-s30" in lahteet or "hls2-l30" in lahteet:
                k |= {"hls", "s2"}
            if "hls2-l30" in lahteet:
                k.add("ls")
            if "sentinel-2-l2a" in lahteet:
                k.add("s2")
        if y.get("planet") is not None:
            k.add("pl")
        pt = y.get("peltotyot")
        if pt is not None and len(pt) and pt["lahteet"].astype(str).str.contains("S1").any():
            k.add("s1")
        vuo = y.get("vuo")
        if vuo is not None:
            k.add("era" if "ERA5" in str(vuo.summat.get("sateilyn_lahde", "")) else "fmi")
        vuosittain[vuosi] = k
    kaikki = set().union(*vuosittain.values()) if vuosittain else set()
    kaikki.add("lpis")
    maa = osat.get("maapera")
    if maa is not None:
        if maa.maalajit:
            kaikki.add("gtk")
        if (maa.maalajit or {}).get("omamaatu"):
            kaikki.add("turve")
        if "korkeus_m" in maa.kerrokset_2m or "rinnevarjostus" in maa.kerrokset_2m:
            kaikki.add("mml")
        if "dtw4_m" in maa.kerrokset_2m or maa.tunnusluvut.get("marka_pct_dtw4") is not None:
            kaikki.add("dtw")
    if any((t.get("saa") or {}).get("pakkassumma") is not None for t in osat.get("talvi") or []):
        kaikki.add("fmi")
    return {"vuodet": vuosittain, "kaikki": kaikki}


def _sivun_lahteet(ankkuri: str, kaytossa: dict) -> set:
    K = kaytossa["kaikki"]
    import re

    m = re.match(r"(kausi|hiili)-(\d{4})", ankkuri)
    if m:
        v = kaytossa["vuodet"].get(int(m.group(2)), set())
        return (v - {"era", "fmi"}) if m.group(1) == "kausi" else ({"s2"} | (v & {"era", "fmi"}))
    for alku, ll in (
        ("pavunvarsi", K),
        ("lahteet", K),
        ("silmays", {"s2", "lpis", "gtk", "dtw"}),
        ("lohko", {"lpis"}),
        ("vaihtelu", {"s2", "pl"}),
        ("maapera", {"gtk", "mml", "dtw", "turve"}),
        ("vertailu", {"s2", "lpis", "gtk", "dtw"}),
        ("talvi", {"hls", "s2", "fmi"}),
    ):
        if ankkuri.startswith(alku):
            return set(ll) & K
    return set()


def _merkitse_lahteet(sivu: str, kaytossa: dict) -> str:
    import re

    m = re.match(r'<section class="sivu [a-z ]+" id="([^"]+)"', sivu)
    if not m:
        return sivu
    ll = " ".join(sorted(_sivun_lahteet(m.group(1), kaytossa)))
    sivu = re.sub(r' data-lahteet="[^"]*"', "", sivu, count=1)
    return sivu.replace(f'id="{m.group(1)}"', f'id="{m.group(1)}" data-lahteet="{ll}"', 1)


def _pavunvarsi_sivu(osat: dict, kaytossa: dict) -> str:
    K = kaytossa["kaikki"]
    tulokset = []
    if any(y.get("peltotyot") is not None and len(y["peltotyot"]) for y in osat["vuodet"].values()):
        tulokset.append(("pt", "Peltotyöt", ["hls", "s2", "s1", "pl"]))
    if osat.get("vaihtelu"):
        tulokset.append(("va", "Kasvuvaihtelu", ["s2", "pl"]))
    if any(y.get("vuo") is not None for y in osat["vuodet"].values()):
        tulokset.append(("hi", "Hiili", ["s2", "era", "fmi"]))
    if osat.get("vertailu") is not None:
        tulokset.append(("ve", "Vertailu", ["s2", "lpis", "gtk", "dtw"]))
    if osat.get("maapera") is not None:
        tulokset.append(("ma", "Maaperä", ["gtk", "turve", "mml", "dtw"]))
    if osat.get("talvi"):
        tulokset.append(("ta", "Talvi", ["hls", "s2", "fmi"]))
    tulokset = [(t, n, [k for k in ll if k in K]) for t, n, ll in tulokset]
    korkein = max((kirja.LAHTEET[k]["h"] for k in K if kirja.LAHTEET[k]["h"] < 2e7), default=0)
    kuvio = kirja.pavunvarsi(sorted(K), tulokset)
    return (
        '<section class="sivu varsi" id="pavunvarsi" data-nimi="Mistä tieto tulee"><div class="sisus">'
        "<div class='tunniste'>Pavunvarsi</div>"
        f"<h2>{len(K)} lähdettä maan alta {kirja.fi(korkein / 1000, 0)} kilometriin</h2>"
        "<ul class='ohjeet'><li>pallon koko = pikselin koko</li><li>katkoviiva = johdettu tai yhdenmukaistettu</li>"
        "<li>kaari = käytetään tuloksessa</li><li>≈ asteikko on katkaistu</li></ul>"
        f"<div class='varsikuva'>{kuvio}</div>"
        "<p class='selite'>Kaikki kuvaavat satelliitit ovat 500–800 km korkeudella, joten se kaista on venytetty. "
        "Laserkeilaus tehdään lentokoneesta; korkeus on suuntaa antava. ERA5-Land on uusanalyysi, ja se on "
        "piirretty ilmakehän kohdalle. Vie osoitin tuloksen tai lähteen päälle. Sama köysi kulkee leveällä "
        "näytöllä jokaisen sivun vasemmassa reunassa, ja siinä syttyvät sivun lähteet.</p></div></section>"
    )


def _sato_varaus(osat: dict) -> str:
    """Satosivu ilman analyysin satoosiota: varauskortti siitä, mitä kukin luku vaatii."""
    sal = (
        "Salaojakartta on mukana: ruudut ryhmitellään myös ojitusluokan mukaan."
        if osat.get("salaojat") is not None
        else "Salaojakartta: varaus. Kun tilan salaojakartta annetaan (viivat tai ojitetut alueet, asennusvuosi, "
        "ojaväli, syvyys, kunto), ruudut ryhmitellään myös ojitusluokan mukaan, ja märkyysluokka korjataan "
        "ojitetuilla alueilla: Luken DTW on maastomalli eikä tunne salaojia."
    )
    return (
        _kortti(
            _avainarvot(
                [
                    ("Satotaso ruuduittain", "varaus: satokartta puuttuu"),
                    ("Vaje lohkon parhaisiin ruutuihin", "varaus"),
                    ("Vaje ruudun omaan maksimiin", f"varaus: vähintään {MIN_SATOVUODET} satokarttavuotta"),
                    ("Vaje samankaltaisiin ruutuihin", "varaus: satokartta + maasto ja märkyys"),
                    ("Maahan päätynyt hiili sadosta", "varaus: satokartta + kasvin kertoimet"),
                ]
            )
        )
        + "<p class='selite'>Satokartta tuodaan satokartoituksen tietueista (x, y, sato, kosteus) tai "
        "Beanstalk Growth Space -näkymän puintidatasta 10 m ruudukkoon. Ilman sitä lohkon sisäinen vaihtelu "
        "on satelliittikuvista suhteellisena, ei satotasona. " + html.escape(sal) + "</p>"
    )


def kirjoita(polku, osat: dict) -> None:
    """``osat``: datasopimus (ARKKITEHTUURI.md). Laskevat osiot tulevat analyysiltä valmiina HTML-osina
    ``osiot``: {kasvu3d, sato, pisteytys}. Lisäksi lohko, historia (df), vuodet: {vuosi: {optinen, peltotyot, tarvekartta}},
    vaihtelu: {ndvi: Vaihtelu, ndre: Vaihtelu}, talvi: [{talvi, viherpeite, talvehtiminen, tuhokuva}],
    lahteet (list[str]), huomiot (list[str])."""
    global _linkita
    lohko = osat["lohko"]
    v = osat.get("vaihtelu") or {}
    maa = osat.get("maapera")
    vert = osat.get("vertailu")
    vuodet = osat["vuodet"]

    # Mitkä osiot raportissa on: määrää, mitkä termit ja ilmiöt selitetään.
    mukana = {"kausi"} if vuodet else set()
    if v:
        mukana.add("vaihtelu")
    if any(y.get("planet") is not None for y in vuodet.values()):
        mukana.add("planet")
    if any(y.get("vuo") is not None for y in vuodet.values()):
        mukana.add("vuo")
    if maa is not None:
        mukana.add("maapera")
    if vert is not None:
        mukana.add("vertailu")
    if osat.get("talvi"):
        mukana.add("talvi")
    termit, ilmiot = sanasto.valitse(mukana)
    linkittaja = sanasto.Linkittaja(termit)
    _linkita = linkittaja

    vv = sorted(vuodet)
    ala = " · ".join(
        x
        for x in (
            lohko.get("kasvi"),
            kirja.fi(lohko["ala_ha"], 2) + " ha",
            (f"kaudet {vv[0]}–{vv[-1]}" if len(vv) > 1 else f"kausi {vv[0]}") if vv else None,
        )
        if x
    )

    sivut: list[str] = []

    def aukeama(rakenna) -> bool:
        linkittaja.uusi_osio()
        s = rakenna()
        if s:
            sivut.append(s)
        return bool(s)

    def sisalto(ankkuri: str, nimi: str, otsikko: str, rakenna) -> None:
        linkittaja.uusi_osio()
        sivut.append(kirja.sisaltosivu(ankkuri, nimi, otsikko, rakenna()))

    kaytossa = _kaytetyt_lahteet(osat)
    try:
        sivut.append(_kansi(lohko, osat, ala))
        aukeama(lambda: _silmays(osat))
        sivut.append(_pavunvarsi_sivu(osat, kaytossa))
        sisalto("lohko", "Lohko ja kasvihistoria", "Lohko", lambda: _lohko_osio(lohko, osat))
        if v:
            on = aukeama(lambda: _vaihtelu_aukeama(v))
            sisalto(
                "vaihtelu-tiedot" if on else "vaihtelu",
                "Kasvuvaihtelu: kartat ja luvut",
                "Kasvuvaihtelu lohkon sisällä",
                lambda: _vaihtelu_osio(v, lohko),
            )
        for vuosi in sorted(vuodet, reverse=True):
            y = vuodet[vuosi]
            on = aukeama(lambda y=y, vuosi=vuosi: _kausi_aukeama(y, vuosi))
            sisalto(
                f"kausi-{vuosi}-tiedot" if on else f"kausi-{vuosi}",
                f"Kausi {vuosi}: käyrä ja peltotyöt",
                f"Kausi {vuosi}{' – ' + y['kasvi'] if y.get('kasvi') else ''}",
                lambda y=y, vuosi=vuosi: _kausi_osio(y, vuosi, lohko),
            )
            if y.get("vuo") is not None:
                aukeama(lambda y=y, vuosi=vuosi: _hiili_aukeama(y["vuo"], vuosi))
                sisalto(
                    f"hiili-{vuosi}-tiedot",
                    f"Hiili {vuosi}: vuot ja säteily",
                    f"Hiilivuot ja säteilyn käyttö {vuosi} (alustava)",
                    lambda y=y, vuosi=vuosi: (
                        _vuo_osio(y["vuo"], vuosi, lohko.get("geometria"))
                        + ((osat.get("osiot") or {}).get("kasvu3d", "") if vuosi == max(vuodet) else "")
                    ),
                )
        sisalto(
            "sato",
            "Sato ja satovaje",
            "Satotaso ja satovaje lohkon sisällä",
            lambda: (osat.get("osiot") or {}).get("sato") or _sato_varaus(osat),
        )
        if (osat.get("osiot") or {}).get("pisteytys"):
            sisalto(
                "pisteytys",
                "Pisteytys",
                "Pisteytys: satokausi ja välikausi",
                lambda: osat["osiot"]["pisteytys"],
            )
        if maa is not None:
            on = aukeama(lambda: _maapera_aukeama(maa))
            sisalto(
                "maapera-tiedot" if on else "maapera",
                "Maaperä: kartat ja luvut",
                "Maaperä, maasto ja hydrologia",
                lambda: _maapera_osio(maa, lohko),
            )
        if vert is not None:
            on = aukeama(lambda: _vertailu_aukeama(vert))
            sisalto(
                "vertailu-tiedot" if on else "vertailu",
                "Vertailu: taulukot",
                "Vertailulohkot ja indeksit",
                lambda: _vertailu_osio(vert),
            )
        for t in osat.get("talvi") or []:
            nimi = f"Talvi {t['talvi']}–{t['talvi'] + 1}"
            on = aukeama(lambda t=t: _talvi_aukeama(t))
            sisalto(
                f"talvi-{t['talvi']}-tiedot" if on else f"talvi-{t['talvi']}",
                nimi + ": tiedot",
                nimi,
                lambda t=t: _talvi_osio(t),
            )
    finally:
        _linkita = lambda teksti: teksti  # noqa: E731

    ilmio_html, termi_html = sanasto.osiot_html(termit, ilmiot)
    ilmio_html = ilmio_html.replace(
        "<article class='ilmio' id='i-pilvet'>",
        "<article class='ilmio' id='i-pilvet'>" + kirja.merkki("tiikeri"),
        1,
    )
    if ilmio_html:
        sivut.append(
            kirja.sisaltosivu("ilmiot", "Ilmiöt", "Ilmiöt: miksi kartta tai käyrä näyttää tältä", ilmio_html)
        )
    sivut.append(kirja.sisaltosivu("termit", "Termit", "Termit", termi_html))
    sivut.append(_takakansi(osat))

    e = html.escape
    tunnus = e(lohko["tunnus"])
    import re

    sivut = [_merkitse_lahteet(x, kaytossa) for x in sivut]

    luettelo = []
    for i, s in enumerate(sivut, 1):
        m = re.match(r'<section class="sivu ([a-z ]+)" id="([^"]+)"[^>]*? data-nimi="([^"]*)"', s)
        luokka, ankkuri, nimi = m.group(1), m.group(2), m.group(3)
        paa = " class='paa'" if "sisalto" not in luokka else ""
        luettelo.append(f"<a href='#{ankkuri}'{paa}><span>{i}</span>{nimi}</a>")
    sivu = f"""<!doctype html><html lang="fi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Kasvukunto {tunnus}</title>
<style>{ilme.fontti_css()}{ilme.CSS}</style></head><body>
{kirja.varsi_reuna()}
<main class="kirja">{"".join(sivut)}</main>
<nav class="sis" id="sis" aria-label="Sisällys" hidden>{"".join(luettelo)}</nav>
<div class="palkki" role="navigation" aria-label="Selaus"><div class="jana" id="jana"></div>
<button type="button" id="sisb" aria-expanded="false" aria-controls="sis">Sisällys</button>
<div class="missa" id="missa" aria-live="polite"></div>
<button type="button" id="ed" aria-label="Edellinen sivu">←</button>
<button type="button" id="se" aria-label="Seuraava sivu">→</button></div>
<script>{ilme.JS}</script></body></html>"""
    with open(polku, "w", encoding="utf-8") as f:
        f.write(sivu)

"""Raportti kevyillä esimerkkiosilla: kirjasen rakenne, ilme ja analyysin valmiit osiot."""

import re

import numpy as np
import pandas as pd
import pytest

import kasvukuntoraportti
from kasvukuntoraportti import ilme


def _osat(osiot=None):
    pv = pd.date_range("2025-05-01", "2025-09-30", freq="5D")
    t = np.linspace(0, 1, len(pv))
    ndvi = 0.2 + 0.65 * np.sin(np.pi * t)
    optinen = pd.DataFrame(
        {
            "pvm": pv,
            "lahde": "sentinel-2-l2a",
            "ndvi_p10": ndvi - 0.05,
            "ndvi_p50": ndvi,
            "ndvi_p90": ndvi + 0.05,
            "kelvollinen_pct": 100.0,
        }
    )
    peltotyot = pd.DataFrame(
        [
            {
                "tyyppi": "oraalle_tulo",
                "alku": "2025-06-01",
                "loppu": "2025-06-10",
                "luottamus": 0.6,
                "lahteet": "HLS",
                "alustava": True,
                "huom": "",
            },
            {
                "tyyppi": "sadonkorjuu",
                "alku": "2025-09-10",
                "loppu": "2025-09-10",
                "luottamus": 1.0,
                "lahteet": "puimuri",
                "alustava": False,
                "huom": "",
            },
        ]
    )
    return {
        "lohko": {"tunnus": "0000000000-1", "ala_ha": 5.25, "kasvi": "Kaura"},
        "historia": pd.DataFrame({"vuosi": [2025], "kasvi": ["Kaura"]}),
        "vuodet": {2025: {"optinen": optinen, "peltotyot": peltotyot, "kasvi": "Kaura", "yhteenveto": []}},
        "lahteet": ["Copernicus Sentinel-2"],
        "huomiot": [],
        "versio": "9.9.9",
        **({"osiot": osiot} if osiot else {}),
    }


@pytest.fixture
def sivu(tmp_path):
    p = tmp_path / "r.html"
    kasvukuntoraportti.kirjoita(
        p,
        _osat(
            {
                "kasvu3d": "<p id='testi-3d'>3D</p>",
                "sato": "<p id='testi-sato'>sato</p>",
                "pisteytys": "<p id='testi-pisteet'>pisteet</p>",
            }
        ),
    )
    return p.read_text(encoding="utf-8")


def test_kirjasen_rakenne_ja_ilme(sivu):
    sivut = re.findall(r'<section class="sivu ([a-z ]+)" id="([^"]+)"', sivu)
    ankkurit = [a for _, a in sivut]
    assert sivut[0] == ("kansi helle", "kansi") and sivut[-1][0] == "kansi taka"
    assert {"lohko", "sato", "pisteytys", "termit"} <= set(ankkurit)
    assert len(ankkurit) == len(set(ankkurit))
    assert sivu.count("@font-face") == 3 and "League Spartan" in sivu and ilme.VIHREA in sivu
    assert "kasvukunto 9.9.9" in sivu  # analyysin versio osista
    assert "fonts.googleapis" not in sivu and "<link" not in sivu


def test_analyysin_osiot_paikoillaan(sivu):
    assert "id='testi-sato'" in sivu and "id='testi-pisteet'" in sivu
    k = sivu.index('id="sato"')
    assert k < sivu.index("id='testi-sato'") < sivu.index('id="pisteytys"')


def test_ilman_osioita_satosivu_on_varaus(tmp_path):
    p = tmp_path / "r.html"
    kasvukuntoraportti.kirjoita(p, _osat())
    s = p.read_text(encoding="utf-8")
    assert "varaus: satokartta puuttuu" in s and "Salaojakartta: varaus" in s
    assert 'id="pisteytys"' not in s

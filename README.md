# Kasvukuntoraportti

Kasvukuntoanalyysin raporttikerros: yksi itsenäinen HTML-kirjanen peltolohkon kasvukunnosta.
Signaali-ilme sisäsivuilla, Helle yöllä -kansi ([joriim/oma-design](https://github.com/joriim/oma-design)),
ja upotettu Beanstalk Growth Space -näkymä (valinnainen `beanstalk4d`).

Analyysi (satelliittiaineisto, vuomallit, vertailu) on repossa
[joriim/Beanstalk-Growth-Analysis](https://github.com/joriim/Beanstalk-Growth-Analysis). Se kutsuu
raporttia `kirjoita(polku, osat)`. Datasopimus, moduulit ja sivukartta: [ARKKITEHTUURI.md](ARKKITEHTUURI.md).

## Käyttö

```bash
pip install "kasvukuntoraportti @ git+https://github.com/joriim/Kasvukuntoraportti"
```

```python
import kasvukuntoraportti

kasvukuntoraportti.kirjoita("raportti.html", osat)
```

Analyysi asentaa paketin riippuvuutena ja kutsuu sitä liitoksen `kasvukunto.raportti.kirjoita` kautta,
joka lisää laskevat osiot (3D-näkymä, satovaje, pisteytys). Ilman niitä raportti näyttää varaukset.

| Moduuli | Sisältö |
|---|---|
| `raportti` | sivukartta (`kirjoita`), osiot, kuvaajat |
| `kirja` | sivutyypit, pistekartat, sataruudukko, merkit, pavunvarsi |
| `ilme` | Signaali-värit ja asteikot, fontit, CSS, selaus |
| `sanasto` | termit ja ilmiöt |

Ilme: [joriim/oma-design](https://github.com/joriim/oma-design). Testit: `pytest`.

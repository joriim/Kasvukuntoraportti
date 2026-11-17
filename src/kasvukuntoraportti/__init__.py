"""Kasvukuntoraportti: peltolohkon kasvukuntoraportti yhtenä HTML-kirjasena.

Signaali-ilme sisäsivuilla, Helle yöllä -kansi.

Analyysi (``kasvukunto``) laskee tulokset ja kutsuu ``kirjoita(polku, osat)``. Datasopimus: ARKKITEHTUURI.md.
"""

__version__ = "0.1.0"

from .raportti import kirjoita  # noqa: E402

__all__ = ["kirjoita", "__version__"]

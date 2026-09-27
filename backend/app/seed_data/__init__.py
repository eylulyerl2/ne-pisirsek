from app.seed_data import (
    baklagiller,
    bolgesel,
    corbalar,
    etler,
    kahvalti_salata_tatli,
    pilav_hamur,
    sebzeler,
    tavuk_balik,
)

ALL_MEALS = [
    *corbalar.MEALS,
    *bolgesel.MEALS,
    *baklagiller.MEALS,
    *sebzeler.MEALS,
    *etler.MEALS,
    *tavuk_balik.MEALS,
    *pilav_hamur.MEALS,
    *kahvalti_salata_tatli.MEALS,
]

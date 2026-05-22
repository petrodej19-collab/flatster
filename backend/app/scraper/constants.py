COUNTRIES: dict[str, str] = {
    "si": "Slovenija",
    "hr": "Hrvaška",
}

REGIONS: dict[str, dict[str, str]] = {
    "si": {
        "ljubljana-mesto": "LJ-mesto",
        "ljubljana-okolica": "LJ-okolica",
        "gorenjska": "Gorenjska",
        "juzna-primorska": "J. Primorska",
        "severna-primorska": "S. Primorska",
        "notranjska": "Notranjska",
        "savinjska": "Savinjska",
        "podravska": "Podravska",
        "koroska": "Koroška",
        "dolenjska": "Dolenjska",
        "posavska": "Posavska",
        "zasavska": "Zasavska",
        "pomurska": "Pomurska",
    },
    "hr": {
        "primorsko-goranska": "Primorsko-goranska",
        "istrska": "Istrska",
        "mesto-zagreb": "Mesto Zagreb",
        "zagrebska": "Zagrebška",
        "dubrovnisko-neretvanska": "Dubrovniško-neretvanska",
        "splitsko-dalmatinska": "Splitsko-dalmatinska",
        "sibenisko-kninska": "Šibeniško-kninska",
        "zadarska": "Zadarska",
        "osijesko-baranjska": "Osiješko-baranjska",
        "vukovarsko-sremska": "Vukovarsko-sremska",
        "virovitisko-podravska": "Virovitiško-podravska",
        "pozesko-slavonska": "Požeško-slavonska",
        "brodsko-posavska": "Brodsko-posavska",
        "medimurska": "Međimurska",
        "varazdinska": "Varaždinska",
        "bjelovarsko-bilogorska": "Bjelovarsko-bilogorska",
        "sisasko-moslavinska": "Sisaško-moslavinska",
        "karlovska": "Karlovška",
        "koprivnisko-krizevska": "Koprivniško-križevska",
        "krapinsko-zagorska": "Krapinsko-zagorska",
        "lisko-senjska": "Liško-senjska",
    },
}

SUBREGIONS: dict[str, dict[str, dict[str, str]]] = {
    "si": {
        "ljubljana-mesto": {
            "lj-bezigrad": "Lj. Bežigrad",
            "lj-center": "Lj. Center",
            "lj-moste-polje": "Lj. Moste-Polje",
            "lj-siska": "Lj. Šiška",
            "lj-vic-rudnik": "Lj. Vič-Rudnik",
        },
        "ljubljana-okolica": {
            "domzale": "Domžale",
            "grosuplje": "Grosuplje",
            "kamnik": "Kamnik",
            "litija": "Litija",
            "lj-jz-del-vic-rudnik": "Lj. J&Z del (Vič, Rudnik)",
            "lj-sv-del-bezigrad": "Lj. SV del (Bežigrad)",
            "lj-sz-del-siska": "Lj. SZ del (Šiška)",
            "lj-v-del-moste-polje": "Lj. V del (Moste-Polje)",
            "logatec": "Logatec",
            "vrhnika": "Vrhnika",
        },
        "gorenjska": {
            "jesenice": "Jesenice",
            "kranj": "Kranj",
            "radovljica": "Radovljica",
            "skofja-loka": "Škofja Loka",
            "trzic": "Tržič",
        },
        "juzna-primorska": {
            "izola": "Izola",
            "koper": "Koper",
            "piran": "Piran",
            "sezana": "Sežana",
        },
        "severna-primorska": {
            "ajdovscina": "Ajdovščina",
            "idrija": "Idrija",
            "nova-gorica": "Nova Gorica",
            "tolmin": "Tolmin",
        },
        "notranjska": {
            "cerknica": "Cerknica",
            "ilirska-bistrica": "Ilirska Bistrica",
            "postojna": "Postojna",
        },
        "savinjska": {
            "celje": "Celje",
            "lasko": "Laško",
            "mozirje": "Mozirje",
            "slovenske-konjice": "Slovenske Konjice",
            "sentjur": "Šentjur",
            "smarje-pri-jelsah": "Šmarje pri Jelšah",
            "velenje": "Velenje",
            "zalec": "Žalec",
        },
        "podravska": {
            "lenart": "Lenart",
            "maribor": "Maribor",
            "ormoz": "Ormož",
            "pesnica": "Pesnica",
            "ptuj": "Ptuj",
            "ruse": "Ruše",
            "slovenska-bistrica": "Slovenska Bistrica",
        },
        "koroska": {
            "dravograd": "Dravograd",
            "radlje-ob-dravi": "Radlje ob Dravi",
            "ravne-na-koroskem": "Ravne na Koroškem",
            "slovenj-gradec": "Slovenj Gradec",
        },
        "dolenjska": {
            "crnomelj": "Črnomelj",
            "kocevje": "Kočevje",
            "metlika": "Metlika",
            "novo-mesto": "Novo mesto",
            "ribnica": "Ribnica",
            "trebnje": "Trebnje",
        },
        "posavska": {
            "brezice": "Brežice",
            "krsko": "Krško",
            "sevnica": "Sevnica",
        },
        "zasavska": {
            "hrastnik": "Hrastnik",
            "trbovlje": "Trbovlje",
            "zagorje-ob-savi": "Zagorje ob Savi",
        },
        "pomurska": {
            "gornja-radgona": "Gornja Radgona",
            "lendava": "Lendava",
            "ljutomer": "Ljutomer",
            "murska-sobota": "Murska Sobota",
        },
    },
    "hr": {},
}

PROPERTY_TYPES: dict[str, str] = {
    "stanovanje": "Stanovanje",
    "hisa": "Hiša",
    "vikend": "Vikend",
    "posest": "Posest",
    "poslovni-prostor": "Poslovni prostor",
    "garaza": "Garaža",
    "pocitniski-objekt": "Počitniški objekt",
}

ROOM_TYPES: list[str] = [
    "garsonjera",
    "1-sobno",
    "15-sobno",
    "2-sobno",
    "25-sobno",
    "3-sobno",
    "35-sobno",
    "4-sobno",
    "45-sobno",
    "5-in-vecsobno",
    "apartma",
    "soba",
]

TRANSACTION_TYPES: list[str] = ["prodaja", "oddaja"]

BASE_URL = "https://www.nepremicnine.net"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

LISTINGS_PER_PAGE = 25

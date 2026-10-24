"""Nastavení – tady se dá všechno upravit bez sahání do zbytku kódu."""

TZ = "Europe/Prague"
DAYS_AHEAD = 14  # kolik dní dopředu sledovat (včetně dneška)

# Mřížka dashboardu: začátky po 30 min od 06:00 do 23:30
GRID_START = "06:00"
GRID_STEP = 30
GRID_SLOTS = 36

# Okna, ve kterých chceš hrát (0 = pondělí … 6 = neděle).
# (od, do) – hra musí celá skončit do "do". None = klidně až do zavíračky.
WINDOWS = {
    0: [("18:00", "22:00")],  # Po
    1: [("18:00", "22:00")],  # Út
    # 2: středa vynechaná
    3: [("18:00", "22:00")],  # Čt
    4: [("18:00", "22:00")],  # Pá
    5: [("10:00", "13:00"), ("15:00", None)],  # So
    6: [("10:00", "13:00"), ("15:00", None)],  # Ne
}

MIN_DURATION = 90   # notifikace od 90 min
IDEAL_DURATION = 120

# Stejný slot znovu nehlásit dřív než za X hodin (kdyby blikal sem a tam)
RENOTIFY_HOURS = 6

VENUES = [
    {
        "id": "onepadel",
        "name": "OnePadel Zličín",
        "area": "Praha 17 – Zličín",
        "type": "courtyone",
        "url": "https://onepadel.cz/book",
        "base": "https://onepadel.cz",
        "tenant": "onepadel",
        "venue": "praha-zlicin",
    },
    {
        "id": "padelpowers",
        "name": "Padel Powers Smíchov",
        "area": "Praha 5 – Smíchov",
        "type": "padelos",
        "url": "https://player.padelos.co/company/217?clubIds=216927&locale=cs",
        "company": "217",
        "club": "216927",
    },
    {
        "id": "padeldzus",
        "name": "Padel Džus Hostivař",
        "area": "Praha 15 – Hostivař",
        "type": "bookaball",
        "url": "https://padeldzus.bookaball.com/cs/bookings/create",
        "base": "https://padeldzus.bookaball.com",
        "location_id": 90,
    },
    {
        "id": "padelmanie",
        "name": "Padelmanie",
        "area": "Praha",
        "type": "reservanto",
        "url": "https://booking.reservanto.cz/Modal/?id=24706&seg=1029&sId=113217&sIds=113217",
    },
    {
        "id": "neride",
        "name": "Padel Neride",
        "area": "Praha",
        "type": "sportelo",
        "url": "https://padelneride.cz/rezervace/",
        "subdomain": "neride",
        "field_group": "3435e961-8ca6-4c14-94ef-a0a4e3fe4ca2",
    },
    {
        "id": "pisecna",
        "name": "Písečná (kryté kurty)",
        "area": "Praha 8 – Troja",
        "type": "playtomic",
        "url": "https://playtomic.com/clubs/tenis-a-padel-klub-pisecna",
        "tenant": "33257960-acca-4aa4-9f77-b6e5ab56f3e5",
        # jen zastřešené kurty (Center court a Court 1 jsou venku)
        "courts": {
            "7efed5be-31bd-4e39-a00a-47fb979ffda6": "Court 2 (krytý)",
            "b95bb160-fa7d-464c-a9a2-ab028d305e4f": "Court 3 (krytý)",
        },
        "open": ("08:00", "22:00"),
    },
]

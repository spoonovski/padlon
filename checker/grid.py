"""Převod různých formátů obsazenosti na jednotnou mřížku.

Každý kurt má na každý den řetězec znaků, jeden znak = začátek po 30 min:
  '.'  zavřeno / neznámo
  '0'  odsud nejde začít ani hodinová hra (obsazeno)
  '1'  jde začít 60 min
  '2'  jde začít 90 min
  '3'  jde začít 120 min a víc
"""
from datetime import datetime, timedelta, date as Date
from zoneinfo import ZoneInfo

from . import config

TZ = ZoneInfo(config.TZ)


def hm(s):
    h, m = s.split(":")[:2]
    return int(h) * 60 + int(m)


GRID0 = hm(config.GRID_START)
STEP = config.GRID_STEP
N = config.GRID_SLOTS


def slot_minutes():
    return [GRID0 + i * STEP for i in range(N)]


def code_for(minutes):
    if minutes >= 120:
        return "3"
    if minutes >= 90:
        return "2"
    if minutes >= 60:
        return "1"
    return "0"


def local_dt(d: Date, minutes: int):
    return datetime(d.year, d.month, d.day, tzinfo=TZ) + timedelta(minutes=minutes)


def to_min(dt: datetime, d: Date):
    """Minuty od půlnoci dne d (lokálně); umí i přes půlnoc (>1440)."""
    dt = dt.astimezone(TZ)
    return (dt.date() - d).days * 1440 + dt.hour * 60 + dt.minute


def from_free_intervals(d: Date, free, opening):
    """free: [(start_min, end_min)] volné úseky, opening: (open_min, close_min)."""
    o, c = opening
    out = []
    for t in slot_minutes():
        if t < o or t >= c:
            out.append(".")
            continue
        avail = 0
        for s, e in free:
            if s <= t < e:
                avail = min(e, c) - t
                break
        out.append(code_for(avail))
    return "".join(out)


def from_busy(d: Date, busy, opening):
    o, c = opening
    busy = sorted((max(s, o), min(e, c)) for s, e in busy if e > o and s < c)
    free, cur = [], o
    for s, e in busy:
        if s > cur:
            free.append((cur, s))
        cur = max(cur, e)
    if cur < c:
        free.append((cur, c))
    return from_free_intervals(d, free, opening)


def from_starts(starts, opening):
    """starts: {start_min: max_duration}; opening: (o, c) nebo None."""
    out = []
    for t in slot_minutes():
        if opening and (t < opening[0] or t >= opening[1]):
            out.append(".")
        else:
            out.append(code_for(starts.get(t, 0)))
    return "".join(out)


def days():
    today = datetime.now(TZ).date()
    return [today + timedelta(days=i) for i in range(config.DAYS_AHEAD)]

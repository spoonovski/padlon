"""Čtení obsazenosti z jednotlivých rezervačních systémů.

Každá funkce vrací seznam řádků: {"id", "name", "cells": {"YYYY-MM-DD": "...."}}
"""
import html as htmllib
import json
import re
import urllib.parse
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

from .grid import TZ, days, from_busy, from_free_intervals, from_starts, hm, to_min
from .net import Session


def iso_dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def opening_from(starts_ends, fallback):
    if not starts_ends:
        return fallback
    return (min(s for s, _ in starts_ends), max(e for _, e in starts_ends))


# ---------------------------------------------------------------- CourtyONE
# OnePadel: Next.js server actions. ID akcí se mění s každým nasazením webu,
# proto je pokaždé dohledáme v jejich JS.

ACTION_NAMES = ("fetchPublicDayOccupancyAction", "fetchPublicVenueBookingSlotsAction")


def _courtyone_actions(s, base):
    page = s.get(base + "/book")
    srcs = re.findall(r'src="(/_next/static/chunks/[^"]+\.js)"', page)
    found = {}
    for src in srcs:
        js = s.get(base + src)
        for m in re.finditer(r'\("([0-9a-f]{40,})",[^"]{0,160}"(' + "|".join(ACTION_NAMES) + r')"', js):
            found[m.group(2)] = m.group(1)
        if len(found) == len(ACTION_NAMES):
            break
    if len(found) != len(ACTION_NAMES):
        raise RuntimeError("CourtyONE: nenašel jsem ID serverových akcí")
    return found


def _courtyone_call(s, base, action_id, arg):
    txt = s.post(base + "/book", data=json.dumps([arg]), headers={
        "Accept": "text/x-component",
        "next-action": action_id,
        "Content-Type": "text/plain;charset=UTF-8",
    })
    for line in txt.splitlines():
        if line.startswith("1:"):
            res = json.loads(line[2:])
            if not res.get("ok"):
                raise RuntimeError(f"CourtyONE odpověď: {res}")
            return res
    raise RuntimeError("CourtyONE: neočekávaná odpověď")


def courtyone(v):
    s, base = Session(), v["base"]
    acts = _courtyone_actions(s, base)
    rows, order = {}, []
    for d in days():
        ymd = d.isoformat()
        arg = {"tenantSlug": v["tenant"], "venueSlug": v["venue"], "ymd": ymd}
        occ = _courtyone_call(s, base, acts["fetchPublicDayOccupancyAction"], arg)["occupancy"]
        slots = _courtyone_call(s, base, acts["fetchPublicVenueBookingSlotsAction"],
                                {**arg, "durationMinutes": 60}).get("slots", [])
        opening = opening_from(
            [(to_min(iso_dt(x["startsAt"]), d), to_min(iso_dt(x["endsAt"]), d)) for x in slots],
            (hm("07:00"), hm("23:00")))
        for court in occ:
            cid = court["courtId"]
            if cid not in rows:
                order.append(cid)
                rows[cid] = {"id": cid, "name": f"Kurt {len(order)}", "cells": {}}
            busy = [(to_min(iso_dt(b["startsAt"]), d), to_min(iso_dt(b["endsAt"]), d))
                    for b in court["blocks"]]
            rows[cid]["cells"][ymd] = from_busy(d, busy, opening)
    return [rows[c] for c in order]


# ------------------------------------------------------------------ PadelOS

def padelos(v):
    s = Session()
    headers = {
        "Accept": "application/json, text/plain, */*",
        "x-clubos-channel": "CLUBOS-WEB", "x-clubos-domain": "PADELOSCO",
        "version": "2.4", "x-clubos-company": v["company"], "x-clubos-club-info": v["club"],
        "Origin": "https://player.padelos.co", "Referer": "https://player.padelos.co/",
    }
    names, per_day = {}, {}
    for d in days():
        ymd = d.isoformat()
        j = s.post_json("https://api.padelos.co/customers/searchByDate", headers=headers, json_body={
            "date": ymd, "sport": "padel", "courtType": "", "courtSize": "", "courtTurf": "",
            "courtFeature": "", "searchTerm": "", "limit": "", "offset": "", "type": ""})
        club = next((c for c in j.get("data", []) if str(c.get("id")) == v["club"]), None)
        starts, spans = {}, []
        for av in (club or {}).get("availability", []):
            dur = int(av["duration"])
            for sl in av.get("slots", []):
                if sl.get("date") != ymd:
                    continue
                t = hm(sl["startTime"])
                spans.append((t, t + dur))
                for c in sl.get("courts", []):
                    if (c.get("courtType") or "Indoor").lower() != "indoor":
                        continue
                    cid = str(c["id"])
                    m = re.match(r"\s*(\d+)\.", c.get("name", ""))
                    names[cid] = f"Kurt {m.group(1)}" if m else c.get("name", cid)
                    cs = starts.setdefault(cid, {})
                    cs[t] = max(cs.get(t, 0), dur)
        per_day[ymd] = (starts, opening_from(spans, (hm("07:00"), hm("23:00"))))
    rows = []
    for cid in sorted(names, key=lambda x: names[x]):
        cells = {ymd: from_starts(st.get(cid, {}), op) for ymd, (st, op) in per_day.items()}
        rows.append({"id": cid, "name": names[cid], "cells": cells})
    return rows


# ---------------------------------------------------------------- Bookaball
# Padel Džus: Laravel, průvodce rezervací drží stav v session. Vrací jen
# "aspoň jeden kurt volný", proto je to jeden řádek za celé centrum.

def bookaball(v):
    s, base = Session(), v["base"]
    s.get(base + "/cs/bookings/create")

    def hdr():
        return {"Accept": "application/json, text/plain, */*", "X-Requested-With": "XMLHttpRequest",
                "Locale": "cs", "Origin": base, "Referer": base + "/cs/bookings/create",
                "X-XSRF-TOKEN": urllib.parse.unquote(s.cookie("XSRF-TOKEN") or "")}

    loc = s.post_json(base + "/api/bookings/create", headers=hdr(),
                      json_body={"step": "STEP_LOCATION", "location_id": v["location_id"]})
    courts = [c for c in loc["prebooking"]["location"].get("courts", [])
              if c.get("sport_type") == "padel" and c.get("type") == "indoor"]
    s.post_json(base + "/api/bookings/create", headers=hdr(), json_body={
        "step": "STEP_SIZE", "sport_type": "padel", "court_size": "double",
        "court_count": 1, "court_type": "indoor"})
    cells = {}
    for d in days():
        ymd = d.isoformat()
        starts, spans = {}, []
        for dur in (90, 120):
            times = s.post_json(base + "/api/bookings/times", headers=hdr(),
                                json_body={"date": ymd, "duration": dur})
            for t in times:
                m = hm(t["time"])
                spans.append((m, m + dur))
                if t.get("available") and not t.get("disabled"):
                    starts[m] = max(starts.get(m, 0), dur)
        cells[ymd] = from_starts(starts, opening_from(spans, None))
    return [{"id": "any", "name": f"Kterýkoliv kurt ({len(courts)})", "cells": cells}]


# --------------------------------------------------------------- Reservanto

class _Inputs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.fields = []

    def handle_starttag(self, tag, attrs):
        if tag != "input":
            return
        a = dict(attrs)
        if not a.get("name"):
            return
        if a.get("type", "").lower() in ("checkbox", "radio") and "checked" not in a:
            return
        if a.get("type", "").lower() in ("submit", "button"):
            return
        self.fields.append((a["name"], htmllib.unescape(a.get("value") or "")))


def reservanto(v):
    s = Session()
    page = s.get(v["url"])
    p = _Inputs()
    p.feed(page)
    base_fields = p.fields
    if not base_fields:
        raise RuntimeError("Reservanto: formulář nenalezen")
    want = {d.isoformat() for d in days()}
    mondays = sorted({d - timedelta(days=d.weekday()) for d in days()})
    rows = {}
    for mon in mondays:
        f = dict(base_fields)
        f["BookingTimeViewModel.LastMondayDay"] = str(mon.day)
        f["BookingTimeViewModel.LastMondayMonth"] = str(mon.month)
        f["BookingTimeViewModel.LastMondayYear"] = str(mon.year)
        txt = s.post("https://booking.reservanto.cz/PlaceRentalLike/Step2_Calendar", form=f,
                     headers={"X-Requested-With": "XMLHttpRequest", "Referer": v["url"]})
        i = txt.find("days:")
        if i < 0:
            raise RuntimeError("Reservanto: v odpovědi chybí data kalendáře")
        data, _ = json.JSONDecoder().raw_decode(txt[i + 5:].lstrip())
        for day in data:
            for loc in day.get("locations", []):
                for g in loc.get("groups", []):
                    for src in g.get("sources", []):
                        cells = src.get("availability") or []
                        if not cells:
                            continue
                        d = iso_dt(cells[0]["StartTime"]).astimezone(TZ).date()
                        ymd = d.isoformat()
                        if ymd not in want:
                            continue
                        spans = [(to_min(iso_dt(c["StartTime"]), d), to_min(iso_dt(c["EndTime"]), d))
                                 for c in cells]
                        free = []
                        for (st, en), c in zip(spans, cells):
                            if c.get("IsFree"):
                                if free and free[-1][1] == st:
                                    free[-1] = (free[-1][0], en)
                                else:
                                    free.append((st, en))
                        row = rows.setdefault(str(src["id"]), {"id": str(src["id"]),
                                                               "name": src["name"], "cells": {}})
                        row["cells"][ymd] = from_free_intervals(d, free, opening_from(spans, None))
    return sorted(rows.values(), key=lambda r: r["name"])


# ----------------------------------------------------------------- Sportelo

def sportelo(v):
    s = Session()
    ds = days()
    t0 = datetime(ds[0].year, ds[0].month, ds[0].day, tzinfo=TZ).astimezone(timezone.utc)
    t1 = t0 + timedelta(days=len(ds)) - timedelta(milliseconds=1)
    z = lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    oh = "\n".join(f'o{i}: openingHourByDate(date: "{d.isoformat()}") {{ timeFrom timeTo isClosed }}'
                   for i, d in enumerate(ds))
    q = f"""query R($fg: FieldsArgs!, $r: ReservationsArgs!, $dh: DisabledHoursInput!) {{
      fields(input: $fg) {{ id name status }}
      reservations(input: $r) {{ __typename
        ... on Reservation {{ field {{ id }} timeFrom timeTo }}
        ... on Lesson {{ fields {{ id }} timeFrom timeTo }} }}
      disabledHours(input: $dh) {{ fieldId dateFrom dateTo }}
      {oh}
    }}"""
    fg = v["field_group"]
    var = {"fg": {"fieldGroupId": fg},
           "r": {"timeFrom": z(t0), "timeTo": z(t1), "fieldGroupId": fg},
           "dh": {"fieldGroupId": fg, "timeFrom": z(t0), "timeTo": z(t1)}}
    j = s.post_json("https://sportelo-reservation-embed.vercel.app/graphql", json_body={"query": q, "variables": var},
                    headers={"x-sport-center-subdomain": v["subdomain"], "x-lang": "cs",
                             "x-platform": "embed", "Accept": "*/*",
                             "Origin": "https://sportelo-reservation-embed.vercel.app"})
    if j.get("errors"):
        raise RuntimeError(f"Sportelo: {j['errors'][0].get('message')}")
    data = j["data"]
    fields = [f for f in data["fields"] if f.get("status") == "ACTIVE"]
    busy = {f["id"]: [] for f in fields}
    for r in data["reservations"]:
        ids = [r["field"]["id"]] if r.get("field") else [f["id"] for f in r.get("fields", [])]
        for fid in ids:
            busy.setdefault(fid, []).append((iso_dt(r["timeFrom"]), iso_dt(r["timeTo"])))
    for h in data["disabledHours"]:
        ids = [h["fieldId"]] if h.get("fieldId") else list(busy)
        for fid in ids:
            busy.setdefault(fid, []).append((iso_dt(h["dateFrom"]), iso_dt(h["dateTo"])))
    rows = []
    for f in sorted(fields, key=lambda f: f["name"]):
        cells = {}
        for i, d in enumerate(ds):
            o = data.get(f"o{i}") or {}
            if o.get("isClosed"):
                cells[d.isoformat()] = "." * len(from_starts({}, None))
                continue
            opening = (hm(o.get("timeFrom") or "00:00"), hm(o.get("timeTo") or "24:00"))
            b = [(to_min(a, d), to_min(e, d)) for a, e in busy.get(f["id"], [])]
            cells[d.isoformat()] = from_busy(d, b, opening)
        rows.append({"id": f["id"], "name": f["name"], "cells": cells})
    return rows


# ---------------------------------------------------------------- Playtomic

def playtomic(v):
    s = Session()
    ds = days()
    want = {d.isoformat() for d in ds}
    starts = {cid: {} for cid in v["courts"]}
    # Víc cest ke stejným datům; první, která odpoví, vyhrává a pamatuje se.
    endpoints = [
        lambda ymd: ("https://playtomic.io/api/v1/availability?user_id=me&sport_id=PADEL"
                     f"&tenant_id={v['tenant']}&local_start_min={ymd}T00:00:00"
                     f"&local_start_max={ymd}T23:59:59"),
        lambda ymd: (f"https://playtomic.com/api/clubs/availability?tenant_id={v['tenant']}"
                     f"&date={ymd}&sport_id=PADEL"),
        lambda ymd: ("https://api.playtomic.io/v1/availability?sport_id=PADEL"
                     f"&tenant_id={v['tenant']}&local_start_min={ymd}T00:00:00"
                     f"&local_start_max={ymd}T23:59:59"),
    ]
    hdr = {"Accept": "application/json", "Referer": "https://playtomic.com/", "Origin": "https://playtomic.com"}
    for d in ds + [ds[-1] + timedelta(days=1)]:
        ymd = d.isoformat()
        res, errors = None, []
        for k, ep in enumerate(endpoints):
            try:
                res = s.get_json(ep(ymd), headers=hdr)
                if k:  # tahle cesta funguje → příště ji zkus první
                    endpoints.insert(0, endpoints.pop(k))
                break
            except Exception as e:
                errors.append(f"{ep(ymd).split('/')[2]}: {type(e).__name__} {e}")
        if res is None:
            raise RuntimeError("Playtomic nedostupný – " + " | ".join(errors))
        for r in res:
            cid = r["resource_id"]
            if cid not in starts:
                continue
            for sl in r.get("slots", []):
                utc = datetime.fromisoformat(f"{r['start_date']}T{sl['start_time']}+00:00")
                loc = utc.astimezone(TZ)
                key = (loc.date().isoformat(), loc.hour * 60 + loc.minute)
                cur = starts[cid].get(key, 0)
                starts[cid][key] = max(cur, int(sl["duration"]))
    opening = (hm(v["open"][0]), hm(v["open"][1]))
    rows = []
    for cid, name in v["courts"].items():
        cells = {}
        for ymd in sorted(want):
            st = {t: dur for (dd, t), dur in starts[cid].items() if dd == ymd}
            cells[ymd] = from_starts(st, opening)
        rows.append({"id": cid, "name": name, "cells": cells})
    return rows


# ------------------------------------------------------------- iSportSystem
# Padel Automat: server vrací HTML rozvrh na 7 dní. Každá buňka = 30 min,
# "Volno" = volné, "povolená pouze N dnů dopředu" = zatím neznámé.

class _ISport(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables, self.day, self.row, self.cell, self.text = [], None, None, None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "h3":
            self.text = ""
        elif tag == "table":
            self.tables.append({"day": self.day, "n": 0, "open": None, "lanes": []})
        elif tag == "tr" and self.tables:
            cls = a.get("class") or ""
            self.row = cls
            if cls.startswith("trSchemaLane_"):
                self.tables[-1]["lanes"].append({"name": "", "cells": []})
        elif tag == "td" and self.tables and self.row is not None:
            t = self.tables[-1]
            if self.row == "hidden":
                t["n"] += 1
            elif self.row == "times" and t["open"] is None:
                self.text = ""
            elif self.row.startswith("trSchemaLane_"):
                t["lanes"][-1]["cells"].append([int(a.get("colspan") or 1), a.get("title") or ""])
        elif tag == "a" and self.row and self.row.startswith("trSchemaLane_") and self.tables:
            cells = self.tables[-1]["lanes"][-1]["cells"]
            if cells and not cells[-1][1]:
                cells[-1][1] = a.get("title") or ""
        elif tag == "span" and self.row and self.row.startswith("trSchemaLane_"):
            self.text = ""

    def handle_data(self, data):
        if self.text is not None:
            self.text += data

    def handle_endtag(self, tag):
        if self.text is None:
            return
        txt = self.text.strip()
        if tag == "h3":
            self.day = txt; self.text = None
        elif tag == "td" and self.row == "times" and self.tables and self.tables[-1]["open"] is None:
            self.tables[-1]["open"] = txt; self.text = None
        elif tag == "span" and self.row and self.row.startswith("trSchemaLane_"):
            lane = self.tables[-1]["lanes"][-1]
            if not lane["name"]:
                lane["name"] = txt
            self.text = None


def parse_isport(html, want_dates, ref_date):
    """-> {lane_name: {ymd: (free_intervals, opening)}}"""
    p = _ISport()
    p.feed(html)
    out = {}
    for t in p.tables:
        m = re.search(r"(\d{1,2})\.(\d{1,2})\.", t["day"] or "")
        if not m or not t["open"] or not t["n"]:
            continue
        day, month = int(m.group(1)), int(m.group(2))
        year = ref_date.year + (1 if month < ref_date.month - 6 else 0)
        ymd = f"{year:04d}-{month:02d}-{day:02d}"
        if ymd not in want_dates:
            continue
        o = hm(t["open"])
        for lane in t["lanes"]:
            free, known = [], []
            pos = o
            for span, title in lane["cells"]:
                st, en = pos, pos + 30 * span
                pos = en
                if "povolen" in title:          # ještě nejde rezervovat
                    continue
                known.append((st, en))
                if title.rstrip().endswith("Volno"):
                    if free and free[-1][1] == st:
                        free[-1] = (free[-1][0], en)
                    else:
                        free.append((st, en))
            opening = (min(k[0] for k in known), max(k[1] for k in known)) if known else None
            out.setdefault(lane["name"], {})[ymd] = (free, opening)
    return out


def isport(v):
    s = Session()
    base = v["base"]
    s.get(base + "/")
    ds = days()
    want = {d.isoformat() for d in ds}
    lanes = {}
    for start in (ds[0], ds[0] + timedelta(days=7)):
        html = s.post(base + "/ajax/ajax.schema.php", headers={"X-Requested-With": "XMLHttpRequest", "Referer": base + "/"},
                      form={"id_sport": v.get("sport", 1), "day": start.day, "month": start.month, "year": start.year,
                            "event": "changeDate", "timetableWidth": 656, "noticeCheckRequested": 0,
                            "noticeCheck": 0, "idNoticeCheck": 0})
        for name, per in parse_isport(html, want, ds[0]).items():
            lanes.setdefault(name, {}).update(per)
    if not lanes:
        raise RuntimeError("iSportSystem: v odpovědi chybí rozvrh")
    rows = []
    for name, per in lanes.items():
        if v.get("lane_filter") and v["lane_filter"].lower() not in name.lower():
            continue
        cells = {}
        for d in ds:
            ymd = d.isoformat()
            free, opening = per.get(ymd, ([], None))
            cells[ymd] = from_free_intervals(d, free, opening) if opening else "." * len(from_starts({}, None))
        rows.append({"id": name, "name": name.replace("Indoor kurt", "Kurt").strip(), "cells": cells})
    return rows


FETCHERS = {
    "courtyone": courtyone, "padelos": padelos, "bookaball": bookaball,
    "reservanto": reservanto, "sportelo": sportelo, "playtomic": playtomic, "isport": isport,
}

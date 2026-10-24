"""Spuštění: python -m checker [--dry-run] [--test-telegram] [--only ID]

Stáhne obsazenost všech center, uloží docs/data.json pro dashboard,
porovná se stavem z minulého běhu a pošle Telegram notifikaci na sloty,
které byly obsazené a teď jsou volné (v tvých časových oknech).
"""
import argparse
import json
import os
import sys
import time
import traceback
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from . import config
from .grid import GRID0, STEP, TZ, days, hm
from .sources import FETCHERS

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data.json"
STATE = ROOT / "state" / "notified.json"

DOW = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"]


def load(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def fits_window(d, start_min, dur):
    for ws, we in config.WINDOWS.get(d.weekday(), []):
        if start_min >= hm(ws) and (we is None or start_min + dur <= hm(we)):
            return True
    return False


def best_dur(code):
    return {"3": config.IDEAL_DURATION, "2": 90, "1": 60}.get(code, 0)


def qualifying(d, idx, code):
    dur = best_dur(code)
    if dur < config.MIN_DURATION:
        return 0
    start = GRID0 + idx * STEP
    # 120 se nevejde do okna? zkus aspoň 90
    for dd in sorted({dur, 90}, reverse=True):
        if dd <= dur and fits_window(d, start, dd):
            return dd
    return 0


def find_new_slots(new, old, now):
    """Vrátí [(venue, row, date, start_min, dur)] – nově uvolněné sloty."""
    oldv = {v["id"]: v for v in (old or {}).get("venues", []) if v.get("ok")}
    out = []
    for v in new["venues"]:
        ov = oldv.get(v["id"])
        if not v.get("ok") or not ov:
            continue
        orows = {r["id"]: r for r in ov["rows"]}
        for r in v["rows"]:
            orow = orows.get(r["id"])
            if not orow:
                continue
            for ymd, cells in r["cells"].items():
                ocells = orow["cells"].get(ymd)
                if not ocells or len(ocells) != len(cells):
                    continue
                d = datetime.fromisoformat(ymd).date()
                for i, c in enumerate(cells):
                    dur = qualifying(d, i, c)
                    if not dur:
                        continue
                    oc = ocells[i]
                    if oc == "." or qualifying(d, i, oc):
                        continue  # dřív neznámé, nebo už dřív volné
                    start = GRID0 + i * STEP
                    when = datetime(d.year, d.month, d.day, tzinfo=TZ) + timedelta(minutes=start)
                    if when <= now:
                        continue
                    out.append((v, r, d, start, dur))
    return out


def fmt_time(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def build_message(slots):
    lines = ["🎾 <b>Uvolnil se kurt!</b>"]
    by_venue = {}
    for v, r, d, start, dur in slots:
        g = by_venue.setdefault(v["id"], (v, {}))[1].setdefault((d, r["name"]), {"row": r, "starts": []})
        g["starts"].append(start)
    for v, groups in by_venue.values():
        lines.append("")
        lines.append(f"<b>{v['name']}</b>")
        for (d, name), g in sorted(groups.items(), key=lambda x: (x[0][0], x[0][1])):
            cells = g["row"]["cells"][d.isoformat()]
            starts = sorted(g["starts"])
            blocks = []  # sousední začátky → jeden blok volna od–do
            for s in starts:
                if blocks and blocks[-1][1] >= s:
                    continue
                # od nového začátku jdi dál, dokud se dá hrát (i přes dřív volné sloty)
                i = (s - GRID0) // STEP
                end = s
                while i < len(cells):
                    q = qualifying(d, i, cells[i])
                    if not q:
                        break
                    end = max(end, GRID0 + i * STEP + q)
                    i += 1
                blocks.append([s, end])
            shown = ", ".join(f"{fmt_time(a)}–{fmt_time(b)}" for a, b in blocks)
            lines.append(f"{DOW[d.weekday()]} {d.day}.{d.month}. · {name} · volno {shown}")
        lines.append(f'<a href="{v["url"]}">→ Rezervovat</a>')
    dash = os.environ.get("DASHBOARD_URL")
    tail = [""] + ([f'<a href="{dash}">Otevřít přehled</a>'] if dash else [])
    text = "\n".join(lines + tail)
    if len(text) > 3900:  # limit Telegramu je 4096 znaků
        out = []
        for ln in lines:
            if len("\n".join(out + [ln])) > 3600:
                break
            out.append(ln)
        out.append("…a další, celý seznam je v přehledu.")
        text = "\n".join(out + tail)
    return text


def send_telegram(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("! TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID nejsou nastavené – zprávu jen vypisuju:")
        print(text)
        return
    body = urllib.parse.urlencode({"chat_id": chat, "text": text, "parse_mode": "HTML",
                                   "disable_web_page_preview": "true"}).encode()
    with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", body, timeout=20) as r:
        r.read()


def fetch_all(only=None):
    venues = []
    for v in config.VENUES:
        if only and v["id"] not in only:
            continue
        t = time.time()
        entry = {k: v[k] for k in ("id", "name", "area", "url")}
        try:
            entry["rows"] = FETCHERS[v["type"]](v)
            entry["ok"] = True
            print(f"✓ {v['name']}: {len(entry['rows'])} kurtů ({time.time() - t:.1f}s)")
        except Exception as e:
            entry.update(ok=False, rows=[], error=f"{type(e).__name__}: {e}")
            print(f"✗ {v['name']}: {entry['error']}")
            traceback.print_exc(file=sys.stderr)
        venues.append(entry)
    return venues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="neposílat Telegram, nic neukládat")
    ap.add_argument("--test-telegram", action="store_true", help="poslat testovací zprávu a skončit")
    ap.add_argument("--only", nargs="*", help="jen vybraná centra (id z configu)")
    a = ap.parse_args()

    if a.test_telegram:
        send_telegram("🎾 Padel checker: Telegram funguje ✔")
        return

    now = datetime.now(TZ)
    old = load(DATA, None)
    venues = fetch_all(a.only)

    # Když nějaké centrum selže, necháme na dashboardu jeho poslední data.
    if old:
        prev = {v["id"]: v for v in old.get("venues", [])}
        for v in venues:
            if not v["ok"] and prev.get(v["id"], {}).get("rows"):
                v["rows"] = prev[v["id"]]["rows"]
                v["stale_since"] = prev[v["id"]].get("stale_since") or old.get("generated")

    new = {
        "generated": now.isoformat(timespec="seconds"),
        "days": [d.isoformat() for d in days()],
        "grid": {"start": config.GRID_START, "step": STEP, "n": config.GRID_SLOTS},
        "windows": {str(k): [[s, e] for s, e in w] for k, w in config.WINDOWS.items()},
        "venues": venues,
    }

    slots = find_new_slots(new, old, now)
    notified = load(STATE, {})
    cutoff = time.time() - config.RENOTIFY_HOURS * 3600
    notified = {k: t for k, t in notified.items() if t > cutoff}
    fresh = []
    for s in slots:
        key = f"{s[0]['id']}|{s[1]['id']}|{s[2].isoformat()}|{s[3]}"
        if key not in notified:
            fresh.append(s)
            notified[key] = time.time()
    print(f"Nově uvolněných slotů: {len(fresh)}")

    if fresh:
        msg = build_message(fresh)
        if a.dry_run:
            print(msg)
        else:
            send_telegram(msg)

    if not a.dry_run:
        DATA.parent.mkdir(parents=True, exist_ok=True)
        DATA.write_text(json.dumps(new, ensure_ascii=False, separators=(",", ":")))
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(notified))

    if not any(v["ok"] for v in venues):
        sys.exit(1)


if __name__ == "__main__":
    main()

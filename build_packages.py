#!/usr/bin/env python3
"""Crea site/data/packages.json.

Modalità:
  python scripts/build_packages.py --demo   dati dimostrativi, nessuna chiamata di rete
  python scripts/build_packages.py          prezzi dei voli reali da Aviasales (Travelpayouts Data API)

Variabili d'ambiente (modalità reale):
  TRAVELPAYOUTS_TOKEN   obbligatoria, il token dal tuo profilo Travelpayouts
  TP_MARKER             facoltativa, il tuo marker di affiliazione Travelpayouts
  BOOKING_AID           facoltativa, il tuo ID affiliato Booking.com

Solo libreria standard di Python, nessuna installazione.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "routes.json"
OUT = ROOT / "site" / "data" / "packages.json"

API = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
AVIASALES = "https://www.aviasales.com"
MIN_NIGHTS, MAX_NIGHTS = 2, 5
MIN_DAYS_AHEAD = 7


def parse_day(value):
    """'2026-11-14T10:35:00+01:00' -> date(2026, 11, 14)"""
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


def fetch_prices(origin, destination, month, token):
    """Chiede ad Aviasales i prezzi andata e ritorno per un mese. Ritorna una lista di offerte."""
    params = {
        "origin": origin,
        "destination": destination,
        "departure_at": month,
        "return_at": month,
        "one_way": "false",
        "currency": "eur",
        "sorting": "price",
        "limit": 100,
        "token": token,
    }
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"X-Access-Token": token, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.load(resp)
    if not body.get("success", False):
        raise RuntimeError(f"risposta non riuscita: {body.get('error')}")
    return body.get("data", [])


def pick_cheapest(offers, today):
    """Tra le offerte sceglie la più economica con partenza futura e 2-5 notti."""
    best = None
    for o in offers:
        try:
            dep, ret = parse_day(o["departure_at"]), parse_day(o["return_at"])
            price = float(o["price"])
        except (KeyError, ValueError, TypeError):
            continue
        nights = (ret - dep).days
        if dep < today + timedelta(days=MIN_DAYS_AHEAD) or not (MIN_NIGHTS <= nights <= MAX_NIGHTS):
            continue
        if best is None or price < best["price"]:
            best = {"price": price, "dep": dep, "ret": ret, "nights": nights, "offer": o}
    return best


def booking_url(city, checkin, checkout, aid):
    q = {"ss": city, "checkin": checkin.isoformat(), "checkout": checkout.isoformat(),
         "group_adults": 2, "no_rooms": 1}
    if aid:
        q["aid"] = aid
    return "https://www.booking.com/searchresults.html?" + urllib.parse.urlencode(q)


def flight_link(offer, marker):
    link = offer.get("link") or ""
    url = AVIASALES + link if link.startswith("/") else AVIASALES
    if marker:
        url += ("&" if "?" in url else "?") + "marker=" + urllib.parse.quote(marker)
    return url


def compose(city, dest, nights, dep, ret, flight_part, aid):
    """Unisce volo (o treno), alloggio, transfer e tessera in un pacchetto."""
    stay_eur = round(dest["hotel_pp_night"] * nights)
    parts = [flight_part, {
        "k": "alloggio", "t": f"{dest['stay']}, {nights} notti", "who": "Booking.com",
        "url": booking_url(dest["city"], dep, ret, aid), "eur": stay_eur, "estimate": True,
        "cta": "Cerca l'alloggio su Booking.com",
    }]
    if dest.get("transfer"):
        parts.append({**dest["transfer"], "k": "transfer", "estimate": True})
    parts.append({**dest["pass"], "k": "spostamenti", "estimate": True})
    return parts


def package(city_key, city, dest_key, dest, nights, dep, ret, flight_part, aid, demo):
    parts = compose(city, dest, nights, dep, ret, flight_part, aid)
    is_train = flight_part.get("train", False)
    return {
        "id": f"{city_key}-{dest_key}",
        "city": dest["city"], "geo": dest["geo"], "nights": nights,
        "depCity": city["name"], "region": city["region"],
        "depPlace": city["station"] if is_train else city["airport"],
        "from": city["iata"] if is_train else city["airport_iata"],
        "to": dest["iata"],
        "depart": dep.isoformat(), "ret": ret.isoformat(),
        "parts": parts,
        "total": sum(p["eur"] for p in parts),
        "livePrice": (not demo) and (not is_train),
    }


def build(config, demo, token=None, marker=None, aid=None, today=None, sleep=0.15):
    today = today or date.today()
    packs, skipped = [], []
    for r in config["routes"]:
        city, dest = config["cities"][r["from"]], config["destinations"][r["to"]]
        mode = r.get("mode", "flight")

        if mode == "train":
            nights = dest["nights"]
            dep = today + timedelta(days=(4 - today.weekday()) % 7 + 7)  # venerdì della prossima settimana
            ret = dep + timedelta(days=nights)
            t = r["train"]
            part = {"k": "volo", "train": True, "who": t["who"], "url": t["url"], "eur": t["eur"], "estimate": True,
                    "t": f"Treno alta velocità andata e ritorno {city['station']} – {dest['city']}",
                    "cta": f"Vai al sito di {t['who']}"}
            packs.append(package(r["from"], city, r["to"], dest, nights, dep, ret, part, aid, demo))
            continue

        if demo:
            nights = dest["nights"]
            dep = today + timedelta(days=(4 - today.weekday()) % 7 + 7)
            ret = dep + timedelta(days=nights)
            part = {"k": "volo", "who": "Aviasales", "url": AVIASALES, "eur": r["demo_price"], "estimate": True,
                    "t": f"Volo andata e ritorno {city['airport']} – {dest['city']}",
                    "cta": "Cerca il volo su Aviasales"}
            packs.append(package(r["from"], city, r["to"], dest, nights, dep, ret, part, aid, demo))
            continue

        best = None
        for month in sorted({today.strftime("%Y-%m"), (today + timedelta(days=31)).strftime("%Y-%m")}):
            try:
                found = pick_cheapest(fetch_prices(city["iata"], dest["iata"], month, token), today)
            except (urllib.error.URLError, RuntimeError, ValueError, TimeoutError) as e:
                print(f"  ! {city['name']} → {dest['city']} ({month}): {e}", file=sys.stderr)
                continue
            finally:
                time.sleep(sleep)
            if found and (best is None or found["price"] < best["price"]):
                best = found
        if not best:
            skipped.append(f"{city['name']} → {dest['city']}")
            continue
        o = best["offer"]
        airline = o.get("airline")
        part = {"k": "volo", "who": "Aviasales", "url": flight_link(o, marker), "eur": round(best["price"]),
                "t": f"Volo andata e ritorno {city['airport']} – {dest['city']}" + (f" (compagnia {airline})" if airline else ""),
                "cta": "Vedi il volo su Aviasales"}
        packs.append(package(r["from"], city, r["to"], dest, best["nights"], best["dep"], best["ret"], part, aid, demo))

    packs.sort(key=lambda p: p["total"])
    return packs, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="dati dimostrativi senza chiamate di rete")
    args = ap.parse_args()

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    token = os.environ.get("TRAVELPAYOUTS_TOKEN", "").strip()
    if not args.demo and not token:
        sys.exit("Manca TRAVELPAYOUTS_TOKEN. Imposta il segreto oppure usa --demo.")

    packs, skipped = build(config, args.demo, token, os.environ.get("TP_MARKER", "").strip() or None,
                           os.environ.get("BOOKING_AID", "").strip() or None)
    if skipped:
        print("Rotte senza offerte valide:", ", ".join(skipped), file=sys.stderr)
    if not packs:
        sys.exit("Nessun pacchetto creato: lascio invariato il file esistente.")

    today = date.today()
    monday = today - timedelta(days=today.weekday())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "demo": bool(args.demo),
        "weekStart": monday.isoformat(), "weekEnd": (monday + timedelta(days=6)).isoformat(),
        "packages": packs,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Creati {len(packs)} pacchetti ({'demo' if args.demo else 'prezzi reali'}) in {OUT}")


if __name__ == "__main__":
    main()

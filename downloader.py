import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, parse_qsl, urlencode, urlunparse
from icalendar import Calendar
from datetime import datetime
import pytz

# ---------- Globale HTTP-Session ----------
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Rapla-ICS-Downloader)"})

def _get(url):
    """Hilfsfunktion: lädt eine URL mit Fehlerbehandlung."""
    r = SESSION.get(url, timeout=30, allow_redirects=True)
    r.raise_for_status()
    return r

# ---------- iCal-Links finden ----------
def find_all_ical_links(html_url: str):
    """Sucht alle <link> und <a>-Tags, die ICS-Dateien verlinken."""
    try:
        r = _get(html_url)
    except Exception:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    links = set()

    # Variante 1: <link rel="alternate" type="text/calendar">
    for tag in soup.find_all("link", rel=True, href=True, type=True):
        rel = " ".join(tag.get("rel")) if isinstance(tag.get("rel"), list) else tag.get("rel", "")
        typ = tag.get("type", "")
        if "alternate" in (rel or "").lower() and "calendar" in (typ or "").lower():
            links.add(urljoin(html_url, tag["href"]))

    # Variante 2: <a href="...ical..." oder ".ics">
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href:
            continue
        if "ical" in href.lower() or href.lower().endswith(".ics"):
            links.add(urljoin(html_url, href))

    return list(links)

# ---------- Varianten testen ----------
def try_common_variants(base_url: str):
    """Probiere gängige URL-Varianten für Rapla-iCal."""
    parts = list(urlparse(base_url))
    q = dict(parse_qsl(parts[4]))
    candidates = []

    for param, value in [("page","ical"),("page","iCal"),("format","ical")]:
        qv = q.copy(); qv[param] = value
        parts_v = parts.copy(); parts_v[4] = urlencode(qv)
        candidates.append(urlunparse(parts_v))

    # Alternative Hauptpfad-Variante
    p = urlparse(base_url)
    qv = q.copy(); qv["page"] = "ical"
    parts_alt = [p.scheme, p.netloc, "/rapla", p.params, urlencode(qv), p.fragment]
    candidates.append(urlunparse(parts_alt))

    found = []
    for u in candidates:
        try:
            r = _get(u)
            if b"BEGIN:VCALENDAR" in r.content:
                found.append(u)
        except requests.RequestException:
            pass
    return found

# ---------- Kalender zusammenführen ----------
def merge_calendars(ics_bytes_list):
    """Führt mehrere ICS-Dateien zusammen (vermeidet doppelte UID)."""
    out = Calendar()
    out.add('PRODID', '-//Rapla Merge//ICS//DE')
    out.add('VERSION', '2.0')
    seen_uids = set()

    for data in ics_bytes_list:
        cal = Calendar.from_ical(data)
        for comp in cal.walk():
            if comp.name != "VEVENT":
                continue
            uid = str(comp.get("UID", "")) or str(comp.get("UID".upper(), ""))
            if uid in seen_uids:
                continue
            seen_uids.add(uid)
            out.add_component(comp)
    return out.to_ical()

# ---------- Hauptfunktion ----------
def download_ics_smart(html_url: str) -> bytes:
    """
    Holt alle erreichbaren iCal-Feeds (über HTML, bekannte Varianten)
    und führt sie ggf. zu einem Kalender zusammen.
    """
    links = set(find_all_ical_links(html_url))
    links.update(try_common_variants(html_url))

    ics_payloads = []
    for link in links:
        try:
            data = _get(link).content
            if b"BEGIN:VCALENDAR" in data:
                ics_payloads.append(data)
        except requests.RequestException:
            pass

    if not ics_payloads:
        raise FileNotFoundError("Kein iCal-Export gefunden – möglicherweise kein öffentlicher iCal verfügbar.")

    # Nur ein Kalender? Dann direkt zurückgeben
    if len(ics_payloads) == 1:
        return ics_payloads[0]

    # Mehrere Kalender? -> Zusammenführen
    return merge_calendars(ics_payloads)

# ---------- (optional) Filterfunktion ----------
def filter_events(ics_data: bytes, keep_keywords=None, tz="Europe/Berlin") -> bytes:
    """Optional: filtert nach Schlagwörtern wie Vorlesung, Übung, Praktikum."""
    if keep_keywords is None:
        keep_keywords = ["Vorlesung", "Üb", "Praktikum", "Übung", "Seminar", "Klausur"]

    cal_in = Calendar.from_ical(ics_data)
    cal_out = Calendar()
    for k in ("prodid", "version", "calscale", "method", "x-wr-calname", "x-wr-timezone"):
        if k.upper() in cal_in:
            cal_out.add(k.upper(), cal_in.get(k.upper()))
    if not cal_out.get("X-WR-TIMEZONE"):
        cal_out.add("X-WR-TIMEZONE", tz)

    tzinfo = pytz.timezone(tz)
    def _ensure_tz(dt):
        if dt is None:
            return None
        if isinstance(dt, datetime):
            if dt.tzinfo is None:
                return tzinfo.localize(dt)
            return dt.astimezone(tzinfo)
        return dt

    for comp in cal_in.walk("VEVENT"):
        summary = str(comp.get("SUMMARY", ""))
        if not any(kw.lower() in summary.lower() for kw in keep_keywords):
            continue
        cal_out.add_component(comp)

    return cal_out.to_ical()

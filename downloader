import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, parse_qsl, urlencode, urlunparse
from icalendar import Calendar, Event
from datetime import datetime
import pytz

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Rapla-ICS-Downloader)"})

def _get(url):
    r = SESSION.get(url, timeout=30, allow_redirects=True)
    r.raise_for_status()
    return r

def _try_variants(base_url: str):
    parts = list(urlparse(base_url))
    q = dict(parse_qsl(parts[4]))
    candidates = []

    for param, value in [("page","ical"),("page","iCal"),("format","ical")]:
        qv = q.copy(); qv[param] = value
        parts_v = parts.copy(); parts_v[4] = urlencode(qv)
        candidates.append(urlunparse(parts_v))

    p = urlparse(base_url)
    qv = q.copy(); qv["page"] = "ical"
    parts_alt = [p.scheme, p.netloc, "/rapla", p.params, urlencode(qv), p.fragment]
    candidates.append(urlunparse(parts_alt))

    for u in candidates:
        try:
            r = _get(u)
            if b"BEGIN:VCALENDAR" in r.content:
                return r.content
        except requests.RequestException:
            continue
    return None

def find_ical_link_in_html(html_url: str):
    try:
        r = _get(html_url)
    except Exception:
        return None
    soup = BeautifulSoup(r.text, "html.parser")

    # rel=alternate + type=text/calendar
    for tag in soup.find_all("link", rel=True, href=True, type=True):
        rel = " ".join(tag.get("rel")) if isinstance(tag.get("rel"), list) else tag.get("rel", "")
        typ = tag.get("type", "")
        if "alternate" in rel.lower() and "calendar" in typ.lower():
            return urljoin(html_url, tag["href"])

    # Fallback: <a> mit 'ical' oder '.ics'
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "ical" in href.lower() or href.lower().endswith(".ics"):
            return urljoin(html_url, href)
    return None

def download_ics_smart(html_url: str) -> bytes:
    ical_url = find_ical_link_in_html(html_url)
    if ical_url:
        data = _get(ical_url).content
        if b"BEGIN:VCALENDAR" in data:
            return data

    data = _try_variants(html_url)
    if data:
        return data

    raise FileNotFoundError("Kein iCal-Export gefunden. Auf dieser Rapla-Seite ist vermutlich kein öffentlicher iCal aktiviert.")

def filter_events(ics_data: bytes, keep_keywords=None, tz="Europe/Berlin") -> bytes:
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
        ev = Event()
        for prop in ("UID","SUMMARY","DESCRIPTION","LOCATION","CATEGORIES","URL","DTSTAMP","CREATED","LAST-MODIFIED"):
            if comp.get(prop):
                ev.add(prop, comp.get(prop))
        dtstart = _ensure_tz(comp.decoded("DTSTART", None))
        dtend = _ensure_tz(comp.decoded("DTEND", None))
        if dtstart: ev.add("DTSTART", dtstart)
        if dtend:   ev.add("DTEND", dtend)
        cal_out.add_component(ev)

    return cal_out.to_ical()

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, parse_qsl, urlencode, urlunparse
from icalendar import Calendar, Event
from datetime import datetime, date, timedelta
import pytz

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Rapla-ICS-Downloader)"})

def _get(url):
    r = SESSION.get(url, timeout=30, allow_redirects=True)
    r.raise_for_status()
    return r

# ---------- iCal-Ermittlung ----------
def find_all_ical_links(html_url: str):
    try:
        r = _get(html_url)
    except Exception:
        return [], None
    soup = BeautifulSoup(r.text, "html.parser")
    links = set()

    # 1) <link rel="alternate" type="text/calendar">
    for tag in soup.find_all("link", rel=True, href=True, type=True):
        rel = " ".join(tag.get("rel")) if isinstance(tag.get("rel"), list) else tag.get("rel", "")
        typ = tag.get("type", "")
        if "alternate" in (rel or "").lower() and "calendar" in (typ or "").lower():
            links.add(urljoin(html_url, tag["href"]))

    # 2) <a href> mit ical oder .ics
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href and ("ical" in href.lower() or href.lower().endswith(".ics")):
            links.add(urljoin(html_url, href))

    return sorted(links), soup

def try_common_variants(base_url: str):
    parts = list(urlparse(base_url))
    q = dict(parse_qsl(parts[4]))
    candidates = []

    for param, value in [("page","ical"),("page","iCal"),("format","ical")]:
        qv = q.copy(); qv[param] = value
        parts_v = parts.copy(); parts_v[4] = urlencode(qv)
        candidates.append(urlunparse(parts_v))

    # Alternative Basis
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
    return sorted(set(found))

def merge_calendars(ics_bytes_list):
    out = Calendar()
    out.add('PRODID', '-//Rapla Merge//ICS//DE')
    out.add('VERSION', '2.0')
    seen_uids = set()

    for data in ics_bytes_list:
        cal = Calendar.from_ical(data)
        for comp in cal.walk("VEVENT"):
            uid = str(comp.get("UID", "")) or str(comp.get("UID".upper(), ""))
            if uid in seen_uids:
                continue
            seen_uids.add(uid)
            out.add_component(comp)
    return out.to_ical()

# ---------- HTML → ICS (Fallback) ----------
TIME_RANGE_RE = re.compile(r"\b([01]?\d|2[0-3]):[0-5]\d\s*-\s*([01]?\d|2[0-3]):[0-5]\d\b")

def _parse_week_dates_from_headers(soup):
    """
    Versucht, die Datumsspalten einer Wochenansicht zu erkennen.
    Sucht nach Mustern wie 'Mo 12.11.' oder '12.11.2025' in Tabellen-Headern.
    """
    days = []
    # Häufig sind die Tagesköpfe in <th> oder <div class="...header...">
    headers = soup.find_all(["th", "div", "span"], text=True)
    date_re = re.compile(r"(\d{1,2})\.(\d{1,2})(?:\.(\d{2,4}))?")
    for h in headers:
        t = " ".join(h.get_text(strip=True).split())
        m = date_re.search(t)
        if not m:
            continue
        d, mth, y = int(m.group(1)), int(m.group(2)), m.group(3)
        if y:
            y = int(y) if len(y) == 4 else (2000 + int(y))
        else:
            # Jahr raten: nimm dieses oder nächstes, je nach Nähe
            today = date.today()
            y = today.year
        try:
            days.append(date(y, mth, d))
        except ValueError:
            pass
    # Eindeutig sortieren und deduplizieren
    days = sorted(list(dict.fromkeys(days)))
    return days

def scrape_html_to_ics(html_url, tz="Europe/Berlin"):
    """
    Heuristisches Scraping:
    - sucht in Event-Boxen/Texten nach 'HH:MM - HH:MM' und einem Titel drumherum
    - ordnet über Spalten-Header (Datum) dem passenden Tag zu
    Diese Heuristik deckt viele Rapla-Skins ab und liefert brauchbare ICS,
    falls kein brauchbarer iCal vorhanden ist.
    """
    r = _get(html_url)
    soup = BeautifulSoup(r.text, "html.parser")
    tzinfo = pytz.timezone(tz)

    cal = Calendar()
    cal.add('PRODID', '-//Rapla HTML Scrape//ICS//DE')
    cal.add('VERSION', '2.0')
    cal.add('X-WR-TIMEZONE', tz)

    week_days = _parse_week_dates_from_headers(soup)

    # Kandidaten für Event-Container (je nach Skin)
    candidates = soup.find_all(["div", "td", "li", "span"], text=True)
    for node in candidates:
        text = " ".join(node.get_text(" ", strip=True).split())
        if not text:
            continue
        m = TIME_RANGE_RE.search(text)
        if not m:
            continue

        # Titel heuristisch: Text ohne die Zeitspanne
        title = text.replace(m.group(0), "").strip(" -:")
        if not title:
            # Wenn in Kindern mehr Infos stehen, nimm die Eltern/Kindernamen
            title = node.get("title") or node.parent.get_text(" ", strip=True)[:80]

        # Uhrzeiten
        sh, eh = m.group(1), m.group(2)
        start_h, start_m = map(int, sh.split(":"))
        end_h, end_m = map(int, eh.split(":"))

        # Tag heuristisch: gehe nach nächstem Datumsknoten "in der Nähe"
        ev_date = None

        # suche in den Eltern/ Geschwistern nach Datumsmustern
        cur = node
        hops = 0
        while cur and hops < 5 and not ev_date:
            # Nachbarschaftstext
            sibling_texts = []
            if cur.previous_sibling:
                sibling_texts.append(str(getattr(cur.previous_sibling, "get_text", lambda **k: cur.previous_sibling)()))
            if cur.next_sibling:
                sibling_texts.append(str(getattr(cur.next_sibling, "get_text", lambda **k: cur.next_sibling)()))
            sibling_texts.append(str(getattr(cur.parent, "get_text", lambda **k: cur.parent)()))

            for st in sibling_texts:
                # suche Konkretdatum dd.mm(.yyyy)
                dm = re.search(r"(\d{1,2})\.(\d{1,2})(?:\.(\d{2,4}))?", st or "")
                if dm:
                    d, mo, yy = int(dm.group(1)), int(dm.group(2)), dm.group(3)
                    if yy:
                        yy = int(yy) if len(yy) == 4 else (2000 + int(yy))
                    else:
                        yy = date.today().year
                    try:
                        ev_date = date(yy, mo, d)
                        break
                    except ValueError:
                        pass
            cur = cur.parent
            hops += 1

        # Falls noch kein Datum: nimm den nächsten künftigen Wochentag aus Headern
        if not ev_date and week_days:
            # wähle den Tag, dessen Wochentag zum Spaltenindex passt – schwer ohne Layoutinfos,
            # daher fallback: nimm den ersten zukünftigen Header-Tag
            today = date.today()
            future = [d for d in week_days if d >= today - timedelta(days=1)]
            ev_date = future[0] if future else week_days[0]

        if not ev_date:
            # keine Datumsinfo -> überspringen
            continue

        dt_start = tzinfo.localize(datetime(ev_date.year, ev_date.month, ev_date.day, start_h, start_m))
        dt_end   = tzinfo.localize(datetime(ev_date.year, ev_date.month, ev_date.day, end_h, end_m))
        if dt_end <= dt_start:
            dt_end += timedelta(hours=1)  # Sicherheitsfallback

        ev = Event()
        ev.add("SUMMARY", title or "Vorlesung")
        ev.add("DTSTART", dt_start)
        ev.add("DTEND", dt_end)
        cal.add_component(ev)

    return cal.to_ical()

# ---------- Kombiniert: ICS-Merge oder Scrape ----------
def download_ics_or_scrape(html_url: str, tz="Europe/Berlin", debug=False):
    ical_links, soup = find_all_ical_links(html_url)
    variant_links = try_common_variants(html_url)
    all_links = sorted(set(ical_links + variant_links))

    if debug:
        print("Gefundene iCal-Links:")
        for u in all_links:
            print("  -", u)

    ics_payloads = []
    for link in all_links:
        try:
            r = _get(link)
            if b"BEGIN:VCALENDAR" in r.content:
                ics_payloads.append(r.content)
        except requests.RequestException:
            pass

    if ics_payloads:
        if debug:
            print(f"iCal-Quellen gefunden: {len(ics_payloads)} (merge falls >1)")
        return (merge_calendars(ics_payloads) if len(ics_payloads) > 1 else ics_payloads[0])

    if debug:
        print("Keine brauchbaren iCal-Quellen – nutze HTML-Scraping-Fallback.")
    return scrape_html_to_ics(html_url, tz=tz)

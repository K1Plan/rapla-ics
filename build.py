import os
from icalendar import Calendar
from downloader import download_ics_or_scrape

def main():
    rapla_url = os.environ["RAPLA_URL"]
    print("Quelle:", rapla_url)

    ics = download_ics_or_scrape(rapla_url, tz="Europe/Berlin", debug=True)

    out_path = "calendar.ics"
    with open(out_path, "wb") as f:
        f.write(ics)
    print(f"✓ geschrieben: {out_path}")

    # Kurzer Überblick: welche Titel sind drin?
    cal = Calendar.from_ical(ics)
    counter = {}
    for ev in cal.walk("VEVENT"):
        s = str(ev.get("SUMMARY", "")).strip() or "(ohne Titel)"
        counter[s] = counter.get(s, 0) + 1
    print("Top-Einträge:", sorted(counter.items(), key=lambda x: -x[1])[:10])

if __name__ == "__main__":
    main()

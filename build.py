import os
from downloader import download_ics_smart, filter_events

def main():
    rapla_url = os.environ["RAPLA_URL"]
    print("Hole Kalender von:", rapla_url)
    try:
        ics_raw = download_ics_smart(rapla_url)
    except Exception as e:
        print("✗ Fehler beim Download:", e)
        return

    ics_filtered = filter_events(ics_raw, keep_keywords=["Vorlesung", "Üb", "Praktikum"], tz="Europe/Berlin")
    out_path = "calendar.ics"
    with open(out_path, "wb") as f:
        f.write(ics_filtered)
    print(f"✓ Fertig: {out_path}")

if __name__ == "__main__":
    main()

# 📅 DHBW Rapla → ICS Auto-Updater

Dieses Repository lädt automatisch deinen DHBW-Rapla-Kalender, filtert auf Vorlesungen, Übungen und Praktika und speichert die Datei als `calendar.ics`.

## 🚀 Einrichtung

1. Gehe zu **Settings → Secrets → Actions** und füge ein neues Secret hinzu:
   - **Name:** `RAPLA_URL`
   - **Wert:** Dein persönlicher Rapla-Link (z. B. `https://rapla.dhbw.de/rapla/internal_calendar?key=...`)

2. Der GitHub Action Workflow läuft **stündlich** und erzeugt/aktualisiert die Datei `calendar.ics`.

3. Die abonnierbare URL lautet:


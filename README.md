# 📅 DHBW Rapla → Auto-Updating ICS Calendar

This project automatically converts your **DHBW Rapla timetable** into an `.ics` calendar file that you can subscribe to in **Google Calendar**, **Apple Calendar**, **Outlook**, or any other calendar app.

It runs entirely through **GitHub Actions** — the calendar updates automatically every hour (or at any interval you choose).

---

## 🚀 Features

* ✅ Automatically fetches your **Rapla calendar** via your personal link  
* 🔁 **Updates every hour** by default  
* 🧩 Supports multiple iCal feeds (merged into one)  
* 🧠 Automatically falls back to **HTML scraping** if Rapla’s iCal export is disabled  
* 🔒 Uses **GitHub Secrets** — your private Rapla key is never stored in the repository  
* 🗓️ Produces a single public `.ics` file that you can **subscribe to or download**

---

## 🧭 How It Works

1. **GitHub Actions** runs a Python script automatically (hourly by default).  
2. The script fetches your Rapla calendar:
   * If an iCal export exists, it downloads and merges all feeds.  
   * If no iCal is available, it parses the HTML timetable directly.  
3. All events are saved as one clean file:  
   **calendar.ics**  
4. The workflow commits this file back to your repository.  
5. You can then subscribe to it via a permanent link.

---

## 🧩 Setup — Use This with Your Own Rapla Link

### 1️⃣ Fork this repository

Click the **“Fork”** button at the top right of this page to create your own copy.

---

### 2️⃣ Add your Rapla link as a GitHub Secret

In your forked repository:

Go to **Settings → Secrets and variables → Actions → New repository secret**

**Name:** `RAPLA_URL`  
**Value:** your personal Rapla calendar link

---

Example:
----
https://rapla.dhbw.de/rapla/internal_calendar?key=YOUR_KEY&salt=YOUR_SALT
----

⚠️ This key is personal — do **not** share it publicly.

---

### 3️⃣ (Optional) Change the update interval

Open `.github/workflows/publish.yml` and edit this part:

----
schedule:
  - cron: "0 * * * *"   # runs every hour (UTC)
----

You can change the timing (in UTC):

| Example        | Description                             |
| -------------- | --------------------------------------- |
| "0 6 * * *"    | once per day at 06:00 UTC (≈ 07:00 CET) |
| "*/30 * * * *" | every 30 minutes                        |
| "0 */4 * * *"  | every 4 hours                           |

---

### 4️⃣ Run the workflow manually (first time)

1. Go to the **Actions** tab  
2. Select **“Build and publish ICS”**  
3. Click **“Run workflow”**

Within about a minute, a file called **calendar.ics** will appear in your repository root.

---

## 🔗 Subscribe to Your Calendar

Use this URL (replace with your GitHub username and repo name):

----
https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/calendar.ics
----

Then add it to your calendar app:

### 🟢 Google Calendar

1. Open **Google Calendar**  
2. Go to **Settings → Add calendar → From URL**  
3. Paste the link above  
4. Click **Add calendar**

It will refresh automatically every few hours.

### 🍎 Apple Calendar (macOS)

1. Go to **File → New Calendar Subscription**  
2. Paste the link  
3. Set **Auto-Refresh** to “Every hour” (recommended)

### 💼 Outlook (Web)

1. Open the **Calendar** view  
2. Click **Add calendar → Subscribe from web**  
3. Paste the link  
4. Save — it will sync automatically

---

## 🧠 Troubleshooting

### ❗ Only “Informatik 2” or one module appears

Rapla often provides separate iCal exports per module.  
The script automatically merges all available links — but if Rapla only exposes one, it will only show that module.  
The HTML scraper fallback should still collect **all visible events** from the timetable.

### ❗ No events appear in the subscribed calendar

* Ensure your repo is **public** (GitHub raw links are only accessible publicly).  
* Try removing and re-adding the calendar (some apps cache old versions).  
* Check your `calendar.ics` file: does it contain future `DTSTART` dates?  
  If not, your Rapla view might not show future weeks — adjust your Rapla filter.

### ❗ The file imports fine but subscription stays empty

This can happen if events lack UIDs or timestamps.  
The current version of this script adds both (`UID` and `DTSTAMP`) so recurring updates should now work correctly.

---

## 🧾 File Overview

| File                          | Purpose                                                            |
| ----------------------------- | ------------------------------------------------------------------ |
| .github/workflows/publish.yml | GitHub Actions workflow — runs automatically on schedule           |
| build.py                      | Main script that downloads your Rapla feed and writes calendar.ics |
| downloader.py                 | Logic for iCal fetching, merging, and HTML scraping                |
| requirements.txt              | Python dependencies                                                |
| calendar.ics                  | Generated calendar file (output)                                   |

---

## ⚙️ Dependencies (handled automatically)

The workflow installs these Python libraries:

----
requests  
beautifulsoup4  
icalendar  
pytz  
----

---

## 💡 Tips & Customization

* You can change which events are kept by editing `filter_events()` in `downloader.py`.  
  Example: include only ["Vorlesung", "Übung", "Klausur"].  
* You can host the resulting `.ics` file anywhere (GitHub, your website, etc.).  
* The calendar includes **unique UIDs** and **timestamps** so your subscription stays synchronized.

---

## 🤝 For Other Users

Anyone with their own Rapla link can use this project!

1. **Fork** the repository  
2. **Add your Rapla link** as `RAPLA_URL` secret  
3. **Run the workflow**  
4. **Subscribe** to your own calendar file

Each user’s calendar stays **private** and independent — the repository itself contains no personal data.

---

## 🧑‍💻 Credits

Developed for **DHBW students** who want an automated, privacy-friendly way to sync their Rapla schedule with modern calendar apps.

Contributions and improvements are always welcome — just make sure never to publish private Rapla keys.

This project was created with help from AI

---

**License:** MIT © 2025

#!/usr/bin/env python3
"""
Waybar Prayer Times & Adzan Countdown
-------------------------------------
Lightweight, zero-dependency prayer times countdown module for Waybar.
Features:
- Auto geolocation via IP (no manual lat/lon setup required)
- Kemenag RI calculation method (Method 20, customizable)
- Real-time countdown to next prayer
- Smart daily local caching (works offline, saves bandwidth)
- Desktop notifications at adzan time via notify-send

Author: Kisworo (github.com/kisworo)
License: MIT
"""

import os
import sys
import json
import time
import urllib.request
import datetime
import subprocess
import argparse

CACHE_DIR = os.path.expanduser("~/.cache")
CACHE_FILE = os.path.join(CACHE_DIR, "waybar-prayer-times.json")
CONFIG_FILE = os.path.expanduser("~/.config/waybar-prayer.conf")

PRAYER_NAMES = {
    "Fajr": "Subuh",
    "Sunrise": "Terbit",
    "Dhuhr": "Dzuhur",
    "Asr": "Ashar",
    "Maghrib": "Maghrib",
    "Isha": "Isya"
}

def load_user_config():
    """Load optional user config from ~/.config/waybar-prayer.conf"""
    config = {
        "city": os.environ.get("PRAYER_CITY", "auto"),
        "method": int(os.environ.get("PRAYER_METHOD", 20)),  # 20 = Kemenag RI
        "notification": True
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip().lower(), v.strip().strip('"').strip("'")
                        if k == "city":
                            config["city"] = v
                        elif k == "method":
                            config["method"] = int(v)
                        elif k == "notification":
                            config["notification"] = v.lower() in ["true", "1", "yes"]
        except Exception:
            pass
    return config

def get_location(city_config="auto"):
    """Get location coordinates automatically via IP, or fallback to Jakarta"""
    if city_config and city_config.lower() != "auto":
        # Search coordinates for specific city name
        try:
            url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(city_config)}&format=json&limit=1"
            req = urllib.request.Request(url, headers={"User-Agent": "WaybarPrayerTimes/1.0"})
            with urllib.request.urlopen(req, timeout=4) as r:
                results = json.loads(r.read().decode())
                if results:
                    return {
                        "city": city_config.title(),
                        "lat": float(results[0]["lat"]),
                        "lon": float(results[0]["lon"]),
                        "country": "Indonesia"
                    }
        except Exception:
            pass

    # Auto IP Geolocation
    try:
        req = urllib.request.Request("http://ip-api.com/json", headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=4) as r:
            data = json.loads(r.read().decode())
            if data.get("status") == "success":
                return {
                    "city": data.get("city", "Jakarta"),
                    "lat": float(data.get("lat", -6.2088)),
                    "lon": float(data.get("lon", 106.8456)),
                    "country": data.get("country", "Indonesia")
                }
    except Exception:
        pass

    # Fallback to ipapi.co
    try:
        req = urllib.request.Request("https://ipapi.co/json/", headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=4) as r:
            data = json.loads(r.read().decode())
            if "latitude" in data:
                return {
                    "city": data.get("city", "Jakarta"),
                    "lat": float(data.get("latitude", -6.2088)),
                    "lon": float(data.get("longitude", 106.8456)),
                    "country": data.get("country_name", "Indonesia")
                }
    except Exception:
        pass

    return {"city": "Jakarta", "lat": -6.2088, "lon": 106.8456, "country": "Indonesia"}

def fetch_prayer_times(lat, lon, method=20):
    """Fetch timings from Aladhan API"""
    try:
        ts = int(time.time())
        url = f"https://api.aladhan.com/v1/timings/{ts}?latitude={lat}&longitude={lon}&method={method}"
        req = urllib.request.Request(url, headers={"User-Agent": "WaybarPrayerTimes/1.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
            if data.get("code") == 200:
                raw = data["data"]["timings"]
                clean = {}
                for k in ["Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha"]:
                    clean[k] = raw.get(k, "00:00")[:5]
                return clean
    except Exception:
        pass
    return None

def get_data(force=False, city_override="auto"):
    today_str = datetime.date.today().isoformat()
    cfg = load_user_config()
    city_target = city_override if city_override != "auto" else cfg["city"]

    # Check cache
    if not force and os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                cached = json.load(f)
            if cached.get("date") == today_str and "timings" in cached:
                if city_target == "auto" or cached.get("city", "").lower() == city_target.lower():
                    return cached
        except Exception:
            pass

    # Fetch fresh data
    loc = get_location(city_target)
    timings = fetch_prayer_times(loc["lat"], loc["lon"], cfg["method"])
    if not timings and os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass

    if not timings:
        timings = {
            "Fajr": "04:26", "Sunrise": "05:43", "Dhuhr": "11:46",
            "Asr": "14:56", "Maghrib": "17:48", "Isha": "18:57"
        }

    data = {
        "date": today_str,
        "city": loc["city"],
        "country": loc.get("country", "Indonesia"),
        "lat": loc["lat"],
        "lon": loc["lon"],
        "timings": timings
    }
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass
    return data

def parse_time(time_str, date_obj):
    h, m = map(int, time_str.split(":"))
    return datetime.datetime.combine(date_obj, datetime.time(h, m))

def notify_user(title, message):
    try:
        subprocess.run(["notify-send", "-u", "normal", "-a", "Adzan", title, message],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def main():
    parser = argparse.ArgumentParser(description="Waybar Prayer Times & Countdown")
    parser.add_argument("--force", action="store_true", help="Force refresh data from API")
    parser.add_argument("--notify", action="store_true", help="Send desktop notification with today's schedule")
    parser.add_argument("--city", type=str, default="auto", help="Override city name")
    parser.add_argument("--list", action="store_true", help="Print schedule directly to terminal")
    args = parser.parse_args()

    data = get_data(force=args.force, city_override=args.city)
    timings = data["timings"]
    city = data["city"]
    now = datetime.datetime.now()
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)

    fardhu = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]
    next_prayer = None
    next_dt = None

    for p in fardhu:
        p_dt = parse_time(timings[p], today)
        if p_dt > now:
            next_prayer = p
            next_dt = p_dt
            break

    if not next_prayer:
        next_prayer = "Fajr"
        next_dt = parse_time(timings["Fajr"], tomorrow)

    diff = next_dt - now
    diff_minutes = max(0, int(diff.total_seconds() // 60))
    hours = diff_minutes // 60
    mins = diff_minutes % 60
    p_name = PRAYER_NAMES[next_prayer]

    if args.list:
        print(f"Jadwal Sholat ({city}) - {today.isoformat()}")
        print("-" * 35)
        for code, label in PRAYER_NAMES.items():
            mark = "➤ " if code == next_prayer else "  "
            print(f"{mark}{label:<8} : {timings[code]}")
        print(f"\nBerikutnya: {p_name} ({diff_minutes} menit lagi)")
        return

    # Desktop notification action (--notify)
    if args.notify:
        sched_lines = []
        for code, label in PRAYER_NAMES.items():
            mark = "➤ " if code == next_prayer else "  "
            sched_lines.append(f"{mark}{label:<7}: {timings[code]}")
        body = f"Lokasi: {city} (Auto)\nBerikutnya: {p_name} ({diff_minutes}m lagi)\n\n" + "\n".join(sched_lines)
        notify_user("📅 Jadwal Sholat Hari Ini", body)
        return

    # Text format for Waybar
    if diff_minutes <= 1:
        text = f"🕌 Waktunya {p_name}!"
        css_class = "adzan"
        flag_file = f"/tmp/adzan_notif_{p_name}_{today.isoformat()}"
        if not os.path.exists(flag_file):
            try:
                open(flag_file, "w").close()
            except Exception:
                pass
            notify_user(f"🕌 Waktu Sholat {p_name}!", f"Telah masuk waktu sholat {p_name} untuk wilayah {city} dan sekitarnya.")
    elif diff_minutes < 60:
        text = f"🕌 {p_name} -{diff_minutes}m"
        css_class = "warning" if diff_minutes <= 15 else "normal"
    else:
        text = f"🕌 {p_name} -{hours}j {mins:02d}m"
        css_class = "normal"

    # Tooltip text
    tooltip_lines = [
        f"🕌 Jadwal Sholat ({city})",
        "─────────────────────────"
    ]
    for code, label in PRAYER_NAMES.items():
        time_str = timings[code]
        if code == next_prayer:
            remaining_str = f"({diff_minutes}m lagi)" if diff_minutes < 60 else f"({hours}j {mins}m lagi)"
            tooltip_lines.append(f"➤ {label:<7}: {time_str}  {remaining_str}")
        else:
            tooltip_lines.append(f"  {label:<7}: {time_str}")

    tooltip_lines.append("─────────────────────────")
    tooltip_lines.append("🖱️ Klik: Notifikasi jadwal")
    tooltip_lines.append("🖱️ Klik Kanan: Perbarui lokasi")

    out = {
        "text": text,
        "tooltip": "\n".join(tooltip_lines),
        "class": css_class,
        "alt": p_name
    }
    print(json.dumps(out))

if __name__ == "__main__":
    main()

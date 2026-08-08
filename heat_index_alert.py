"""
Heat Risk Alert — per-user version
--------------------------------------
Reads each user's saved settings from Firebase Realtime Database
(city + Celsius threshold, keyed by their Telegram chat_id), checks
the live heat index for their city, and sends a Telegram message
directly to that user if their threshold is reached.

Firebase data shape (as saved by the companion app):
  users/
    6225843135: "[\"Dumaguete\",30]"   # value is a JSON-encoded [city, threshold_C] string

Required environment variables:
  FIREBASE_CRED_PATH   -> path to Firebase service account JSON
  FIREBASE_DB_URL      -> https://heatriskapp-default-rtdb.firebaseio.com
  OWM_API_KEY          -> OpenWeatherMap API key
  TELEGRAM_BOT_TOKEN   -> Telegram bot token from BotFather

Install: pip install firebase-admin requests
"""

import os
import json
import logging
import requests
import firebase_admin
from firebase_admin import credentials, db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("heat_risk_alert")

FIREBASE_CRED_PATH = os.environ["FIREBASE_CRED_PATH"]
FIREBASE_DB_URL = os.environ["FIREBASE_DB_URL"]
OWM_API_KEY = os.environ["OWM_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

OWM_URL = "https://api.openweathermap.org/data/2.5/weather"
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_CRED_PATH)
        firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DB_URL})
    log.info("Firebase initialized.")


def get_users():
    ref = db.reference("users")
    users = ref.get() or {}
    log.info(f"Loaded {len(users)} user record(s) from Firebase.")
    return users


def parse_user_record(chat_id: str, raw_value):
    try:
        parsed = json.loads(raw_value)
        city = str(parsed[0]).strip()
        threshold_c = float(parsed[1])
        return city, threshold_c
    except (TypeError, ValueError, IndexError, json.JSONDecodeError) as e:
        log.warning(f"Skipping user '{chat_id}': couldn't parse record {raw_value!r} ({e})")
        return None


def fetch_weather_metric(city: str):
    params = {"q": f"{city},PH", "appid": OWM_API_KEY, "units": "metric"}
    try:
        resp = requests.get(OWM_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data["main"]["temp"], data["main"]["humidity"]
    except requests.RequestException as e:
        log.error(f"Weather fetch failed for '{city}': {e}")
        return None
    except (KeyError, ValueError) as e:
        log.error(f"Unexpected weather response for '{city}': {e}")
        return None


def compute_heat_index_celsius(temp_c: float, humidity: float) -> float:
    T = temp_c * 9 / 5 + 32
    R = humidity

    if T < 80:
        hi_f = T
    else:
        hi_f = (
            -42.379 + 2.04901523 * T + 10.14333127 * R
            - 0.22475541 * T * R - 0.00683783 * T * T
            - 0.05481717 * R * R + 0.00122874 * T * T * R
            + 0.00085282 * T * R * R - 0.00000199 * T * T * R * R
        )
        if R < 13 and 80 <= T <= 112:
            hi_f -= ((13 - R) / 4) * ((17 - abs(T - 95)) / 17) ** 0.5
        if R > 85 and 80 <= T <= 87:
            hi_f += ((R - 85) / 10) * ((87 - T) / 5)

    hi_c = (hi_f - 32) * 5 / 9
    return round(hi_c, 1)


def send_telegram_message(chat_id: str, text: str) -> bool:
    payload = {"chat_id": chat_id, "text": text}
    try:
        resp = requests.post(TELEGRAM_URL, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        log.error(f"Telegram send failed for chat_id {chat_id}: {e}")
        return False


def process_user(chat_id: str, raw_value):
    record = parse_user_record(chat_id, raw_value)
    if record is None:
        return

    city, threshold_c = record
    weather = fetch_weather_metric(city)
    if weather is None:
        return

    temp_c, humidity = weather
    heat_index_c = compute_heat_index_celsius(temp_c, humidity)

    log.info(f"[{chat_id}] {city}: temp={temp_c}C humidity={humidity}% heat_index={heat_index_c}C (threshold={threshold_c}C)")

    if heat_index_c >= threshold_c:
        message = (
            f"⚠️ Heat Risk Alert — {city}\n"
            f"Current heat index: {heat_index_c}°C (your threshold: {threshold_c}°C)\n"
            f"Temperature: {temp_c}°C, Humidity: {humidity}%\n"
            f"Stay hydrated and avoid prolonged sun exposure."
        )
        if send_telegram_message(chat_id, message):
            log.info(f"Alert sent to chat_id {chat_id}.")
    else:
        log.info(f"No alert needed for chat_id {chat_id}.")


def main():
    init_firebase()
    users = get_users()
    if not users:
        log.info("No users found in Firebase. Exiting.")
        return
    for chat_id, raw_value in users.items():
        process_user(chat_id, raw_value)


if __name__ == "__main__":
    main()

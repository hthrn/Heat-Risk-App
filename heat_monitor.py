"""
Negros Oriental Heat Index Monitor
------------------------------------
Checks the live heat index for every city and municipality in Negros
Oriental, Philippines, and posts an alert to a Telegram channel for
any locality that has reached the configured threshold.

Required environment variables:
  OWM_API_KEY          -> OpenWeatherMap API key
  TELEGRAM_BOT_TOKEN   -> Telegram bot token from BotFather
  TELEGRAM_CHANNEL_ID  -> numeric channel ID, e.g. -1001234567890
  HEAT_INDEX_THRESHOLD -> optional, defaults to 105 (Fahrenheit)

Install: pip install requests
"""

import os
import logging
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("negor_heat_monitor")

OWM_API_KEY = os.environ["OWM_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]
HEAT_INDEX_THRESHOLD = float(os.environ.get("HEAT_INDEX_THRESHOLD", 105))

OWM_URL = "https://api.openweathermap.org/data/2.5/weather"
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# 6 component cities + 19 municipalities of Negros Oriental
NEGROS_ORIENTAL_LGUS = [
    "Bais,PH", "Bayawan,PH", "Canlaon,PH", "Dumaguete,PH", "Guihulngan,PH", "Tanjay,PH",
    "Amlan,PH", "Ayungon,PH", "Bacong,PH", "Basay,PH", "Bindoy,PH", "Dauin,PH",
    "Jimalalud,PH", "La Libertad,PH", "Mabinay,PH", "Manjuyod,PH", "Pamplona,PH",
    "San Jose,PH", "Santa Catalina,PH", "Siaton,PH", "Sibulan,PH", "Tayasan,PH",
    "Valencia,PH", "Vallehermoso,PH", "Zamboanguita,PH",
]


def fetch_weather(city: str):
    params = {"q": city, "appid": OWM_API_KEY, "units": "imperial"}
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


def compute_heat_index(temp_f: float, humidity: float) -> float:
    T, R = temp_f, humidity
    if T < 80:
        return T

    hi = (
        -42.379 + 2.04901523 * T + 10.14333127 * R
        - 0.22475541 * T * R - 0.00683783 * T * T
        - 0.05481717 * R * R + 0.00122874 * T * T * R
        + 0.00085282 * T * R * R - 0.00000199 * T * T * R * R
    )

    if R < 13 and 80 <= T <= 112:
        hi -= ((13 - R) / 4) * ((17 - abs(T - 95)) / 17) ** 0.5
    if R > 85 and 80 <= T <= 87:
        hi += ((R - 85) / 10) * ((87 - T) / 5)

    return round(hi, 1)


def send_telegram_message(text: str) -> bool:
    payload = {"chat_id": TELEGRAM_CHANNEL_ID, "text": text}
    try:
        resp = requests.post(TELEGRAM_URL, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        log.error(f"Telegram send failed: {e}")
        return False


def check_lgu(lgu: str):
    weather = fetch_weather(lgu)
    if weather is None:
        return

    temp_f, humidity = weather
    heat_index = compute_heat_index(temp_f, humidity)
    town_name = lgu.split(",")[0]

    log.info(f"{town_name}: temp={temp_f}F humidity={humidity}% heat_index={heat_index}F")

    if heat_index >= HEAT_INDEX_THRESHOLD:
        message = (
            f"⚠️ Heat Index Alert — {town_name}, Negros Oriental\n"
            f"Current heat index: {heat_index}°F (threshold: {HEAT_INDEX_THRESHOLD}°F)\n"
            f"Temperature: {temp_f}°F, Humidity: {humidity}%\n"
            f"Stay hydrated and avoid prolonged sun exposure."
        )
        if send_telegram_message(message):
            log.info(f"Alert posted for {town_name}.")


def main():
    for lgu in NEGROS_ORIENTAL_LGUS:
        check_lgu(lgu)


if __name__ == "__main__":
    main()

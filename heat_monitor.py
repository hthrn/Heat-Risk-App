import os
import requests

# --- CONFIGURATION VIA ENVIRONMENT VARIABLES ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY')

# Channel handle (e.g., @YourChannelHandle) or numeric Channel ID
CHANNEL_ID = "@YOUR_NEGROS_ORIENTAL_CHANNEL" 

# Firebase endpoint storing your list of Negros Oriental cities
FIREBASE_CITIES_URL = "https://heatriskapp-default-rtdb.firebaseio.com/negros_oriental_cities.json"

# Fallback locations if Firebase is empty/unreachable
FALLBACK_CITIES = ["Dumaguete", "Bais", "Tanjay", "Bayawan", "Guihulngan"]


def get_pagasa_heat_tier(heat_index):
    """
    Categorizes the heat index (feels_like in °C) according to official PAGASA levels.
    """
    if heat_index >= 52.0:
        return {
            "level": "☠️ EXTREME DANGER",
            "advice": "Heat stroke is imminent! Avoid all outdoor physical activity."
        }
    elif heat_index >= 42.0:
        return {
            "level": "🔴 DANGER",
            "advice": "Heat cramps and heat exhaustion are likely. Heat stroke is probable with continued exposure. Stay indoors."
        }
    elif heat_index >= 33.0:
        return {
            "level": "🟠 EXTREME CAUTION",
            "advice": "Heat cramps and heat exhaustion are possible. Limit direct sun exposure and drink plenty of water."
        }
    elif heat_index >= 27.0:
        return {
            "level": "🟡 CAUTION",
            "advice": "Fatigue is possible with prolonged exposure. Stay hydrated throughout the day."
        }
    else:
        return {
            "level": "🟢 NORMAL / SAFE",
            "advice": "Heat index is within comfortable safety limits."
        }


def fetch_target_cities():
    """Fetches list of Negros Oriental cities stored in Firebase Realtime Database."""
    try:
        response = requests.get(FIREBASE_CITIES_URL, timeout=10)
        if response.status_code == 200 and response.json():
            return response.json()
    except Exception as e:
        print(f"Error fetching from Firebase: {e}")
    
    print("Using fallback city list.")
    return FALLBACK_CITIES


def fetch_weather(city_name):
    """Queries OpenWeatherMap API for live temperature and heat index in Celsius."""
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city_name},PH&units=metric&appid={OPENWEATHER_API_KEY}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return {
                "temp": round(data["main"]["temp"], 1),
                "heat_index": round(data["main"]["feels_like"], 1)
            }
    except Exception as e:
        print(f"Error fetching weather for {city_name}: {e}")
    return None


def send_telegram_bulletin(message_text):
    """Posts formatted bulletin to the Telegram Channel."""
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": message_text,
        "parse_mode": "Markdown"
    }
    res = requests.post(telegram_url, json=payload)
    return res.json()


def run_heat_risk_check():
    cities = fetch_target_cities()
    report_lines = ["🌴 *NEGROS ORIENTAL HEAT INDEX BULLETIN* 🇵🇭\n"]

    for city in cities:
        weather = fetch_weather(city)
        if weather:
            temp = weather["temp"]
            heat_index = weather["heat_index"]
            tier = get_pagasa_heat_tier(heat_index)

            city_block = (
                f"📍 *{city}*\n"
                f"• Actual Temp: `{temp}°C` | Heat Index: `{heat_index}°C`\n"
                f"• PAGASA Level: {tier['level']}\n"
                f"• Guidance: _{tier['advice']}_\n"
            )
            report_lines.append(city_block)

    full_bulletin = "\n".join(report_lines)
    res = send_telegram_bulletin(full_bulletin)
    print("Post result:", res)


if __name__ == "__main__":
    run_heat_risk_check()

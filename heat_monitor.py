import requests
import json

# --- CONFIGURATION ---
FIREBASE_DATABASE_URL = "https://heatriskapp-default-rtdb.firebaseio.com"  # Base URL without trailing slash
OPENWEATHER_API_KEY = "YOUR_OPENWEATHER_API_KEY"
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "6225843135"

def get_firebase_user_data(chat_id):
    """
    Fetches ["Dumaguete", "31"] stored under the Chat ID node in Firebase.
    """
    url = f"{FIREBASE_DATABASE_URL}/{chat_id}.json"
    response = requests.get(url)
    
    if response.status_code == 200 and response.json():
        # Firebase returns JSON string array: ["Dumaguete", "31"]
        data = response.json()
        city = data[0]
        threshold = float(data[1])
        return city, threshold
    else:
        print("Failed to fetch data from Firebase.")
        return None, None

def get_live_weather(city_name):
    """
    Queries OpenWeatherMap API for live temperature in Celsius.
    """
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city_name}&units=metric&appid={OPENWEATHER_API_KEY}"
    response = requests.get(url)
    
    if response.status_code == 200:
        weather_data = response.json()
        temp = weather_data["main"]["temp"]
        feels_like = weather_data["main"]["feels_like"]
        return temp, feels_like
    else:
        print(f"Error fetching weather from OpenWeatherMap: {response.status_code}")
        return None, None

def send_telegram_notification(chat_id, message):
    """
    Sends message to Telegram user via Bot API.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    return response.json()

def check_and_notify():
    # 1. Read from Firebase
    city, threshold = get_firebase_user_data(CHAT_ID)
    if not city or threshold is None:
        return

    # 2. Get OpenWeather data
    current_temp, feels_like = get_live_weather(city)
    if current_temp is None:
        return

    # 3. Format message depending on threshold condition
    if current_temp >= threshold:
        header = "⚠️ *HEAT RISK WARNING!*"
        status = "🚨 *Status:* Threshold reached or exceeded! Take precautions."
    else:
        header = "ℹ️ *Routine Temperature Update*"
        status = "✅ *Status:* Conditions are safe (below threshold)."

    # Construct complete update text
    message = (
        f"{header}\n\n"
        f"📍 *Location:* {city}\n"
        f"🌡️ *Current Temp:* {current_temp}°C\n"
        f"☀️ *Feels Like:* {feels_like}°C\n"
        f"🎯 *Set Threshold:* {threshold}°C\n\n"
        f"{status}"
    )

    # 4. ALWAYS send notification to Telegram
    res = send_telegram_notification(CHAT_ID, message)
    if res.get("ok"):
        print("Telegram notification sent successfully!")
    else:
        print(f"Failed to send Telegram message: {res}")

# Run function
if __name__ == "__main__":
    check_and_notify()
    

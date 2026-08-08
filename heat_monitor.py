import os
import requests

FIREBASE_URL = os.environ.get("FIREBASE_URL")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")

def get_city_heat_index(city_name):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={OPENWEATHER_API_KEY}&units=metric"
    response = requests.get(url).json()
    
    if response.get("cod") == 200:
        temp = response["main"]["temp"]
        feels_like = response["main"]["feels_like"]
        return max(temp, feels_like)
    else:
        print(f"Failed to fetch weather for {city_name}: {response.get('message')}")
        return None

def send_telegram_alert(chat_id, city, temp, threshold):
    message = (
        f"⚠️ *HEAT RISK ALERT*\n\n"
        f"📍 *Location:* {city}\n"
        f"🌡️ *Current Heat Index:* {temp:.1f}°C\n"
        f"🎯 *Your Set Threshold:* {threshold:.1f}°C\n\n"
        f"Stay hydrated and take necessary precautions!"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=payload)

def main():
    if not FIREBASE_URL or not TELEGRAM_BOT_TOKEN or not OPENWEATHER_API_KEY:
        print("Missing required environment secrets.")
        return

    db_url = FIREBASE_URL.rstrip('/') + '/.json'
    response = requests.get(db_url)
    if response.status_code != 200 or not response.json():
        print("No user data found in Firebase.")
        return

    data = response.json()

    # Handle both nested 'users' structure from App Inventor and root structure
    users_data = data.get("users", data) if isinstance(data, dict) else data

    for chat_id, user_info in users_data.items():
        try:
            # Handle list layout saved from App Inventor [City, Threshold]
            if isinstance(user_info, list) and len(user_info) >= 2:
                city = user_info[0]
                threshold = float(user_info[1])
            elif isinstance(user_info, dict):
                city = user_info.get("city")
                threshold = float(user_info.get("threshold", 0))
            else:
                continue

            current_temp = get_city_heat_index(city)
            
            if current_temp is not None:
                print(f"User {chat_id} ({city}): Current = {current_temp}°C, Threshold = {threshold}°C")
                if current_temp >= threshold:
                    print(f"Sending alert to {chat_id}...")
                    send_telegram_alert(chat_id, city, current_temp, threshold)
        except Exception as e:
            print(f"Error evaluating user {chat_id}: {e}")

if __name__ == "__main__":
    main()

import requests
from datetime import datetime, timedelta, timezone
import time
import os
import threading
from flask import Flask

# Настройки Telegram (лучше через переменные окружения)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "7792007489:AAFF2Ud1QDsneeAzigHM8i1w7VMOj3ScQ90")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "7583703295")
LOG_FILE = "mlb_signal_log.txt"
YEKT = timezone(timedelta(hours=5))
app = Flask(__name__)

def send_telegram_message(text):
    """Отправка сообщения в Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        response = requests.post(url, params=params)
        return response.json()
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")
        return None

def get_today_date():
    """Текущая дата в формате YYYY-MM-DD"""
    return datetime.utcnow().strftime('%Y-%m-%d')

def clean_team_name(name):
    """Конвертируем названия команд в формат MLB для URL"""
    name = name.lower().strip()
    team_map = {
        "d-backs": "dbacks", "diamondbacks": "dbacks",
        "white sox": "whitesox", "blue jays": "bluejays",
        "red sox": "redsox", "royals": "royals",
        "tigers": "tigers", "twins": "twins",
        "indians": "guardians", "guardians": "guardians",
        "astros": "astros", "angels": "angels",
        "athletics": "athletics", "mariners": "mariners",
        "rangers": "rangers", "braves": "braves",
        "marlins": "marlins", "mets": "mets",
        "phillies": "phillies", "nationals": "nationals",
        "cubs": "cubs", "reds": "reds",
        "brewers": "brewers", "pirates": "pirates",
        "cardinals": "cardinals", "dodgers": "dodgers",
        "padres": "padres", "giants": "giants",
        "rockies": "rockies", "rays": "rays",
        "orioles": "orioles", "yankees": "yankees"
    }
    short_name = name.split()[-1] if " " in name else name
    return team_map.get(short_name, short_name)

def format_game_url(game):
    """Генерируем корректную ссылку на матч"""
    home_team = game.get("teams", {}).get("home", {}).get("team", {})
    away_team = game.get("teams", {}).get("away", {}).get("team", {})
    home_name = clean_team_name(home_team.get("name", ""))
    away_name = clean_team_name(away_team.get("name", ""))
    date_utc = game.get("gameDate", "").split("T")[0]
    game_pk = game.get("gamePk")
    
    if not all([home_name, away_name, date_utc, game_pk]):
        return "Ссылка отсутствует"
    
    return f"https://www.mlb.com/gameday/{away_name}-vs-{home_name}/{date_utc.replace('-', '/')}/{game_pk}/live"

def utc_to_yekt(dt_str):
    """Конвертируем UTC время в Екатеринбург"""
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ")
        return dt.replace(tzinfo=timezone.utc).astimezone(YEKT).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return dt_str

def check_and_send_signals():
    print(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Проверка матчей...")
    
    try:
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={get_today_date()}&hydrate=linescore"
        headers = {'User-Agent': 'Mozilla/5.0'}
        data = requests.get(url, headers=headers).json()
        games = data.get("dates", [{}])[0].get("games", [])
    except Exception as e:
        print(f"Ошибка получения данных: {e}")
        return

    sent_signals = set()
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            sent_signals.update(line.strip() for line in f)

    new_signals = []
    
    for game in games:
        status = game.get("status", {}).get("detailedState", "").lower()
        if status != "in progress":
            continue

        linescore = game.get("linescore", {})
        current_inning = linescore.get("currentInning", 0)
        inning_half = linescore.get("inningHalf", "").lower()
        
        if inning_half != "top" or current_inning < 4 or current_inning > 9:
            continue

        score_home = game.get("teams", {}).get("home", {}).get("score", 0)
        score_away = game.get("teams", {}).get("away", {}).get("score", 0)
        if score_home != 0 or score_away != 0:
            continue

        game_pk = game.get("gamePk")
        if not game_pk or str(game_pk) in sent_signals:
            continue

        home_team = game.get("teams", {}).get("home", {}).get("team", {}).get("name", "?")
        away_team = game.get("teams", {}).get("away", {}).get("team", {}).get("name", "?")
        game_time = utc_to_yekt(game.get("gameDate", ""))
        game_url = format_game_url(game)

        message = (
            f"⚾ <b>MLB Сигнал! (ИНН {current_inning})</b>\n"
            f"▸ <b>{away_team} vs {home_team}</b>\n"
            f"▸ Время: {game_time}\n"
            f"▸ Счёт: 0-0 (Top {current_inning})\n"
            f"▸ <a href='{game_url}'>Смотреть на MLB.com</a>"
        )

        print(f"Найден подходящий матч: {away_team} vs {home_team} (ИНН {current_inning})")
        send_telegram_message(message)
        new_signals.append(str(game_pk))

    if new_signals:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write("\n".join(new_signals) + "\n")

    print(f"Проверено матчей: {len(games)}, новых сигналов: {len(new_signals)}")

def mlb_tracker_loop():
    while True:
        try:
            check_and_send_signals()
        except Exception as e:
            print(f"Критическая ошибка: {e}")
        time.sleep(300)  # Проверка каждые 5 минут

@app.route('/')
def home():
    return "MLB Tracker работает! Последняя проверка: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def run_flask():
    app.run(host='0.0.0.0', port=10000)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    print("MLB Tracker запущен. Ожидание матчей 0-0 (4-9 иннинг)...")
    mlb_tracker_loop()

import time
from datetime import datetime, time as dt_time

from handle_user_data import get_all_telegram_ids
from main import bot_telegram

MEAL_TIMES = {
    "colazione": (dt_time(7, 0), dt_time(11, 0)),
    "pranzo": (dt_time(11, 0), dt_time(15, 0)),
    "cena": (dt_time(16, 0), dt_time(23, 0)),
}





def extract_meal_type(current_time):
    for meal_type, (start_time, end_time) in MEAL_TIMES.items():
        if start_time <= current_time <= end_time:
            return meal_type
    return ""


@bot_telegram.message_handler(func=lambda message: True)
def handle_user_meal(telegram_id, message_text, mysql_cursor):
    food = message_text.strip()
    current_time = datetime.now().time()
    meal_type = extract_meal_type(current_time)

    if meal_type:
        save_user_meal(telegram_id, meal_type, food, mysql_cursor)


def save_user_meal(user_id, meal_type, food, mysql_cursor):
    current_time = datetime.now()
    current_date = current_time.date()
    week_number = current_time.strftime("%U")
    weekday = current_time.strftime("%A").lower()

    sql_query = (
        "INSERT INTO utenti (telegram_id, weekly_diet_last_week, weekly_diet_counter) "
        "VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE weekly_diet_last_week = %s, weekly_diet_counter = weekly_diet_counter + 1"
    )
    mysql_cursor.execute(sql_query, (user_id, week_number, 1, week_number))

    column_name = f'weekly_meals_{week_number}_{weekday}_{meal_type}_food'
    sql_query = f"UPDATE utenti SET {column_name} = %s WHERE telegram_id = %s"
    mysql_cursor.execute(sql_query, (food, user_id))


def send_periodic_reminders(telegram_ids, bot_telegram):
    for telegram_id in telegram_ids:
        for meal_type in MEAL_TIMES:
            send_meal_reminder(telegram_id, meal_type, bot_telegram)


def send_meal_reminder(telegram_id, meal_type, bot_telegram):
    try:
        current_time = datetime.now().time()

        if meal_type in MEAL_TIMES and MEAL_TIMES[meal_type][0] <= current_time <= MEAL_TIMES[meal_type][1]:
            bot_telegram.send_message(telegram_id, f"{meal_type.capitalize()}! Cosa hai mangiato a {meal_type}?")
        else:
            print(f"Non è il momento giusto per il pasto {meal_type}.")
    except Exception as e:
        print(f"Errore durante l'invio del promemoria pasto: {e}")


def periodic_reminder(telegram_id, message, mysql_cursor_reminder, bot_telegram_reminder):
    while True:
        telegram_ids = get_all_telegram_ids()
        send_periodic_reminders(telegram_ids, bot_telegram_reminder)
        handle_user_meal(telegram_id, message, mysql_cursor_reminder)
        time.sleep(60 * 60 * 24)

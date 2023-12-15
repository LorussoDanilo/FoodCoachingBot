# La tua funzione per inviare i promemoria periodici
from datetime import datetime, time

from handle_user_data import get_all_telegram_ids


def send_periodic_reminders(telegram_id, user_profiles_collection, bot_telegram):
    telegram_ids = get_all_telegram_ids(user_profiles_collection)
    for telegram_id in telegram_ids:
        send_meal_reminder(telegram_id, "colazione", bot_telegram)
        send_meal_reminder(telegram_id, "pranzo", bot_telegram)
        send_meal_reminder(telegram_id, "cena", bot_telegram)
    return telegram_id


# Funzione che invia i messaggi di reminder all'utente.
def send_meal_reminder(telegram_id, meal_type, bot_telegram):
    if telegram_id is not None and isinstance(telegram_id, int) and telegram_id >= 0:
        current_time = datetime.now().time()
        if meal_type == "colazione" and time(7) <= current_time <= time(11, 0):
            bot_telegram.send_message(telegram_id, "Buongiorno! Cosa hai mangiato a colazione?")
        elif meal_type == "pranzo" and time(11) <= current_time <= time(15, 0):
            bot_telegram.send_message(telegram_id, "Pranzo time! Cosa hai mangiato a pranzo?")
        elif meal_type == "cena" and time(16, 0) <= current_time <= time(23, 0):
            bot_telegram.send_message(telegram_id, "Cena! Cosa hai mangiato a cena?")
    else:
        print("Chat ID non valido:", telegram_id)


# Funzione per eseguire le attività periodicamente
def periodic_task(user_profiles_collection, bot_telegram, event):
    while not event.wait(60 * 60 * 24):  # Wait for 24 hours
        send_periodic_reminders(user_profiles_collection, bot_telegram)
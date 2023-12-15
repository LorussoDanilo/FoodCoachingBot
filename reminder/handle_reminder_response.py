# Funzione che gestisce i pasti inviati dall'utente
from datetime import datetime, time

from pymongo import UpdateOne


def handle_user_meal(user_id, message_text, user_profiles_collection):
    # Puoi implementare la tua logica per estrarre i dati relativi al cibo dal messaggio
    # Ad esempio, puoi usare espressioni regolari o altri metodi di parsing
    # Qui, supponiamo che il messaggio contenga solo il cibo inserito dall'utente
    food = message_text.strip()

    # Otteniamo il tipo di pasto in base all'orario attuale
    current_time = datetime.now().time()
    meal_type = ""
    if time(7) <= current_time <= time(11, 0):
        meal_type = "colazione"
    elif time(11) <= current_time <= time(15, 0):
        meal_type = "pranzo"
    elif time(16, 0) <= current_time <= time(23, 0):
        meal_type = "cena"

    if meal_type:
        # Salva il pasto nel database
        save_user_meal(user_id, meal_type, food, user_profiles_collection)


# Metodo per salvare sul database la dieta settimanale dell'utente
def save_user_meal(user_id, meal_type, food, user_profiles_collection):
    current_time = datetime.now()

    # Trova il profilo utente corrispondente
    user_profile = user_profiles_collection.find_one({'telegram_id': user_id})

    # Controlla se il profilo utente esiste
    if user_profile:
        # Ottieni la data corrente
        current_date = current_time.date()

        # Ottieni la settimana corrente e il giorno della settimana
        week_number = current_time.strftime("%U")
        weekday = current_time.strftime("%A").lower()

        # Verifica se è cambiata la settimana
        if 'last_week' in user_profile.get('weekly_meals', {}):
            last_week = user_profile['weekly_meals']['last_week']
            if last_week != week_number:
                # Aggiorna il contatore settimanale e salva la settimana attuale
                user_profiles_collection.update_one(
                    {'telegram_id': user_id},
                    {
                        '$set': {
                            'weekly_diet.last_week': week_number,
                            'weekly_diet.counter': user_profile.get('weekly_meals', {}).get('counter', 0) + 1
                        }
                    }
                )

        # Costruisci il percorso nel documento per inserire il pasto
        path = f'weekly_meals.{week_number}.days.{weekday}.{meal_type}.food'

        # Crea l'oggetto UpdateOne per l'operazione di aggiornamento
        update_operation = UpdateOne(
            {'telegram_id': user_id},
            {'$set': {path: food}},
            upsert=True
        )

        # Esegui l'operazione di aggiornamento nel database
        user_profiles_collection.bulk_write([update_operation])


# Funzione che gestisce i pasti inviati dall'utente
from datetime import datetime, time


def handle_user_meal(user_id, message_text, mysql_cursor):
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
        save_user_meal(user_id, meal_type, food, mysql_cursor)


def save_user_meal(user_id, meal_type, food, mysql_cursor):
    current_time = datetime.now()

    # Ottieni la data corrente
    current_date = current_time.date()

    # Ottieni la settimana corrente e il giorno della settimana
    week_number = current_time.strftime("%U")
    weekday = current_time.strftime("%A").lower()

    # Verifica se è cambiata la settimana
    mysql_cursor.execute("SELECT weekly_diet_last_week, weekly_diet_counter FROM utenti WHERE telegram_id = %s",
                         (user_id,))
    result = mysql_cursor.fetchone()

    if result:
        last_week, counter = result

        if last_week != week_number:
            # Aggiorna il contatore settimanale e salva la settimana attuale
            mysql_cursor.execute(
                "UPDATE utenti SET weekly_diet_last_week = %s, weekly_diet_counter = %s WHERE telegram_id = %s",
                (week_number, counter + 1, user_id))
    else:
        # Se l'utente non ha ancora una voce nella tabella utenti, inseriscila
        mysql_cursor.execute(
            "INSERT INTO utenti (telegram_id, weekly_diet_last_week, weekly_diet_counter) VALUES (%s, %s, %s)",
            (user_id, week_number, 1))

    # Costruisci il percorso nel documento per inserire il pasto
    column_name = f'weekly_meals_{week_number}_{weekday}_{meal_type}_food'
    sql_query = f"UPDATE utenti SET {column_name} = %s WHERE telegram_id = %s"

    # Esegui l'operazione di aggiornamento nel database
    mysql_cursor.execute(sql_query, (food, user_id))

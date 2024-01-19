import calendar
from datetime import datetime


def get_or_insert_dieta_settimanale(cursor, telegram_id, date):
    # Cerca se esiste già una riga per la data nella tabella dieta_settimanale
    cursor.execute("SELECT dieta_settimanale_id FROM dieta_settimanale WHERE telegram_id = %s AND data = %s",
                   (telegram_id, date))
    dieta_settimanale_id = cursor.fetchone()

    if dieta_settimanale_id:
        # Se esiste già, restituisci l'ID
        return dieta_settimanale_id[0]
    else:
        # Altrimenti, inserisci una nuova riga e restituisci il nuovo ID
        cursor.execute("INSERT INTO dieta_settimanale (dieta_settimanale_id, telegram_id, data) VALUES (%s, %s, %s)",
                       (0, telegram_id, date))
        return cursor.fetchone()[0]


def get_or_insert_giorno_settimana(cursor, dieta_settimanale_id, weekday_name):
    # Cerca se esiste già una riga per il giorno nella tabella giorno_settimana
    cursor.execute("SELECT giorno_settimana_id FROM giorno_settimana WHERE dieta_settimanale_id = %s AND nome = %s",
                   (dieta_settimanale_id, weekday_name))
    giorno_settimana_id = cursor.fetchone()

    if giorno_settimana_id:
        # Se esiste già, restituisci l'ID
        return giorno_settimana_id[0]
    else:
        # Altrimenti, inserisci una nuova riga e restituisci il nuovo ID
        cursor.execute("INSERT INTO giorno_settimana (dieta_settimanale_id, nome) VALUES (%s, %s)",
                       (dieta_settimanale_id, weekday_name))
        cursor.execute("SELECT LAST_INSERT_ID()")  # Ottieni l'ID dell'ultima riga inserita
        return cursor.fetchone()[0]


def get_or_insert_periodo_giorno(cursor, giorno_settimana_id, meal_type):
    # Cerca se esiste già una riga per il periodo_giorno nella tabella periodo_giorno
    cursor.execute("SELECT periodo_giorno_id FROM periodo_giorno WHERE nome = %s AND giorno_settimana_id = %s",
                   (meal_type, giorno_settimana_id))
    periodo_giorno_id = cursor.fetchone()

    if periodo_giorno_id:
        # Se esiste già, restituisci l'ID
        return periodo_giorno_id[0]
    else:
        # Altrimenti, inserisci una nuova riga e restituisci il nuovo ID
        cursor.execute("INSERT INTO periodo_giorno (nome, giorno_settimana_id) VALUES (%s, %s)",
                       (meal_type, giorno_settimana_id))
        cursor.execute("SELECT LAST_INSERT_ID()")  # Ottieni l'ID dell'ultima riga inserita
        return cursor.fetchone()[0]


# Funzione per gestire la risposta del pasto
def save_user_food_response(bot_telegram, mysql_cursor, mysql_connection, telegram_id, meal_type, food_name):

    try:
        datetime.now().time()
        date = datetime.now().date()

        # Ottieni o inserisci l'ID della riga nella tabella dieta_settimanale
        dieta_settimanale_id = get_or_insert_dieta_settimanale(mysql_cursor, telegram_id, date)

        # Ottieni il nome del giorno della settimana (es. "Monday")
        weekday_name = calendar.day_name[date.weekday()]

        # Ottieni o inserisci l'ID della riga nella tabella giorno_settimana
        giorno_settimana_id = get_or_insert_giorno_settimana(mysql_cursor, dieta_settimanale_id, weekday_name)

        # Ottieni o inserisci l'ID della riga nella tabella periodo_giorno
        periodo_giorno_id = get_or_insert_periodo_giorno(mysql_cursor, giorno_settimana_id, meal_type)

        # Inserisci il cibo nella tabella cibo
        mysql_cursor.execute("INSERT INTO cibo (nome, periodo_giorno_id) VALUES (%s, %s)",
                             (food_name, periodo_giorno_id))

        # Esegui il commit delle modifiche al database
        mysql_connection.commit()

        return bot_telegram.send_message(telegram_id, f"{meal_type} inserito/a correttamente!")

    except Exception as e:
        print(f"Errore durante l'inserimento del cibo: {e}")

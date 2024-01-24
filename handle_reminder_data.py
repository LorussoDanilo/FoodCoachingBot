import calendar
import locale
from datetime import datetime

# Imposta la lingua italiana per il modulo locale
locale.setlocale(locale.LC_TIME, 'it_IT')


def get_or_insert_dieta_settimanale(cursor, telegram_id, date):
    try:
        # Cerca se esiste già una riga per la data o la data successiva nella tabella dieta_settimanale
        cursor.execute(
            "SELECT dieta_settimanale_id FROM dieta_settimanale WHERE telegram_id = %s AND (data = %s OR data = DATE_ADD(%s, INTERVAL 1 DAY))",
            (telegram_id, date, date))
        existing_row = cursor.fetchone()

        if existing_row:
            # Se esiste già, restituisci l'ID
            return existing_row[0]
        else:
            # Ottieni l'indice massimo attuale per l'utente
            cursor.execute("SELECT MAX(dieta_settimanale_id) FROM dieta_settimanale WHERE telegram_id = %s", (telegram_id,))
            max_dieta_settimanale_id = cursor.fetchone()[0]

            # Incrementa l'indice
            new_dieta_settimanale_id = max_dieta_settimanale_id + 1 if max_dieta_settimanale_id is not None else 1

            # Inserisci una nuova riga con l'indice incrementato
            cursor.execute(
                "INSERT INTO dieta_settimanale (dieta_settimanale_id, telegram_id, data) VALUES (%s, %s, %s)",
                (new_dieta_settimanale_id, telegram_id, date))

            return new_dieta_settimanale_id
    except Exception as e:
        print(f"get_or_insert_dieta_settimanale: {e}")



def get_or_insert_giorno_settimana(cursor, dieta_settimanale_id, weekday_name):
    try:
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
    except Exception as e:
        print(f"insert_giorno settimana: {e}")



def get_or_insert_periodo_giorno(cursor, giorno_settimana_id, meal_type):
    try:
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
    except Exception as e:
        print(f"insert_periodo_giorno: {e}")


# Funzione per gestire la risposta del pasto
def save_user_food_response(bot_telegram, mysql_cursor, mysql_connection, telegram_id, meal_type, food_name):

    try:
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

        return bot_telegram.send_message(telegram_id,
                                         f"{meal_type} inserito/a correttamente! Ora puoi chiedermi ciò che desideri 😊")

    except Exception as e:
        print(f"Errore durante l'inserimento del cibo: {e}")


def get_food_for_day(telegram_id, dieta_data, nome_giorno, cursor):
    # Ottieni l'ID della dieta settimanale per la data specificata
    cursor.execute("SELECT dieta_settimanale_id FROM dieta_settimanale WHERE telegram_id = ? AND data = ?",
                   (telegram_id, dieta_data))
    result = cursor.fetchone()

    if result is None:
        # Nessuna dieta trovata per la data specificata
        return []

    dieta_settimanale_id = result[0]

    # Ottieni l'ID del giorno della settimana
    cursor.execute("SELECT giorno_settimana_id FROM giorno_settimana WHERE nome = ? AND dieta_settimanale_id = ?",
                   (nome_giorno, dieta_settimanale_id))
    result = cursor.fetchone()

    if result is None:
        # Nessun giorno della settimana trovato con il nome specificato
        return []

    giorno_settimana_id = result[0]

    # Ottieni i cibi per il giorno specificato
    cursor.execute("""
        SELECT cibo.nome, cibo.calorie
        FROM cibo
        INNER JOIN periodo_giorno ON cibo.periodo_giorno_id = periodo_giorno.periodo_giorno_id
        WHERE periodo_giorno.giorno_settimana_id = ?
    """, (giorno_settimana_id,))

    cibi_giorno = []
    for row in cursor.fetchall():
        cibo = {'nome': row[0], 'calorie': row[1]}
        cibi_giorno.append(cibo)

    return cibi_giorno


def get_dieta_dates_by_telegram_id(telegram_id, mysql_cursor):
    try:
        # Esegui la query per ottenere le date della dieta per un determinato utente
        mysql_cursor.execute("SELECT DISTINCT data FROM dieta_settimanale WHERE telegram_id = %s", (telegram_id,))

        # Recupera i risultati della query
        result = mysql_cursor.fetchall()

        # Restituisci le date delle diete
        dieta_dates = [row[0] for row in result]
        return dieta_dates

    except Exception as e:
        # Gestisci eventuali eccezioni
        print(f"Errore durante l'ottenimento delle date della dieta: {e}")
        return []



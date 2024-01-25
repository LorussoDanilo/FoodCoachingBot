"""
Questo modulo contiene le funzioni che servono per gestire l'invio dei reminder e il successivo salvataggio nel database delle risposte
degli utenti dopo i reminder

    Danilo Lorusso - Version 1.0
"""

import calendar
import locale
from datetime import datetime, timedelta

from src.handle_user_data import get_all_telegram_ids
from src.controls import check_time_in_range
import time as trem

# Imposta la lingua italiana per il modulo locale
locale.setlocale(locale.LC_TIME, 'it_IT')


def send_reminder_message(event, bot_telegram, ORA_COLAZIONE_START, ORA_COLAZIONE_END, ORA_PRANZO_START, ORA_PRANZO_END,
                          ORA_CENA_START, ORA_CENA_END):
    """
        Questa funzione serve per inviare in determinati eventi temporali dei reminder per conoscere
         la dieta settimanale dell'utente

        :param event: serve per gestire gli eventi e alternare l'esecuzione dei metodi
        :type event: Event
        :param bot_telegram: corrisponde alla variabile che contiene l'api key del proprio bot_telegram
                            e permette di accedere ai metodi della libreria Telebot
        :type bot_telegram: Telebot
        :param ORA_COLAZIONE_START: inizio dell'intervallo per l'ora di colazione
        :type ORA_COLAZIONE_START: time.py
        :param ORA_COLAZIONE_END: fine dell'intervallo per l'ora di colazione
        :type ORA_COLAZIONE_END: time.py
        :param ORA_PRANZO_START: inizio dell'intervallo per l'ora di pranzo
        :type ORA_PRANZO_START: time.py
        :param ORA_PRANZO_END: fine dell'intervallo per l'ora di pranzo
        :type ORA_PRANZO_END: time.py
        :param ORA_CENA_START: inizio dell'intervallo per l'ora di cena
        :type ORA_CENA_START: time.py
        :param ORA_CENA_END: fine dell'intervallo per l'ora di cena
        :type ORA_CENA_END: time.py


        :return: il reminder da inviare all'utente
        :rtype: Message
        """
    telegram_ids = get_all_telegram_ids()

    current_time_reminder = datetime.now().time()
    # Serializzazione dell'oggetto Message

    while event.is_set():
        for telegram_id in telegram_ids:
            if check_time_in_range(current_time_reminder, ORA_COLAZIONE_START, ORA_COLAZIONE_END):
                bot_telegram.send_message(telegram_id, "Buongiorno! Cosa hai mangiato a colazione?", trem.sleep(10))

            elif check_time_in_range(current_time_reminder, ORA_PRANZO_START, ORA_PRANZO_END):
                bot_telegram.send_message(telegram_id, "Pranzo time! Cosa hai mangiato a pranzo?", trem.sleep(10))

            elif check_time_in_range(current_time_reminder, ORA_CENA_START, ORA_CENA_END):
                bot_telegram.send_message(telegram_id, "Cena! Cosa hai mangiato a cena?", trem.sleep(10))


# chat_id checks id corresponds to your list or not.
def send_week_reminder_message(event, bot_telegram):
    """
    Questa funzione serve per inviare un reminder settimanale per ricordare di visualizzare
     i dati della dieta settimanale

    :param event: serve per gestire gli eventi e alternare l'esecuzione dei metodi
    :type event: Event
    :param bot_telegram: corrisponde alla variabile che contiene l'api key del proprio bot_telegram
                        e permette di accedere ai metodi della libreria Telebot
    :type bot_telegram: Telebot

    :return: il reminder da inviare all'utente
    :rtype: Message
    """
    telegram_ids = get_all_telegram_ids()

    datetime.now().time()
    # Serializzazione dell'oggetto Message
    while not event.is_set():
        for telegram_id in telegram_ids:
            bot_telegram.send_message(telegram_id,
                                      "E' passata una settimana! Tieni d'occhio la tua dieta. Tocca su /dashboard",
                                      trem.sleep(60 * 60 * 24 * 7))


def get_or_insert_dieta_settimanale(cursor, telegram_id, date):
    """
    Questa funzione serve per ottenere la dieta settimanale corrente oppure inserire
    una nuova dieta settimanale nel momento in cui passa una settimana

    :param cursor: serve per eseguire le query
    :type cursor: Cursor
    :param telegram_id: telegram_id dell'utente
    :type telegram_id: int
    :param date: serve per ottenere la data corrente
    :type date: date

    :return: l'id della dieta settimanale
    :rtype: int
    """
    try:
        # Cerca se esiste già una riga per la data o la data successiva nella tabella dieta_settimanale
        cursor.execute(
            "SELECT dieta_settimanale_id, data FROM dieta_settimanale WHERE telegram_id = %s AND (data = %s OR data = "
            "DATE_ADD(%s, INTERVAL 1 DAY))",
            (telegram_id, date, date))
        existing_row = cursor.fetchone()

        if existing_row:
            # Se esiste già, restituisci l'ID
            return existing_row[0]
        else:
            # Ottieni l'indice massimo attuale per l'utente
            cursor.execute("SELECT MAX(dieta_settimanale_id) FROM dieta_settimanale WHERE telegram_id = %s",
                           (telegram_id,))
            max_dieta_settimanale_id = cursor.fetchone()[0]

            # Ottieni la data della dieta settimanale precedente (se esiste)
            if max_dieta_settimanale_id is not None:
                cursor.execute(
                    "SELECT data FROM dieta_settimanale WHERE telegram_id = %s AND dieta_settimanale_id = %s",
                    (telegram_id, max_dieta_settimanale_id))
                last_week_date = cursor.fetchone()

                if last_week_date:
                    # Calcola la data successiva
                    next_week_date = last_week_date[0] + timedelta(days=7)
                    # Se la data attuale è successiva alla data della settimana precedente, incrementa l'ID
                    if date >= next_week_date:
                        new_dieta_settimanale_id = max_dieta_settimanale_id + 1
                    else:
                        new_dieta_settimanale_id = max_dieta_settimanale_id
                else:
                    new_dieta_settimanale_id = max_dieta_settimanale_id + 1
            else:
                new_dieta_settimanale_id = 1

            # Inserisci una nuova riga con l'indice incrementato
            cursor.execute(
                "INSERT INTO dieta_settimanale (dieta_settimanale_id, telegram_id, data) VALUES (%s, %s, %s)",
                (new_dieta_settimanale_id, telegram_id, date))

            return new_dieta_settimanale_id
    except Exception as e:
        print(f"get_or_insert_dieta_settimanale: {e}")


def get_or_insert_giorno_settimana(cursor, dieta_settimanale_id, weekday_name):
    """
        Questa funzione serve per ottenere il giorno della settimana corrente o inserirne uno se non esiste

        :param cursor: serve per eseguire le query
        :type cursor: Cursor
        :param dieta_settimanale_id: l'ultimo dieta_settimanale_id inserito
        :type dieta_settimanale_id: int
        :param weekday_name: serve per ottenere il nome del giorno corrente
        :type weekday_name: str

        :return: l'id del giorno della settimana
        :rtype: int
        """
    try:
        # Cerca se esiste già una riga per il giorno nella tabella giorno_settimana
        cursor.execute("SELECT giorno_settimana_id FROM giorno_settimana WHERE dieta_settimanale_id = %s AND nome = %s",
                       (weekday_name, dieta_settimanale_id))
        giorno_settimana_id = cursor.fetchone()

        if giorno_settimana_id:
            # Se esiste già, restituisci l'ID
            return giorno_settimana_id[0]
        else:
            # Altrimenti, inserisci una nuova riga e restituisci il nuovo ID
            cursor.execute("INSERT INTO giorno_settimana (nome, dieta_settimanale_id) VALUES (%s, %s)",
                           (weekday_name, dieta_settimanale_id))
            cursor.execute("SELECT LAST_INSERT_ID()")  # Ottieni l'ID dell'ultima riga inserita
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"insert_giorno settimana: {e}")


def get_or_insert_periodo_giorno(cursor, giorno_settimana_id, meal_type):
    """
        Questa funzione serve per ottenere il periodo del giorno corrente o inserirne uno se non esiste

        :param cursor: serve per eseguire le query
        :type cursor: Cursor
        :param giorno_settimana_id: l'ultimo giorno_settimana_id inserito
        :type giorno_settimana_id: int
        :param meal_type: serve per ottenere il nome del periodo del giorno (colazione, pranzo e cena) in
         base alla fascia oraria in cui ci si trova
        :type meal_type: str

        :return: l'id del periodo del giorno
        :rtype: int
        """
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
    """
        Questa funzione serve per salvare le risposte dell'utente nel database dopo che il reminder è stato inviato

        E' usato nell'handler dei messaggi dopo la profilazione

        :param bot_telegram: corrisponde alla variabile che contiene l'api key del proprio bot_telegram
                            e permette di accedere ai metodi della libreria Telebot
        :type bot_telegram: Telebot
        :param mysql_cursor: serve per eseguire le query
        :type mysql_cursor: Cursor
        :param mysql_connection: serve per eseguire le query
        :type mysql_connection: Cursor
        :param telegram_id: telegram_id dell'utente
        :type telegram_id: int
        :param food_name: risposta data dall'utente dopo il reminder
        :type food_name: str
        :param meal_type: serve per ottenere il nome del periodo del giorno (colazione, pranzo e cena) in
         base alla fascia oraria in cui ci si trova
        :type meal_type: str


        :return: la commit della query per salvare la risposta dell'utente dopo il reminder
         nel database e il messaggio di conferma del salvataggio all'utente
        :rtype: Message
        """
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
    """
        Questa funzione serve per recuperare i nomi dei cibi in base alla data

        :param telegram_id: telegram_id dell'utente
        :type telegram_id: int
        :param dieta_data: è la data corrispondente alla dieta settimanale
        :type dieta_data: date
        :param nome_giorno: serve per recuperare il nome del giorno all'iinterno della dieta settimanale
        :type nome_giorno: str
        :param cursor: serve per eseguire le query
        :type cursor: Cursor


        :return: la lista dei cibi
        :rtype: list
        """
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
    """
        Questa funzione serve per recuperare le date delle diete dell'utente in base al telegram id

        :param telegram_id: è l'id telegram dell'utente
        :type telegram_id: int
        :param mysql_cursor: serve per eseguire le query
        :type mysql_cursor: Cursor

        :return: la lista delle date delle diete dell'utente
        :rtype: list
        """
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

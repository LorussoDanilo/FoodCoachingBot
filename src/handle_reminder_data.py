"""
Questo modulo contiene le funzioni che servono per gestire l'invio dei reminder e il successivo salvataggio nel database
 delle risposte degli utenti dopo i reminder

    Danilo Lorusso - Version 1.0
"""

import calendar
import locale
import time as trem
import traceback
from datetime import datetime, timedelta

import requests
from deep_translator import GoogleTranslator

from src.handle_user_data import get_all_telegram_ids

# Imposta la lingua italiana per il modulo locale
locale.setlocale(locale.LC_TIME, 'it_IT')


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

    if not event.is_set():
        for telegram_id in telegram_ids:
            bot_telegram.send_message(telegram_id,
                                      "E' passata una settimana! Tieni d'occhio la tua dieta. Tocca su /report",
                                      trem.sleep(60*60*7))
def send_water_reminder_message(event, bot_telegram):
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

    if not event.is_set():
        for telegram_id in telegram_ids:
            bot_telegram.send_message(telegram_id,
                                      "💧Registra il tuo consumo di acqua di oggi con il comando /consumo_acqua💧",
                                      trem.sleep(20))


def get_or_insert_dieta_settimanale(cursor, telegram_id, date):
    """
    Questa funzione serve per ottenere la dieta settimanale corrente oppure inserire
    una nuova dieta settimanale nel momento in cui passa una settimana

    :param cursor: serve per eseguire le query
    :type cursor: Cursor
    :param telegram_id: telegram_id dell'utente
    :type telegram_id: int
    :param date: serve per ottenere la data corrente quando viene richiamata la funzione
    :type date: date

    :return: l'id della dieta settimanale
    :rtype: int
    """
    try:
        cursor.execute(
            "SELECT dieta_settimanale_id, data FROM dieta_settimanale WHERE telegram_id = %s AND (data = %s OR data = "
            "DATE_ADD(%s, INTERVAL 1 DAY))",
            (telegram_id, date, date))
        existing_row = cursor.fetchone()

        if existing_row:
            return existing_row[0]
        else:
            cursor.execute("SELECT MAX(dieta_settimanale_id) FROM dieta_settimanale WHERE telegram_id = %s",
                           (telegram_id,))
            max_dieta_settimanale_id = cursor.fetchone()[0]

            if max_dieta_settimanale_id is not None:
                cursor.execute(
                    "SELECT data FROM dieta_settimanale WHERE telegram_id = %s AND dieta_settimanale_id = %s",
                    (telegram_id, max_dieta_settimanale_id))
                last_week_date = cursor.fetchone()

                if last_week_date:
                    next_week_date = last_week_date[0] + timedelta(days=7)
                    if date == next_week_date:
                        # Non assegnare manualmente l'ID, lascia che sia autoincrementato
                        cursor.execute(
                            "INSERT INTO dieta_settimanale (telegram_id, data) VALUES (%s, %s)",
                            (telegram_id, date))
                        cursor.execute("SELECT LAST_INSERT_ID()")
                        new_dieta_settimanale_id = cursor.fetchone()[0]
                        return new_dieta_settimanale_id
                    else:
                        # Se la data non è successiva, restituisci l'ID massimo attuale
                        return max_dieta_settimanale_id
                else:
                    # Se non c'è nessuna data precedente, restituisci l'ID massimo attuale
                    return max_dieta_settimanale_id

            else:
                # Se non c'è alcuna riga, inserisci la prima con ID autoincrementale
                cursor.execute(
                    "INSERT INTO dieta_settimanale (telegram_id, data) VALUES (%s, %s)",
                    (telegram_id, date))
                cursor.execute("SELECT LAST_INSERT_ID()")
                new_dieta_settimanale_id = cursor.fetchone()[0]
                return new_dieta_settimanale_id

    except Exception as e:
        traceback.print_exc()
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
                       (dieta_settimanale_id, weekday_name))

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
def save_user_food_response(bot_telegram, mysql_cursor, mysql_connection, telegram_id, meal_type, food_name, app_id,
                            app_key):
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
        :param app_id:
        :type app_id: str
        :param app_key:
        :type app_key: str


        :return: la commit della query per salvare la risposta dell'utente dopo il reminder
         nel database e il messaggio di conferma del salvataggio all'utente
        :rtype: Message
        """
    try:
        date = datetime.now().date()

        # Ottieni o inserisci l'ID della riga nella tabella dieta_settimanale
        mysql_cursor.execute("START TRANSACTION")
        dieta_settimanale_id = get_or_insert_dieta_settimanale(mysql_cursor, telegram_id, date)
        print("save-user-response" + dieta_settimanale_id.__str__())

        # Ottieni il nome del giorno della settimana (es. "Monday")
        weekday_name = calendar.day_name[date.weekday()]

        # Ottieni o inserisci l'ID della riga nella tabella giorno_settimana
        giorno_settimana_id = get_or_insert_giorno_settimana(mysql_cursor, dieta_settimanale_id, weekday_name)

        # Ottieni o inserisci l'ID della riga nella tabella periodo_giorno
        periodo_giorno_id = get_or_insert_periodo_giorno(mysql_cursor, giorno_settimana_id, meal_type)

        # Inserisci il cibo nella tabella cibo
        mysql_cursor.execute("INSERT INTO cibo (nome, periodo_giorno_id) VALUES (%s, %s)",
                             (food_name, periodo_giorno_id))
        mysql_cursor.execute("COMMIT")

        # Esegui il commit delle modifiche al database
        mysql_connection.commit()

        # traduzione del cibo inserito dall'utente
        translated_food = traduci_testo(food_name)
        # Inverti il dizionario
        # Aggiungi i valori nutrizionali nella riga della tabella cibo
        nutritional_info_items = get_nutritional_info(translated_food, app_id, app_key)

        if nutritional_info_items:
            update_query = "UPDATE cibo SET "
            values = []
            for key, value in nutritional_info_items:
                update_query += f"{key} = %s, "
                values.append(value)
            # Rimuovi l'ultima virgola dalla stringa di query
            update_query = update_query.rstrip(', ')
            # Aggiungi il resto della tua query
            update_query += " WHERE nome = %s AND periodo_giorno_id = %s"
            # Aggiorna la riga della tabella cibo con i nuovi valori nutrizionali
            mysql_cursor.execute(update_query, values + [food_name, periodo_giorno_id])
            # Esegui il commit delle modifiche al database
            mysql_connection.commit()

        return bot_telegram.send_message(telegram_id,
                                         f"{meal_type} inserito/a correttamente! ✅\n\n Ora puoi chiedermi ciò che desideri 😊")

    except Exception as e:
        print(f"Errore durante l'inserimento del cibo: {e}")


def get_nutritional_info(food_name, app_id, app_key):
    """
    Questa funzione serve per recuperare le informazioni nutrizionali del cibo inserito dall'utente e salvarlo
    nella tabella valori_nutrizionali

    :param food_name: nome del cibo inserito dall'utente
    :type food_name: str
    :param app_id: app id dell'api edamam
    :type app_id: str
    :param app_key: app key dell'api edamam
    :type app_key: str

    :return: informazioni nutrizionali del cibo inserito dall'utente
    :rtype: str
    """

    try:
        base_url = "https://api.edamam.com/api/nutrition-data"

        # Costruisci i parametri della richiesta
        params = {
            'app_id': app_id,
            'app_key': app_key,
            'ingr': food_name
        }

        # Esegui la richiesta all'API di Edamam
        response = requests.get(base_url, params=params)

        # Verifica se la richiesta è stata eseguita con successo (status code 200)
        if response.status_code == 200:
            data = response.json()

            # Estrai solo i valori nutrizionali desiderati
            selected_nutrients = {
                'Energy': '',
                'Carbohydrate': '',
                'Fiber': '',
                'Sugars': '',
                'Protein': '',
                'Cholesterol': '',
                'Sodium': '',
                'Iron': '',
                'Zinc': '',
                'Phosphorus': '',
                'Water': ''
            }

            if 'totalNutrients' in data:
                nutrients = data['totalNutrients']
                for nutrient in nutrients.values():
                    nutrient_label = nutrient.get('label', '').split(',')[0].strip()
                    nutrient_quantity = nutrient.get('quantity', '')
                    nutrient_unit = nutrient.get('unit', '')
                    if nutrient_label in selected_nutrients:
                        selected_nutrients[nutrient_label] = f"{nutrient_quantity} {nutrient_unit}"

                return selected_nutrients.items()  # Spostato fuori dal ciclo

        else:
            print(f"Errore nella richiesta API: {response.status_code}")
            return None

    except Exception as e:
        print(f"Errore durante l'elaborazione delle informazioni nutrizionali: {e}")
        return None


def traduci_testo(testo):
    """

    :param testo: testo inserito dall'utente da tradurre
    :type testo: str
    :return: testo tradotto
    :rtype: str
    """

    try:
        traduzione = GoogleTranslator(source='auto', target='en').translate(testo)
        return traduzione
    except Exception as e:
        print(f"Errore durante la traduzione: {e}")
        return None

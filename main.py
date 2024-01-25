import io
import locale
import os
import pickle
import tempfile
import threading
import time as trem
from datetime import datetime, time
from queue import Queue

import pandas as pd
import requests
from dotenv import load_dotenv
from matplotlib import pyplot as plt
from mysql.connector import IntegrityError, errorcode
from reportlab.pdfgen import canvas
from roboflow import Roboflow
from telebot.types import InputFile

from chatGPT_response import write_chatgpt
from handle_reminder_data import save_user_food_response, get_food_for_day, get_dieta_dates_by_telegram_id
from handle_user_data import get_user_profile, create_new_user, ask_next_question, get_all_telegram_ids, \
    voice_recognizer, _clear
from utils.connection import connect, connect_mysql, call_create_tables_if_not_exists
from utils.controls import control_tag

locale.setlocale(locale.LC_TIME, 'it_IT')
load_dotenv()

# Constant
START_COMMAND = 'start'
EDIT_COMMAND = 'modifica'
PROFILO_COMMAND = 'profilo'
DASHBOARD_COMMAND = 'dashboard'

# Domande da porre all'utente durante la profilazione o modifica dei dati del profilo
questions_and_fields = [
    ('Qual è la tua età?', 'eta'),
    ('Quali sono le tue patologie o disturbi?', 'malattie'),
    ('Che sentimento provi mentre mangi o pensi al cibo? Indicalo scrivendo: tristezza, indifferenza, ansia, felicità',
     'emozione')
]

# Periodo giorno
meal_type = None

# Connessione a MySQL
mysql_connection, mysql_cursor = connect_mysql()

# metodo per creare il database e le tabelle del database
call_create_tables_if_not_exists()

# Inizializzazione variabili per il bot telegram, api di chat gpt e del file xml con le informazioni
openai, bot_telegram, root = connect()

# Variabile per gestire le funzionalità del chatbot. Serve per capire quando una funzionalità deve cominciare
event = threading.Event()

# Indice delle domande
index = 0

ORA_COLAZIONE_START = time(7, 0)
ORA_COLAZIONE_END = time(11, 0)
ORA_PRANZO_START = time(11, 51,10)
ORA_PRANZO_END = time(15, 0)
ORA_CENA_START = time(16, 0)
ORA_CENA_END = time(23, 50)

ORA_REMINDER_SETTIMANALE = time(11, 13, 10)

queue = Queue()

user_response_message = []  # This initializes an empty list named user_response_message_id


def check_time_in_range(current_time, start_time, end_time):
    return start_time <= current_time <= end_time


if __name__ == '__main__':

    @bot_telegram.message_handler(commands=[DASHBOARD_COMMAND])
    def generate_all_weekly_diets_pdf(message):
        telegram_id = message.chat.id
        dieta_dates = get_dieta_dates_by_telegram_id(telegram_id, mysql_cursor)

        user_profile = get_user_profile(telegram_id)

        # Creazione del PDF
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer)

        # Informazioni utente
        pdf.drawString(100, 800, 'Informazioni Utente:')
        table_data = [
            ['Nome Utente', 'Età', 'Malattie', 'Emozione'],
            [user_profile.get('nome_utente'), user_profile.get('eta'), user_profile.get('malattie'),
             user_profile.get('emozione')]
        ]
        info_utente = pd.DataFrame(table_data)

        table_style = [('BACKGROUND', (0, 0), (-1, 0), 'grey'),
                       ('TEXTCOLOR', (0, 0), (-1, 0), 'white'),
                       ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                       ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                       ('BOTTOMPADDING', (0, 0), (-1, 0), 12)]

        # Creare una lista di dizionari per ogni stile
        styles = []
        for style in table_style:
            props = [(style[0], style[2])]

            # Aggiungi gli elementi solo se presenti nella tupla
            if len(style) >= 4:
                props.append(('color', style[3]))
            if len(style) >= 5:
                props.append(('text-align', style[4]))
            if len(style) >= 6:
                props.append(('font-name', style[5]))
            if len(style) >= 7:
                props.append(('bottom-padding', style[6]))

            styles.append({'selector': 'tr', 'props': props})

        # Applica lo stile al DataFrame e assegna il risultato a styled_info_utente
        styled_info_utente = info_utente.style.set_table_styles(styles)

        pdf.drawString(100, 700, 'Dieta Settimanale:')

        # Itera attraverso tutte le settimane
        for dieta_data in dieta_dates:
            pdf.drawString(100, 680, f'Settimana del {dieta_data}')

            # Creazione del plot per la settimana corrente
            plt.figure(figsize=(10, 6))
            giorni_settimana = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

            for giorno in giorni_settimana:
                cibi_giorno = get_food_for_day(telegram_id, dieta_data, giorno, mysql_cursor)
                calorie_cibi = [cibo['calorie'] for cibo in cibi_giorno]
                plt.plot(calorie_cibi, label=giorno)

            plt.xlabel('Periodo del Giorno')
            plt.ylabel('Calorie')
            plt.title('Dieta Settimanale')
            plt.legend()
            plt.savefig('weekly_diet_plot.png')
            plt.close()

            # Includi il plot nel PDF
            pdf.drawInlineImage('weekly_diet_plot.png', 100, 500, width=400, height=200)
            pdf.showPage()  # Aggiungi una nuova pagina per ogni settimana

        # Salva il PDF prima di inviarlo
        pdf.save()

        # Verifica che il buffer contenga dati prima di inviare il documento
        if buffer.tell() > 0:
            buffer.seek(0)
            # Invia il PDF all'utente
            bot_telegram.send_document(telegram_id, document=InputFile(buffer),
                                       caption='Dieta Settimanale')

        # Rimuovi il file temporaneo del plot
        if os.path.exists('weekly_diet_plot.png'):
            os.remove('weekly_diet_plot.png')

        buffer.seek(0)
        return buffer


    # metodo per gestire il comando /profilo per visualizzare i dati del profilo
    @bot_telegram.message_handler(commands=[PROFILO_COMMAND])
    def show_user_profile(message):
        telegram_id = message.chat.id

        # Ottieni le informazioni dell'utente dal database
        user_profile = get_user_profile(telegram_id)

        if user_profile:
            # Costruisci il messaggio delle informazioni dell'utente
            profile_message = f"<i>Profilo di</i> <b>{message.chat.first_name}:</b>\n"
            for key, value in user_profile.items():
                if key.lower() != 'telegram_id':  # Escludi l'ID di Telegram dal messaggio
                    profile_message += f"<i>{key.capitalize()}:</i> <b>{value}</b>\n"

            # Invia il messaggio delle informazioni dell'utente con formattazione HTML
            bot_telegram.send_message(telegram_id, profile_message, parse_mode='HTML', disable_notification=True)
        else:
            # Messaggio se l'utente non ha un profilo
            bot_telegram.send_message(telegram_id, "Non hai ancora completato il tuo profilo.")


    # Metodo per gestire il comando /modifica
    @bot_telegram.message_handler(commands=[EDIT_COMMAND])
    def edit_command(message):
        telegram_id = message.chat.id
        index_edit = 0
        user_profile_edit = get_user_profile(telegram_id)
        if not user_profile_edit:
            create_new_user(telegram_id, message.chat.username)

        bot_telegram.send_message(telegram_id, message.chat.username + " " + "modifica i dati del tuo profilo!")
        # Invia il messaggio iniziale

        # Domande per l'aggiornamento delle informazioni

        # Inizia a fare domande per l'aggiornamento delle informazioni
        ask_next_question(telegram_id, bot_telegram, questions_and_fields, index_edit)


    # Metodo per gestire il comando /start
    @bot_telegram.message_handler(commands=[START_COMMAND])
    def send_welcome(message):
        # setto l'evento a true

        global questions_and_fields, index
        event.set()
        telegram_id = message.chat.id

        user_profile_start = get_user_profile(telegram_id)
        print(user_profile_start)

        # Controllo se l'utente non esiste
        if not user_profile_start:
            # Se l'utente non esiste viene creato inserendo l'id telegram e il suo username
            create_new_user(telegram_id, message.chat.username)

        # Tutte le informazioni necessarie sono state fornite
        msg = control_tag(root, "./telegram/informazioni", START_COMMAND, "spiegazioni")
        bot_telegram.send_message(telegram_id, msg.replace('{nome}', message.chat.first_name))
        # Inizia chiedendo la prima domanda
        print("pre-start" + index.__str__())

        question, field = questions_and_fields[index]
        bot_telegram.send_message(telegram_id, question)
        # Incremento dell'indice per proseguire nelle domande

        index += 1

        print("post-start" + index.__str__())


    # Metodo per gestire le risposte dell'utente alle domande della profilazione
    @bot_telegram.message_handler(func=lambda message: True, content_types=['text', 'voice', 'photo'])
    def handle_profile_response(message):
        global mysql_connection, mysql_cursor, event, index, reminder_message_thread
        user_response = str(message.text)
        telegram_id = message.chat.id
        telegram_ids = get_all_telegram_ids()
        current_time_reminder = datetime.now().time()

        try:
            if index < len(questions_and_fields):
                # Esecuzione della query per aggiornare il profilo dell'utente nel database
                update_query = f"UPDATE utenti SET {questions_and_fields[index - 1][1]} = %s WHERE telegram_id = %s"
                mysql_cursor.execute(update_query, (user_response, telegram_id))
                # Commit delle modifiche al database
                mysql_connection.commit()
                confirmation_message = f"{questions_and_fields[index - 1][1]} salvat*: {user_response}"
                bot_telegram.send_message(telegram_id, confirmation_message)
                # Passa alla prossima domanda se ci sono ancora domande
                question, field = questions_and_fields[index]
                bot_telegram.send_message(telegram_id, question)
                index += 1
                print("handle_profile_response" + index.__str__())

            elif index == len(questions_and_fields):
                update_query = f"UPDATE utenti SET {questions_and_fields[index - 1][1]} = %s WHERE telegram_id = %s"
                mysql_cursor.execute(update_query, (user_response, telegram_id))
                # Commit delle modifiche al database
                mysql_connection.commit()
                confirmation_message = f"{questions_and_fields[index - 1][1]} salvat*: {user_response}"
                bot_telegram.send_message(telegram_id, confirmation_message)
                bot_telegram.send_message(telegram_id,
                                          "Il tuo profilo è completo. Grazie! Chiedimi ciò che desideri😊")
                index += 1

                for telegram_id in telegram_ids:
                    if check_time_in_range(current_time_reminder, ORA_COLAZIONE_START, ORA_COLAZIONE_END):
                        bot_telegram.send_message(telegram_id, "Buongiorno! Cosa hai mangiato a colazione?")

                    elif check_time_in_range(current_time_reminder, ORA_PRANZO_START, ORA_PRANZO_END):
                        bot_telegram.send_message(telegram_id, "Pranzo time! Cosa hai mangiato a pranzo?")

                    elif check_time_in_range(current_time_reminder, ORA_CENA_START, ORA_CENA_END):
                        bot_telegram.send_message(telegram_id, "Cena! Cosa hai mangiato a cena?")
                    else:
                        event.clear()



            elif index > len(questions_and_fields):

                if event.is_set():
                    reminder_message_thread = threading.Thread(target=send_reminder_message, daemon=True)
                    reminder_message_thread.start()

                    reminder_thread = threading.Thread(target=handle_reminder_response, daemon=True, args=(message,))
                    reminder_thread.start()

                else:
                    reminder_week_message_thread = threading.Thread(target=send_week_reminder_message, daemon=True)
                    reminder_week_message_thread.start()
                    if message.reply_to_message and message.reply_to_message.text in user_response_message:
                        user_profile = get_user_profile(telegram_id)
                        timestamp = message.reply_to_message.date

                        # Converti il timestamp in un oggetto datetime
                        data_messaggio = datetime.utcfromtimestamp(timestamp).strftime('%d/%m/%y')

                        user_response_reply = (
                            f"Considera che in questa data {data_messaggio} ho mangiato: "
                            f"{message.reply_to_message.text}. In riferimento a quella data: {user_response}"
                        )
                        respost = write_chatgpt(openai, user_response_reply, user_profile, mysql_cursor, telegram_id)
                        print(user_response_reply)
                        bot_telegram.send_message(telegram_id, respost)
                    else:

                        if message.content_type == 'text':

                            user_profile = get_user_profile(telegram_id)
                            print(user_profile)
                            respost = write_chatgpt(openai, user_response, user_profile, mysql_cursor, telegram_id)
                            bot_telegram.send_message(telegram_id, respost)
                        elif message.content_type == 'voice':
                            voice_handler(message)
                        elif message.content_type == 'photo':
                            photo_handler(message)

        except Exception as e:
            print(f"Valore errato: {e}")
            telegram_id = message.chat.id
            bot_telegram.send_message(telegram_id, "Hai inserito un valore errato. Riprova.")

        except IntegrityError as integrity_error:
            print(f"Vincolo di integrità violato: {integrity_error}")
            telegram_id = message.chat.id
            bot_telegram.send_message(telegram_id, "Hai inserito un valore errato. Riprova.")

        except mysql_cursor.Error as db_error:
            if db_error.errno == errorcode.ER_TRUNCATED_WRONG_VALUE:
                # Handle the specific error for incorrect integer value
                bot_telegram.send_message(telegram_id,
                                          "Errore: Valore non valido per il campo 'eta'. Inserisci un numero valido.")
            else:
                # Handle other database errors
                bot_telegram.send_message(telegram_id, f"Errore del database: {db_error}")


@bot_telegram.message_handler(func=lambda message: True)
def handle_reminder_response(message):
    global meal_type, mysql_cursor, mysql_connection, queue, user_response_message

    serialized_message = pickle.dumps(message)
    queue.put(serialized_message)

    telegram_ids = get_all_telegram_ids()
    deserialized_message = pickle.loads(serialized_message)
    user_response_message.append(str(deserialized_message.text))
    user_response = str(deserialized_message.text)

    current_time_reminder = datetime.now().time()
    try:

        if check_time_in_range(current_time_reminder, ORA_COLAZIONE_START, ORA_COLAZIONE_END):
            for telegram_id in telegram_ids:
                meal_type = "colazione"
                save_user_food_response(bot_telegram, mysql_cursor, mysql_connection, telegram_id, meal_type,
                                        user_response)
                event.clear()
                event.wait(10)
                event.set()
        elif check_time_in_range(current_time_reminder, ORA_PRANZO_START, ORA_PRANZO_END):
            for telegram_id in telegram_ids:
                meal_type = "pranzo"
                save_user_food_response(bot_telegram, mysql_cursor, mysql_connection, telegram_id, meal_type,
                                        user_response)
                event.clear()
                event.wait(20)
                event.set()

        elif check_time_in_range(current_time_reminder, ORA_CENA_START, ORA_CENA_END):
            for telegram_id in telegram_ids:
                meal_type = "cena"
                save_user_food_response(bot_telegram, mysql_cursor, mysql_connection, telegram_id, meal_type,
                                        user_response)
                event.clear()
                event.wait(10)
                event.set()

    except Exception as main_exception:
        # Handle the main exception (e.g., log the error)
        print(f"Main exception occurred: {main_exception}")




# chat_id checks id corresponds to your list or not.
def send_week_reminder_message():
    telegram_ids = get_all_telegram_ids()

    current_time_reminder = datetime.now().time()
    # Serializzazione dell'oggetto Message
    while not event.is_set():
        for telegram_id in telegram_ids:
            bot_telegram.send_message(telegram_id,
                                      "E' passata una settimana! Tieni d'occhio la tua dieta. Tocca su /dashboard",
                                      trem.sleep(60 * 60 * 24 * 7))


def send_reminder_message():
    telegram_ids = get_all_telegram_ids()

    current_time_reminder = datetime.now().time()
    # Serializzazione dell'oggetto Message

    while event.is_set():
        for telegram_id in telegram_ids:
            if check_time_in_range(current_time_reminder, ORA_COLAZIONE_START, ORA_COLAZIONE_END):
                bot_telegram.send_message(telegram_id, "Buongiorno! Cosa hai mangiato a colazione?", trem.sleep(10))

            elif check_time_in_range(current_time_reminder, ORA_PRANZO_START, ORA_PRANZO_END):
                bot_telegram.send_message(telegram_id, "Pranzo time! Cosa hai mangiato a pranzo?", trem.sleep(20))

            elif check_time_in_range(current_time_reminder, ORA_CENA_START, ORA_CENA_END):
                bot_telegram.send_message(telegram_id, "Cena! Cosa hai mangiato a cena?", trem.sleep(10))


# Metodo per gestire i messaggi vocali dell'utente
@bot_telegram.message_handler(func=lambda message: True)
def voice_handler(message):
    file_id = message.voice.file_id
    file = bot_telegram.get_file(file_id)
    telegram_id = message.chat.id

    file_size = file.file_size
    if int(file_size) >= 715000:
        bot_telegram.send_message(message.chat.id, 'La dimensione del file è troppo grande.')
    else:
        download_file = bot_telegram.download_file(file.file_path)
        with open('audio.ogg', 'wb') as file:
            file.write(download_file)

        # chiamare la funzione che permette di riconoscere la voce e convertire il file .ogg in .wav
        text = voice_recognizer()

        user_profile = get_user_profile(telegram_id)
        print(user_profile)
        respost = write_chatgpt(openai, text, user_profile, mysql_cursor, telegram_id)
        bot_telegram.send_message(message.chat.id, respost)
        # chiamare il metodo per cancellare i file .ogg e .wav generati
        _clear()


@bot_telegram.message_handler(func=lambda message: True)
def photo_handler(message):
    print("oddio")
    telegram_id = message.chat.id
    # Esegui il riconoscimento del cibo

    photo_result = photo_recognizer(message)
    if message.caption:
        results = photo_result + message.caption
        user_profile = get_user_profile(telegram_id)
        print(results)
        respost = write_chatgpt(openai, results, user_profile, mysql_cursor, telegram_id)
        bot_telegram.send_message(telegram_id, respost)
    else:
        results = photo_result
        user_profile = get_user_profile(telegram_id)
        print(results)
        respost = write_chatgpt(openai, results, user_profile, mysql_cursor, telegram_id)
        bot_telegram.send_message(telegram_id, respost)


def photo_recognizer(message):
    try:
        # Ottieni l'oggetto PhotoSize con la foto di dimensioni più grandi
        photo = message.photo[-1]
        bot_token = os.getenv('TOKEN_TELEGRAM')
        telegram_id = message.chat.id

        # Ottieni l'oggetto File corrispondente all'oggetto PhotoSize
        file_info = bot_telegram.get_file(photo.file_id)

        # Costruisci l'URL dell'immagine
        image_url = f'https://api.telegram.org/file/bot{bot_token}/{file_info.file_path}'

        # Salva temporaneamente l'immagine su disco
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_file.write(requests.get(image_url).content)
            temp_file.close()  # Chiudi il file dopo aver scritto

            rf = Roboflow(api_key="DdgoW5JHoOafvCdYGtUE")
            project = rf.workspace().project("merge-wrowm")
            model = project.version(2).model
            result = model.predict(temp_file.name, confidence=40, overlap=30)
            # Esegui l'inferenza utilizzando il percorso temporaneo del file
            if result:
                print(result.json())
                # Rimuovi il file temporaneo
                os.remove(temp_file.name)
                predictions = result.json().get("predictions", [])
                recognized_class = predictions[0]["class"]
                print(recognized_class)
                return recognized_class
            else:
                os.remove(temp_file.name)
                return bot_telegram.send_message(telegram_id, "Foto non riconosciuta. Riprovare!")


    except Exception as e:
        print(f"Error in photo_recognizer: {e}")
        bot_telegram.reply_to(message, "Si è verificato un errore durante il riconoscimento dell'immagine.")


# Esegui il polling infinito del bot Telegram
bot_telegram.infinity_polling()

"""
Questo modulo consente di gestire i dati e i messaggi degli utenti. Permette di prendere in input dei messaggi vocali,
testuali e foto

    Danilo Lorusso - Version 1.0
"""

import locale
import logging
import os
import subprocess
import tempfile
import traceback
from datetime import datetime, time
from sqlite3 import IntegrityError

import requests
import speech_recognition as sr
from mysql.connector import errorcode
from roboflow import Roboflow
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from src.connection import connect_mysql
from src.controls import check_time_in_range

handle_user_response_gpt_enabled = False
locale.setlocale(locale.LC_TIME, 'it_IT')
# if per creare la directory dei logs
LOG_FOLDER = '.logs'
if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)

# configurazione della cartella di log
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=f'{LOG_FOLDER}/app.log'
)

# inizializzazione della variabile usata per riempire il file di logger
logger = logging.getLogger('telegram-bot')
logging.getLogger('urllib3.connectionpool').setLevel('INFO')


# Inizializzazione degli intervalli orari per inviare i reminder
ORA_COLAZIONE_START = time(8, 0)
ORA_COLAZIONE_END = time(9, 0)
ORA_PRANZO_START = time(11, 0)
ORA_PRANZO_END = time(12, 40)
ORA_CENA_START = time(16, 30)
ORA_CENA_END = time(23, 50)

reply_markup_emozioni = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("Felicità", callback_data='emozione_felicità'),
        InlineKeyboardButton("Tristezza", callback_data='emozione_tristezza'),
        InlineKeyboardButton("Indifferenza", callback_data='emozione_indifferenza')
    ],
    [
        InlineKeyboardButton("Ansia", callback_data='emozione_ansia'),
        InlineKeyboardButton("Paura", callback_data='emozione_paura'),
        InlineKeyboardButton("Rabbia", callback_data='emozione_rabbia')
    ],
    [
        InlineKeyboardButton("Disgusto", callback_data='emozione_disgusto')
        # Aggiungi altri pulsanti per diverse emozioni, se necessario
    ]
])

reply_markup_stile_vita = InlineKeyboardMarkup([
    [InlineKeyboardButton("Sedentario", callback_data='stile_vita_sedentario')],
    [InlineKeyboardButton("Bilanciato", callback_data='stile_vita_bilanciato')],
    [InlineKeyboardButton("Sportivo", callback_data='stile_vita_sportivo')]
    # Aggiungi altri pulsanti per diverse emozioni
])

reply_markup_obiettivo = InlineKeyboardMarkup([
    [InlineKeyboardButton("Curiosità", callback_data='obiettivo_curiosità')],
    [InlineKeyboardButton("Dimagrire", callback_data='obiettivo_dimagrire')],
    [InlineKeyboardButton("Consigli alimentari per dieta sana",
                          callback_data='obiettivo_consigli_alimentari_per_dieta_sana')],
    [InlineKeyboardButton("Consigli specifici per le malattie",
                          callback_data='obiettivo_consigli_specifici_per_le_malattie')]
    # Aggiungi altri pulsanti per diverse emozioni
])

# Domande da porre all'utente durante la profilazione o modifica dei dati del profilo
questions_and_fields = [
    ('Qual è la tua età? 🧍‍♂️', 'eta'),
    ('Quali sono le tue patologie o disturbi? 🩺', 'malattie'),
    ('Quale emozione provi mentre mangi o pensi al cibo? 🧠', 'emozione'),
    ('Qual è il tuo peso in Kg? ⚖️', 'peso'),
    ('Qual è la tua altezza in cm? 📏', 'altezza'),
    ('Qual è il tuo stile di vita? 🚶', 'stile_vita'),
    ('Perchè vorresti utilizzare questo servizio? 🎯', 'obiettivo'),
]

mysql_connection, mysql_cursor = connect_mysql()


def create_new_user(telegram_id, username):
    """
        Questa funzione permette di creare un nuovo utente inserendo nella tabella utenti il telegram_id e lo username
        di telegram

        :param telegram_id: id_telegram dell'utente ottenuto tramite i metodi della libreria telebot
        :type telegram_id: int
        :param username: username dell'utente di telegram
        :type username: str

        :return: la query che inserisce nella tabella utenti il telegram id e lo username di telegram
        :rtype: None
        """
    try:
        # Connect to MySQL and get a cursor
        mysql_connection_create_user, cursor = connect_mysql()

        # Create a new user entry in the database with the provided Telegram ID and username
        cursor.execute("INSERT INTO utenti (telegram_id, nome_utente) VALUES (%s, %s)", (telegram_id, username))
        mysql_connection_create_user.commit()

        # Close the cursor
        cursor.close()

    except Exception as e:
        print(f"Error creating new user: {e}")


def update_user_profile(field_name, user_profile, response):
    """
        Questa funzione permette di aggiornare i campi della tabella utenti del database. Usato per il comando /modifica
        per avviare la modifica dei dati del profilo utente

        :param field_name: campo della tabella utenti
        :type field_name: str
        :param user_profile: dizionario che contiene i dati del profilo utente
        :type user_profile: dict
        :param response: messaggio di risposta dell'utente per la modifica dei dati
        :type user_profile: dict

        :return: la query che aggiorna i dati del profilo dell'utente nella tabella utenti
        :rtype: None
    """

    # Definisci le associazioni tra le parole chiave della risposta e i campi del profilo utente
    update_profile_fields = {
        'telegram_id': 'telegram_id',
        'nome_utente': '{nome}',
        'eta': 'eta',
        'malattie': 'malattie',
        'emozione': 'emozione'
        # Aggiungi gli altri campi del profilo utente
    }

    # Estrai il campo corrispondente dalla risposta
    db_field = update_profile_fields.get(field_name.lower())
    if db_field and response:
        user_profile[db_field] = response
    print(response)


def get_user_profile(telegram_id):
    """
            Questa funzione permette di ottenere tutti i dati del profilo utente in base all'id telegram

            :param telegram_id: id telegram dell'utente
            :type telegram_id: int

            :return: la query che recupera i dati del profilo dell'utente nella tabella utenti
            :rtype: dict
        """
    try:
        mysql_connection, mysql_cursor = connect_mysql()

        # Query SQL to retrieve the user profile based on telegram_id
        mysql_cursor.execute("SELECT * FROM utenti WHERE telegram_id = %s", (telegram_id,))
        result = mysql_cursor.fetchone()
        print(result)
        # Close the cursor
        mysql_cursor.close()

        # Return the user profile if present, otherwise an empty dictionary
        return dict(zip(mysql_cursor.column_names, result)) if result else {}

    except Exception as e:
        print(f"Error getting user profile: {e}")


# Funzione per ottenere gli ID delle diete settimanali per un utente
def get_dieta_settimanale_ids(telegram_id):
    """
    Questa funzione permette di ottenere tutti gli delle diete settimanali attraverso l'id telegram

    :param telegram_id: telegram_id dell'utente
    :type telegram_id: int

    :return: il risultato della query per ottenere tutti gli id settimanali
    :rtype: list
    """
    mysql_connection, mysql_cursor = connect_mysql()
    try:
        mysql_cursor.execute("SELECT dieta_settimanale_id FROM dieta_settimanale WHERE telegram_id = %s",
                             (telegram_id,))
        result = mysql_cursor.fetchall()
        return [row[0] for row in result]
    except Exception as e:
        print(f"Errore nel recupero degli ID delle diete settimanali: {e}")
    finally:
        mysql_cursor.close()
        mysql_connection.close()


def get_dieta_settimanale_profile(dieta_settimanale_id):
    """
    Questa funzione permette di ottenere tutti i dati della dieta settimanale in base all'id della dieta settimanale.

    :param dieta_settimanale_id: id della dieta settimanale
    :type dieta_settimanale_id: int

    :return: la query che recupera i dati della dieta settimanale nella tabella dieta_settimanale
    :rtype: dict
    """
    mysql_connection, mysql_cursor = connect_mysql()
    try:

        # Query SQL to retrieve the dieta settimanale profile based on dieta_settimanale_id
        mysql_cursor.execute("SELECT * FROM dieta_settimanale WHERE dieta_settimanale_id = %s", (dieta_settimanale_id,))
        result = mysql_cursor.fetchone()

        # Close the cursor
        mysql_cursor.close()

        # Return the dieta settimanale profile if present, otherwise an empty dictionary
        return dict(zip(mysql_cursor.column_names, result)) if result else {}

    except Exception as e:
        print(f"Error getting dieta settimanale profile: {e}")
    finally:
        mysql_connection.close()


def get_all_telegram_ids():
    """
    Questa funzione permette di ottenere tutti gli id telegram degli utenti

    :return: la query che recupera tutti gli id telegram degli utenti
    :rtype: collections.iterable
   """

    mysql_connection, mysql_cursor = connect_mysql()
    # Query SQL per recuperare tutti gli ID di Telegram dalla tabella utenti
    mysql_cursor.execute("SELECT telegram_id FROM utenti")
    result = mysql_cursor.fetchall()
    mysql_cursor.close()

    # Restituisci una lista di ID di Telegram
    return [row[0] for row in result]


# Update data Funzione per fare domande per l'aggiornamento delle informazioni
def ask_next_question(telegram_id, bot, index):
    """
    Questa funzione permette di fare le domande di profilazione all'utente

    :param telegram_id: id telegram dell'utente
    :type telegram_id: int
    :param bot: permette di usare i metodi della libreria Telebot
    :type bot: Telebot
    :param index: indice della domanda che viene fatta all'utente che viene incrementato ciclicamente
    :type index: int


    :return: la domanda da fare all'utente
    :rtype: Message
    """
    if index < len(questions_and_fields):
        question, field = questions_and_fields[index]
        bot.send_message(telegram_id, question)
        # Registra la funzione di gestione della risposta
        bot.register_next_step_handler_by_chat_id(telegram_id, lambda m: handle_update_response(m, telegram_id, bot,
                                                                                                questions_and_fields,
                                                                                                index))
    else:
        # Se tutte le domande sono state fatte, comunica all'utente che i dati sono stati aggiornati
        bot.send_message(telegram_id,
                         "I tuoi dati sono stati aggiornati con successo! Puoi chiedermi ciò che desideri 😊")

    # Funzione per gestire la risposta dell'utente
    def handle_update_response(message, telegram_id_update, bot_update, questions_and_fields_update, index_update):
        """
            Questa funzione permette di salvare le risposte dell'utente nel database aggiornando cosi i dati dell'utente

            :param message: messaggio dell'utente
            :type message: Message
            :param telegram_id_update: id telegram dell'utente
            :type telegram_id_update: int
            :param bot_update: permette di usare i metodi della libreria Telebot
            :type bot_update: Telebot
            :param questions_and_fields_update: lista che contiene le domande e i campi della tabella utenti a cui
                    si riferiscono
            :type questions_and_fields_update: list
            :param index_update: indice della domanda che viene fatta all'utente che viene incrementato ciclicamente
            :type index_update: int

            :return: la query di aggiornamento dei dati utilizzata in ask_next_question
            :rtype: None
        """

        try:
            user_response = str(message.text)
            telegram_user_id = message.chat.id
            # Check if the user exists in the database

            # Connessione a MySQL e ottenimento di un cursore
            mysql_connection, cursor = connect_mysql()

            # Esecuzione della query per aggiornare il profilo dell'utente nel database
            update_query = (f"UPDATE utenti SET {questions_and_fields_update[index_update][1]} = %s WHERE telegram_id "
                            f"= %s")
            cursor.execute(update_query, (user_response, telegram_user_id))

            # Commit delle modifiche al database
            mysql_connection.commit()

            # Invio di un messaggio di conferma all'utente
            confirmation_message = f"{questions_and_fields_update[index_update][1]} aggiornato/a: {user_response}"
            bot_update.send_message(telegram_user_id, confirmation_message)

            # Chiudi la connessione al database
            mysql_connection.close()

            # Passa alla prossima domanda se ci sono ancora domande
            ask_next_question(telegram_id_update, bot_update, index_update + 1)

        except Exception as e:
            print(f"Errore durante la gestione della risposta: {e}")


def voice_recognizer():
    """
    Questa funzione permette di processare l'audio convertendolo, attraverso un programma esterno da scaricare,
    l'audio di telegram dal formato .ogg al formato .wav. Viene salvato temporaneamente il file audio, riconosciuto
    il testo dalla voce con la funzione di SpeechToText di GoogleApiCloudConsole, e poi cancellato.

    :return: il testo riconosciuto dal vocale
    :rtype: str
    """

    ffmpeg_path = os.getenv('FFMPEG_PATH')
    # inizializzazione della variabile usata per riconoscere la lingua dei messaggi vocali
    language = os.getenv('VOICE_RECOGNIZER_LANGUAGE')
    recognizer = sr.Recognizer()
    # convertire un file audio da formato OGG a formato WAV
    subprocess.run([ffmpeg_path, '-i', 'audio.ogg', 'audio.wav', '-y'])

    audio_file_path = 'audio.wav'

    with sr.AudioFile(audio_file_path) as file:
        audio = recognizer.record(file)

    # Set up the SpeechRecognition recognizer
    try:
        # recognizer_google
        text = recognizer.recognize_google_cloud(audio, os.getenv('GOOGLE_APPLICATION_CREDENTIALS'), language=language)
        print(text + ' recognizer')

    except sr.UnknownValueError:
        logger.warning("Google Cloud Speech Recognition could not understand the audio.")
        text = 'Parole non riconosciute Unkonown.'

    except sr.RequestError as e:
        logger.error(f"Google Cloud Speech Recognition request failed; {e}")
        text = 'Parole non riconosciute. Request failed'

    except Exception as e:
        logger.error(f"Exception:\n{traceback.format_exc()}")
        print(f"Exception: {e}")
        text = 'Parole non riconosciute. General_exception'

    return text


# Metodo per cancellare i file .ogg e .wav generati
def clear_audio():
    """
        Questa funzione permette di cancellare i file audio salvati temporaneamente

        :return: cancellazione dei file audio temporanei
        :rtype: None
    """
    input_path = 'audio.ogg'
    output_path = 'audio.wav'
    _files = [input_path, output_path]
    for _file in _files:
        if os.path.exists(_file):
            os.remove(_file)


def photo_recognizer(message, bot_telegram):
    """
    Questa funzione permette di riconoscere le foto inviate dall'utente e ritornare il testo
    che rappresenta il risultato del riconoscimento della foto

    :param message: messaggio dell'utente, che in questo caso è una foto
    :type message: Message
    :param bot_telegram: permette di usare i metodi della libreria Telebot
    :type bot_telegram: Telebot

    :return: il testo ottenuto dal riconoscimento dell'immagine
    :rtype: str
    """

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




class ProfilazioneBot:
    global mysql_connection, mysql_cursor

    def __init__(self, bot_telegram):
        self.from_user = None
        self.data = None
        self.questions_and_fields = questions_and_fields
        self.bot_telegram = bot_telegram
        self.index = 0
        self.user_profile = {}
        self.profile_completed = False

        @bot_telegram.callback_query_handler(func=lambda call: True)
        def handle_buttons_callback(call):
            user_id = call.from_user.id
            user_response = call.data
            current_time_reminder = datetime.now().time()
            print(self.index)
            if user_response == 'consenso_si':
                # Utente ha acconsentito, puoi iniziare con le domande di profilazione
                bot_telegram.send_message(user_id, "Ottimo! Cominciamo con le domande di profilazione 👤")
                self.invia_domanda_attuale(user_id)  # Inizia chiedendo la prima domanda
            if user_response == 'consenso_no':
                # Utente ha rifiutato, puoi gestire di conseguenza
                bot_telegram.send_message(user_id,
                                          "Puoi utilizzare il bot, ma non acconsentendo alla profilazione, "
                                          "risulterà meno efficiente😢")
                if check_time_in_range(current_time_reminder, ORA_COLAZIONE_START, ORA_COLAZIONE_END):
                    bot_telegram.send_message(user_id,
                                              "Colazione time! 🥛 Cosa hai mangiato a colazione? \n⚠️ Indica prima del cibo la "
                                              "quantità.")

                elif check_time_in_range(current_time_reminder, ORA_PRANZO_START, ORA_PRANZO_END):
                    bot_telegram.send_message(user_id,
                                              "Pranzo time! 🍽 Cosa hai mangiato a pranzo?\n ⚠️ Indica prima del cibo la quantità.")

                elif check_time_in_range(current_time_reminder, ORA_CENA_START, ORA_CENA_END):
                    bot_telegram.send_message(user_id,
                                              "Cena time! 🍽 Cosa hai mangiato a cena?\n ⚠️ Indica prima del cibo la quantità.")
                self.profile_completed = True

            if user_response.startswith('emozione_'):
                emozione_selezionata = user_response[len('emozione_'):]
                self.salva_profilo(user_id, 'emozione', emozione_selezionata)
                self.index += 1
                self.invia_domanda_attuale(user_id)
            elif user_response.startswith('stile_vita_'):
                stile_vita_selezionato = user_response[len('stile_vita_'):]
                self.salva_profilo(user_id, 'stile_vita', stile_vita_selezionato)
                self.index += 1
                self.invia_domanda_attuale(user_id)
            elif user_response.startswith('obiettivo_'):
                obiettivo_selezionato = user_response[len('obiettivo_'):]
                self.salva_profilo(user_id, 'obiettivo', obiettivo_selezionato)
                self.bot_telegram.send_message(user_id,
                                               "Grazie! Profilo completato ✅\n\n Chiedimi ciò che desideri😊")
                self.index += 1
                self.profile_completed = True

                if check_time_in_range(current_time_reminder, ORA_COLAZIONE_START, ORA_COLAZIONE_END):
                    bot_telegram.send_message(user_id,
                                              "Colazione time! 🥛 Cosa hai mangiato a colazione? \n⚠️ Indica prima del cibo la "
                                              "quantità.")

                elif check_time_in_range(current_time_reminder, ORA_PRANZO_START, ORA_PRANZO_END):
                    bot_telegram.send_message(user_id,
                                              "Pranzo time! 🍽 Cosa hai mangiato a pranzo? \n⚠️ Indica prima del cibo la quantità.")

                elif check_time_in_range(current_time_reminder, ORA_CENA_START, ORA_CENA_END):
                    bot_telegram.send_message(user_id,
                                              "Cena time! 🍽 Cosa hai mangiato a cena? \n⚠️ Indica prima del cibo la quantità.")


    def invia_domanda_attuale(self, chat_id):
        if not self.profile_completed and self.index < len(self.questions_and_fields):
            question, field = self.questions_and_fields[self.index]
            print(f"Current index: {self.index}, Current field: {field}")
            if field == 'emozione':
                self.bot_telegram.send_message(chat_id, text=question, reply_markup=reply_markup_emozioni)
            elif field == 'stile_vita':
                self.bot_telegram.send_message(chat_id, text=question, reply_markup=reply_markup_stile_vita)
            elif field == 'obiettivo':
                self.bot_telegram.send_message(chat_id, text=question, reply_markup=reply_markup_obiettivo)
            else:
                self.bot_telegram.send_message(chat_id, text=question)

    # Aggiungi il gestore del callback per le emozioni

    def gestisci_risposta(self, user_id, user_response):
        try:
            if not self.profile_completed and self.index < len(questions_and_fields):
                question, field = questions_and_fields[self.index]

                # Altrimenti, gestisci la risposta come testo
                self.user_profile[field] = user_response

                # Esegui l'aggiornamento del profilo nel database se necessario
                self.salva_profilo(user_id, field, user_response)

                self.index += 1
                self.invia_domanda_attuale(user_id)
        except Exception as db_error:

            if hasattr(db_error, 'errno') and db_error == errorcode.ER_TRUNCATED_WRONG_VALUE:
                # Handle the specific error for incorrect integer value
                self.bot_telegram.send_message(user_id,
                                               text="⚠️Errore: Valore non valido per il campo 'eta'. Inserisci un numero valido.")
            else:
                # Handle other database errors
                self.bot_telegram.send_message(user_id, text=f"⚠️Hai inserito un valore errato. Riprova")

        if self.index == len(questions_and_fields):
            # Gestisci altre logiche dopo che tutte le domande sono state completate
            self.profile_completed = True

    def salva_profilo(self, chat_id, field, value):
        global mysql_connection, mysql_cursor
        try:
            mysql_connection, mysql_cursor = connect_mysql()

            # Esecuzione della query per aggiornare il profilo dell'utente nel database
            update_query = f"UPDATE utenti SET {field} = %s WHERE telegram_id = %s"
            mysql_cursor.execute(update_query, (value, chat_id))

            # Commit delle modifiche al database
            mysql_connection.commit()

            # Puoi anche inviare una conferma all'utente se lo desideri
            confirmation_message = f"Grazie! 😊 La tua risposta per <b>{field}</b> è: <b>{value}</b>"
            self.bot_telegram.send_message(chat_id, confirmation_message, parse_mode='HTML', disable_notification=True)
        except IntegrityError as integrity_error:

            print(f"Vincolo di integrità violato: {integrity_error}")

            self.bot_telegram.send_message(chat_id, text="⚠️ Hai inserito un valore errato. Riprova.")

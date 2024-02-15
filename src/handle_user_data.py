"""
Questo modulo consente di gestire i dati e i messaggi degli utenti. Permette di prendere in input dei messaggi vocali,
testuali e foto

    Danilo Lorusso - Version 1.0
"""

import io
import locale
import logging
import os
import subprocess
import tempfile
from datetime import datetime, time
from sqlite3 import IntegrityError
from PIL import Image  # Add this import
from io import BytesIO
import base64
import requests
import speech_recognition as sr
from mysql.connector import errorcode
from pydub import AudioSegment
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import json


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
ORA_COLAZIONE_START = time(6, 0)
ORA_COLAZIONE_END = time(9, 0)
ORA_PRANZO_START = time(12, 0)
ORA_PRANZO_END = time(15, 00)
ORA_CENA_START = time(18, 00)
ORA_CENA_END = time(21, 00)

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


def delete_user_profile(telegram_id):
    """
        Questa funzione permette di revocare il consenso al trattamento dei dati cancellando i dati del profilo

        :param field_name: campo della tabella utenti
        :type field_name: str
        :param user_profile: dizionario che contiene i dati del profilo utente
        :type user_profile: dict

        :return: la query che cancella i dati del profilo dell'utente nella tabella utenti
        :rtype: None
    """
    fields_to_delete = ['eta', 'malattie', 'emozione', 'peso', 'altezza', 'stile_vita', 'obiettivo']
    delete_query = f"UPDATE utenti SET {', '.join(f'{field} = NULL' for field in fields_to_delete)} WHERE telegram_id = %s"

    # Esegui la query SQL
    mysql_cursor.execute(delete_query, (telegram_id,))

    # Conferma e chiudi la connessione al database
    mysql_connection.commit()




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


def voice_recognizer(openai):
    """
    Questa funzione permette di processare l'audio convertendolo, attraverso un programma esterno da scaricare,
    l'audio di telegram dal formato .ogg al formato .wav. Viene salvato temporaneamente il file audio, riconosciuto
    il testo dalla voce con la funzione di SpeechToText di GoogleApiCloudConsole, e poi cancellato.

    :return: il testo riconosciuto dal vocale
    :rtype: str
    """
    ffmpeg_path = os.getenv('FFMPEG_PATH')

    recognizer = sr.Recognizer()
    # convertire un file audio da formato OGG a formato WAV
    subprocess.run([ffmpeg_path, '-i', 'audio.ogg', 'audio.wav', '-y'])

    audio_file_path = 'audio.wav'

    with sr.AudioFile(audio_file_path) as file:
        recognizer.record(file)
    try:
        # Carica il file audio
        audio = AudioSegment.from_file(audio_file_path, format="wav")
        # Utilizza solo i primi 10 secondi
        audio = audio[:10000]
        # Esporta l'audio in formato WAV in un buffer di byte
        buffer = io.BytesIO()
        buffer.name = 'audio.wav'
        audio.export(buffer, format="wav")

        # recognizer_openai_whisper
        response = openai.Audio.transcribe("whisper-1", buffer)

        # Gestisci correttamente la risposta
        if 'text' in response:
            text = response['text']
            return text
        else:
            print("Risposta inattesa da OpenAI:", response)
            return "Parole non riconosciute. General_exception"
    except Exception as e:
        print("Errore durante il riconoscimento vocale:", e)
        return "Parole non riconosciute. General_exception"


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


def download_and_encode_image(image_url):
    response = requests.get(image_url)
    if response.status_code == 200:
        image_content = response.content
        image = Image.open(BytesIO(image_content))
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    else:
        raise ValueError(f"Failed to download image from {image_url}, status code: {response.status_code}")



def photo_recognizer(message, bot_telegram, openai):
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
            base64_image = download_and_encode_image(image_url)

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.getenv('TOKEN_CHAT_GPT')}"
            }

            payload = {
                "model": "gpt-4-vision-preview",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Scrivi solo la quantità come questo formato di esempio 100g con accanto il nome del cibo. Non scrivere il punto finale"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 300
            }

            # Utilizza OpenAI Vision per analizzare l'immagine
            result = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            print(result)

            # Esegui l'inferenza utilizzando il percorso temporaneo del file
            if result.status_code == 200:
                chatgpt_response = result.json()
                if 'choices' in chatgpt_response and chatgpt_response['choices']:
                    content_value = chatgpt_response['choices'][0]['message']['content']
                    return content_value
                else:
                    os.remove(temp_file.name)
                    print("Errore durante l'estrazione del valore 'content' dal risultato di OpenAI API.")
                    return bot_telegram.send_message(telegram_id,
                                                     "Errore durante l'estrazione del risultato. Riprovare!")
            else:
                os.remove(temp_file.name)
                print(f"Errore durante la richiesta a OpenAI API. Codice di risposta: {result.status_code}")
                print(result.text)  # Stampa il testo della risposta per ottenere dettagli aggiuntivi
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

            if call.data == 'cancella_si':
                # Esegui l'aggiornamento nel database per cancellare i dati del profilo
                delete_user_profile(user_id)
                # Invia un messaggio di conferma
                bot_telegram.send_message(user_id, "I dati del 👤profilo sono stati cancellati🚨.\n Considera di condividere i dati del tuo profilo per rendere le mie risposte più efficienti😊")

            elif call.data == 'cancella_no':
                # L'utente ha scelto di non cancellare i dati
                bot_telegram.send_message(user_id, "Hai scelto di non cancellare i dati del profilo😊. \n Le mie risposte saranno più efficienti😁")

            if user_response == 'consenso_modifica_si':
                # Utente ha acconsentito, puoi iniziare con le domande di profilazione
                bot_telegram.send_message(user_id, "Ottimo! Cominciamo con le domande di profilazione 👤")
                self.invia_domanda_attuale(user_id)  # Inizia chiedendo la prima domanda
            if user_response == 'consenso_modifica_no':
                # Utente ha rifiutato, puoi gestire di conseguenza
                bot_telegram.send_message(user_id,
                                          "Puoi utilizzare il bot, ma non acconsentendo alla profilazione, "
                                          "le mie risposte risulteranno meno efficienti😢")
                self.profile_completed = True

            if user_response == 'consenso_si':
                # Utente ha acconsentito, puoi iniziare con le domande di profilazione
                bot_telegram.send_message(user_id, "Ottimo! Cominciamo con le domande di profilazione 👤")
                self.invia_domanda_attuale(user_id)  # Inizia chiedendo la prima domanda
            if user_response == 'consenso_no':
                # Utente ha rifiutato, puoi gestire di conseguenza
                bot_telegram.send_message(user_id,
                                          "Puoi utilizzare il bot, ma non acconsentendo alla profilazione, "
                                          "le mie risposte risulteranno meno efficienti😢")
                self.profile_completed = True
                if check_time_in_range(current_time_reminder, ORA_COLAZIONE_START, ORA_COLAZIONE_END):
                    bot_telegram.send_message(user_id,
                                              "Colazione time! 🥛 Cosa hai mangiato a colazione? \n⚠️ Indica prima del cibo "
                                              "la quantità.")

                elif check_time_in_range(current_time_reminder, ORA_PRANZO_START, ORA_PRANZO_END):
                    bot_telegram.send_message(user_id,
                                              "Pranzo time! 🍽 Cosa hai mangiato a pranzo? \n⚠️ Indica prima del cibo la quantità.")

                elif check_time_in_range(current_time_reminder, ORA_CENA_START, ORA_CENA_END):
                    bot_telegram.send_message(user_id,
                                              "Cena time! 🍽 Cosa hai mangiato a cena? \n⚠️ Indica prima del cibo la quantità.")

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
                                              "Colazione time! 🥛 Cosa hai mangiato a colazione? \n⚠️ Indica prima del cibo "
                                              "la quantità.")

                elif check_time_in_range(current_time_reminder, ORA_PRANZO_START, ORA_PRANZO_END):
                    bot_telegram.send_message(user_id,
                                              "Pranzo time! 🍽 Cosa hai mangiato a pranzo? \n⚠️ Indica prima del cibo la quantità.")

                elif check_time_in_range(current_time_reminder, ORA_CENA_START, ORA_CENA_END):
                    bot_telegram.send_message(user_id,
                                              "Cena time! 🍽 Cosa hai mangiato a cena? \n⚠️ Indica prima del cibo la quantità.")
                else:
                    print("Non è orario per i reminder")



            elif user_response.startswith('consumo_acqua_'):
                consumo_acqua_selezionato = user_response[len('consumo_acqua_'):]
                print(consumo_acqua_selezionato)
                self.salva_consumo_acqua(user_id, consumo_acqua_selezionato)







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

    def salva_consumo_acqua(self, chat_id, consumo_acqua):
        global mysql_connection, mysql_cursor
        try:
            mysql_connection, mysql_cursor = connect_mysql()

            # Ottieni l'ultimo ID presente nella tabella giorno_settimana
            get_last_id_query = "SELECT MAX(giorno_settimana_id) FROM giorno_settimana"
            mysql_cursor.execute(get_last_id_query)
            last_giorno_settimana_id = mysql_cursor.fetchone()[0]

            if last_giorno_settimana_id is not None:
                # Esegui l'inserimento o l'aggiornamento nella tabella consumo_acqua
                insert_update_query = """
                INSERT INTO consumo_acqua (giorno_settimana_id, consumo)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE consumo = %s, giorno_settimana_id = LAST_INSERT_ID(giorno_settimana_id)
                """
                mysql_cursor.execute(insert_update_query, (last_giorno_settimana_id, consumo_acqua, consumo_acqua))

                # Commit delle modifiche al database
                mysql_connection.commit()

                # Ottieni l'ID dell'ultimo record inserito o aggiornato
                last_inserted_id_query = "SELECT LAST_INSERT_ID()"
                mysql_cursor.execute(last_inserted_id_query)
                last_inserted_id = mysql_cursor.fetchone()[0]

                # Invia un messaggio di conferma all'utente
                confirmation_message = f"Grazie! 😊 Il tuo consumo di acqua giornaliero è stato registrato.✅\n Hai consumato: {consumo_acqua} litri💧\n\n Chiedimi ciò che desideri 😊"
                self.bot_telegram.send_message(chat_id, confirmation_message, disable_notification=True)

        except IntegrityError as integrity_error:
            print(f"Vincolo di integrità violato: {integrity_error}")
            self.bot_telegram.send_message(chat_id, text="⚠️ Hai inserito un valore errato. Riprova.")








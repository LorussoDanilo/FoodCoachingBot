import logging
import os
import subprocess
import threading
import time
import traceback

import speech_recognition as sr
from dotenv import load_dotenv

from chatGPT_response import write_chatgpt
from handle_reminder_response import periodic_reminder
from handle_user_data import get_user_profile, create_new_user, ask_next_question, get_all_telegram_ids
from utils.connection import connect, connect_mysql, call_create_tables_and_data_if_not_exists
from utils.controls import control_tag

load_dotenv()

# Constant
START_COMMAND = 'start'
EDIT_COMMAND = 'modifica'

# Connessione a MySQL
mysql_connection, mysql_cursor = connect_mysql()
# metodo per creare il database e le tabelle del database
call_create_tables_and_data_if_not_exists()

# Dizionario per tenere traccia dello stato dell'utente
user_states = {}

# Dichiarazione di telegram_id come variabile globale

# Aggiungi una variabile di controllo per indicare se tutte le risposte sono state date
all_responses_received = False
periodic_thread_running = False
openai, bot_telegram, root = connect()
asking_questions = True

event = threading.Event()
index = 0
questions_and_fields = [
    ('Qual è la tua età?', 'eta'),
    ('Quali sono le tue patologie o disturbi?', 'malattie'),
    ('Che sentimento provi mentre mangi o pensi al cibo? Indicalo scrivendo: tristezza, indifferenza, ansia, felicità',
     'emozione')
]

BOT_TOKEN = os.getenv("TOKEN_TELEGRAM")

# Verifica che il token sia stato fornito
if BOT_TOKEN is None:
    raise Exception('Il token per il bot deve essere fornito (variabile TOKEN_TELEGRAM)')

r = sr.Recognizer()

users = get_all_telegram_ids()

LOG_FOLDER = '.logs'
if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)



logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=f'{LOG_FOLDER}/app.log'
)

logger = logging.getLogger('telegram-bot')
logging.getLogger('urllib3.connectionpool').setLevel('INFO')

language = 'it-IT'



if __name__ == '__main__':

    @bot_telegram.message_handler(commands=[EDIT_COMMAND])
    def edit_command(message):
        global asking_questions, question_and_fields
        telegram_id = message.chat.id
        index1 = 0
        user_profile_edit = get_user_profile(telegram_id)
        if not user_profile_edit:
            create_new_user(telegram_id, message.chat.username)

        bot_telegram.send_message(telegram_id, message.chat.username + " " + "modifica i dati del tuo profilo!")
        # Invia il messaggio iniziale

        # Domande per l'aggiornamento delle informazioni

        # Inizia a fare domande per l'aggiornamento delle informazioni
        ask_next_question(telegram_id, bot_telegram, questions_and_fields, index1)


    @bot_telegram.message_handler(commands=[START_COMMAND])
    def send_welcome(message):
        event.set()
        global questions_and_fields, index  # Dichiarazione di telegram_id come variabile globale

        telegram_id = message.chat.id
        # Check if the user exists in the database
        user_profile_start = get_user_profile(telegram_id)
        print(user_profile_start)
        if not user_profile_start:
            # User doesn't exist, create a new entry in the database
            create_new_user(telegram_id, message.chat.username)

        # Tutte le informazioni necessarie sono state fornite
        msg = control_tag(root, "./telegram/informazioni", START_COMMAND, "spiegazioni")
        bot_telegram.send_message(telegram_id, msg.replace('{nome}', message.chat.first_name))
        # Inizia chiedendo la prima domanda
        print("pre-start" + index.__str__())

        question, field = questions_and_fields[index]
        bot_telegram.send_message(telegram_id, question)
        index += 1

        print("post-start" + index.__str__())

    @bot_telegram.message_handler(content_types=['text', 'voice'])
    def handle_user_messages(message):
        global asking_questions, index, questions_and_fields  # Aggiungi questa riga
        telegram_id = message.chat.id

        if event.is_set() and len(questions_and_fields) >= index:
            # Gestisci i nuovi messaggi degli utenti qui
            handle_user_response(message)
        else:
            if message.content_type == 'text':
                event.clear()
                user_response = str(message.text)
                user_profile = get_user_profile(telegram_id)
                print(user_profile)
                respost = write_chatgpt(openai, user_response, user_profile)
                bot_telegram.send_message(message.chat.id, respost)
                mysql_connection.close()

            elif message.content_type == 'voice':
                voice_handler(message)




@bot_telegram.message_handler(func=lambda message: True)
def handle_user_response(message):
    global index, mysql_connection
    try:
        print("pre-handler" + index.__str__())
        user_response = str(message.text)
        telegram_id = message.chat.id
        mysql_connection, cursor = connect_mysql()

        # Esecuzione della query per aggiornare il profilo dell'utente nel database
        update_query = f"UPDATE utenti SET {questions_and_fields[index - 1][1]} = %s WHERE telegram_id = %s"
        cursor.execute(update_query, (user_response, telegram_id))

        # Commit delle modifiche al database
        mysql_connection.commit()

        confirmation_message = f"{questions_and_fields[index - 1][1]} salvat*: {user_response}"
        bot_telegram.send_message(telegram_id, confirmation_message)

        # Passa alla prossima domanda se ci sono ancora domande
        if index <= len(questions_and_fields):
            question, field = questions_and_fields[index]
            bot_telegram.send_message(telegram_id, question)
            index += 1


        print("post-handler" + index.__str__())

    except IndexError as e:
        print(f"Ultima domanda raggiunta: {e}")
        event.clear()
        telegram_id = message.chat.id
        bot_telegram.send_message(telegram_id,
                                  "Il tuo profilo è completo. Grazie! Chiedimi ciò che desideri😊")
        mysql_connection.close()


@bot_telegram.message_handler(func=lambda message: True)
def voice_handler(message):
    global language
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

        # Call the function with the desired language
        text = voice_recognizer()
        event.clear()

        user_profile = get_user_profile(telegram_id)
        print(user_profile)
        respost = write_chatgpt(openai, text, user_profile)
        bot_telegram.send_message(message.chat.id, respost)
        mysql_connection.close()
        _clear()


def voice_recognizer():
    ffmpeg_path = 'C:\\Users\\Danilo Lorusso\\Desktop\\ffmpeg-master-latest-win64-gpl\\bin\\ffmpeg.exe'
    global r, language

    #convertire un file audio da formato OGG a formato WAV
    subprocess.run([ffmpeg_path, '-i', 'audio.ogg', 'audio.wav', '-y'])

    audio_file_path = 'audio.wav'

    with sr.AudioFile(audio_file_path) as file:
        audio = r.record(file)

    # Set up the SpeechRecognition recognizer
    try:
        # Use recognize_sphinx instead of recognize_google
        text = r.recognize_google_cloud(audio, os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), language=language)
        print(text + ' recognizer')

    except sr.UnknownValueError:
        logger.warning("Google Cloud Speech Recognition could not understand the audio.")
        text = 'Parole non riconosciute.'

    except sr.RequestError as e:
        logger.error(f"Google Cloud Speech Recognition request failed; {e}")
        text = 'Parole non riconosciute.'

    except Exception as e:
        logger.error(f"Exception:\n{traceback.format_exc()}")
        print(f"Exception: {e}")
        text = 'Parole non riconosciute.'

    return text


def _clear():
    input_path = 'audio.ogg'
    output_path = 'audio.wav'
    _files = [input_path, output_path]
    for _file in _files:
        if os.path.exists(_file):
            os.remove(_file)


# Esegui il polling infinito del bot Telegram
bot_telegram.infinity_polling()

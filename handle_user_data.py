import os

from utils.connection import connect_mysql
import traceback
import subprocess
import speech_recognition as sr
import logging

handle_user_response_gpt_enabled = False

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


def create_new_user(telegram_id, username):
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
    try:
        # Connect to MySQL and get a cursor
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


def get_all_telegram_ids():
    mysql_connection, mysql_cursor = connect_mysql()
    # Query SQL per recuperare tutti gli ID di Telegram dalla tabella utenti
    mysql_cursor.execute("SELECT telegram_id FROM utenti")
    result = mysql_cursor.fetchall()
    mysql_cursor.close()

    # Restituisci una lista di ID di Telegram
    return [row[0] for row in result]


# Update data Funzione per fare domande per l'aggiornamento delle informazioni
def ask_next_question(telegram_id, bot, questions_and_fields, index):
    if index < len(questions_and_fields):
        question, field = questions_and_fields[index]
        bot.send_message(telegram_id, question)
        # Registra la funzione di gestione della risposta
        bot.register_next_step_handler_by_chat_id(telegram_id, lambda m: handle_update_response(m, telegram_id, bot,
                                                                                                questions_and_fields,
                                                                                                index))
    else:
        # Se tutte le domande sono state fatte, comunica all'utente che i dati sono stati aggiornati
        bot.send_message(telegram_id, "I tuoi dati sono stati aggiornati con successo!")

    # Funzione per gestire la risposta dell'utente
    def handle_update_response(message, telegram_id_update, bot_update, questions_and_fields_update, index_update):
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
            ask_next_question(telegram_id_update, bot_update, questions_and_fields_update, index_update + 1)

        except Exception as e:
            print(f"Errore durante la gestione della risposta: {e}")


def voice_recognizer():
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
        # Use recognize_sphinx instead of recognize_google
        text = recognizer.recognize_google_cloud(audio, os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), language=language)
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


# Metodo per cancellare i file .ogg e .wav generati
def _clear():
    input_path = 'audio.ogg'
    output_path = 'audio.wav'
    _files = [input_path, output_path]
    for _file in _files:
        if os.path.exists(_file):
            os.remove(_file)

import threading
import time

from dotenv import load_dotenv
from mysql.connector import IntegrityError

from chatGPT_response import write_chatgpt
from handle_reminder_response import periodic_reminder
from handle_user_data import get_user_profile, create_new_user, ask_next_question, get_all_telegram_ids, \
    voice_recognizer, _clear
from utils.connection import connect, connect_mysql, call_create_tables_and_data_if_not_exists
from utils.controls import control_tag

load_dotenv()

# Constant
START_COMMAND = 'start'
EDIT_COMMAND = 'modifica'
PROFILO_COMMAND = 'profilo'

# Domande da porre all'utente durante la profilazione o modifica dei dati del profilo
questions_and_fields = [
    ('Qual è la tua età?', 'eta'),
    ('Quali sono le tue patologie o disturbi?', 'malattie'),
    ('Che sentimento provi mentre mangi o pensi al cibo? Indicalo scrivendo: tristezza, indifferenza, ansia, felicità',
     'emozione')
]

# variabile contenente tutti gli id telegram degli utenti registrati
users = get_all_telegram_ids()

# Connessione a MySQL
mysql_connection, mysql_cursor = connect_mysql()

# metodo per creare il database e le tabelle del database
call_create_tables_and_data_if_not_exists()

# Inizializzazione variabili per il bot telegram, api di chat gpt e del file xml con le informazioni
openai, bot_telegram, root = connect()

# variabile booleana per verificare se il thread è in esecuzione o meno
periodic_thread_running = False

# Variabile per gestire le funzionalità del chatbot. Serve per capire quando una funzionalità deve cominciare
event = threading.Event()

# Indice delle domande
index = 0


# Avvio del thread per inviare i reminders
def send_periodic_reminders(message_id):
    while True:
        message = bot_telegram.get_message(message_id)
        telegram_id = message.chat.id
        periodic_reminder(telegram_id, message, mysql_cursor, bot_telegram)
        time.sleep(3600)


# Metodo per gestire il message handler dei reminder
def your_message_handler(message):
    message_id = message.message_id
    periodic_reminders_thread = threading.Thread(target=send_periodic_reminders, args=(message_id,))
    periodic_reminders_thread.start()


# Impostazione del gestore del messaggio
bot_telegram.message_handler(func=your_message_handler)

if __name__ == '__main__':

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
        event.set()
        global questions_and_fields, index  # Dichiarazione di telegram_id come variabile globale

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

    # metodo per gestire i messaggi dell'utente dopo la profilazione. Sono gestiti sia i messaggi di testo che quelli
    # vocali
    @bot_telegram.message_handler(content_types=['text', 'voice'])
    def handle_user_messages(message):
        global index, questions_and_fields
        telegram_id = message.chat.id

        # Finchè l'evento è settato a True viene eseguito il metodo handle_user_response altrimenti i messaggi vengono
        # passati a chatgpt.
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


# Metodo per gestire le risposte dell'utente alle domande della profilazione
@bot_telegram.message_handler(func=lambda message: True)
def handle_user_response(message):
    global index, mysql_connection, mysql_cursor
    try:
        print("pre-handler" + index.__str__())
        user_response = str(message.text)
        telegram_id = message.chat.id
        mysql_connection, mysql_cursor = connect_mysql()

        # Esecuzione della query per aggiornare il profilo dell'utente nel database
        update_query = f"UPDATE utenti SET {questions_and_fields[index - 1][1]} = %s WHERE telegram_id = %s"
        mysql_cursor.execute(update_query, (user_response, telegram_id))

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
    except Exception as e:
        print(f"Valore errato: {e}")
        telegram_id = message.chat.id
        bot_telegram.send_message(telegram_id, "Hai inserito un valore errato. Riprova.")

    except IntegrityError as integrity_error:
        print(f"Vincolo di integrità violato: {integrity_error}")
        telegram_id = message.chat.id
        bot_telegram.send_message(telegram_id, "Hai inserito un valore errato. Riprova.")


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
        event.clear()

        user_profile = get_user_profile(telegram_id)
        print(user_profile)
        respost = write_chatgpt(openai, text, user_profile)
        bot_telegram.send_message(message.chat.id, respost)
        mysql_connection.close()
        # chiamare il metodo per cancellare i file .ogg e .wav generati
        _clear()


# Esegui il polling infinito del bot Telegram
bot_telegram.infinity_polling()

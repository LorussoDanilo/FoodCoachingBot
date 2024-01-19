import asyncio
import threading
import time
import tracemalloc
from datetime import datetime, time

from dotenv import load_dotenv
from mysql.connector import IntegrityError

from chatGPT_response import write_chatgpt
from handle_reminder_data import save_user_food_response
from handle_user_data import get_user_profile, create_new_user, ask_next_question, get_all_telegram_ids, \
    voice_recognizer, _clear
from utils.connection import connect, connect_mysql, call_create_tables_if_not_exists
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

# Crea una coda per gestire l'invio dei promemoria pasti
reminder_queue = asyncio.Queue()
tracemalloc.start()


# Invia i promemoria pasti in modo asincrono
async def send_meal_reminder_loop(message):
    global reminder_queue
    await reminder_queue.put(message)
    loop = asyncio.get_event_loop()
    await loop.create_task(send_meal_reminder_async())
    loop.run_forever()  # Utilizza asyncio.create_task per avviare la funzione asincrona


# Thread per gestire l'invio dei promemoria pasti
async def send_meal_reminder_async():
    global meal_type, mysql_cursor, mysql_connection, reminder_queue

    while True:
        try:
            message = await reminder_queue.get()  # Wait if the queue is empty
            current_time = datetime.now().time()
            telegram_ids = get_all_telegram_ids()
            user_response = str(message.text)

            for telegram_id in telegram_ids:
                if time(7, 0) <= current_time <= time(11, 0):
                    bot_telegram.send_message(telegram_id, "Buongiorno! Cosa hai mangiato a colazione?")
                    meal_type = "colazione"
                    save_user_food_response(bot_telegram, mysql_cursor, mysql_connection, telegram_id, meal_type,
                                            user_response)

                elif current_time >= time(12, 0) and datetime.now().time() <= time(14, 0):
                    bot_telegram.send_message(telegram_id, "Pranzo time! Cosa hai mangiato a pranzo?")
                    meal_type = "pranzo"
                    save_user_food_response(bot_telegram, mysql_cursor, mysql_connection, telegram_id, meal_type,
                                            user_response)
                elif current_time >= time(15, 0) and datetime.now().time() <= time(22, 0):
                    bot_telegram.send_message(telegram_id, "Cena! Cosa hai mangiato a cena?")
                    meal_type = "cena"
                    save_user_food_response(bot_telegram, mysql_cursor, mysql_connection, telegram_id, meal_type,
                                            user_response)
                    await asyncio.sleep(60 * 60 * 24)  # Wait for 24 hours before sending the next reminder

        except Exception as e:
            print(f"Error during meal reminder sending: {e}")


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

    # metodo per gestire i messaggi dell'utente dopo la profilazione. Sono gestiti sia i messaggi di testo che quelli
    # vocali
    @bot_telegram.message_handler(content_types=['text', 'voice'], )
    def handle_messages_after_profile_questions(message):
        global index, questions_and_fields
        telegram_id = message.chat.id

        # Finchè l'evento è settato a True viene eseguito il metodo handle_user_response altrimenti i messaggi vengono
        # passati a chatgpt.
        if event.is_set() and len(questions_and_fields) >= index:
            # Gestisci i nuovi messaggi degli utenti qui
            handle_profile_response(message)
        else:
            # Impostazione del gestore del messaggio
            # Invia i promemoria pasti in modo asincrono
            asyncio.run(send_meal_reminder_loop(message))
            # Impostazione del gestore del messaggio
            if message.content_type == 'text':
                user_response = str(message.text)
                asyncio.create_task(handle_user_response_after_reminder(user_response, telegram_id))

            elif message.content_type == 'voice':
                voice_handler(message)


# Metodo per gestire le risposte dell'utente dopo l'invio del promemoria pasto
async def handle_user_response_after_reminder(user_response, telegram_id):
    # Your subsequent code after the completion of send_meal_reminder_async
    user_profile = get_user_profile(telegram_id)
    print(user_profile)
    respost = write_chatgpt(openai, user_response, user_profile)
    bot_telegram.send_message(telegram_id, respost)


# Metodo per gestire le risposte dell'utente alle domande della profilazione
@bot_telegram.message_handler(func=lambda message: True)
def handle_profile_response(message):
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
        asyncio.run(send_meal_reminder_loop(message))
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

        user_profile = get_user_profile(telegram_id)
        print(user_profile)
        respost = write_chatgpt(openai, text, user_profile)
        bot_telegram.send_message(message.chat.id, respost)
        mysql_connection.close()
        # chiamare il metodo per cancellare i file .ogg e .wav generati
        _clear()


# Esegui il polling infinito del bot Telegram
bot_telegram.infinity_polling()

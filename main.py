import os
import threading
import openai
from dotenv import load_dotenv

from chatGPT_response import write_chatgpt
from utils.connection import connect, connect_mongodb
from utils.controls import control_tag
from reminder.handle_reminder_response import handle_user_meal
from handle_user_data import get_user_profile, update_user_profile, ask_user_info
from reminder.reminder import periodic_task, send_periodic_reminders

load_dotenv()

# constant
MONGODB_URI = os.getenv('MONGODB_URI')
COLLECTION_NAME = os.getenv('COLLECTION_NAME')
DATABASE_NAME = os.getenv('foodCoachUsers')
START_COMMAND = 'start'

if __name__ == '__main__':
    openai, bot_telegram, root = connect()
    control_eta = False
    mongo_client, user_profiles_collection = connect_mongodb()

    # Create an Event object
    stop_event = threading.Event()

    # Flag to check if the thread is already running
    periodic_thread_running = False

    @bot_telegram.message_handler(commands=[START_COMMAND])
    def send_welcome(message):
        msg = control_tag(root, "./telegram/informazioni", START_COMMAND, "spiegazioni")
        bot_telegram.send_message(message.chat.id, msg.replace('{nome}', message.chat.first_name))


    @bot_telegram.message_handler(func=lambda message: True)
    def echo_all(message):
        telegram_id = message.chat.id
        # Call the function if the user doesn't have a name
        ask_user_info(telegram_id, user_profiles_collection, bot_telegram, 'age', 'Qual è la tua età?')

        global periodic_thread_running

        # Start the thread for periodic tasks only if it hasn't been started
        if not periodic_thread_running:
            # Avvia il thread per le attività periodiche
            periodic_task(user_profiles_collection, bot_telegram, stop_event)
            periodic_thread_running = True

        # Once the user has a name, send periodic reminders
        send_periodic_reminders(telegram_id, user_profiles_collection, bot_telegram)

        # Invia i promemoria dei pasti
        print(message.text)

        # Simula il salvataggio del profilo utente nel database
        user_message = message.text
        # Gestisci il pasto inviato dall'utente
        handle_user_meal(telegram_id, user_message, user_profiles_collection)

        # Aggiorna il profilo utente con la risposta corrente
        response = write_chatgpt(openai, user_message)

        print(response)
        bot_telegram.send_message(message.chat.id, response)

    # Ciclo principale del bot
    bot_telegram.infinity_polling()

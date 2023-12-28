import threading

import openai
from dotenv import load_dotenv

from chatGPT_response import write_chatgpt
from handle_user_data import ask_user_info, get_user_profile, create_new_user
from utils.connection import connect, connect_mysql
from utils.controls import control_tag

load_dotenv()

# constant
START_COMMAND = 'start'

# Create an Event object
stop_event = threading.Event()
mysql_connection, mysql_cursor = connect_mysql()
# Flag to check if the thread is already running
periodic_thread_running = False

if __name__ == '__main__':
    openai, bot_telegram, root = connect()


    @bot_telegram.message_handler(commands=[START_COMMAND])
    def send_welcome(message):
        telegram_id = message.chat.id

        # Check if the user exists in the database
        user_profile = get_user_profile(telegram_id)

        if not user_profile:
            # User doesn't exist, create a new entry in the database
            create_new_user(telegram_id, message.chat.username)

        # Tutte le informazioni necessarie sono state fornite
        msg = control_tag(root, "./telegram/informazioni", START_COMMAND, "spiegazioni")
        bot_telegram.send_message(telegram_id, msg.replace('{nome}', message.chat.first_name))
        questions_and_fields_eta = [('Qual è la tua età?', 'eta')]
        questions_and_fields_malattie = [('Quali sono le tue patologie o disturbi?', 'malattie')]
        questions_and_fields_emozione = [('Che sentimento provi mentre mangi o pensi al cibo', 'emozione')]

        if not user_profile.get('eta'):
            # L'utente non ha fornito l'età, chiedi le informazioni mancanti
            ask_user_info(telegram_id, bot_telegram, questions_and_fields_eta)
            return

        if not user_profile.get('malattie'):
            # L'utente non ha fornito informazioni sulle malattie, chiedi le informazioni mancanti
            ask_user_info(telegram_id, bot_telegram, questions_and_fields_malattie)
            return

        if not user_profile.get('emozione'):
            # L'utente non ha fornito informazioni sull'emozione, chiedi le informazioni mancanti
            ask_user_info(telegram_id, bot_telegram, questions_and_fields_emozione)
            return


    # Ciclo principale del bot
    bot_telegram.infinity_polling()

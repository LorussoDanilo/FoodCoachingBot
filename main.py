import threading
import time

from dotenv import load_dotenv

from chatGPT_response import write_chatgpt
from handle_user_data import ask_user_info, get_user_profile, create_new_user
from utils.connection import connect, connect_mysql
from utils.controls import control_tag

load_dotenv()

# Constant
START_COMMAND = 'start'

# Connessione a MySQL
mysql_connection, mysql_cursor = connect_mysql()

# Evento per fermare il thread
stop_event = threading.Event()

# Flag per verificare se il thread periodico è già in esecuzione
periodic_thread_running = False

# Dizionario per tenere traccia dello stato dell'utente
user_states = {}

# Dichiarazione di telegram_id come variabile globale
telegram_id = None

# Aggiungi una variabile di controllo per indicare se tutte le risposte sono state date
all_responses_received = False


def periodic_task():
    # Nel loop del thread periodico, controlla se tutte le risposte sono state ricevute
    while not stop_event.is_set() and not all_responses_received:
        # Tuo codice per il task periodico qui
        time.sleep(60)  # Esempio: attesa di 60 secondi tra i cicli


if __name__ == '__main__':
    openai, bot_telegram, root = connect()

    @bot_telegram.message_handler(commands=[START_COMMAND])
    def send_welcome(message):
        global telegram_id  # Dichiarazione di telegram_id come variabile globale
        telegram_id = message.chat.id

        # Check if the user exists in the database
        user_profile = get_user_profile(telegram_id)

        if not user_profile:
            # User doesn't exist, create a new entry in the database
            create_new_user(telegram_id, message.chat.username)

        # Tutte le informazioni necessarie sono state fornite
        msg = control_tag(root, "./telegram/informazioni", START_COMMAND, "spiegazioni")
        bot_telegram.send_message(telegram_id, msg.replace('{nome}', message.chat.first_name))
        questions_and_fields = [
            ('Qual è la tua età?', 'eta'),
            ('Quali sono le tue patologie o disturbi?', 'malattie'),
            ('Che sentimento provi mentre mangi o pensi al cibo? Indicalo scrivendo: Positivo, Neutrale, Negativo', 'emozione')
        ]

        for question, field in questions_and_fields:
            if not user_profile.get(field):
                # L'utente non ha fornito l'informazione, chiedi le informazioni mancanti
                user_states[telegram_id] = {'current_question': question, 'current_field': field}
                ask_user_info(telegram_id, bot_telegram, questions_and_fields, user_states)
                return
        # Se tutte le domande sono state risposte, puoi eseguire ulteriori azioni qui

        @bot_telegram.message_handler(func=lambda message_gpt: message_gpt.chat.id == telegram_id)
        def handle_user_response(message_gpt):
            response_from_chatgpt = write_chatgpt(openai, message_gpt, user_profile)

            # Invia la risposta di ChatGPT al bot Telegram
            bot_telegram.send_message(telegram_id, response_from_chatgpt)

            print(f"Tutte le domande sono state risposte da {telegram_id}")

            global all_responses_received
            all_responses_received = True


    # Start del thread periodico
    if not periodic_thread_running:
        threading.Thread(target=periodic_task, daemon=True).start()
        periodic_thread_running = True

    stop_event.set()
    # Esegui il polling infinito del bot Telegram
    bot_telegram.infinity_polling()



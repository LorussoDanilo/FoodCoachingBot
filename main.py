import threading

from dotenv import load_dotenv

from chatGPT_response import write_chatgpt
from handle_user_data import get_user_profile, create_new_user, ask_next_question
from utils.connection import connect, connect_mysql, call_create_tables_and_data_if_not_exists
from utils.controls import control_tag

load_dotenv()

# Constant
START_COMMAND = 'start'
EDIT_COMMAND = 'modifica'

# Connessione a MySQL
mysql_connection, mysql_cursor = connect_mysql()

# Dizionario per tenere traccia dello stato dell'utente
user_states = {}

# Dichiarazione di telegram_id come variabile globale
telegram_id = None

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

# metodo per creare il database e le tabelle del database
call_create_tables_and_data_if_not_exists()

if __name__ == '__main__':

    @bot_telegram.message_handler(commands=[EDIT_COMMAND])
    def edit_command(message):
        global telegram_id, asking_questions, question_and_fields
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
        global telegram_id, questions_and_fields, index  # Dichiarazione di telegram_id come variabile globale

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


    @bot_telegram.message_handler(func=lambda message: True)
    def handle_user_messages(message):
        global telegram_id, asking_questions, index, questions_and_fields  # Aggiungi questa riga
        telegram_id = message.chat.id
        if event.is_set() and len(questions_and_fields) >= index:
            # Gestisci i nuovi messaggi degli utenti qui
            # ask_next_question_start(bot_telegram, question_and_fields, telegram_id, index)
            handle_user_response(message)
        else:
            event.clear()
            user_response = str(message.text)
            user_profile = get_user_profile(telegram_id)
            print(user_profile)
            respost = write_chatgpt(openai, user_response, user_profile)
            bot_telegram.send_message(message.chat.id, respost)
            mysql_connection.close()


@bot_telegram.message_handler(func=lambda message: True)
def handle_user_response(message):
    global index, mysql_connection
    try:
        print("pre-handler" + index.__str__())
        user_response = str(message.text)
        telegram_user_id = message.chat.id
        mysql_connection, cursor = connect_mysql()

        # Esecuzione della query per aggiornare il profilo dell'utente nel database
        update_query = f"UPDATE utenti SET {questions_and_fields[index - 1][1]} = %s WHERE telegram_id = %s"
        cursor.execute(update_query, (user_response, telegram_user_id))

        # Commit delle modifiche al database
        mysql_connection.commit()

        confirmation_message = f"{questions_and_fields[index - 1][1]} salvat*: {user_response}"
        bot_telegram.send_message(telegram_user_id, confirmation_message)

        # Passa alla prossima domanda se ci sono ancora domande
        if index <= len(questions_and_fields):
            question, field = questions_and_fields[index]
            bot_telegram.send_message(telegram_id, question)
            index += 1

        print("post-handler" + index.__str__())

    except Exception as e:
        print(f"Errore durante la gestione della risposta: {e}")
        event.clear()
        bot_telegram.send_message(telegram_id,
                                  "Il tuo profilo è completo. Grazie! Ora puoi porre al chatbot una qualsiasi domanda")
        mysql_connection.close()


# Esegui il polling infinito del bot Telegram
bot_telegram.infinity_polling()

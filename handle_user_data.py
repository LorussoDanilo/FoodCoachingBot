from utils.connection import connect_mysql


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


def get_user_profile(telegram_id):
    try:
        # Connect to MySQL and get a cursor
        mysql_connection, mysql_cursor = connect_mysql()

        # Query SQL to retrieve the user profile based on telegram_id
        mysql_cursor.execute("SELECT * FROM utenti WHERE telegram_id = %s", (telegram_id,))
        result = mysql_cursor.fetchone()

        # Close the cursor
        mysql_cursor.close()

        # Return the user profile if present, otherwise an empty dictionary
        return dict(zip(mysql_cursor.column_names, result)) if result else {}

    except Exception as e:
        print(f"Error getting user profile: {e}")

        return {}  # Raising the exception to be caught by the calling code


def get_all_telegram_ids(mysql_cursor):
    # Query SQL per recuperare tutti gli ID di Telegram dalla tabella utenti
    mysql_cursor.execute("SELECT telegram_id FROM utenti")
    result = mysql_cursor.fetchall()
    mysql_cursor.close()

    # Restituisci una lista di ID di Telegram
    return [row[0] for row in result]


def ask_user_info(telegram_id, bot, questions_and_fields, state):
    state = {
        'current_index': 0,
        'user_state': {field: False for _, field in questions_and_fields}
    }

    current_question, current_field = questions_and_fields[state['current_index']]

    @bot.message_handler(func=lambda message: message.chat.id == telegram_id)
    def handle_user_response(message):
        try:
            nonlocal current_question, current_field
            user_response = str(message.text)  # Assicurati che user_response sia una stringa
            telegram_user_id = message.chat.id

            # Connessione a MySQL e ottenimento di un cursore
            mysql_connection, cursor = connect_mysql()

            # Esecuzione della query per aggiornare il profilo dell'utente nel database
            update_query = f"UPDATE utenti SET {current_field} = %s WHERE telegram_id = %s"
            cursor.execute(update_query, (user_response, telegram_user_id))

            # Invio di un messaggio di conferma all'utente
            confirmation_message = f"{current_field} salvat*: {user_response}"
            bot.send_message(telegram_user_id, confirmation_message)

            # Commit delle modifiche al database
            mysql_connection.commit()

            # Chiusura del cursore
            cursor.close()

            # Aggiornamento dello stato dell'utente
            state['user_state'][current_field] = True

            # Verifica se ci sono altre domande da fare
            next_question, next_field = get_next_question(state['user_state'])
            if next_field:
                # Fai la prossima domanda
                bot.send_message(telegram_user_id, next_question)
                current_question, current_field = next_question, next_field
            else:
                # Se tutte le domande sono state risposte, invia un messaggio finale
                bot.send_message(telegram_user_id, "Grazie per le risposte! Il tuo profilo è completo. Puoi chiedere "
                                                   "al chatbot ciò che desideri!")
                # Chiudi la connessione al database
                mysql_connection.close()

                # Chiudi il cursore
                cursor.close()

        except Exception as e:
            print(f"Errore durante la gestione della risposta: {e}")

    def get_next_question(user_state):
        for question, field in questions_and_fields:
            if not user_state[field]:
                return question, field
        return None, None

    # Inizia con la prima domanda
    bot.send_message(telegram_id, current_question)

    # Registra l'handler del messaggio per la prima domanda
    bot.add_message_handler(handle_user_response)

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


def ask_user_info(telegram_id, bot, questions_and_fields):
    """
    Ask the user for information and update the user profile in the database.

    :param telegram_id: Telegram user ID
    :param bot: Telegram bot
    :param questions_and_fields: List of tuples containing (question, field) pairs
    """
    # Initialize user state
    user_state = {field: False for _, field in questions_and_fields}

    @bot.message_handler(func=lambda message: message.chat.id == telegram_id)
    def handle_user_response(message):
        # Your message handling logic here

        global question
        nonlocal user_state

        # Extract necessary information from the user's message
        user_response = message.text
        telegram_user_id = message.chat.id

        # Connect to MySQL and get a cursor
        mysql_connection, cursor = connect_mysql()

        # Find the field corresponding to the user's response
        current_field = None
        for question, field in questions_and_fields:
            if not user_state[field]:
                current_field = field
                break

        if current_field:
            # Execute the query to update the user's profile in the database
            update_query = f"UPDATE utenti SET {current_field} = %s WHERE telegram_id = %s"
            cursor.execute(update_query, (user_response, telegram_user_id))

            # Send a confirmation message to the user
            confirmation_message = f"{current_field} salvat*: {user_response}"
            bot.send_message(telegram_user_id, confirmation_message)

            # Close the cursor
            cursor.close()

            # Update the user state
            user_state[current_field] = True

            # Check if there are more questions to ask
            next_field = None
            for question, field in questions_and_fields:
                if not user_state[field]:
                    next_field = field
                    break

            if next_field:
                # Ask the next question
                bot.send_message(telegram_user_id, question)
                return

            # If all questions are answered, send a final message
            bot.send_message(telegram_user_id, "Grazie per le risposte! Ora possiamo procedere con altro.")
            mysql_connection.commit()
            # Additional logic for the next step...

    # Ask the first question
    first_question, first_field = questions_and_fields[0]
    bot.send_message(telegram_id, first_question)

    # Register the message handler
    bot.add_message_handler(handle_user_response)



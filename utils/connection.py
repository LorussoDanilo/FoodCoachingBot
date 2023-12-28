# Function to connect to MongoDB
import os
import xml.etree.ElementTree as et

import mysql
import mysql.connector
import openai
import telebot


# constant
TOKEN_CHAT_GPT = 'TOKEN_CHAT_GPT'
TOKEN_TELEGRAM = 'TOKEN_TELEGRAM'
FILE_XML = 'FILE_XML'


def connect_mysql():
    mysql_host = os.getenv("MYSQL_HOST")
    mysql_user = os.getenv("MYSQL_USER")
    mysql_password = os.getenv("MYSQL_PASSWORD")
    mysql_database = os.getenv("MYSQL_DATABASE")

    try:
        # Crea la connessione
        connection = mysql.connector.connect(
            host=mysql_host,
            user=mysql_user,
            password=mysql_password,
            database=mysql_database
        )

        if connection.is_connected():
            print("Connessione a MySQL riuscita!")

            # Crea un oggetto Cursor
            cursor = connection.cursor()

            # Restituisci la connessione e il cursore
            return connection, cursor
    except Exception as e:
        print(f"Errore durante la connessione a MySQL: {e}")

    # Restituisci None se la connessione non è riuscita
    return None, None


# Questa funzione serve per gestire le API e le risorse del progetto
# come l'xml del testo relativo ai comandi usati dall'utente
def connect():
    openai.api_key = os.getenv(TOKEN_CHAT_GPT)
    bot = telebot.TeleBot(os.getenv(TOKEN_TELEGRAM))
    tree = et.parse(os.getenv(FILE_XML))
    return openai, bot, tree.getroot()

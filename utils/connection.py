# Function to connect to MongoDB
import locale
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

locale.setlocale(locale.LC_TIME, 'it_IT')


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
            password=mysql_password
        )

        if connection.is_connected():
            print("Connessione a MySQL riuscita!")

            # Crea un oggetto Cursor
            cursor = connection.cursor()

            # Chiama la funzione per verificare e creare il database se necessario
            create_database_if_not_exists(cursor, mysql_database)

            # Utilizza il database
            cursor.execute(f"USE {mysql_database}")

            # Restituisci la connessione e il cursore
            return connection, cursor
    except Exception as e:
        print(f"Errore durante la connessione a MySQL: {e}")

    # Restituisci None se la connessione non è riuscita
    return None, None


def check_database_existence(cursor, database_name):
    try:
        cursor.execute("SHOW DATABASES")
        databases = cursor.fetchall()
        return (database_name,) in databases
    except Exception as e:
        print(f"Errore durante il controllo dell'esistenza del database: {e}")
        return False


def create_database_if_not_exists(cursor, database_name):
    if not check_database_existence(cursor, database_name):
        try:
            cursor.execute(f"CREATE DATABASE {database_name}")
            print(f"Database '{database_name}' creato con successo.")
        except Exception as e:
            print(f"Errore durante la creazione del database: {e}")


def create_tables(cursor):
    try:
        # Crea le tabelle
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS utenti (
          telegram_id INT PRIMARY KEY,
          nome_utente VARCHAR(255),
          eta INT,
          malattie VARCHAR(255),
          emozione VARCHAR(255) CHECK (emozione IN ('tristezza', 'indifferenza', 'ansia', 'felicità'))
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS dieta_settimanale (
          dieta_settimanale_id INT AUTO_INCREMENT PRIMARY KEY,
          data DATE NOT NULL,
          telegram_id INT NOT NULL,
          FOREIGN KEY(telegram_id) REFERENCES utenti(telegram_id)
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS giorno_settimana (
          giorno_settimana_id INT AUTO_INCREMENT PRIMARY KEY,
          nome VARCHAR(255) NOT NULL, 
          dieta_settimanale_id INT NOT NULL,
          FOREIGN KEY(dieta_settimanale_id) REFERENCES dieta_settimanale(dieta_settimanale_id)
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS periodo_giorno (
         periodo_giorno_id INT AUTO_INCREMENT PRIMARY KEY,
         nome VARCHAR(255) NOT NULL CHECK (nome IN ('Colazione', 'Pranzo', 'Cena')),
         giorno_settimana_id INT NOT NULL,
         FOREIGN KEY(giorno_settimana_id) REFERENCES giorno_settimana(giorno_settimana_id)
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cibo (
          cibo_id INT AUTO_INCREMENT PRIMARY KEY,
          nome VARCHAR(255),
          periodo_giorno_id INT NOT NULL,
          FOREIGN KEY(periodo_giorno_id) REFERENCES periodo_giorno(periodo_giorno_id)
        );
        """)

        print("Tabelle create con successo.")
    except Exception as e:
        print(f"Errore durante la creazione delle tabelle: {e}")


def call_create_tables_if_not_exists():
    connection, cursor = connect_mysql()

    if connection and cursor:
        create_tables(cursor)

        # Commit e chiudi la connessione
        connection.commit()
        connection.close()


# Questa funzione serve per gestire le API e le risorse del progetto
# come l'xml del testo relativo ai comandi usati dall'utente
def connect():
    openai.api_key = os.getenv(TOKEN_CHAT_GPT)
    bot = telebot.TeleBot(os.getenv(TOKEN_TELEGRAM))
    tree = et.parse(os.getenv(FILE_XML))
    return openai, bot, tree.getroot()

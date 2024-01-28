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
    """Questa funzione permette di aprire la connessione con mysql in locale,
    crea il database foodcoachusers e le tabelle se non esiste o uno o l'altro.

    :return: mysql_cursor e mysql_connection
    :rtype: connection.cursor, connection
    """
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
            create_database_and_table_if_not_exists(cursor, mysql_database)

            # Restituisci la connessione e il cursore
            return connection, cursor
    except Exception as e:
        print(f"Errore durante la connessione a MySQL: {e}")

    # Restituisci None se la connessione non è riuscita
    return None, None


def check_database_existence(cursor, database_name):
    """
    Questa funzione controlla se il database esiste

    :param cursor: cursore della connessione per eseguire le query
    :type cursor: Cursor
    :param database_name: nome del database di cui vogliamo controllare l'esistenza
    :type database_name: str

    :return: True oppure False
    :rtype: boolean

    """
    try:
        cursor.execute("SHOW DATABASES")
        databases = cursor.fetchall()
        return (database_name,) in databases
    except Exception as e:
        print(f"Errore durante il controllo dell'esistenza del database: {e}")
        return False


def create_database_and_table_if_not_exists(cursor, database_name):
    """
    Questa funzione crea il database se non esiste

    :param cursor: cursore della connessione per eseguire le query
    :type cursor: Cursor
    :param database_name: nome del database che vogliamo creare e di cui controlliamo l'esistenza
    :type database_name: stl

    :return: l'esecuzione della query per creare il database (se non esiste) e il metodo per creare le tabelle.
    :rtype: None

    """
    if not check_database_existence(cursor, database_name):
        try:
            cursor.execute(f"CREATE DATABASE {database_name}")
            print(f"Database '{database_name}' creato con successo.")

            create_tables(cursor, database_name)
        except Exception as e:
            print(f"Errore durante la creazione del database: {e}")
    else:
        create_tables(cursor, database_name)


def create_tables(cursor, database_name):
    """
        Questa funzione crea le tabelle se non esistono.

        :param cursor: cursore della connessione per eseguire le query
        :type cursor: Cursor
        :param database_name: nome del database
        :type database_name: str


        :return: l'esecuzione della query per creare le tabelle se non esistono altrimenti non fa nulla
        :rtype: None
        """
    try:
        # Utilizza il database
        cursor.execute(f"USE {database_name}")
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
          energy VARCHAR(255),
          carbohydrate VARCHAR(255),
          fiber VARCHAR(255),
          sugars VARCHAR(255),
          protein VARCHAR(255),
          cholesterol VARCHAR(255),
          sodium VARCHAR(255),
          iron VARCHAR(255),
          zinc VARCHAR(255),
          phosphorus VARCHAR(255),
          water VARCHAR(255),
          FOREIGN KEY(periodo_giorno_id) REFERENCES periodo_giorno(periodo_giorno_id)
        );
        """)

        print("Tabelle create con successo.")
    except Exception as e:
        print(f"Errore durante la creazione delle tabelle: {e}")


# Questa funzione serve per gestire le API e le risorse del progetto
# come l'xml del testo relativo ai comandi usati dall'utente
def connect():
    """
        Questa funzione serve per assegnare le chiavi delle api e le chiavi segrete utili al funzionamento del bot.

        :return: openai api key, token_telegram api key e la root dove è contenuto il file xml per i messaggi di info
        :rtype: str

    """

    openai.api_key = os.getenv(TOKEN_CHAT_GPT)
    bot = telebot.TeleBot(os.getenv(TOKEN_TELEGRAM))
    tree = et.parse(os.getenv(FILE_XML))
    return openai, bot, tree.getroot()

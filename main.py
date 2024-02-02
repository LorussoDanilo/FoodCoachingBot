"""
Questo modulo contiene i vari handler dei messagi dell'utente e la gestione dei comandi di telegram

    Danilo Lorusso - Version 1.0
"""

import locale
import os
import pickle
import threading
import time as trem
from datetime import datetime, time
from io import BytesIO
from queue import Queue

import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image
from dotenv import load_dotenv
from mysql.connector import IntegrityError, errorcode
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from src.chatGPT_response import write_chatgpt, write_chatgpt_for_dieta_info
from src.connection import connect, connect_mysql
from src.controls import check_time_in_range, split_chunks
from src.handle_reminder_data import save_user_food_response, send_week_reminder_message
from src.handle_user_data import get_user_profile, create_new_user, ask_next_question, get_all_telegram_ids, \
    voice_recognizer, clear_audio, photo_recognizer, get_dieta_settimanale_ids, \
    get_dieta_settimanale_profile


def generate_all_weekly_diets_pdf(message):
    """
    Questa funzione serve per gestire il comando report e genera un pdf con il plot delle diete settimanali dell'utente

    :type message: Message

    :return: pdf con i dati delle diete settimanali
    :rtype: BytesIO
    """
    print(message)


def show_user_profile(message):
    """
    Questa funzione serve per gestire il comando profilo e permette di visualizzare le informazioni del profilo

    :type message: Message

    :return: i dati del profilo utente in forma tabellare
    :rtype: Message
    """
    print(message)


def send_welcome(message):
    """
    Questa funzione serve per gestire il comando /start ed invia il messaggio di info. Successivamente avvia la
    profilazione nuovamente all'utente le domande di profilazione

    :type message: Message

    :return: domande per la profilazione dell'utente
    :rtype: Message
    """
    print(message)


def edit_command(message):
    """
    Questa funzione serve per gestire il comando /modifica e permette di modificare i dati del profilo ponendo
    nuovamente all'utente le domande di profilazione

    :type message: Message

    :return: domande per l'aggiornamento dei dati del profilo
    :rtype: Message
    """
    print(message)


def handle_reminder_response_copy(message):
    """
    Questa funzione serve per gestire le risposte subito dopo il reminder cosi da salvare il cibo nel database.
    Questo handler viene utilizzato attraverso un thread e si ripete ciclicamente ogni n ore

    :type message: Message


    :return: la query per salvare il cibo scritto dall'utente nel messaggio
    :rtype: Message
    """
    print(message)


def handle_profile_response_copy(message):
    """
    Questa funzione serve per gestire le risposte dell'utente alle domande della profilazione salvando le risposte nel
    database.
    Inoltre, gestisce anche la conversazione post-profilazione attraverso l'utilizzo di un indice che determina l'inizio
    e la fine delle domande per la profilazione. Vengono accettate dopo la profilazione in input, messaggi testuali,
    vocali e fotografie. E' possibile anche rispondere ai messaggi di risposta ai reminder permettendo all'utente
    di fare delle opportune domande per gli alimenti nella data del messaggio a cui sta rispondendo.
    Questa è una funzione di copia poichè il message handler non viene letto dalla pydoc

    :type message: Message

    :return: domande per la profilazione dell'utente, reminder e passa le risposte a chatgpt
    :rtype: Message
    """
    print(message)


def photo_handler_copy(message):
    """
    Questo handler serve per poter gestire le risposte alle foto anche con caption. Ovvero, tramite chatgpt
    Questa è una funzione di copia poichè il message handler non viene letto dalla pydoc


    :type message: Message

    :return: un messaggio all'utente con la risposta data da chatgpt
    :rtype: Message
    """
    print(message)


def voice_handler_copy(message):
    """
    Questo handler serve per poter gestire le risposte ai messaggi vocali. Ovvero, tramite chatgpt
    Questa è una funzione di copia poichè il message handler non viene letto dalla pydoc

    :type message: Message

    :return: un messaggio all'utente con la risposta data da chatgpt
    :rtype: Message
    """
    print(message)


# per poter usare i formati orari e di data italiani
locale.setlocale(locale.LC_TIME, 'it_IT')

# per poter leggere il file .env
load_dotenv()

# Constant
START_COMMAND = 'start'
EDIT_COMMAND = 'modifica'
PROFILO_COMMAND = 'profilo'
REPORT_COMMAND = 'report'

reply_markup = InlineKeyboardMarkup([
    [InlineKeyboardButton("Felicità", callback_data='emozione_felicità')],
    [InlineKeyboardButton("Tristezza", callback_data='emozione_tristezza')],
    [InlineKeyboardButton("Indifferenza", callback_data='emozione_indifferenza')],
    [InlineKeyboardButton("Ansia", callback_data='emozione_ansia')],
    [InlineKeyboardButton("Paura", callback_data='emozione_paura')],
    [InlineKeyboardButton("Rabbia", callback_data='emozione_rabbia')],
    [InlineKeyboardButton("Disgusto", callback_data='emozione_disgusto')],
    # Aggiungi altri pulsanti per diverse emozioni
])

# Domande da porre all'utente durante la profilazione o modifica dei dati del profilo
questions_and_fields = [
    ('Qual è la tua età?', 'eta'),
    ('Quali sono le tue patologie o disturbi?', 'malattie'),
    (reply_markup, 'emozione')
]

# Periodo giorno
meal_type = None

# Connessione a MySQL e creazione del database e delle tabelle se non esistono
mysql_connection, mysql_cursor = connect_mysql()

# Inizializzazione variabili per il bot telegram, api di chat gpt e del file xml con le informazioni
openai, bot_telegram, root = connect()

# Inizializzazione delle chiavi per l'api di edamam
app_id = os.getenv('EDAMAM_APP_ID')
app_key = os.getenv('EDAMAM_APP_KEY')

api_key = os.getenv('GOOGLE_CLOUD_API_KEY')

# Variabile per gestire le funzionalità del chatbot. Serve per capire quando una funzionalità deve cominciare
event = threading.Event()

# Indice delle domande
index = 0

# Inizializzazione degli intervalli orari per inviare i reminder
ORA_COLAZIONE_START = time(8, 0)
ORA_COLAZIONE_END = time(9, 0)
ORA_PRANZO_START = time(11, 0)
ORA_PRANZO_END = time(12, 0)
ORA_CENA_START = time(16, 30)
ORA_CENA_END = time(23, 50)

ORA_REMINDER_SETTIMANALE = time(11, 13, 10)

# inizializzazione della coda per i messaggi dei reminder
queue = Queue()

# inizializzazione della lista che contiene le risposte ai messaggi dei reminder dell'utente
user_response_message = []

# Variabile di stato per coordinare l'esecuzione tra i thread
event_send_reminder = threading.Event()
event_handle_response = threading.Event()

MAX_MESSAGE_LENGTH = 400

start_command_used = False

frase_is_food = ("Mi dispiace, non sono in grado di rispondere a domande su questo "
                 "argomento. Rispondo solo a domande riguardanti l'alimentazione.")

if __name__ == '__main__':

    @bot_telegram.message_handler(commands=[REPORT_COMMAND])
    def generate_all_weekly_diets_pdf(message):
        """
            Questa funzione serve per gestire il comando report e genera un pdf con il plot delle diete settimanali
            dell'utente

            :type message: Message

            :return: pdf con i dati delle diete settimanali
            :rtype: BytesIO
        """
        global mysql_connection, mysql_cursor
        telegram_id = message.chat.id
        user_profile = get_user_profile(telegram_id)
        dieta_settimanale_ids = get_dieta_settimanale_ids(telegram_id)

        for ds_id in dieta_settimanale_ids:
            # Query per ottenere i dati
            query_colazione = """
                   SELECT gs.nome AS giorno, CAST(c.energy AS DECIMAL(10, 2))
                   FROM giorno_settimana gs
                   JOIN periodo_giorno pg ON gs.giorno_settimana_id = pg.giorno_settimana_id
                   JOIN cibo c ON pg.periodo_giorno_id = c.periodo_giorno_id
                   WHERE pg.nome = 'Colazione';
                   """

            query_pranzo = """
                   SELECT gs.nome AS giorno, CAST(c.energy AS DECIMAL(10, 2))
                   FROM giorno_settimana gs
                   JOIN periodo_giorno pg ON gs.giorno_settimana_id = pg.giorno_settimana_id
                   JOIN cibo c ON pg.periodo_giorno_id = c.periodo_giorno_id
                   WHERE pg.nome = 'Pranzo';
                   """

            query_cena = """
                   SELECT gs.nome AS giorno, CAST(c.energy AS DECIMAL(10, 2))
                   FROM giorno_settimana gs
                   JOIN periodo_giorno pg ON gs.giorno_settimana_id = pg.giorno_settimana_id
                   JOIN cibo c ON pg.periodo_giorno_id = c.periodo_giorno_id
                   WHERE pg.nome = 'Cena';
                   """

            query_totale_calorie = """
                   SELECT gs.nome AS giorno, SUM(CAST(c.energy AS DECIMAL(10, 2))) AS totale_calorie
                   FROM giorno_settimana gs
                   JOIN periodo_giorno pg ON gs.giorno_settimana_id = pg.giorno_settimana_id
                   JOIN cibo c ON pg.periodo_giorno_id = c.periodo_giorno_id
                   GROUP BY gs.nome;
                   """

            # Esegui le query
            mysql_cursor.execute(query_colazione)
            data_colazione = mysql_cursor.fetchall()

            mysql_cursor.execute(query_pranzo)
            data_pranzo = mysql_cursor.fetchall()

            mysql_cursor.execute(query_cena)
            data_cena = mysql_cursor.fetchall()

            mysql_cursor.execute(query_totale_calorie)
            data_totale_calorie = mysql_cursor.fetchall()

            # Chiudi la connessione al datab
            # ase
            mysql_connection.close()
            dieta_settimanale = get_dieta_settimanale_profile(ds_id)

            # Trasforma i dati in DataFrame
            df_colazione = pd.DataFrame(data_colazione, columns=['Giorno', 'Calorie Colazione'])
            df_pranzo = pd.DataFrame(data_pranzo, columns=['Giorno', 'Calorie Pranzo'])
            df_cena = pd.DataFrame(data_cena, columns=['Giorno', 'Calorie Cena'])
            df_totale_calorie = pd.DataFrame(data_totale_calorie, columns=['Giorno', 'Totale Calorie'])

            # Crea i grafici senza mostrare la GUI
            plt.figure(figsize=(15, 10))

            # Grafico Colazione
            plt.subplot(221)
            plt.bar(df_colazione['Giorno'], df_colazione['Calorie Colazione'])
            plt.title('Kcal durante la colazione')
            plt.savefig('colazione.png')

            # Grafico Pranzo
            plt.subplot(222)
            plt.bar(df_pranzo['Giorno'], df_pranzo['Calorie Pranzo'])
            plt.title('Kcal durante il pranzo')
            plt.savefig('pranzo.png')

            # Grafico Cena
            plt.subplot(223)
            plt.bar(df_cena['Giorno'], df_cena['Calorie Cena'])
            plt.title('Kcal durante la cena')
            plt.savefig('cena.png')

            # Grafico Totale Calorie
            plt.subplot(224)
            plt.bar(df_totale_calorie['Giorno'], df_totale_calorie['Totale Calorie'])
            plt.title('Totale Kcal per giorno')
            plt.savefig('totale_calorie.png')

            # Chiudi la figura
            plt.close()

            # Crea una lista con il percorso delle immagini
            images = ['totale_calorie.png']

            # Crea un documento PDF con ReportLab
            pdf_output = BytesIO()
            c = canvas.Canvas(pdf_output, pagesize=letter)

            # Informazioni utente
            user_info = (f"Informazioni Utente - Nome: {user_profile.get('nome_utente')}, "
                         f"Età: {user_profile.get('eta')}, Malattie: {user_profile.get('malattie')},"
                         f" Emozione: {user_profile.get('emozione')}")
            dieta_settimanale_info = (f"Dieta Settimana {dieta_settimanale.get('dieta_settimanale_id')},"
                                      f" {dieta_settimanale.get('data')}")
            mysql_connection, mysql_cursor = connect_mysql()
            feedback_dieta = write_chatgpt_for_dieta_info(openai, user_profile, mysql_cursor, telegram_id)

            # Fattore di scala per ridimensionare le immagini
            scale_factor = 0.5  # Puoi regolare questo valore a seconda delle dimensioni desiderate

            # Impostazioni della pagina
            page_width, page_height = letter
            start_x = 60  # Puoi regolare questa posizione x di partenza
            max_width = page_width - start_x

            # Aggiungi le immagini al PDF
            for image_path in images:
                c.drawString(240, 780, dieta_settimanale_info)
                c.drawString(start_x, 750, user_info)

                # Creazione di un oggetto Paragraph per gestire il wrapping del testo
                style = getSampleStyleSheet()["BodyText"]
                text_object = Paragraph(feedback_dieta, style=style)

                # Disegna il testo "Feedback" sopra il paragrafo "feedback_dieta"
                c.drawString(start_x, 710, "Feedback")

                # Disegna il paragrafo "feedback_dieta" con wrapping
                text_object.wrapOn(c, max_width, page_height)
                text_object.drawOn(c, start_x, 660)  # Regola la coordinata y in base alle tue esigenze

                # Aggiungi l'immagine al PDF, ridimensionata proporzionalmente
                try:
                    img = Image.open(image_path)
                    original_width, original_height = img.size

                    # Calcola le nuove dimensioni
                    new_width = int(original_width * scale_factor)
                    new_height = int(original_height * scale_factor)

                    page_width, page_height = letter

                    # Calcola le coordinate per centrare l'immagine
                    x = (page_width - new_width) / 2
                    y = (page_height - new_height) / 2

                    c.drawInlineImage(img, x, y, width=new_width, height=new_height)
                except Exception as e:
                    print(f"Errore nell'aggiunta di {image_path} al PDF: {e}")

            # Salva il PDF
            c.save()

            # Invia il documento PDF all'utente Telegram
            pdf_output.seek(0)
            pdf_file = pdf_output.getvalue()
            bot_telegram.send_document(telegram_id, document=('dieta_settimanale.pdf', pdf_file))

            # Cancella le immagini
            image_files = ['colazione.png', 'pranzo.png', 'cena.png', 'totale_calorie.png']
            for image_file in image_files:
                if os.path.exists(image_file):
                    os.remove(image_file)


    # metodo per gestire il comando /profilo per visualizzare i dati del profilo
    @bot_telegram.message_handler(commands=[PROFILO_COMMAND])
    def show_user_profile(message):
        """
        Questa funzione serve per gestire il comando profilo e permette di visualizzare le informazioni del profilo

        :type message: Message

        :return: i dati del profilo utente in forma tabellare
        :rtype: Message
        """
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
    def edit_profile(message):
        """
        Questa funzione serve per gestire il comando profilo e permette di modificare i dati del profilo ponendo
        nuovamente all'utente le domande di profilazione

        :type message: Message

        :return: domande per l'aggiornamento dei dati del profilo
        :rtype: Message
        """

        telegram_id = message.chat.id
        index_edit = 0
        user_profile_edit = get_user_profile(telegram_id)
        if not user_profile_edit:
            create_new_user(mysql_cursor, mysql_connection)

        # Invia il messaggio iniziale
        bot_telegram.send_message(telegram_id, message.chat.username + " " + "modifica i dati del tuo profilo!")

        # Inizia a fare domande per l'aggiornamento delle informazioni
        ask_next_question(telegram_id, bot_telegram, questions_and_fields, index_edit)

        reminder_message_thread = threading.Thread(target=send_reminder_message, daemon=True, args=(
            event, bot_telegram, ORA_COLAZIONE_START, ORA_COLAZIONE_END, ORA_PRANZO_START, ORA_PRANZO_END,
            ORA_CENA_START, ORA_CENA_END,))
        reminder_message_thread.start()


    # Metodo per gestire il comando /start
    @bot_telegram.message_handler(commands=[START_COMMAND])
    def send_welcome(message):
        """
        Questa funzione serve per gestire il comando start ed invia il messaggio di info. Successivamente avvia
        la profilazione nuovamente all'utente le domande di profilazione

        :type message: Message

        :return: domande per la profilazione dell'utente
        :rtype: Message
        """

        global questions_and_fields, index, start_command_used
        if not start_command_used:

            # setto l'evento a true
            event.set()
            telegram_id = message.chat.id

            user_profile_start = get_user_profile(telegram_id)
            print(user_profile_start)
            username = message.chat.username

            # Controllo se l'utente non esiste
            if not user_profile_start:
                # Se l'utente non esiste viene creato inserendo l'id telegram e il suo username
                create_new_user(telegram_id, username)

            # Inizia chiedendo il consenso ai dati
            reply_markup_consenso = InlineKeyboardMarkup([
                [InlineKeyboardButton("Si", callback_data='consenso_si'),
                 InlineKeyboardButton("No", callback_data='consenso_no')]
            ])
            consenso_message = (
                "Prima di cominciare con le domande di profilazione, dobbiamo ottenere il tuo consenso per "
                "l'uso dei dati. Acconsenti?")
            bot_telegram.send_message(telegram_id, consenso_message, reply_markup=reply_markup_consenso)
            start_command_used = True
        else:
            bot_telegram.send_message(message.chat.id,
                                      "Il comando di start è stato già utilizzato. Chiedimi ciò che desideri😊")


    # Funzione per gestire la risposta ai pulsanti di consenso
    @bot_telegram.callback_query_handler(func=lambda call: True)
    def handle_consenso_buttons(call):
        global index
        user_id = call.from_user.id
        consenso_answer = call.data
        emozione_answer = call.data
        telegram_id = call.from_user.id

        if consenso_answer == 'consenso_si':
            # Utente ha acconsentito, puoi iniziare con le domande di profilazione
            bot_telegram.send_message(user_id, "Ottimo! Cominciamo con le domande di profilazione.")
            # Inizia chiedendo la prima domanda

            question, field = questions_and_fields[index]
            bot_telegram.send_message(telegram_id, question)
            # Incremento dell'indice per proseguire nelle domande

            index += 1
            # Aggiungi il codice per iniziare le domande di profilazione
        elif consenso_answer == 'consenso_no':
            # Utente ha rifiutato, puoi gestire di conseguenza
            bot_telegram.send_message(user_id, "Puoi utilizzare il bot ma non acconsentendo alla profilazione, "
                                               "risulterà meno efficiente😢")
            index = len(questions_and_fields) + 1
            event.clear()
        # Recupera il testo del pulsante dal callback data
        elif emozione_answer.startswith('emozione_'):
            emozione_selezionata = emozione_answer[len('emozione_'):]
            update_query = f"UPDATE utenti SET {questions_and_fields[index - 1][1]} = %s WHERE telegram_id = %s"
            mysql_cursor.execute(update_query, (emozione_selezionata, telegram_id))
            # Commit delle modifiche al database
            mysql_connection.commit()

            confirmation_message = f"Grazie! 😊 La tua risposta per il campo <b>{questions_and_fields[index - 1][1]}</b> è: <b>{emozione_selezionata}</b>"
            bot_telegram.send_message(telegram_id, confirmation_message, parse_mode='HTML', disable_notification=True)
            print(index.__str__() + "callback_data")
            index += 1


    # Gestisci altri possibili callback_data

    @bot_telegram.message_handler(func=lambda message: True, content_types=['text', 'voice', 'photo'])
    def handle_profile_response(message):
        """
        Questa funzione serve per gestire le risposte dell'utente alle domande della profilazione salvando le risposte
        nel database. Inoltre, gestisce anche la conversazione post-profilazione attraverso l'utilizzo di un indice
        che determina l'inizio e la fine delle domande per la profilazione. Vengono accettate dopo la profilazione
        in input, messaggi testuali, vocali e fotografie. E' possibile anche rispondere ai messaggi di risposta
        ai reminder permettendo all'utente di fare delle opportune domande per gli alimenti nella data del
        messaggio a cui sta rispondendo

        :type message: Message

        :return: domande per la profilazione dell'utente, reminder e passa le risposte a chatgpt
        :rtype: Message
        """
        global mysql_connection, mysql_cursor, event, index, event_send_reminder
        user_response = str(message.text)
        telegram_id = message.chat.id

        try:
            if index < len(questions_and_fields):

                # Esecuzione della query per aggiornare il profilo dell'utente nel database
                update_query = f"UPDATE utenti SET {questions_and_fields[index - 1][1]} = %s WHERE telegram_id = %s"
                mysql_cursor.execute(update_query, (user_response, telegram_id))
                # Commit delle modifiche al database
                mysql_connection.commit()

                confirmation_message = f"Grazie! 😊 La tua risposta per il campo <b>{questions_and_fields[index - 1][1]}</b> è: <b>{user_response}</b>"
                bot_telegram.send_message(telegram_id, confirmation_message, parse_mode='HTML',
                                          disable_notification=True)
                # Passa alla prossima domanda se ci sono ancora domande
                question, field = questions_and_fields[index]

                if field == 'emozione':
                    bot_telegram.send_message(telegram_id,
                                              "Che emozione provi mentre mangi o pensi al cibo? Seleziona un'emozione:",
                                              reply_markup=reply_markup)
                    print(index.__str__() + "emozione_question")
                    index += 1

                else:
                    bot_telegram.send_message(telegram_id, question)
                    index += 1
                    print(index.__str__() + "not_emozione_question")

                print("handle_profile_response" + index.__str__())

            elif index > len(questions_and_fields):
                if event.is_set():
                    event_send_reminder.set()
                    reminder_message_thread = threading.Thread(target=send_reminder_message, daemon=True, args=(
                        event, bot_telegram, ORA_COLAZIONE_START, ORA_COLAZIONE_END, ORA_PRANZO_START, ORA_PRANZO_END,
                        ORA_CENA_START, ORA_CENA_END,))
                    reminder_message_thread.start()

                    reminder_thread = threading.Thread(target=handle_reminder_response, daemon=True, args=(message,))
                    reminder_thread.start()

                else:
                    reminder_week_message_thread = threading.Thread(target=send_week_reminder_message, daemon=True,
                                                                    args=(event, bot_telegram,))
                    reminder_week_message_thread.start()
                    if message.reply_to_message and message.reply_to_message.text in user_response_message:
                        user_profile = get_user_profile(telegram_id)
                        timestamp = message.reply_to_message.date

                        # Converti il timestamp in un oggetto datetime
                        data_messaggio = datetime.utcfromtimestamp(timestamp).strftime('%d/%m/%y')

                        user_response_reply = (
                            f"Considera che in questa data {data_messaggio} ho mangiato: "
                            f"{message.reply_to_message.text}. In riferimento a quella data: {user_response}"
                        )
                        response_chunks = write_chatgpt(bot_telegram, openai, user_response_reply, user_profile,
                                                        mysql_cursor, telegram_id)

                        if response_chunks == frase_is_food:
                            bot_telegram.send_message(telegram_id, frase_is_food)
                        else:

                            # Invia ciascun elemento della lista ogni 5 secondi
                            for chunk in response_chunks:
                                # Suddividi il chunk in pezzi da 400 parole
                                splitted = split_chunks(chunk)

                                # Invia ciascun pezzo ogni 5 secondi
                                for split_chunk in splitted:
                                    split_chunk += "..."
                                    bot_telegram.send_message(telegram_id, split_chunk, trem.sleep(8))
                    else:

                        if message.content_type == 'text':

                            user_profile = get_user_profile(telegram_id)
                            print(user_profile)

                            response_chunks = write_chatgpt(bot_telegram, openai, user_response, user_profile,
                                                            mysql_cursor, telegram_id)

                            if response_chunks == frase_is_food:
                                bot_telegram.send_message(telegram_id, frase_is_food)
                            else:

                                # Invia ciascun elemento della lista ogni 5 secondi
                                for chunk in response_chunks:
                                    # Suddividi il chunk in pezzi da 400 parole
                                    splitted = split_chunks(chunk)

                                    # Invia ciascun pezzo ogni 5 secondi
                                    for split_chunk in splitted:
                                        split_chunk += "..."
                                        bot_telegram.send_message(telegram_id, split_chunk, trem.sleep(8))

                        elif message.content_type == 'voice':
                            voice_handler(message)
                        elif message.content_type == 'photo':
                            photo_handler(message)
        except IndexError as ie:
            print(f"Index error: {ie}")
            bot_telegram.send_message(telegram_id,
                                      "Grazie! Ora il tuo profilo è completo. Chiedimi ciò che desideri😊")
            index += 1
            event.clear()

        except Exception as e:
            print(f"Vincolo di integrità violato: {e}")


        except IntegrityError as integrity_error:
            print(f"Vincolo di integrità violato: {integrity_error}")
            telegram_id = message.chat.id
            bot_telegram.send_message(telegram_id, "Hai inserito un valore errato. Riprova.")

        except mysql_cursor.Error as db_error:
            if db_error.errno == errorcode.ER_TRUNCATED_WRONG_VALUE:
                # Handle the specific error for incorrect integer value
                bot_telegram.send_message(telegram_id,
                                          "Errore: Valore non valido per il campo 'eta'. Inserisci un numero valido.")
            else:
                # Handle other database errors
                bot_telegram.send_message(telegram_id, f"Errore del database: {db_error}")


@bot_telegram.message_handler(func=lambda message: True, content_types=['text', 'voice', 'photo'])
def handle_reminder_response(message):
    """
    Questa funzione serve per gestire le risposte subito dopo il reminder cosi da salvare il cibo nel database.
    Questo handler viene utilizzato attraverso un thread e si ripete ciclicamente ogni n ore

    :type message: Message


    :return: la query per salvare il cibo scritto dall'utente nel messaggio
    :rtype: Message
    """
    global meal_type, mysql_cursor, mysql_connection, queue, user_response_message, event_send_reminder, \
        event_handle_response

    serialized_message = pickle.dumps(message)
    queue.put(serialized_message)

    telegram_ids = get_all_telegram_ids()
    deserialized_message = pickle.loads(serialized_message)
    user_response_message.append(str(deserialized_message.text))
    user_response = str(deserialized_message.text)

    current_time_reminder = datetime.now().time()
    try:

        if check_time_in_range(current_time_reminder, ORA_COLAZIONE_START, ORA_COLAZIONE_END):
            for telegram_id in telegram_ids:
                meal_type = "colazione"
                if message.content_type == 'text':
                    save_user_food_response(bot_telegram, mysql_cursor, mysql_connection, telegram_id, meal_type,
                                            user_response, app_id, app_key)

                elif message.content_type == 'voice':
                    file_id = message.voice.file_id
                    file = bot_telegram.get_file(file_id)
                    download_file = bot_telegram.download_file(file.file_path)
                    with open('audio.ogg', 'wb') as file:
                        file.write(download_file)

                    text = voice_recognizer()
                    save_user_food_response(bot_telegram, mysql_cursor, mysql_connection, telegram_id, meal_type,
                                            text, app_id, app_key)
                    clear_audio()
                elif message.content_type == 'photo':
                    text = photo_recognizer(message, bot_telegram)
                    save_user_food_response(bot_telegram, mysql_cursor, mysql_connection, telegram_id, meal_type,
                                            text, app_id, app_key)

                event.clear()
                event.wait(40)
                event_send_reminder.set()
                event.set()
        elif check_time_in_range(current_time_reminder, ORA_PRANZO_START, ORA_PRANZO_END):
            for telegram_id in telegram_ids:
                meal_type = "pranzo"
                if message.content_type == 'text':
                    save_user_food_response(bot_telegram, mysql_cursor, mysql_connection, telegram_id, meal_type,
                                            user_response, app_id, app_key)

                elif message.content_type == 'voice':
                    file_id = message.voice.file_id
                    file = bot_telegram.get_file(file_id)
                    download_file = bot_telegram.download_file(file.file_path)
                    with open('audio.ogg', 'wb') as file:
                        file.write(download_file)

                    text = voice_recognizer()
                    save_user_food_response(bot_telegram, mysql_cursor, mysql_connection, telegram_id, meal_type,
                                            text, app_id, app_key)
                    clear_audio()
                elif message.content_type == 'photo':
                    text = photo_recognizer(message, bot_telegram)
                    save_user_food_response(bot_telegram, mysql_cursor, mysql_connection, telegram_id, meal_type,
                                            text, app_id, app_key)
                event.clear()
                event.wait(40)
                event_send_reminder.set()
                event.set()

        elif check_time_in_range(current_time_reminder, ORA_CENA_START, ORA_CENA_END):
            for telegram_id in telegram_ids:
                meal_type = "cena"
                if message.content_type == 'text':
                    save_user_food_response(bot_telegram, mysql_cursor, mysql_connection, telegram_id, meal_type,
                                            user_response, app_id, app_key)

                elif message.content_type == 'voice':
                    file_id = message.voice.file_id
                    file = bot_telegram.get_file(file_id)
                    download_file = bot_telegram.download_file(file.file_path)

                    with open('audio.ogg', 'wb') as file:
                        file.write(download_file)

                    text = voice_recognizer()
                    print(text)
                    save_user_food_response(bot_telegram, mysql_cursor, mysql_connection, telegram_id, meal_type,
                                            text, app_id, app_key)
                    clear_audio()
                elif message.content_type == 'photo':
                    text = photo_recognizer(message, bot_telegram)
                    save_user_food_response(bot_telegram, mysql_cursor, mysql_connection, telegram_id, meal_type,
                                            text, app_id, app_key)

                event.clear()
                event.wait(40)
                event_send_reminder.set()
                event.set()
        else:
            event.clear()

    except Exception as main_exception:
        # Handle the main exception (e.g., log the error)
        print(f"Main exception occurred: {main_exception}")


# Metodo per gestire i messaggi vocali dell'utente
@bot_telegram.message_handler(func=lambda message: True)
def voice_handler(message):
    """
    Questo handler serve per poter gestire le risposte ai messaggi vocali. Ovvero, tramite chatgpt

    :type message: Message

    :return: un messaggio all'utente con la risposta data da chatgpt
    :rtype: Message
    """
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
        print(text)

        user_profile = get_user_profile(telegram_id)
        print(user_profile)
        response_chunks = write_chatgpt(bot_telegram, openai, text, user_profile,
                                        mysql_cursor, telegram_id)

        if response_chunks == frase_is_food:
            bot_telegram.send_message(telegram_id, frase_is_food)
        else:

            # Invia ciascun elemento della lista ogni 5 secondi
            for chunk in response_chunks:
                # Suddividi il chunk in pezzi da 400 parole
                splitted = split_chunks(chunk)

                # Invia ciascun pezzo ogni 5 secondi
                for split_chunk in splitted:
                    split_chunk += "..."
                    bot_telegram.send_message(telegram_id, split_chunk, trem.sleep(8))
        # chiamare il metodo per cancellare i file .ogg e .wav generati
        clear_audio()


@bot_telegram.message_handler(func=lambda message: True)
def photo_handler(message):
    """
    Questo handler serve per poter gestire le risposte alle foto anche con caption. Ovvero, tramite chatgpt

    :type message: Message

    :return: un messaggio all'utente con la risposta data da chatgpt
    :rtype: Message
    """

    telegram_id = message.chat.id
    # Esegui il riconoscimento del cibo

    photo_result = photo_recognizer(message, bot_telegram)
    if message.caption:
        results = photo_result + message.caption
        user_profile = get_user_profile(telegram_id)
        print(results)
        response_chunks = write_chatgpt(bot_telegram, openai, results, user_profile,
                                        mysql_cursor, telegram_id)

        if response_chunks == frase_is_food:
            bot_telegram.send_message(telegram_id, frase_is_food)
        else:

            # Invia ciascun elemento della lista ogni 5 secondi
            for chunk in response_chunks:
                # Suddividi il chunk in pezzi da 400 parole
                splitted = split_chunks(chunk)

                # Invia ciascun pezzo ogni 5 secondi
                for split_chunk in splitted:
                    split_chunk += "..."
                    bot_telegram.send_message(telegram_id, split_chunk, trem.sleep(8))
    else:
        results = photo_result
        user_profile = get_user_profile(telegram_id)
        print(results)
        response_chunks = write_chatgpt(bot_telegram, openai, results, user_profile,
                                        mysql_cursor, telegram_id)

        if response_chunks == frase_is_food:
            bot_telegram.send_message(telegram_id, frase_is_food)
        else:

            # Invia ciascun elemento della lista ogni 5 secondi
            for chunk in response_chunks:
                # Suddividi il chunk in pezzi da 400 parole
                splitted = split_chunks(chunk)

                # Invia ciascun pezzo ogni 5 secondi
                for split_chunk in splitted:
                    split_chunk += "..."
                    bot_telegram.send_message(telegram_id, split_chunk, trem.sleep(8))


def send_reminder_message(event, bot_telegram, ORA_COLAZIONE_START, ORA_COLAZIONE_END, ORA_PRANZO_START, ORA_PRANZO_END,
                          ORA_CENA_START, ORA_CENA_END):
    """
        Questa funzione serve per inviare in determinati eventi temporali dei reminder per conoscere
         la dieta settimanale dell'utente

        :param event: serve per gestire gli eventi e alternare l'esecuzione dei metodi
        :type event: Event
        :param bot_telegram: corrisponde alla variabile che contiene l'api key del proprio bot_telegram
                            e permette di accedere ai metodi della libreria Telebot
        :type bot_telegram: Telebot
        :param ORA_COLAZIONE_START: inizio dell'intervallo per l'ora di colazione
        :type ORA_COLAZIONE_START: time.py
        :param ORA_COLAZIONE_END: fine dell'intervallo per l'ora di colazione
        :type ORA_COLAZIONE_END: time.py
        :param ORA_PRANZO_START: inizio dell'intervallo per l'ora di pranzo
        :type ORA_PRANZO_START: time.py
        :param ORA_PRANZO_END: fine dell'intervallo per l'ora di pranzo
        :type ORA_PRANZO_END: time.py
        :param ORA_CENA_START: inizio dell'intervallo per l'ora di cena
        :type ORA_CENA_START: time.py
        :param ORA_CENA_END: fine dell'intervallo per l'ora di cena
        :type ORA_CENA_END: time.py


        :return: il reminder da inviare all'utente
        :rtype: Message
        """
    telegram_ids = get_all_telegram_ids()

    current_time_reminder = datetime.now().time()
    # Serializzazione dell'oggetto Message

    while event.is_set() and event_send_reminder.is_set():
        for telegram_id in telegram_ids:
            if check_time_in_range(current_time_reminder, ORA_COLAZIONE_START, ORA_COLAZIONE_END):
                bot_telegram.send_message(telegram_id,
                                          "Buongiorno! Cosa hai mangiato a colazione? Indica prima del cibo la "
                                          "quantità.",
                                          trem.sleep(40))
                event_send_reminder.clear()  # Disattiva l'evento per inviare il reminder

            elif check_time_in_range(current_time_reminder, ORA_PRANZO_START, ORA_PRANZO_END):
                bot_telegram.send_message(telegram_id,
                                          "Pranzo time! Cosa hai mangiato a pranzo? Indica prima del cibo la quantità.",
                                          trem.sleep(40))
                event_send_reminder.clear()  # Disattiva l'evento per inviare il reminder

            elif check_time_in_range(current_time_reminder, ORA_CENA_START, ORA_CENA_END):
                bot_telegram.send_message(telegram_id,
                                          "Cena! Cosa hai mangiato a cena? Indica prima del cibo la quantità.",
                                          trem.sleep(40))
            else:
                event.clear()

            event_send_reminder.clear()  # Disattiva l'evento per inviare il reminder
    event_send_reminder.wait()  # Attendere che l'evento per inviare il reminder venga attivato


# Esegui il polling infinito del bot Telegram
bot_telegram.infinity_polling()

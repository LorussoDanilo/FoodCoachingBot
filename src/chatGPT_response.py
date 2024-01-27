"""
Questo modulo contiene le funzioni che servono per passare i messaggi degli utenti a chatgpt applicando i filtri conversazionali

    Danilo Lorusso - Version 1.0
"""


import locale

from src.controls import is_food_question

locale.setlocale(locale.LC_TIME, 'it_IT')


def write_chatgpt(openai, message, profilo_utente, mysql_cursor, telegram_id):
    """
    Questa funzione serve per passare i messaggi dell'utente a chatgpt filtrandole con is_food_question e passando
    a chatgpt anche il profilo dell'utente e la dieta settimanale

    :param openai: api key di openai
    :type openai: ChatCompletion
    :param message: messaggio inviato dall'utente
    :type message: Message
    :param profilo_utente: dati del profilo utente
    :type profilo_utente: dict
    :param mysql_cursor: cursore per eseguire le query
    :type mysql_cursor: execute, fetchall
    :param telegram_id: telegram_id dell'utente
    :type telegram_id: int

    :return: la risposta data da chatgpt
    :rtype: str
    """

    dieta_settimanale_text = ""
    try:
        # Estrai il testo dal messaggio
        # Estrai il testo dal messaggio
        if hasattr(message, 'text'):
            message_text = message.text
        else:
            message_text = str(message)

        # Estrai le informazioni dal profilo dell'utente
        eta = profilo_utente.get('eta')
        malattie = profilo_utente.get('malattie')
        emozione = profilo_utente.get('emozione')

        dieta_settimanale_info = get_dieta_settimanale_info(mysql_cursor, telegram_id)

        if dieta_settimanale_info:
            # Costruisci una rappresentazione testuale delle diete settimanali
            dieta_settimanale_text = f"La mia dieta settimanale è la seguente:\n" + dieta_settimanale_info.__str__()

        # Aggiungi le informazioni del profilo e della dieta settimanale al messaggio di input per ChatGPT
        input_con_profilo_e_dieta = (
            f"La mia età è: {eta} | La mia malattia o disturbo è: {', '.join(malattie)} | Io quando mangio o penso al "
            f"cibo provo un sentimento: {emozione}"f" | {dieta_settimanale_text}"
            f" | Mettiti nei panni di un nutrizionista,tieni conto della mia età, delle mie malattie o disturbi, "
            f"l'emozione che provo quando mangio o penso al cibo e alla mia dieta settimanale"
            f" e adatta il tuo linguaggio "
            f"prima di rispondere alla seguente domanda:"
            f" |\n{message_text}"
        )

        # Aggiungi logica per filtrare in base all'argomento della domanda
        if is_food_question(message_text):
            # Se la domanda riguarda il cibo, invia la richiesta a OpenAI con le informazioni del profilo e della dieta
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": input_con_profilo_e_dieta}
                ]
            )
            print(input_con_profilo_e_dieta)

            # Verifica se la risposta è valida e contiene contenuti
            if response and "choices" in response and response["choices"]:
                # Ottieni la risposta grezza da OpenAI
                raw_response = response["choices"][0]["message"]["content"]

                # Aggiungi personalizzazioni in base alle informazioni del profilo
                if emozione == 'felicità':
                    raw_response += " Spero che tu possa continuare a goderti il tuo pasto felice!"

                return raw_response
            else:
                # Gestisci risposte vuote o inaspettate
                return "Mi dispiace, non ho ricevuto una risposta valida da OpenAI."

        else:
            # Se l'argomento non riguarda il cibo, restituisci una risposta specifica
            return ("Mi dispiace, non sono in grado di rispondere a domande su questo argomento. Rispondo solo a "
                    "domande riguardanti l'alimentazione.")

    except Exception as e:
        # Registra eventuali eccezioni che potrebbero verificarsi
        print(f"Si è verificato un errore in write_chatgpt: {e}")
        return "Si è verificato un errore durante la generazione della risposta."


def get_dieta_settimanale_info(cursor, telegram_id):
    """
        Questa funzione serve per recuperare i dati delle diete settimanali svolte dall'utente

        :param cursor: cursore per eseguire le query
        :type cursor: execute, fetchall
        :param telegram_id: id_telegram dell'utente
        :type telegram_id: int

        :return: la lista delle diete settimanali sotto forma di stringa
        :rtype: str
        """
    try:
        # Esegui la query per ottenere le informazioni sulla dieta settimanale dell'utente
        cursor.execute("""
            SELECT ds.dieta_settimanale_id, ds.data, gs.nome AS nome_giorno, pg.nome AS nome_periodo, c.nome AS nome_cibo
            FROM dieta_settimanale ds
            JOIN giorno_settimana gs ON ds.dieta_settimanale_id = gs.dieta_settimanale_id
            JOIN periodo_giorno pg ON gs.giorno_settimana_id = pg.giorno_settimana_id
            JOIN cibo c ON pg.periodo_giorno_id = c.periodo_giorno_id
            WHERE ds.telegram_id = %s
            ORDER BY ds.data, gs.nome, pg.nome;
        """, (telegram_id,))

        # Ottieni tutti i risultati delle query
        results = cursor.fetchall()

        #Fare la query per ottenere il nome del cibo dall'id nella tabella dei valori nutrizionali
        #Poi mettere i risultati della query in una variabile

        # Creare una struttura dati per memorizzare le informazioni
        dieta_settimanale_info = []

        # Processa i risultati della query e popola la struttura dati
        for result in results:
            dieta_settimanale_id, data, nome_giorno, nome_periodo, nome_cibo = result
            # Creare una lista con i risultati della query per i valori nutrizionali ed aggiungere gli elementi della lista con .append qui sotto

            dieta_settimanale_info.append({
                'dieta_settimanale_id': dieta_settimanale_id,
                'data': data,
                'nome_giorno': nome_giorno,
                'nome_periodo': nome_periodo,
                'nome_cibo': nome_cibo
            })

        return dieta_settimanale_info

    except Exception as e:
        print(f"Si è verificato un errore durante l'estrazione delle informazioni sulla dieta settimanale: {e}")
        return None
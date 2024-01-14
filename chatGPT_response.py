from utils.controls import is_food_question


def write_chatgpt(openai, message, profilo_utente):
    try:
        # Estrai il testo dal messaggio
        message_text = message.text if hasattr(message, 'text') else str(message)

        # Estrai le informazioni dal profilo dell'utente
        eta = profilo_utente.get('eta', None)
        malattie = profilo_utente.get('malattie', [])
        emozione_mangiare = profilo_utente.get('emozione_mangiare', None)

        # Aggiungi le informazioni del profilo al messaggio di input per ChatGPT
        input_con_profilo = (
            f"La mia età è: {eta} | Le/la mia malattia/e è/sono: {', '.join(malattie)} | Io quando mangio o penso al cibo provo un sentimento: {emozione_mangiare}"
            f" | Mettiti nei panni di un nutrizionista,tieni conto di queste informazioni e adatta il tuo linguaggio considerando che provo {emozione_mangiare} quando mangio o penso al cibo, prima di rispondere alla seguente domanda:"
            f" | {message_text}"
        )

        # Aggiungi logica per filtrare in base all'argomento della domanda
        if is_food_question(message_text):
            # Se la domanda riguarda il cibo, invia la richiesta a OpenAI con le informazioni del profilo
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": input_con_profilo}
                ]
            )

            # Verifica se la risposta è valida e contiene contenuti
            if response and "choices" in response and response["choices"]:
                # Ottieni la risposta grezza da OpenAI
                raw_response = response["choices"][0]["message"]["content"]

                # Aggiungi personalizzazioni in base alle informazioni del profilo
                if emozione_mangiare == 'Positivo':
                    raw_response += " Spero che tu possa continuare a goderti il tuo pasto felice!"

                return raw_response
            else:
                # Gestisci risposte vuote o inaspettate
                return "Mi dispiace, non ho ricevuto una risposta valida da OpenAI."

        else:
            # Se l'argomento non riguarda il cibo, restituisci una risposta specifica
            return "Mi dispiace, non sono in grado di rispondere a domande su questo argomento. Rispondo solo a domande " \
                   "riguardanti l'alimentazione."

    except Exception as e:
        # Registra eventuali eccezioni che potrebbero verificarsi
        print(f"Si è verificato un errore in write_chatgpt: {e}")
        return "Si è verificato un errore durante la generazione della risposta."

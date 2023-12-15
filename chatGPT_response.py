from utils.controls import is_food_question


def write_chatgpt(openai, message):
    # Aggiungi una logica di filtro per determinare l'argomento della domanda
    if is_food_question(message):
        # Se la domanda riguarda il cibo, invia la richiesta a OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": message}
            ]
        )
        return response["choices"][0]["message"]["content"]
    else:
        # Se l'argomento non riguarda il cibo, restituisci una risposta specifica
        return "Mi dispiace, non sono in grado di rispondere a domande su questo argomento. Rispondo solo a domande " \
               "riguardanti l'alimentazione "

"""
Modulo che contiene i metodi di controllo dell'input e i filtri delle risposte applicati all'utente
"""

import locale

locale.setlocale(locale.LC_TIME, 'it_IT')


def is_food_question(question):
    """
        Questa funzione serve per filtrare le risposte dell'utente al solo ambito food attraverso l'uso di keywords

        :param question: domanda posta dall'utente
        :type question: str

        :return: True (è una domanda legata al food) o False (NON è una domanda legata al food)
                in base alla risposta dell'utente
        :rtype: boolean
        """
    # Aggiungi qui la tua logica per determinare se la domanda riguarda il cibo
    # Ad esempio, potresti usare delle parole chiave o espressioni regolari
    food_keywords = ["cibo", "pasto", "mangiare", "malattie", "disturbi", "nutrizionali", "ingredienti", "ingrediente",
                     "cibo,", "nutrizione", "alimenti", "nutrienti", "dieta", "proteine", "carboidrati", "grassi",
                     "fibre", "vitamine", "minerali", "calorie", "antiossidanti",
                     "alimenti", "biologico", "integrali", "integrale", "pianta-based", "prodotti", "vegetale",
                     "lattiero-caseari", "gluten-free", "vegetariano", "vegano", "peso corporeo", "diabete",
                     "colesterolo", "pressione sanguigna", "idratazione", "cibo sano",
                     "obesità", "diabete di tipo 2", "malattie cardiache", "iperlipidemia", "ipertensione",
                     "aterosclerosi", "celiachia", "intolleranze alimentari",
                     "allergie alimentari", "disturbi alimentari", "anoressia nervosa", "Bulimia nervosa", "sovrappeso",
                     "malnutrizione", "disturbi metabolici", "gotta", "osteoporosi", "anemia",
                     "disturbi gastrointestinali", "reflusso gastroesofageo", "reflusso",
                     "malattia del fegato grasso non alcolico", "sindrome metabolica",
                     "sindrome dell'intestino irritabile", "diarrea", "costipazione", "mangiarlo", "mangiarli",
                     "mangiato", "insulina"]
    return any(keyword in question.lower() for keyword in food_keywords)


# Decoratore per il controllo del testo in input
def correct_text_xml(function):
    """
    L'obiettivo apparente di questo decoratore è pulire il testo in input, rimuovendo gli spazi bianchi iniziali,
    gestendo il caso in cui una riga è vuota, e sostituendo _bn_ con un carattere di nuova riga.

    :param function: Prende come argomento una funzione (function). Il suo scopo principale è eseguire delle operazioni
            aggiuntive sul testo in input.
    :type function:

    :return: restituisce una nuova funzione (wrapper)
    :rtype: LiteralString
    """

    # Prende una stringa (item), rimuove gli spazi bianchi iniziali tramite item.lstrip(), e restituisce None se la
    # stringa risultante è vuota, altrimenti restituisce la stringa stessa.
    def f(item):
        return item.lstrip() if not item.lstrip().__eq__('') else None

    # passa i parametri alla funzione originale (function). Il risultato della chiamata a function viene
    # successivamente elaborato: la stringa viene suddivisa in righe, gli spazi bianchi iniziali vengono rimossi da
    # ciascuna riga tramite la funzione f, le righe non nulle vengono filtrate e alla fine tutte le righe vengono
    # unite in una stringa separata da newline (\n). Inoltre, _bn_ viene sostituito con un carattere di nuova riga.
    def wrapper(arg1, arg2, arg3, arg4):
        text = function(arg1, arg2, arg3, arg4).split("\n")
        text = list(filter(lambda item2: item2 is not None, list(map(lambda item: f(item), text))))
        return ("\n".join(text)).replace("_bn_", "\n")

    return wrapper


# Verrà eseguita dopo essere stata passata come argomento alla funzione correct_text_xml
@correct_text_xml
def control_tag(root_xml, path, tag, attributo):
    for child in root_xml.findall(path):
        if child.attrib.get("type") == tag:
            return child.find(attributo).text


def check_time_in_range(current_time, start_time, end_time):
    """
            Questa funzione serve per controllare che il tempo attuale si trovi all'interno di un intervallo

            :param current_time: tempo attuale
            :type current_time: time.py
            :param start_time: inizio dell'intervallo temporale
            :type start_time: time.py
            :param end_time: fine dell'intervallo temporale
            :type end_time: time.py

            :return: True (è nell'intervallo) o False (NON è nell'intervallo)
            :rtype: boolean
            """
    return start_time <= current_time <= end_time

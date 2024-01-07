# metodo per determinare se la domanda riguarda il cibo
import re

def is_food_question(question):
    # Aggiungi qui la tua logica per determinare se la domanda riguarda il cibo
    # Ad esempio, potresti usare delle parole chiave o espressioni regolari
    food_keywords = ["cibo", "pasto", "mangiare", "malattie", "disturbi", "nutrizionali", "ingredienti", "ingrediente",
                     "Cibo e Nutrizione", "Alimenti", "Nutrienti", "Dieta" , "Proteine", "Carboidrati", "Grassi",
                     "Fibre", "Vitamine", "Minerali", "Calorie", "Antiossidanti",
                     "Superfood", "Alimenti biologici", "Alimenti integrali", "Pianta-based", "Prodotti "
                     "lattiero-caseari", "Gluten-free", "Vegetariano", "Vegano", "Peso corporeo", "Diabete",
                     "Colesterolo", "Pressione sanguigna", "Idratazione", "Cibo sano",
                     "Obesità", "Diabete di tipo 2", "Malattie cardiache", "Iperlipidemia", "Ipertensione",
                     "Aterosclerosi", "Celiachia", "Intolleranze alimentari",
                     "Allergie alimentari", "Disturbi alimentari", "Anoressia nervosa", "Bulimia nervosa", "Sovrappeso",
                     "Malnutrizione", "Disturbi metabolici", "Gotta", "Osteoporosi", "Anemia",
                     "Disturbi gastrointestinali", "Reflusso gastroesofageo",
                     "Malattia del fegato grasso non alcolico", "Sindrome metabolica",
                     "Sindrome dell'Intestino Irritabile", "Diarrea", "Costipazione"]
    return any(keyword in question.lower() for keyword in food_keywords)




# Decoratore per il controllo del testo in input
def correct_text_xml(function):
    """
    L'obiettivo apparente di questo decoratore è pulire il testo in input, rimuovendo gli spazi bianchi iniziali,
    gestendo il caso in cui una riga è vuota, e sostituendo _bn_ con un carattere di nuova riga.

    :param function: Prende come argomento una funzione (function). Il suo scopo principale è eseguire delle
    operazioni aggiuntive sul testo in input.
    :return: restituisce una nuova funzione (wrapper)
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

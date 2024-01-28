FOODCOACHINGBOT
-
Guida installazione:
- Installare python 3.10 o superiore
- Clonare la repository
- Creare la venv (virtual environment) di python con il comando python *-m venv venv*
- Spostarsi nella directory *\venv\Scripts* e digitare il comando *activate*
- Scaricare lo zip da: https://github.com/BtbN/FFmpeg-Builds/releases. Questo programma è necessario per convertire i file audio da .ogg a .wav
- Scaricare il file JSon delle credenziali di google cloud platform (nel .env inserire il path dove si trova questo file )
- Generare la chiave per l'API di chatgpt


Generazione documentazione:
 - pip install sphinx_rtd_theme
 - sphinx-apidoc -o docs src/
 -  cd docs
 - sphinx-quickstart
 - modificare il file index.rst scrivendo sotto a Contents: modules
 - Attenzione al path nei file .rst per l'automodule. In questo caso il path sarà, esempio: src.handle_reminder_data
 - Modificare il file di configurazione Sphinx (conf.py) aggiungendo questa linea di codice: sys.path.insert(0, os.path.abspath('..')) e aggiungere anche html_builder = 'html'
 - extensions = ['sphinx.ext.autodoc','sphinx.ext.viewcode','sphinx.ext.napoleon',]
 - .\make hmtl
 - .\make clean html per pulire. Poi rigenerare l'html
 

Descrizione:
 - Chatbot telegram che ha lo scopo di fornire consigli dietetici

Profilazione:
- L'utente viene profilato solo quando viene premuto il comando /start. Ovvero, quando avvia il bot. Gli viene chiesto: età, disturbi alimentari e l'emozione che prova quando mangia o pensa al cibo.

Modifica dati profilo:
- L'utente può modificare i dati del proprio profilo attraverso il comando /modifica

Visualizza dati profilo:
- L'utente può visualizzare i dati del proprio profilo con il comando /profilo

Visualizza dashboard:
- L'utente può visualizzare i dati delle diete settimanali su un pdf plottando i dati delle diete settimanali

Dieta settimanale:
- L'utente, attraverso i reminder di colazione, pranzo e cena costruisce la sua dieta settimanale. Nella risposta ai reminder l'utente salva il cibo nel database e vengono salvati in automatico anche i valori nutrizionali del cibo con l'api di edamame. Inoltre, viene mandato un reminder settimanale per avvisare l'utente che è trascorsa una settimana e che deve visualizzare la sua dieta settimanale

Modalità di interazione:
- Testuale: l'utente può chiedere al chatbot qualsiasi domanda inerente al cibo.
- Vocale: l'utente può comunicare anche tramite messaggi vocali con l'utilizzo dell'api di Google Speech-To-Text
- Fotografia: l'utente può inviare una foto del cibo al chatbot e il chatbot risponde se va bene oppure no in base ai vari filtri utilizzando l'api di Roboflow di un modello allenato con un dataset di piatti pugliesi.

Filtri conversazionali:
- E' presente un filtro che permette all’utente di poter chattare con il bot tramite telegram di argomenti riguardanti solo l’ambito food. Realizzato attraverso l'identificazione di keyword nel messaggio dell'utente
- Il chatbot adatta la conversazione in base al profilo dell’utente, ovvero in base all’età, disturbi e che tipo di sentimento prova mentre mangia o pensa al cibo.
- Il chatbot adatta la conversazione anche in base alle diete settimanali dell'utente ottenute durante l'utilizzo dell'app

Message Reply:
- L'utente può rispondere ai vecchi reminder facendo domande su quello specifico giorno. Es: L'utente vuole chiedere al chatbot se ha fatto bene a mangiare anche un altro cibo in quel giorno

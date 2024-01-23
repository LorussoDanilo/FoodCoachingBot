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

Descrizione:
 - Chatbot telegram che ha lo scopo di fornire consigli dietetici

Profilazione:
- L'utente viene profilato solo quando viene premuto il comando /start. Ovvero, quando avvia il bot. Gli viene chiesto: età, disturbi alimentari e l'emozione che prova quando mangia o pensa al cibo.

Modifica dati profilo:
- L'utente può modificare i dati del proprio profilo attraverso il comando /modifica

Modalità di interazione:
- Testuale: l'utente può chiedere al chatbot qualsiasi domanda inerente al cibo.
- Vocale: l'utente può comunicare anche tramite messaggi vocali

Filtri conversazionali:
- E' presente un filtro che permette all’utente di poter chattare con il bot tramite telegram di argomenti riguardanti solo l’ambito food. Realizzato attraverso l'identificazione di keyword nel messaggio dell'utente
- Il chatbot adatta la conversazione in base al profilo dell’utente, ovvero in base all’età, disturbi e che tipo di sentimento prova mentre mangia o pensa al cibo.

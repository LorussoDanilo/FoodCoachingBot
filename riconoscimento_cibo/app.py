import json
from roboflow import Roboflow
from flask import Flask, request
import tempfile
import os

app = Flask(__name__)


@app.route('/upload', methods=['POST'])
def upload_image():

    file = request.files['file']
    if file.filename == '':
        return "Nessun file selezionato", 400

    if file:
        # Salva temporaneamente l'immagine su disco
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file.save(temp_file.name)

        rf = Roboflow(api_key="DdgoW5JHoOafvCdYGtUE")
        project = rf.workspace().project("food-coaching-object-detection")
        model = project.version(4).model

        # Esegui l'inferenza utilizzando il percorso temporaneo del file
        result = model.predict(temp_file.name, confidence=40, overlap=30)
        print(result.json())

        # Rimuovi il file temporaneo
        os.remove(temp_file.name)

        return result.json()["predictions"][0]["class"]


if __name__ == '__main__':
    app.run(port=5000)

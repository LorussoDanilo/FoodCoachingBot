# Function to connect to MongoDB
import os
import xml.etree.ElementTree as ET

import openai
import telebot
from pymongo import MongoClient

# constant
TOKEN_CHAT_GPT = 'TOKEN_CHAT_GPT'
TOKEN_TELEGRAM = 'TOKEN_TELEGRAM'
FILE_XML = 'FILE_XML'


def connect_mongodb():
    mongodb_uri = os.getenv("MONGODB_URI")
    database_name = os.getenv("DATABASE_NAME")
    collection_name = os.getenv("COLLECTION_NAME")

    client = MongoClient(mongodb_uri)
    db = client[database_name]
    collection = db[collection_name]

    return client, collection


# Questa funzione serve per gestire le API e le risorse del progetto
# come l'xml del testo relativo ai comandi usati dall'utente
def connect():
    openai.api_key = os.getenv(TOKEN_CHAT_GPT)
    bot = telebot.TeleBot(os.getenv(TOKEN_TELEGRAM))
    tree = ET.parse(os.getenv(FILE_XML))
    return openai, bot, tree.getroot()

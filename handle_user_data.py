from bson import ObjectId
from pymongo import MongoClient


def update_user_profile(field_name, user_profile, response):
    # Analizza la risposta del chatbot e aggiorna il profilo utente
    update_profile_fields = {
        'telegram_id': field_name,
        'name': field_name,
        'age': field_name,
        'diseases': field_name,
        'food': field_name,
    }

    for keyword, (field, extractor) in update_profile_fields.items():
        if keyword in response.lower():
            value = extractor(response)
            if value is not None:
                user_profile[field] = value


def get_user_profile(telegram_id, user_profiles_collection):
    return user_profiles_collection.find_one({'telegram_id': telegram_id}) or {}


def get_all_telegram_ids(user_profiles_collection):
    # Assuming user_profiles_collection is a PyMongo collection
    # Connect to the MongoDB database
    client = MongoClient("mongodb://localhost:27017")  # Update with your MongoDB connection string
    db = client["foodCoachUsers"]
    collection = db[user_profiles_collection]

    # Query to retrieve all documents with a 'telegram_id' field
    cursor = collection.find({}, {'telegram_id': 1, '_id': 0})

    # Extract Telegram IDs from the cursor
    telegram_ids = [profile.get('telegram_id') for profile in cursor]

    # Close the MongoDB connection
    client.close()

    return telegram_ids


def ask_user_info(telegram_id, user_profiles_collection, bot_telegram, field_name, prompt_message):
    # Check if the user already exists in the database
    user_profile = get_user_profile(telegram_id, user_profiles_collection)

    if not user_profile:
        user_profile = {
            "_id": ObjectId(),
            "name": "",
            "age": "",
            "diseases": "",
            "weekly_meals": [
                {
                    "week_number": "",
                    "days": {
                        "lunedi": {"colazione": {"food": ""}, "pranzo": {"food": ""}, "cena": {"food": ""}},
                        "martedi": {"colazione": {"food": ""}, "pranzo": {"food": ""}, "cena": {"food": ""}},
                        "mercoledi": {"colazione": {"food": ""}, "pranzo": {"food": ""}, "cena": {"food": ""}},
                        "giovedi": {"colazione": {"food": ""}, "pranzo": {"food": ""}, "cena": {"food": ""}},
                        "venerdi": {"colazione": {"food": ""}, "pranzo": {"food": ""}, "cena": {"food": ""}},
                        "sabato": {"colazione": {"food": ""}, "pranzo": {"food": ""}, "cena": {"food": ""}},
                        "domenica": {"colazione": {"food": ""}, "pranzo": {"food": ""}, "cena": {"food": ""}},
                    },
                }
            ],
        }

    if not user_profile.get(field_name):
        # Ask the user for the information
        bot_telegram.send_message(telegram_id, prompt_message)

        # Wait for the user's response
        response = bot_telegram.get_updates()[-1].message.text

        # Update the user profile with the provided information
        user_profile[field_name] = response
        update_user_profile(telegram_id, user_profile, response)

        bot_telegram.send_message(telegram_id, f"Grazie, {response}! La tua {field_name} è stata salvata.")

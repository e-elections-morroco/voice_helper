
from io import BytesIO
import io
import speech_recognition as sr
import pyttsx3
import pymysql
from flask import Flask, jsonify, request
from flask_cors import CORS
import base64
from pydub import AudioSegment

app = Flask(__name__)


def base64_to_audio_segment(base64_data):
    try:
        # Add padding to the Base64 data if needed
        missing_padding = len(base64_data) % 4
        if missing_padding:
            base64_data += "=" * (4 - missing_padding)

        # Decode the Base64 data
        audio_data = base64.b64decode(base64_data)

        # Store the decoded data in a BytesIO variable
        audio_stream = BytesIO(audio_data)

        # Convert the BytesIO variable to an AudioSegment
        audio_segment = AudioSegment.from_file(audio_stream)

        print("Audio successfully converted to an AudioSegment.")

        return audio_segment
    except Exception as e:
        print("An error occurred:", str(e))
        return jsonify(
            status="error",
            error="Error : function base64_to_audio_segment",
            errorMessage=str(e),
        )
        # return None


def recherche_mots_old(tableau, mots):
    for mot in mots:
        if mot not in tableau:
            return 0  # Retourne 0 si au moins l'un des mots n'est pas trouvé
    return 1  # Retourne 1 si tous les mots sont trouvés


def recherche_mots(text, hotwords):
    for hotword in hotwords:
        found = False
        for element in text:
            if element in hotword:
                found = True
                break
        if not found:
            return 0
    return 1

def getParams(actionCode, actionText, orderCode):

    params = {
        "actionCode": actionCode,
        "actionText": actionText,
        "orderCode": orderCode,
    }
    return params


@app.route("/voicebot", methods=["POST"])
def perform_action():
    data = request.get_json()  # Retrieve JSON data from the POST request
    # Now you can access the 'langue' parameter from the JSON data
    base64_audio_data = data.get("base64data")
    provider = data.get("provider")
    langue = data.get("langue", "arabe") 
    host = data.get("database_ip")

    if langue == "":
        langue = "anglais"

    # Créer une connexion à la base de données MySQL
    conn = pymysql.connect(
        host=host,
        user="root",
        password="",
        database="e_elections",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    if langue.lower() == "francais":
        langue = "fr"
    elif langue.lower() == "anglais":
        langue = "en"
    elif langue.lower() == "arabe": 
        langue = "ar"
    else:
        return jsonify(error="Langue non prise en charge ", langue=langue)
    try:
        recognizer = sr.Recognizer()
        text_speech = pyttsx3.init()
    except:
        print("Something went wrong")
    else:
        print("Nothing went wrong")

    with conn.cursor() as cursor:
        cursor.execute(f"SELECT * FROM voice_commands")
        rows = cursor.fetchall()
        orders = [row[f"order_text_{langue}"] for row in rows]
        hotwords = [row[f"hotwords_{langue}"].split(" ") for row in rows]
        actioncodes = [row[f"action_code"] for row in rows]
        actions = [row[f"action_text"] for row in rows]
        ordercodes = [row[f"id"] for row in rows]
    # Lire le contenu du fichier contenant la chaîne Base64
    audio_segment = base64_to_audio_segment(base64_audio_data)

    if provider == "vosk":
        print("Provider : Vosk")
    elif provider == "google":
        if langue.lower() == "fr":
            langue = "fr-FR"
        elif langue.lower() == "en":
            langue = "en-US"
        elif langue.lower() == "ar":
            langue = "ar-AR"
        else:
            langue = "en-US"
        if audio_segment is not None:
            # Créer un objet Recognizer
            recognizer = sr.Recognizer()
            # Convertir AudioSegment en bytes
            audio_bytes = io.BytesIO()
            audio_segment.export(audio_bytes, format="wav")
            # Utiliser l'objet AudioFile avec l'objet BytesIO
            with sr.AudioFile(audio_bytes) as source:
                audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language=langue)
            print("Texte reconnu par google :", text)

    try:
        myinput = text
        correct = False
        for i in range(len(orders)):
            order = orders[i]
            hotword = hotwords[i]
            actioncode = actioncodes[i]
            action = actions[i]
            ordercode = ordercodes[i]
            if (
                myinput.lower() == order.lower()
                or recherche_mots(myinput.lower().split(), hotword) == 1
            ):
                correct = True
                break
        if correct:
            print("Action executed successfully")
            return jsonify(
                langue=langue,
                text=myinput.lower(),
                action=action,
            )
            base64_audio_data = ""
        else:
            print("Command not recognized")
            return jsonify(
                status="error",
                error="Command not recognized",
                langue=langue,
                text=myinput.lower(),
                provider=provider,
            )

    except sr.UnknownValueError:
        print(f"Désolé, je n'ai pas compris le son en {langue}")
        return jsonify(
            status="error", error="Désolé, je n'ai pas compris le son en {langue}"
        )

    except sr.RequestError:
        print(f"Désolé, le service est actuellement indisponible en {langue}")
        return jsonify(
            status="error",
            error="Désolé, le service est actuellement indisponible en {langue}",
        )
    return jsonify(
        status="error", error="Error :  Action not found", errorMessage=audio_segment
    )

if __name__ == "__main__":
    CORS(app)
    app.run(host="0.0.0.0", port=5002, debug=False)

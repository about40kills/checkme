import os
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, request

from audio import mp3_to_ogg, ogg_to_wav
from lookup import extract_number, lookup_name
from responses import found, no_number, not_found
from asr import transcribe
from tts import speak

try:
    from twilio.rest import Client
except ImportError:  # pragma: no cover - exercised only when dependency is missing
    Client = None


load_dotenv()

app = Flask(__name__, static_folder="static")

TWILIO_SID = os.getenv("TWILIO_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN", "")
FROM_NUMBER = os.getenv("TWILIO_WHATSAPP_FROM", "")
BASE_URL = os.getenv("BASE_URL", "").rstrip("/")
AUDIO_DIR = Path(app.static_folder) / "audio"

_twilio_client = None


def get_client():
    global _twilio_client

    if _twilio_client is None:
        if Client is None:
            raise RuntimeError("Twilio SDK is not installed. Run `pip install twilio`.")
        if not TWILIO_SID or not TWILIO_TOKEN:
            raise RuntimeError("Twilio credentials are missing. Set TWILIO_SID and TWILIO_TOKEN.")
        _twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)
    return _twilio_client


@app.route("/", methods=["GET"])
def health():
    return {"status": "running"}, 200


@app.route("/webhook", methods=["POST"])
def webhook():
    from_number = request.form.get("From", "")
    num_media = int(request.form.get("NumMedia", 0))

    try:
        if num_media > 0:
            content_type = request.form.get("MediaContentType0", "")
            media_url = request.form.get("MediaUrl0", "")

            if "audio" in content_type and media_url:
                response = requests.get(
                    media_url,
                    auth=(TWILIO_SID, TWILIO_TOKEN),
                    timeout=30,
                )
                response.raise_for_status()
                handle_voice(response.content, from_number)
            else:
                send_text(from_number, "Mesrɛ wo, soma voice note nko ara anaa text no.")
        else:
            body = request.form.get("Body", "").strip()
            handle_text(body, from_number)
    except Exception as exc:
        app.logger.exception("Webhook processing failed: %s", exc)
        if from_number:
            send_text(from_number, "Biribi nkɔɔ yie. Mesrɛ wo, san soma no bio.")

    return "", 200


def send_text(to, message):
    get_client().messages.create(from_=FROM_NUMBER, to=to, body=message)


def send_voice(to, ogg_bytes):
    if not BASE_URL:
        raise RuntimeError("BASE_URL is missing. Set it to your ngrok HTTPS URL.")

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4()}.ogg"
    path = AUDIO_DIR / filename
    path.write_bytes(ogg_bytes)

    media_url = f"{BASE_URL}/static/audio/{filename}"
    get_client().messages.create(from_=FROM_NUMBER, to=to, media_url=[media_url])


def build_reply_text(number):
    if not number:
        return no_number()

    name = lookup_name(number)
    return found(number, name) if name else not_found(number)


def handle_voice(ogg_bytes, from_number):
    wav = ogg_to_wav(ogg_bytes)
    text = transcribe(wav)
    print(f"Transcribed: {text}")

    if not text:
        send_text(from_number, "Mente ase. Mesrɛ wo, ka number no bio.")
        return

    reply_text = build_reply_text(extract_number(text))
    mp3 = speak(reply_text)

    if not mp3:
        send_text(from_number, reply_text)
        return

    ogg = mp3_to_ogg(mp3)
    send_voice(from_number, ogg)


def handle_text(body, from_number):
    reply_text = build_reply_text(extract_number(body))
    mp3 = speak(reply_text)

    if not mp3:
        send_text(from_number, reply_text)
        return

    ogg = mp3_to_ogg(mp3)
    send_voice(from_number, ogg)


if __name__ == "__main__":
    app.run(debug=True, port=5000)

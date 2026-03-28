from flask import Flask, request
from twilio.rest import Client
from dotenv import load_dotenv
import os, requests
from collections import Counter

load_dotenv()
app = Flask(__name__, static_folder="static")

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
FROM_NUMBER = os.getenv("TWILIO_WHATSAPP_FROM")
BASE_URL = os.getenv("BASE_URL")

client = Client(TWILIO_SID, TWILIO_TOKEN)

SESSIONS = {}  # Store state for USSD flows
ANALYTICS = {
    "total_messages": 0,
    "voice_messages": 0,
    "text_messages": 0,
    "lookup_requests": 0,
    "found_hits": 0,
    "not_found_hits": 0,
    "no_number_hits": 0,
    "ussd_sessions_started": 0,
    "language_counts": Counter(),
    "top_numbers": Counter(),
}


@app.route("/", methods=["GET"])
def health():
    return {"status": "running"}, 200


@app.route("/metrics", methods=["GET"])
def metrics():
    return {
        "status": "ok",
        "total_messages": ANALYTICS["total_messages"],
        "voice_messages": ANALYTICS["voice_messages"],
        "text_messages": ANALYTICS["text_messages"],
        "lookup_requests": ANALYTICS["lookup_requests"],
        "found_hits": ANALYTICS["found_hits"],
        "not_found_hits": ANALYTICS["not_found_hits"],
        "no_number_hits": ANALYTICS["no_number_hits"],
        "ussd_sessions_started": ANALYTICS["ussd_sessions_started"],
        "language_counts": dict(ANALYTICS["language_counts"]),
        "top_numbers": ANALYTICS["top_numbers"].most_common(5),
    }, 200


@app.route("/webhook", methods=["POST"])
def webhook():
    from_number = request.form.get("From")
    num_media = int(request.form.get("NumMedia", 0))
    ANALYTICS["total_messages"] += 1

    if num_media > 0:
        ANALYTICS["voice_messages"] += 1
        content_type = request.form.get("MediaContentType0", "")
        media_url = request.form.get("MediaUrl0")

        if "audio" in content_type:
            ogg_bytes = requests.get(
                media_url,
                auth=(TWILIO_SID, TWILIO_TOKEN)
            ).content
            handle_voice(ogg_bytes, from_number)
        else:
            send_text(from_number, "Mesrɛ wo soma voice note ama me.")
    else:
        ANALYTICS["text_messages"] += 1
        body = request.form.get("Body", "").strip()
        handle_text(body, from_number)

    return "", 200


def send_text(to, message):
    client.messages.create(from_=FROM_NUMBER, to=to, body=message)


def send_voice(to, ogg_bytes):
    import uuid
    os.makedirs("static/audio", exist_ok=True)
    filename = f"{uuid.uuid4()}.ogg"
    path = f"static/audio/{filename}"
    with open(path, "wb") as f:
        f.write(ogg_bytes)
    url = f"{BASE_URL}/static/audio/{filename}"
    client.messages.create(from_=FROM_NUMBER, to=to, media_url=[url])


def process_message(text, from_number):
    """Core logic to process incoming text and manage USSD state flow."""
    from lookup import extract_number, lookup_record
    from responses import found, not_found, no_number, ask_amount, ask_reference, confirm_transfer
    from tts import speak
    from audio import mp3_to_ogg
    from language_support import detect_language, translate_reply

    text = text.strip()
    detected_lang = detect_language(text)
    ANALYTICS["language_counts"][detected_lang] += 1
    session = SESSIONS.get(from_number)

    if session:
        state = session.get("state")

        if state == "USSD_MAIN_MENU":
            if text == "1":
                session["state"] = "USSD_SEND_MONEY_MENU"
                send_text(
                    from_number,
                    "Send Money\n1. MoMo User\n2. Non-MoMo\n0. Cancel"
                )
            elif text == "0":
                send_text(from_number, "USSD session ended.")
                SESSIONS.pop(from_number, None)
            else:
                send_text(from_number, "Invalid option. Reply 1 to Send Money or 0 to Cancel.")
            return

        if state == "USSD_SEND_MONEY_MENU":
            if text == "1":
                session["state"] = "USSD_ENTER_NUMBER"
                send_text(from_number, "Enter Number (e.g. 0244123456):")
            elif text == "0":
                send_text(from_number, "USSD session ended.")
                SESSIONS.pop(from_number, None)
            else:
                send_text(from_number, "For demo, reply 1 for MoMo User or 0 to Cancel.")
            return

        if state == "USSD_ENTER_NUMBER":
            target_number = extract_number(text)
            if not target_number:
                send_text(from_number, "Invalid number. Enter a valid Ghana number.")
                return

            record = lookup_record(target_number)
            if not record:
                send_text(from_number, f"Number {target_number} not found. Enter another number.")
                return

            session["target_number"] = target_number
            session["target_name"] = record["display_name"]
            session["state"] = "USSD_CONFIRM_NAME"
            send_text(
                from_number,
                f"Name: {record['display_name']}\nNumber: {target_number}\n1. Confirm\n2. Re-enter Number\n0. Cancel"
            )
            return

        if state == "USSD_CONFIRM_NAME":
            if text == "1":
                session["state"] = "USSD_ENTER_AMOUNT"
                send_text(from_number, ask_amount())
            elif text == "2":
                session["state"] = "USSD_ENTER_NUMBER"
                send_text(from_number, "Enter Number:")
            elif text == "0":
                send_text(from_number, "USSD session ended.")
                SESSIONS.pop(from_number, None)
            else:
                send_text(from_number, "Reply 1 to Confirm, 2 to Re-enter Number, or 0 to Cancel.")
            return

        if state == "USSD_ENTER_AMOUNT":
            clean_amount = text.replace(",", "").strip()
            if not clean_amount.replace(".", "", 1).isdigit():
                send_text(from_number, "Invalid amount. Enter numbers only (e.g. 50 or 50.00).")
                return
            session["amount"] = clean_amount
            session["state"] = "USSD_ENTER_REFERENCE"
            send_text(from_number, ask_reference())
            return

        if state == "USSD_ENTER_REFERENCE":
            # The user requested a simulation that runs up to the "Enter Reference" point.
            ref = text if text else "N/A"
            send_text(
                from_number,
                f"USSD simulation complete.\nTo: {session.get('target_name', 'Unknown')} ({session.get('target_number', '-')})\n"
                f"Amount: GHS {session.get('amount', '-')}\nReference: {ref}\n"
                "This is where MTN *170# would proceed to PIN entry."
            )
            SESSIONS.pop(from_number, None)
            return

        if state == "AWAITING_CONFIRMATION":
            # Check for positive confirmation
            if text.lower() in ["yes", "y", "send", "continue", "yep", "yeah"]:
                session["state"] = "AWAITING_AMOUNT"
                send_text(from_number, ask_amount())
            else:
                send_text(from_number, "Transfer cancelled.")
                SESSIONS.pop(from_number, None)
            return

        elif state == "AWAITING_AMOUNT":
            session["amount"] = text
            session["state"] = "AWAITING_REFERENCE"
            send_text(from_number, ask_reference())
            return

        elif state == "AWAITING_REFERENCE":
            amount = session["amount"]
            target_number = session["target_number"]
            record = lookup_record(target_number)
            name = record["display_name"] if record else "Unknown User"
            
            # Show final PIN prompt and clear state
            send_text(from_number, confirm_transfer(name, target_number, amount, text))
            SESSIONS.pop(from_number, None)
            return

    if text.replace(" ", "") in {"*170#", "*170"}:
        SESSIONS[from_number] = {"state": "USSD_MAIN_MENU"}
        ANALYTICS["ussd_sessions_started"] += 1
        send_text(
            from_number,
            "MTN MoMo (*170#) Simulation\n1. Send Money\n2. Withdraw Cash (demo disabled)\n3. Airtime (demo disabled)\n0. Cancel"
        )
        return

    # Normal "look up number" flow
    ANALYTICS["lookup_requests"] += 1
    number = extract_number(text)
    if not number:
        reply_text = no_number()
        ANALYTICS["no_number_hits"] += 1
    else:
        ANALYTICS["top_numbers"][number] += 1
        record = lookup_record(number)
        if record:
            reply_text = found(number, record)
            ANALYTICS["found_hits"] += 1
            # Setup session for USSD simulator
            SESSIONS[from_number] = {
                "state": "AWAITING_CONFIRMATION",
                "target_number": number
            }
        else:
            reply_text = not_found(number)
            ANALYTICS["not_found_hits"] += 1

    localized_reply = translate_reply(reply_text, detected_lang)
    tts_lang = detected_lang if detected_lang in {"tw", "en"} else "tw"
    mp3 = speak(localized_reply, lang=tts_lang)

    # TTS returned empty — fall back to text
    if not mp3:
        send_text(from_number, localized_reply)
        return

    ogg = mp3_to_ogg(mp3)
    send_voice(from_number, ogg)


def handle_voice(ogg_bytes, from_number):
    from audio import ogg_to_wav
    from asr import transcribe
    from language_support import detect_language

    wav = ogg_to_wav(ogg_bytes)
    text = transcribe(wav)
    lang = detect_language(text)
    print(f"Transcribed ({lang}): {text}")

    # ASR returned empty — ask user to retry
    if not text:
        send_text(from_number, "Mente ase. Mesrɛ wo, ka number no bio.")
        return

    process_message(text, from_number)


def handle_text(body, from_number):
    process_message(body, from_number)


if __name__ == "__main__":
    app.run(debug=True, port=5000)

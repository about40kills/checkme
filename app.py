from flask import Flask, request
from twilio.rest import Client
from dotenv import load_dotenv
import os
import re
import threading
import requests
from collections import Counter

load_dotenv()
app = Flask(__name__, static_folder="static")

def _required_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def normalize_whatsapp_number(raw):
    """Return WhatsApp-formatted E.164 number (e.g. whatsapp:+233XXXXXXXXX)."""
    if not raw:
        return None

    candidate = raw.strip()
    if candidate.startswith("whatsapp:"):
        candidate = candidate.split(":", 1)[1].strip()

    plus = "+" if candidate.startswith("+") else ""
    digits = re.sub(r"\D", "", candidate)
    if not digits:
        return None

    if not plus and len(digits) == 10 and digits.startswith("0"):
        digits = "233" + digits[1:]

    if not plus and digits.startswith("00"):
        digits = digits[2:]

    e164 = f"+{digits}"
    if not re.fullmatch(r"\+\d{8,15}", e164):
        return None
    return f"whatsapp:{e164}"
 

TWILIO_SID = _required_env("TWILIO_SID")
TWILIO_TOKEN = _required_env("TWILIO_TOKEN")
FROM_NUMBER = normalize_whatsapp_number(_required_env("TWILIO_WHATSAPP_FROM"))
BASE_URL = _required_env("BASE_URL").rstrip("/")

if not FROM_NUMBER:
    raise RuntimeError("TWILIO_WHATSAPP_FROM must be a valid WhatsApp number (E.164).")

client = Client(TWILIO_SID, TWILIO_TOKEN)

# TTS cache — avoids re-calling GhanaNLP for the same text (e.g. repeated no_number replies).
_tts_cache = {}
_tts_cache_lock = threading.Lock()
_TTS_CACHE_MAX = 50  # max entries to avoid unbounded memory growth


def _tts_cached(text):
    """Return cached MP3 bytes for text, calling GhanaNLP TTS only on cache miss."""
    from tts import speak
    with _tts_cache_lock:
        if text in _tts_cache:
            return _tts_cache[text]
    mp3 = speak(text, lang="tw")
    if mp3:
        with _tts_cache_lock:
            if len(_tts_cache) >= _TTS_CACHE_MAX:
                oldest = next(iter(_tts_cache))
                del _tts_cache[oldest]
            _tts_cache[text] = mp3
    return mp3


def send_prompt(to, english, twi):
    """Send English text immediately, then follow with a Twi voice note."""
    send_text(to, english)
    from audio import mp3_to_ogg
    mp3 = _tts_cached(twi)
    if mp3:
        try:
            ogg = mp3_to_ogg(mp3)
            send_voice(to, ogg)
        except Exception as e:
            print(f"[VOICE ERROR] {e}", flush=True)


_lock = threading.Lock()
SESSIONS = {}  # Store state for USSD flows — guarded by _lock
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


@app.route("/test-reply", methods=["GET"])
def test_reply():
    """Hit this URL to verify Twilio can send a WhatsApp message to a number.
    Usage: curl "http://127.0.0.1:5000/test-reply?to=whatsapp:+233XXXXXXXXX"
    """
    to = normalize_whatsapp_number(request.args.get("to"))
    if not to:
        return {"error": "Pass a valid ?to number (e.g. whatsapp:+233XXXXXXXXX)."}, 400
    try:
        msg = client.messages.create(
            from_=FROM_NUMBER,
            to=to,
            body="✅ CheckMe test reply — Twilio is working."
        )
        return {"status": "sent", "sid": msg.sid}, 200
    except Exception as e:
        return {"status": "failed", "error": str(e)}, 500


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
    payload = request.form.to_dict(flat=True)
    threading.Thread(
        target=process_incoming_payload,
        args=(payload,),
        daemon=True
    ).start()
    return "", 200


def send_text(to, message):
    normalized_to = normalize_whatsapp_number(to)
    if not normalized_to:
        raise ValueError(f"Invalid WhatsApp 'to' number: {to!r}")
    client.messages.create(from_=FROM_NUMBER, to=normalized_to, body=message)


def send_voice(to, ogg_bytes):
    import uuid
    normalized_to = normalize_whatsapp_number(to)
    if not normalized_to:
        raise ValueError(f"Invalid WhatsApp 'to' number: {to!r}")
    os.makedirs("static/audio", exist_ok=True)
    filename = f"{uuid.uuid4()}.ogg"
    path = f"static/audio/{filename}"
    with open(path, "wb") as f:
        f.write(ogg_bytes)
    url = f"{BASE_URL}/static/audio/{filename}"
    client.messages.create(from_=FROM_NUMBER, to=normalized_to, media_url=[url])

    # Delete the file after 90s — enough time for Twilio to fetch it.
    def _cleanup():
        import time
        time.sleep(90)
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
    threading.Thread(target=_cleanup, daemon=True).start()


def process_incoming_payload(payload):
    from_number = normalize_whatsapp_number(payload.get("From"))
    num_media = int(payload.get("NumMedia", 0) or 0)
    with _lock:
        ANALYTICS["total_messages"] += 1

    if not from_number:
        print(f"[WEBHOOK ERROR] Missing/invalid From number: {payload.get('From')!r}", flush=True)
        return

    try:
        if num_media > 0:
            with _lock:
                ANALYTICS["voice_messages"] += 1
            content_type = payload.get("MediaContentType0", "")
            media_url = payload.get("MediaUrl0")

            if "audio" in content_type and media_url:
                response = requests.get(
                    media_url,
                    auth=(TWILIO_SID, TWILIO_TOKEN),
                    timeout=20
                )
                response.raise_for_status()
                handle_voice(response.content, from_number)
            else:
                send_text(from_number, "Mesrɛ wo soma voice note ama me.")
        else:
            with _lock:
                ANALYTICS["text_messages"] += 1
            body = payload.get("Body", "").strip()
            handle_text(body, from_number)

    except Exception as e:
        print(f"[WEBHOOK ERROR] from={from_number} error={e}", flush=True)
        import traceback
        traceback.print_exc()
        try:
            send_prompt(from_number, "Something went wrong. Please try again.", "Hwee bɔne bi abɛba. Mesrɛ wo, xia bio.")
        except Exception as send_err:
            print(f"[SEND ERROR] Could not send error reply: {send_err}", flush=True)


def process_message(text, from_number):
    """Core logic to process incoming text and manage USSD state flow."""
    from lookup import extract_number, lookup_record
    from responses import found, not_found, no_number, ask_amount, ask_reference, confirm_transfer, transfer_success
    from tts import speak
    from audio import mp3_to_ogg
    from language_support import detect_language

    text = text.strip()
    detected_lang = detect_language(text)
    with _lock:
        ANALYTICS["language_counts"][detected_lang] += 1
    with _lock:
        session = SESSIONS.get(from_number)

    # If the user sends a new number lookup while inside any non-lang-select session, reset.
    if session and session.get("state") != "LANG_SELECT" and extract_number(text):
        with _lock:
            SESSIONS.pop(from_number, None)
        session = None

    if session:
        state = session.get("state")
        lang = session.get("lang", "tw")

        # ── Language selection ────────────────────────────────────────────────
        if state == "LANG_SELECT":
            pending = session.get("pending_number")
            if text == "1":
                chosen_lang = "tw"
            elif text == "2":
                chosen_lang = "ee"
            else:
                from responses import LANG_SELECT_ENGLISH, LANG_SELECT_VOICE
                send_prompt(from_number, LANG_SELECT_ENGLISH, LANG_SELECT_VOICE)
                return

            # Language chosen — do the lookup now
            record = lookup_record(pending)
            if record:
                reply_text = found(pending, record, lang=chosen_lang)
                with _lock:
                    ANALYTICS["found_hits"] += 1
                    ANALYTICS["top_numbers"][pending] += 1
                    SESSIONS[from_number] = {
                        "state": "AWAITING_CONFIRMATION",
                        "target_number": pending,
                        "lang": chosen_lang,
                    }
            else:
                reply_text = not_found(pending, lang=chosen_lang)
                with _lock:
                    ANALYTICS["not_found_hits"] += 1
                    ANALYTICS["top_numbers"][pending] += 1

            mp3 = _tts_cached(reply_text)
            if mp3:
                try:
                    ogg = mp3_to_ogg(mp3)
                    send_voice(from_number, ogg)
                except Exception as e:
                    print(f"[VOICE ERROR] {e}", flush=True)
                    send_text(from_number, reply_text)
            else:
                send_text(from_number, reply_text)
            return

        if state == "USSD_MAIN_MENU":
            if text == "1":
                with _lock:
                    session["state"] = "USSD_SEND_MONEY_MENU"
                send_prompt(from_number, "Send Money\n1. MoMo User\n2. Non-MoMo\n0. Cancel", "Soma Sika. Tua 1 ma MoMo User, 2 ma obiara a ɔnni MoMo, 0 sɛ wo gyae.")
            elif text == "2":
                with _lock:
                    session["state"] = "USSD_CASHOUT_ENTER_NUMBER"
                send_prompt(from_number, "Cash Out (Withdraw)\nEnter agent number or your number:", "Twe Sika. Hyɛ agent number anaasɛ wo number no.")
            elif text == "3":
                with _lock:
                    session["state"] = "USSD_AIRTIME_ENTER_NUMBER"
                send_prompt(from_number, "Buy Airtime\nEnter phone number (or leave blank for yourself):", "Tɔ Airtime. Hyɛ number a wopɛ sɛ wo tɔ ma no, anaasɛ gyae sɛ ɛyɛ ma wo ankasa.")
            elif text == "4":
                with _lock:
                    session["state"] = "USSD_CHECK_BALANCE"
                send_prompt(from_number, "Enter your MoMo PIN to check balance:", "Hyɛ wo MoMo PIN sɛ wo hwɛ wo sika.")
            elif text == "5":
                with _lock:
                    session["state"] = "USSD_MINI_STATEMENT"
                send_prompt(from_number, "Enter your MoMo PIN to view mini statement:", "Hyɛ wo MoMo PIN sɛ wo hwɛ wo nkontaabu tiawa.")
            elif text == "0":
                send_prompt(from_number, "USSD session ended.", "USSD session wie ase.")
                with _lock:
                    SESSIONS.pop(from_number, None)
            else:
                send_prompt(from_number, "Invalid option.\n1.Send Money 2.Cash Out 3.Airtime 4.Balance 5.Statement 0.Cancel", "Nsa a woaka no nnyɛ pa. Tua 1 ma Soma Sika, 2 ma Twe Sika, 3 ma Airtime, 4 ma Sika Hwɛ, 5 ma Nkontaabu, 0 ma Gyae.")
            return

        if state == "USSD_SEND_MONEY_MENU":
            if text == "1":
                with _lock:
                    session["state"] = "USSD_ENTER_NUMBER"
                send_prompt(from_number, "Enter number (e.g. 0244123456):", "Hyɛ number no, te sɛ: sero tu foɔfoɔ foɔfoɔ wɔn tu tri fɔ faif seks.")
            elif text == "0":
                send_prompt(from_number, "USSD session ended.", "USSD session wie ase.")
                with _lock:
                    SESSIONS.pop(from_number, None)
            else:
                send_prompt(from_number, "Reply 1 for MoMo User or 0 to Cancel.", "Tua 1 ma MoMo User anaasɛ 0 sɛ wo pɛ sɛ wo gyae.")
            return

        if state == "USSD_CASHOUT_ENTER_NUMBER":
            target_number = extract_number(text) or text.strip()
            with _lock:
                session["target_number"] = target_number
                session["state"] = "USSD_CASHOUT_ENTER_AMOUNT"
            send_prompt(from_number, f"Withdraw from {target_number}\nEnter amount (GHS):", f"Twe sika firi {target_number}. Hyɛ sika dodoɔ a wopɛ sɛ wo twe no.")
            return

        if state == "USSD_CASHOUT_ENTER_AMOUNT":
            clean = text.replace(",", "").strip()
            if not clean.replace(".", "", 1).isdigit():
                send_prompt(from_number, "Invalid amount. Enter numbers only (e.g. 100).", "Sika dodoɔ no nnyɛ pa. Hyɛ nɔma nko ara, te sɛ: ɔha.")
                return
            with _lock:
                session["amount"] = clean
                session["state"] = "USSD_CASHOUT_PIN"
            send_prompt(from_number, f"Withdraw GHS {clean} from {session.get('target_number', '-')}\nEnter PIN to confirm:", f"Twe GHS {clean} firi {session.get('target_number', '-')}. Hyɛ wo PIN sɛ wo si ho ban.")
            return

        if state == "USSD_CASHOUT_PIN":
            send_prompt(
                from_number,
                f"✅ Cash Out complete.\nGHS {session.get('amount', '-')} withdrawn from {session.get('target_number', '-')}.",
                f"Twe Sika wie ase. Wotwe GHS {session.get('amount', '-')} firi {session.get('target_number', '-')}. Ɛha na MTN *170# bɛhyɛ twe sika no mu."
            )
            with _lock:
                SESSIONS.pop(from_number, None)
            return

        if state == "USSD_AIRTIME_ENTER_NUMBER":
            target = extract_number(text) or text.strip()
            with _lock:
                session["target_number"] = target
                session["state"] = "USSD_AIRTIME_ENTER_AMOUNT"
            send_prompt(from_number, f"Buy airtime for {target}\nEnter amount (GHS):", f"Tɔ airtime ma {target}. Hyɛ sika dodoɔ a wopɛ sɛ wo tɔ no.")
            return

        if state == "USSD_AIRTIME_ENTER_AMOUNT":
            clean = text.replace(",", "").strip()
            if not clean.replace(".", "", 1).isdigit():
                send_text(from_number, "Invalid amount. Enter numbers only (e.g. 5).")
                return
            send_prompt(
                from_number,
                f"✅ Airtime complete.\nGHS {clean} airtime sent to {session.get('target_number', '-')}.",
                f"Airtime tɔ wie ase. Wosomaa GHS {clean} airtime kɔ {session.get('target_number', '-')}. Ɛha na MTN *170# bɛhyɛ airtime tɔ no mu."
            )
            with _lock:
                SESSIONS.pop(from_number, None)
            return

        if state == "USSD_CHECK_BALANCE":
            send_prompt(
                from_number,
                "✅ Balance Check.\nMoMo Balance: GHS 1,250.00\nE-Levy Wallet: GHS 0.00\n(Demo balance)",
                "Wo sika hwɛ wie ase. Wo MoMo sika yɛ GHS ɔha aduonu num. E-Levy Wallet yɛ sero. Yei yɛ demo sika, ɛnyɛ daa sika."
            )
            with _lock:
                SESSIONS.pop(from_number, None)
            return

        if state == "USSD_MINI_STATEMENT":
            send_prompt(
                from_number,
                "✅ Mini Statement (last 5 transactions):\n1. Sent GHS 50 → Kofi Mensah\n2. Received GHS 200\n3. Airtime GHS 10\n4. Cash Out GHS 100\n5. Sent GHS 30\n(Demo data)",
                "Nkontaabu Tiawa. Wosomaa GHS aduonum ma Kofi Mensah. Wonyaa GHS ahaanu. Wotɔɔ airtime GHS du. Wotwe GHS ɔha. Wosomaa GHS aduasa. Yei yɛ demo data."
            )
            with _lock:
                SESSIONS.pop(from_number, None)
            return

        if state == "USSD_ENTER_NUMBER":
            target_number = extract_number(text)
            if not target_number:
                send_prompt(from_number, "Invalid number. Enter a valid Ghana number (e.g. 0244123456).", "Number no nnyɛ pa. Hyɛ Ghana number pa, te sɛ: sero tu foɔfoɔ foɔfoɔ wɔn tu tri fɔ faif seks.")
                return

            record = lookup_record(target_number)
            if not record:
                send_prompt(from_number, f"Number {target_number} not found. Enter another number.", f"Yɛnhuu {target_number} mu biara. Hyɛ number foforo.")
                return

            with _lock:
                session["target_number"] = target_number
                session["target_name"] = record["display_name"]
                session["state"] = "USSD_CONFIRM_NAME"
            send_prompt(
                from_number,
                f"Name: {record['display_name']}\nNumber: {target_number}\n1. Confirm\n2. Re-enter Number\n0. Cancel",
                f"Din de {record['display_name']}, number {target_number}. Tua 1 sɛ wo si ho ban, 2 sɛ wo hyɛ number bio, 0 sɛ wo gyae."
            )
            return

        if state == "USSD_CONFIRM_NAME":
            if text == "1":
                with _lock:
                    session["state"] = "USSD_ENTER_AMOUNT"
                send_prompt(from_number, ask_amount(), "Hyɛ sika dodoɔ a wopɛ sɛ wo soma, te sɛ: aduonum.")
            elif text == "2":
                with _lock:
                    session["state"] = "USSD_ENTER_NUMBER"
                send_prompt(from_number, "Re-enter number:", "Hyɛ number no bio.")
            elif text == "0":
                send_prompt(from_number, "USSD session ended.", "USSD session wie ase.")
                with _lock:
                    SESSIONS.pop(from_number, None)
            else:
                send_prompt(from_number, "Reply 1 to Confirm, 2 to Re-enter Number, 0 to Cancel.", "Tua 1 sɛ wo si ho ban, 2 sɛ wo hyɛ number bio, anaasɛ 0 sɛ wo gyae.")
            return

        if state == "USSD_ENTER_AMOUNT":
            clean_amount = text.replace(",", "").strip()
            if not clean_amount.replace(".", "", 1).isdigit():
                send_prompt(from_number, "Invalid amount. Enter numbers only (e.g. 50 or 50.00).", "Sika dodoɔ no nnyɛ pa. Hyɛ nɔma nko ara, te sɛ: aduonum.")
                return
            with _lock:
                session["amount"] = clean_amount
                session["state"] = "USSD_ENTER_REFERENCE"
            send_prompt(from_number, ask_reference(), "Hyɛ nsɛm a wobɛka ho, anaasɛ gyae sɛ nni ho.")
            return

        if state == "USSD_ENTER_REFERENCE":
            ref = text if text else "N/A"
            send_prompt(
                from_number,
                f"Enter PIN to confirm.\nTo: {session.get('target_name', 'Unknown')} ({session.get('target_number', '-')})\nAmount: GHS {session.get('amount', '-')}\nRef: {ref}",
                f"Hyɛ wo PIN sɛ wo tua. Wosoma GHS {session.get('amount', '-')} kɔ {session.get('target_name', 'Onipa')}. Ɛha na MTN *170# bɛfa wo PIN na atua sika no."
            )
            with _lock:
                SESSIONS.pop(from_number, None)
            return

        if state == "AWAITING_CONFIRMATION":
            if text.lower() in ["yes", "y", "send", "continue", "yep", "yeah"]:
                with _lock:
                    session["state"] = "AWAITING_AMOUNT"
                send_prompt(from_number, ask_amount(), "Hyɛ sika dodoɔ a wopɛ sɛ wo soma, te sɛ: aduonum.")
            else:
                send_prompt(from_number, "Transfer cancelled.", "Wagyae sika soma no.")
                with _lock:
                    SESSIONS.pop(from_number, None)
            return

        elif state == "AWAITING_AMOUNT":
            with _lock:
                session["amount"] = text
                session["state"] = "AWAITING_REFERENCE"
            send_prompt(from_number, ask_reference(), "Hyɛ nsɛm a wobɛka ho, anaasɛ gyae sɛ nni ho.")
            return

        elif state == "AWAITING_REFERENCE":
            amount = session["amount"]
            target_number = session["target_number"]
            record = lookup_record(target_number)
            name = record["display_name"] if record else "Onipa"
            ref = text if text.strip() else "N/A"
            send_text(from_number, confirm_transfer(name, target_number, amount, ref, lang=lang))
            with _lock:
                session["reference"] = ref
                session["state"] = "AWAITING_PIN"
            return

        elif state == "AWAITING_PIN":
            amount = session.get("amount", "-")
            target_number = session.get("target_number", "-")
            ref = session.get("reference", "N/A")
            record = lookup_record(target_number)
            name = record["display_name"] if record else "Onipa"
            success_msg = transfer_success(name, target_number, amount, ref, lang=lang)
            send_text(from_number, success_msg)
            mp3 = _tts_cached(success_msg)
            if mp3:
                try:
                    ogg = mp3_to_ogg(mp3)
                    send_voice(from_number, ogg)
                except Exception as e:
                    print(f"[VOICE ERROR] PIN success voice failed: {e}", flush=True)
            with _lock:
                SESSIONS.pop(from_number, None)
            return

    if text.replace(" ", "") in {"*170#", "*170"}:
        with _lock:
            SESSIONS[from_number] = {"state": "USSD_MAIN_MENU"}
            ANALYTICS["ussd_sessions_started"] += 1
        send_prompt(
            from_number,
            "MTN MoMo (*170#)\n1. Send Money\n2. Cash Out\n3. Buy Airtime\n4. Check Balance\n5. Mini Statement\n0. Cancel",
            "MTN MoMo. Tua 1 ma Soma Sika, 2 ma Twe Sika, 3 ma Tɔ Airtime, 4 ma Hwɛ Wo Sika, 5 ma Nkontaabu Tiawa, 0 ma Gyae."
        )
        return

    # Normal "look up number" flow
    with _lock:
        ANALYTICS["lookup_requests"] += 1
    number = extract_number(text)

    if not number:
        # No number detected — reply in last known lang or Twi default
        last_lang = (SESSIONS.get(from_number) or {}).get("lang", "tw")
        reply_text = no_number(lang=last_lang)
        with _lock:
            ANALYTICS["no_number_hits"] += 1
        send_text(from_number, reply_text)
        mp3 = _tts_cached(reply_text)
        if mp3:
            try:
                ogg = mp3_to_ogg(mp3)
                send_voice(from_number, ogg)
            except Exception as e:
                print(f"[VOICE ERROR] {e}", flush=True)
        return

    # Number found — ask language preference before doing the lookup
    from responses import LANG_SELECT_ENGLISH, LANG_SELECT_VOICE
    with _lock:
        SESSIONS[from_number] = {"state": "LANG_SELECT", "pending_number": number}
        ANALYTICS["lookup_requests"] += 1
    send_prompt(from_number, LANG_SELECT_ENGLISH, LANG_SELECT_VOICE)


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
        from responses import no_number
        last_lang = (SESSIONS.get(from_number) or {}).get("lang", "tw")
        msg = "Mente ase. " + no_number(lang=last_lang) if last_lang == "tw" else "Mɔ̃ o. " + no_number(lang=last_lang)
        send_prompt(from_number, "Could not understand audio. Please try again.", msg)
        return

    process_message(text, from_number)


def handle_text(body, from_number):
    process_message(body, from_number)


if __name__ == "__main__":
    app.run(debug=True, port=5001)

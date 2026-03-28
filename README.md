# MoMo Check Demo

WhatsApp voice-note demo for checking the registered name behind a Ghana mobile money number before sending money.

## What it does

1. A user sends a Twi voice note or text message to a WhatsApp bot.
2. Twilio forwards the message to this Flask app.
3. The app downloads the audio, converts it, and sends it to GhanaNLP ASR.
4. A phone number is extracted from the transcription.
5. The app looks up a mock MoMo name and sends a Twi voice-note reply back through WhatsApp.

## Quick setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Install `ffmpeg` separately:

```bash
brew install ffmpeg
```

Copy the environment template:

```bash
cp .env.example .env
```

Fill in:

- `TWILIO_SID`
- `TWILIO_TOKEN`
- `TWILIO_WHATSAPP_FROM`
- `GHANANLP_KEY`
- `BASE_URL`

## Run locally

```bash
venv/bin/python app.py
```

In a second terminal:

```bash
ngrok http 5000
```

Set your Twilio WhatsApp sandbox webhook to:

```text
https://YOUR-NGROK-URL/webhook
```

## Smoke tests

Health check:

```bash
curl http://127.0.0.1:5000/
```

Import check:

```bash
venv/bin/python -c "from app import app; print('imports OK')"
```

Lookup logic:

```bash
venv/bin/python -m unittest discover -s tests
```

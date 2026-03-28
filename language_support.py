import os
import re
from ghana_nlp import GhanaNLP
from dotenv import load_dotenv

load_dotenv()
nlp = GhanaNLP(api_key=os.getenv("GHANANLP_KEY"))

SUPPORTED_REPLY_LANGS = {"tw", "en"}
ENGLISH_HINT_WORDS = {
    "hello", "hi", "please", "check", "number", "name", "send",
    "money", "account", "for", "me", "is", "the", "to", "this",
}


def detect_language(text):
    """
    Lightweight language detection for Twi/English demo flow.
    Defaults to Twi when confidence is low.
    """
    if not text:
        return "tw"

    lowered = text.lower()

    if any(char in lowered for char in ("ɛ", "ɔ")):
        return "tw"

    words = re.findall(r"[a-zA-Z']+", lowered)
    if not words:
        return "tw"

    hits = sum(1 for word in words if word in ENGLISH_HINT_WORDS)
    ratio = hits / max(len(words), 1)
    return "en" if ratio >= 0.25 else "tw"


def translate_reply(text, target_lang):
    """
    Translate Twi-origin response into target language when supported.
    Returns original text if translation fails or language unsupported.
    """
    if not text or target_lang not in SUPPORTED_REPLY_LANGS or target_lang == "tw":
        return text

    try:
        return nlp.translate(text, language_pair=f"tw-{target_lang}")
    except Exception as e:
        print(f"Translation error to {target_lang}: {e}")
        return text

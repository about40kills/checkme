from ghana_nlp import GhanaNLP
import os
from dotenv import load_dotenv

load_dotenv()

nlp = GhanaNLP(api_key=os.getenv("GHANANLP_KEY"))


def speak(text, lang="tw"):
    """Convert text to MP3 audio bytes using GhanaNLP TTS."""
    try:
        return nlp.tts(text, lang=lang)  # returns MP3 bytes
    except Exception as e:
        print(f"TTS error for lang={lang}: {e}")
        if lang != "tw":
            try:
                return nlp.tts(text, lang="tw")
            except Exception as twi_error:
                print(f"TTS fallback error for tw: {twi_error}")
        return b""

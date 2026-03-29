from ghana_nlp import GhanaNLP
import os
from dotenv import load_dotenv

load_dotenv()

nlp = GhanaNLP(api_key=os.getenv("GHANANLP_KEY"))


def speak(text, lang="tw"):
    """Convert text to MP3 audio bytes using GhanaNLP TTS."""
    try:
        result = nlp.tts(text, lang=lang)
        if isinstance(result, bytes) and len(result) > 0:
            return result
        print(f"TTS error for lang={lang}: API returned {type(result).__name__}: {result}", flush=True)
    except Exception as e:
        print(f"TTS error for lang={lang}: {e}", flush=True)

    if lang != "tw":
        try:
            fallback = nlp.tts(text, lang="tw")
            if isinstance(fallback, bytes) and len(fallback) > 0:
                return fallback
            print(f"TTS fallback error for tw: API returned {type(fallback).__name__}: {fallback}", flush=True)
        except Exception as twi_error:
            print(f"TTS fallback error for tw: {twi_error}", flush=True)
    return b""

from ghana_nlp import GhanaNLP
import tempfile, os
from dotenv import load_dotenv

load_dotenv()

nlp = GhanaNLP(api_key=os.getenv("GHANANLP_KEY"))
ASR_LANGUAGE = os.getenv("GHANANLP_ASR_LANGUAGE", "tw")


def transcribe(wav_bytes):
    """Transcribe WAV audio bytes using GhanaNLP STT."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(wav_bytes)
        path = f.name
    try:
        return nlp.stt(path, language=ASR_LANGUAGE)
    except Exception as e:
        print(f"ASR error: {e}")
        return ""
    finally:
        os.unlink(path)

from ghana_nlp import GhanaNLP
import tempfile, os
from dotenv import load_dotenv

load_dotenv()

nlp = GhanaNLP(api_key=os.getenv("GHANANLP_KEY"))


def transcribe(wav_bytes):
    """Transcribe WAV audio bytes using GhanaNLP STT."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(wav_bytes)
        path = f.name
    try:
        try:
            # If "auto" is supported for your plan/model, this enables multilingual detection.
            return nlp.stt(path, language="auto")
        except Exception:
            # Fallback to Twi for backwards compatibility.
            return nlp.stt(path, language="tw")
    except Exception as e:
        print(f"ASR error: {e}")
        return ""
    finally:
        os.unlink(path)

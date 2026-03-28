import os
import tempfile

from dotenv import load_dotenv

try:
    from ghana_nlp import GhanaNLP
except ImportError:  # pragma: no cover - exercised only when dependency is missing
    GhanaNLP = None


load_dotenv()


def _get_nlp():
    if GhanaNLP is None:
        raise RuntimeError("ghana-nlp is not installed. Run `pip install ghana-nlp`.")

    api_key = os.getenv("GHANANLP_KEY")
    if not api_key:
        raise RuntimeError("GHANANLP_KEY is missing.")

    return GhanaNLP(api_key=api_key)


def transcribe(wav_bytes):
    if not wav_bytes:
        return ""

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
        wav_file.write(wav_bytes)
        path = wav_file.name

    try:
        return _get_nlp().stt(path, language="tw")
    except Exception as exc:
        print(f"ASR error: {exc}")
        return ""
    finally:
        os.unlink(path)

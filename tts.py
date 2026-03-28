import os

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


def speak(text):
    if not text:
        return b""

    try:
        return _get_nlp().tts(text, lang="tw")
    except Exception as exc:
        print(f"TTS error: {exc}")
        return b""

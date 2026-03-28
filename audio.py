import os
import subprocess
import tempfile
from io import BytesIO

try:
    from pydub import AudioSegment
except ImportError:  # pragma: no cover - exercised only when dependency is missing
    AudioSegment = None


def _require_pydub():
    if AudioSegment is None:
        raise RuntimeError("pydub is not installed. Run `pip install pydub`.")


def ogg_to_wav(ogg_bytes):
    _require_pydub()

    audio = AudioSegment.from_ogg(BytesIO(ogg_bytes))
    buf = BytesIO()
    audio.export(buf, format="wav", parameters=["-ar", "16000", "-ac", "1"])
    return buf.getvalue()


def mp3_to_ogg(mp3_bytes):
    if not mp3_bytes:
        return b""

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as mp3_file:
        mp3_file.write(mp3_bytes)
        mp3_path = mp3_file.name

    ogg_path = mp3_path.replace(".mp3", ".ogg")

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                mp3_path,
                "-c:a",
                "libopus",
                "-ac",
                "1",
                "-ar",
                "48000",
                ogg_path,
            ],
            check=True,
            capture_output=True,
        )
        with open(ogg_path, "rb") as ogg_file:
            return ogg_file.read()
    finally:
        if os.path.exists(mp3_path):
            os.unlink(mp3_path)
        if os.path.exists(ogg_path):
            os.unlink(ogg_path)

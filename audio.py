from pydub import AudioSegment
from io import BytesIO
import subprocess, tempfile, os


def ogg_to_wav(ogg_bytes):
    """Convert OGG voice note bytes to 16kHz mono WAV for ASR."""
    audio = AudioSegment.from_ogg(BytesIO(ogg_bytes))
    buf = BytesIO()
    audio.export(buf, format="wav", parameters=["-ar", "16000", "-ac", "1"])
    return buf.getvalue()


def mp3_to_ogg(mp3_bytes):
    """Convert MP3 bytes (from TTS) to OGG/Opus for WhatsApp playback."""
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(mp3_bytes)
        mp3_path = f.name
    ogg_path = mp3_path.replace(".mp3", ".ogg")
    subprocess.run([
        "ffmpeg", "-y", "-i", mp3_path,
        "-c:a", "libopus", "-ac", "1",
        "-ar", "48000", ogg_path
    ], check=True, capture_output=True)
    with open(ogg_path, "rb") as f:
        result = f.read()
    os.unlink(mp3_path)
    os.unlink(ogg_path)
    return result

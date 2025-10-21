import os
import uuid
from flask import Flask, render_template, request, send_file, abort
import pyttsx3

# Try to import pydub for MP3 conversion (requires ffmpeg installed)
try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except Exception:
    HAS_PYDUB = False

app = Flask(__name__)

# === Safe AUDIO_DIR creation ===
AUDIO_DIR = os.path.join("static", "audio")

# If "audio" exists as a file, delete it
if os.path.isfile(AUDIO_DIR):
    os.remove(AUDIO_DIR)

# Create the directory
os.makedirs(AUDIO_DIR, exist_ok=True)


def pick_voice(engine, requested: str) -> str | None:
    """Try to pick a male/female voice if available."""
    voices = engine.getProperty("voices") or []
    requested = (requested or "").lower()

    female_keywords = ["zira", "hazel", "aria", "jenny", "sonia", "female"]
    male_keywords = ["david", "mark", "guy", "ryan", "male"]

    for v in voices:
        name = (getattr(v, "name", "") or "").lower()
        if requested == "female" and any(k in name for k in female_keywords):
            return v.id
        if requested == "male" and any(k in name for k in male_keywords):
            return v.id

    return None  # fallback: default voice


def tts_to_wav(text: str, voice_pref: str, rate: int = 200) -> str:
    """Synthesize text to a WAV file using pyttsx3."""
    out_wav = os.path.join(AUDIO_DIR, f"speech_{uuid.uuid4().hex}.wav")
    engine = pyttsx3.init()

    # Apply voice if possible
    voice_id = pick_voice(engine, voice_pref)
    if voice_id:
        engine.setProperty("voice", voice_id)

    # Speaking rate
    engine.setProperty("rate", rate)

    # Save to WAV
    engine.save_to_file(text, out_wav)
    engine.runAndWait()
    return out_wav


def maybe_convert_to_mp3(wav_path: str) -> tuple[str, str]:
    """Convert WAV -> MP3 if pydub+ffmpeg are available."""
    if HAS_PYDUB:
        try:
            mp3_path = wav_path[:-4] + ".mp3"
            AudioSegment.from_wav(wav_path).export(mp3_path, format="mp3")
            return mp3_path, "audio/mpeg"
        except Exception:
            pass
    return wav_path, "audio/wav"


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/speak", methods=["POST"])
def speak():
    text = (request.form.get("text") or "").strip()
    voice = (request.form.get("voice") or "female").lower()
    rate = int(request.form.get("rate", 200))

    if not text:
        abort(400, "No text provided.")

    # 1) TTS to WAV
    wav_path = tts_to_wav(text, voice, rate)

    # 2) Convert to MP3 if possible
    out_path, mimetype = maybe_convert_to_mp3(wav_path)

    return send_file(
        out_path,
        mimetype=mimetype,
        as_attachment=True,
        download_name=os.path.basename(out_path)
    )


if __name__ == "__main__":
    app.run(debug=True)

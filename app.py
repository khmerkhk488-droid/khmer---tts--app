import json
import os
import tempfile
import urllib.error
import urllib.request

from flask import Flask, jsonify, render_template, request, send_file

app = Flask(__name__)

DOSLARB_API_KEY = os.getenv("DOSLARB_API_KEY")

VOICES = {
    "female": "sovann",
    "male": "puthi",
    "sovann": "sovann",
    "puthi": "puthi",
}


@app.get("/")
def index():
    return render_template("index.html")


def make_speech(text, voice):
    if not DOSLARB_API_KEY:
        raise RuntimeError("DOSLARB_API_KEY is not configured")

    doslarb_voice = VOICES.get(voice, "sovann")

    payload = json.dumps({
        "text": text,
        "voice": doslarb_voice
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://doslarb.cloud/api/v1/tts",
        data=payload,
        headers={
            "Authorization": f"Bearer {DOSLARB_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            audio_data = response.read()

        if not audio_data:
            raise RuntimeError("Doslarb returned empty audio")

        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)

        with open(path, "wb") as f:
            f.write(audio_data)

        return path

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Doslarb API error {e.code}: {error_body}"
        )


@app.post("/api/tts")
def tts():
    data = request.get_json(silent=True) or {}

    text = (data.get("text") or "").strip()
    voice = (data.get("voice") or "female").lower()

    if not text:
        return jsonify({
            "error": "សូមបញ្ចូលអត្ថបទជាមុនសិន"
        }), 400

    if len(text) > 1200:
        return jsonify({
            "error": "អត្ថបទវែងពេក។ Doslarb Free អនុញ្ញាតប្រហែល 1200 តួអក្សរក្នុងមួយសំណើ។"
        }), 400

    try:
        path = make_speech(text, voice)

        response = send_file(
            path,
            mimetype="audio/mpeg",
            as_attachment=False,
            download_name="khmer-speech.mp3"
        )

        @response.call_on_close
        def cleanup():
            try:
                os.remove(path)
            except OSError:
                pass

        return response

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)

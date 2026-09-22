import asyncio
import os
import tempfile

import edge_tts
from flask import Flask, jsonify, render_template, request, send_file

app = Flask(__name__)

VOICES = {
    "female": "km-KH-SreymomNeural",
    "male": "km-KH-PisethNeural",
}


@app.get("/")
def index():
    return render_template("index.html")


async def make_speech(text, voice, rate):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        await communicate.save(path)
        return path
    except Exception:
        try:
            os.remove(path)
        except OSError:
            pass
        raise


@app.post("/api/tts")
def tts():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    gender = str(data.get("gender", "female"))
    rate = str(data.get("rate", "+0%"))

    if not text:
        return jsonify({"error": "សូមបញ្ចូលអត្ថបទជាភាសាខ្មែរ។"}), 400

    if len(text) > 5000:
        return jsonify({"error": "អត្ថបទវែងពេក។ សូមកាត់ឱ្យក្រោម 5,000 តួអក្សរ។"}), 400

    voice = VOICES.get(gender, VOICES["female"])

    # Keep rate within a safe range.
    try:
        rate_num = int(rate.replace("%", "").replace("+", ""))
        rate_num = max(-50, min(50, rate_num))
        rate = f"{rate_num:+d}%"
    except ValueError:
        rate = "+0%"

    try:
        path = asyncio.run(make_speech(text, voice, rate))
        response = send_file(
            path,
            mimetype="audio/mpeg",
            as_attachment=False,
            download_name="khmer-tts.mp3",
        )

        @response.call_on_close
        def cleanup():
            try:
                os.remove(path)
            except OSError:
                pass

        return response
    except Exception as exc:
        return jsonify({
            "error": "មិនអាចបង្កើតសំឡេងបានទេ។ សូមពិនិត្យ Internet ហើយសាកម្ដងទៀត។",
            "details": str(exc),
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)

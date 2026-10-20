import os
import uuid
from collections import defaultdict

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session
from google import genai
from google.genai import types
from werkzeug.utils import secure_filename

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
SECRET_KEY = os.getenv("FLASK_SECRET_KEY")

if not API_KEY:
    raise RuntimeError("Missing GEMINI_API_KEY environment variable.")
if not SECRET_KEY:
    raise RuntimeError("Missing FLASK_SECRET_KEY environment variable.")

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

client = genai.Client(api_key=API_KEY)
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Prototype-only memory. This is cleared when the server restarts.
histories = defaultdict(list)

ALLOWED_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
}

SYSTEM_PROMPT = (
    "You are a helpful multilingual AI assistant. Understand and respond "
    "in the language used by the user, including Afaan Oromo, Amharic, "
    "English, and other languages. If a file is attached, analyze it and "
    "answer the user's question about its contents. Be honest when unsure."
)


@app.get("/")
def index():
    if "chat_id" not in session:
        session["chat_id"] = uuid.uuid4().hex
    return render_template("index.html")


@app.post("/chat")
def chat():
    message = request.form.get("message", "").strip()
    uploaded = request.files.get("file")

    if not message and not (uploaded and uploaded.filename):
        return jsonify(error="Write a message or attach a file."), 400

    chat_id = session.get("chat_id")
    if not chat_id:
        chat_id = uuid.uuid4().hex
        session["chat_id"] = chat_id

    parts = [
        types.Part.from_text(
            text=f"{SYSTEM_PROMPT}\n\nUser message:\n{message or 'Please analyze the attached file.'}"
        )
    ]

    if uploaded and uploaded.filename:
        filename = secure_filename(uploaded.filename)
        extension = os.path.splitext(filename)[1].lower()

        if extension not in ALLOWED_TYPES:
            return jsonify(error="Allowed files: PNG, JPG, WEBP, PDF and TXT."), 400

        data = uploaded.read()
        if not data:
            return jsonify(error="The file is empty."), 400
        if len(data) > 10 * 1024 * 1024:
            return jsonify(error="Maximum upload size is 10 MB."), 400

        mime_type = ALLOWED_TYPES[extension]
        if mime_type == "text/plain":
            try:
                content = data.decode("utf-8")
            except UnicodeDecodeError:
                return jsonify(error="TXT file must use UTF-8 encoding."), 400
            parts.append(types.Part.from_text(
                text=f"\nAttached text file ({filename}):\n{content}"
            ))
        else:
            parts.append(types.Part.from_bytes(data=data, mime_type=mime_type))

    history = histories[chat_id][-12:]
    contents = history + [types.Content(role="user", parts=parts)]

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
        )
        answer = response.text or "I couldn't generate a text response."

        # Store a text-only version of the turn in temporary server memory.
        histories[chat_id] = history + [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=message or "Analyze attached file.")],
            ),
            types.Content(
                role="model",
                parts=[types.Part.from_text(text=answer)],
            ),
        ]
        histories[chat_id] = histories[chat_id][-12:]
        return jsonify(reply=answer)
    except Exception:
        app.logger.exception("Gemini API request failed")
        return jsonify(
            error="Gemini request failed. Check your API key, model access, internet connection, and quota."
        ), 502


@app.post("/clear")
def clear_chat():
    chat_id = session.get("chat_id")
    if chat_id:
        histories.pop(chat_id, None)
    return jsonify(message="Conversation cleared.")


@app.errorhandler(413)
def file_too_large(_error):
    return jsonify(error="Maximum upload size is 10 MB."), 413


if __name__ == "__main__":
    # For local testing only. Use a production WSGI server when deployed.
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)

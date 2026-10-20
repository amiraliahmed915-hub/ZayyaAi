# Gemini AI Website Chatbot

A Flask website chatbot using Google's Gemini API. Supports multilingual text chat, image/PDF/TXT uploads, and temporary in-memory conversation history.

## Setup

1. Create a Gemini API key at https://aistudio.google.com/apikey.
2. Copy `.env.example` to `.env`.
3. Put your key in `GEMINI_API_KEY` and set a long random `FLASK_SECRET_KEY`.
4. Install dependencies: `python -m pip install -r requirements.txt`
5. Run locally: `python app.py`
6. Open http://127.0.0.1:5000

## Deploying

- Set `GEMINI_API_KEY`, `FLASK_SECRET_KEY`, and optionally `GEMINI_MODEL` as environment variables in your hosting provider.
- Use a Python 3.12 runtime and the included `Procfile`.
- Never upload `.env` or expose the API key in browser JavaScript.
- Use HTTPS and add authentication/rate limiting before public production use.

## Notes

- Conversation memory is temporary and resets when the server restarts.
- Maximum upload size is 10 MB. Supported extensions: PNG, JPG, JPEG, WEBP, PDF, TXT.
- Uploaded files are sent to the Gemini API for analysis.

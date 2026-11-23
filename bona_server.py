"""One-process Flask website and local AI backend for Bona."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, request, send_file

from bona_backend import (
    DEFAULT_MODEL,
    build_messages,
    chat_with_local_model,
    list_local_models,
    validate_model_name,
)


ROOT = Path(__file__).resolve().parent
DESKTOP_EXE = ROOT / "dist" / "BonaLocal.exe"

app = Flask(__name__, static_folder=str(ROOT), static_url_path="")

_history: dict[str, list[dict[str, str]]] = {}
_MAX_SESSION_HISTORY = 12


@app.get("/")
def index():
    return send_file(ROOT / "index.html")


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "bona"})


@app.get("/api/models")
def models():
    try:
        names = list_local_models()
    except RuntimeError as error:
        return jsonify({"models": [], "error": str(error)}), 503
    return jsonify({"models": names, "default": DEFAULT_MODEL})


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Send a JSON request body."}), 400

    prompt = payload.get("prompt")
    model = payload.get("model", DEFAULT_MODEL)
    session_id = payload.get("session_id", "browser")
    if not isinstance(prompt, str):
        return jsonify({"error": "The prompt must be text."}), 400
    if not isinstance(model, str):
        return jsonify({"error": "The model name must be text."}), 400
    if not isinstance(session_id, str) or len(session_id) > 128:
        return jsonify({"error": "Invalid session ID."}), 400

    try:
        model = validate_model_name(model)
        history = _history.setdefault(session_id, [])[-_MAX_SESSION_HISTORY:]
        messages = build_messages(history, prompt, "")
        answer = chat_with_local_model(model, messages)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 503

    history = _history.setdefault(session_id, [])
    history.extend(
        (
            {"role": "user", "content": prompt.strip()},
            {"role": "assistant", "content": answer},
        )
    )
    _history[session_id] = history[-_MAX_SESSION_HISTORY:]
    return jsonify({"answer": answer, "model": model})


@app.post("/api/session/reset")
def reset_session():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Send a JSON request body."}), 400
    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or len(session_id) > 128:
        return jsonify({"error": "Invalid session ID."}), 400
    _history.pop(session_id, None)
    return jsonify({"status": "reset"})


@app.get("/download/BonaLocal.exe")
def download_desktop():
    if not DESKTOP_EXE.is_file():
        return jsonify({"error": "The Windows executable has not been built."}), 404
    return send_file(
        DESKTOP_EXE,
        as_attachment=True,
        download_name="BonaLocal.exe",
        mimetype="application/x-msdownload",
    )


def main() -> None:
    host = os.environ.get("BONA_HOST", "127.0.0.1")
    port = int(os.environ.get("BONA_PORT", "4173"))
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()

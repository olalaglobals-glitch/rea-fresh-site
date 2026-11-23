import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import bona_backend


class LocalOllamaHandler(BaseHTTPRequestHandler):
    received = None

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        type(self).received = json.loads(self.rfile.read(content_length).decode("utf-8"))
        response = json.dumps({"message": {"content": "Suggested change."}}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, _format, *_args):
        pass


class BonaBackendTests(unittest.TestCase):
    def test_model_name_rejects_shell_metacharacters(self):
        with self.assertRaises(ValueError):
            bona_backend.validate_model_name("model; do-something")

    def test_context_skips_secrets_and_dependency_folders(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "main.py").write_text("print('hello')", encoding="utf-8")
            (root / ".env").write_text("TOKEN=private", encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "hidden.js").write_text("private", encoding="utf-8")

            context = bona_backend.collect_project_context(root)

        self.assertIn("--- main.py ---", context)
        self.assertNotIn("TOKEN=private", context)
        self.assertNotIn("hidden.js", context)

    def test_chat_uses_only_local_service_and_returns_response(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), LocalOllamaHandler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            with patch.object(bona_backend, "OLLAMA_BASE_URL", base_url):
                answer = bona_backend.chat_with_local_model(
                    "qwen2.5-coder:3b",
                    [{"role": "user", "content": "Say hello"}],
                )
            self.assertEqual(answer, "Suggested change.")
            self.assertEqual(LocalOllamaHandler.received["stream"], False)
            self.assertEqual(LocalOllamaHandler.received["model"], "qwen2.5-coder:3b")
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)


if __name__ == "__main__":
    unittest.main()

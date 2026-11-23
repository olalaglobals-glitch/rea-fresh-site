import unittest
from unittest.mock import patch

import bona_server


class BonaServerTests(unittest.TestCase):
    def setUp(self):
        bona_server.app.config.update(TESTING=True)
        self.client = bona_server.app.test_client()

    def test_home_page_is_served(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Bona", response.data)

    def test_health_is_available(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_chat_rejects_missing_prompt(self):
        response = self.client.post("/api/chat", json={"session_id": "test"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("prompt", response.get_json()["error"].lower())

    def test_chat_calls_local_backend(self):
        with patch.object(bona_server, "chat_with_local_model", return_value="Local answer"):
            response = self.client.post(
                "/api/chat",
                json={"prompt": "Explain this function", "session_id": "test"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["answer"], "Local answer")

    def test_models_reports_unavailable_ollama(self):
        with patch.object(
            bona_server,
            "list_local_models",
            side_effect=RuntimeError("Ollama is unavailable"),
        ):
            response = self.client.get("/api/models")
        self.assertEqual(response.status_code, 503)
        self.assertIn("Ollama", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main()

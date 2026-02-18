"""
tests/test_navigation.py
========================
Tests de navigation automatisés – TESE935

Ces tests vérifient que toutes les routes de l'application
répondent correctement (codes HTTP, présence de contenu…).

Lancement :
    python -m unittest tests/test_navigation.py -v   (sans pytest)
    pytest tests/test_navigation.py -v               (avec pytest)
"""

import sys
import os
import unittest
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module
from app import app


def make_client():
    """Crée un client de test Flask avec une DB temporaire."""
    app.config["TESTING"] = True
    fd, db_path = tempfile.mkstemp(suffix=".db")
    original_db = app_module.DB_PATH
    app_module.DB_PATH = db_path
    app_module.init_db()
    client = app.test_client()
    return client, fd, db_path, original_db


def teardown_client(fd, db_path, original_db):
    app_module.DB_PATH = original_db
    os.close(fd)
    os.unlink(db_path)


# ──────────────────────────────────────────────────────────────
# 1. Tests de navigation de base
# ──────────────────────────────────────────────────────────────

class TestNavigation(unittest.TestCase):

    def setUp(self):
        self.client, self.fd, self.db_path, self.orig_db = make_client()

    def tearDown(self):
        teardown_client(self.fd, self.db_path, self.orig_db)

    def test_homepage_returns_200(self):
        """La page d'accueil doit retourner HTTP 200."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_homepage_contains_title(self):
        """La page d'accueil doit afficher le titre de l'app."""
        response = self.client.get("/")
        self.assertIn(b"FakeNews Detector", response.data)

    def test_add_news_page_returns_200(self):
        """La page d'ajout doit retourner HTTP 200."""
        response = self.client.get("/add")
        self.assertEqual(response.status_code, 200)

    def test_add_news_page_contains_form(self):
        """La page d'ajout doit contenir un formulaire."""
        response = self.client.get("/add")
        self.assertIn(b"<form", response.data)

    def test_status_endpoint_returns_json(self):
        """L'endpoint /status doit retourner un JSON valide."""
        response = self.client.get("/status")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("status", data)
        self.assertEqual(data["status"], "ok")

    def test_status_contains_news_count(self):
        """L'endpoint /status doit inclure le nombre de news."""
        response = self.client.get("/status")
        data = response.get_json()
        self.assertIn("news_count", data)
        self.assertIsInstance(data["news_count"], int)

    def test_404_on_unknown_route(self):
        """Une route inexistante doit retourner 404."""
        response = self.client.get("/route-qui-nexiste-pas")
        self.assertEqual(response.status_code, 404)


# ──────────────────────────────────────────────────────────────
# 2. Tests d'ajout de news (POST)
# ──────────────────────────────────────────────────────────────

class TestAddNews(unittest.TestCase):

    def setUp(self):
        self.client, self.fd, self.db_path, self.orig_db = make_client()

    def tearDown(self):
        teardown_client(self.fd, self.db_path, self.orig_db)

    def test_add_real_news(self):
        """Ajouter une news vérifiée doit rediriger vers l'accueil."""
        response = self.client.post("/add", data={
            "title":   "Scientists confirm water on Mars",
            "content": "NASA researchers found evidence of liquid water beneath the Martian surface.",
            "source":  "https://nasa.gov",
            "label":   "real"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"ajout", response.data)

    def test_add_fake_news(self):
        """Ajouter une fausse news doit aussi fonctionner."""
        response = self.client.post("/add", data={
            "title":   "Aliens hold concert at Eiffel Tower",
            "content": "Thousands of extraterrestrials visited Paris last night.",
            "source":  "https://fake-example.com",
            "label":   "fake"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_add_news_without_title_fails(self):
        """Ajouter une news sans titre doit afficher une erreur."""
        response = self.client.post("/add", data={
            "title":   "",
            "content": "Some content",
            "label":   "real"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"obligatoire", response.data)

    def test_add_news_without_content_fails(self):
        """Ajouter une news sans contenu doit afficher une erreur."""
        response = self.client.post("/add", data={
            "title":   "Un titre",
            "content": "",
            "label":   "real"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"obligatoire", response.data)

    def test_news_appears_in_list(self):
        """Après ajout, la news doit apparaître dans la liste."""
        self.client.post("/add", data={
            "title":   "Test news unique XYZ123",
            "content": "Contenu de test pour vérifier l'affichage.",
            "label":   "real"
        })
        response = self.client.get("/")
        self.assertIn(b"Test news unique XYZ123", response.data)

    def test_news_count_increases(self):
        """Le compteur de news doit augmenter après ajout."""
        before = self.client.get("/status").get_json()["news_count"]
        self.client.post("/add", data={
            "title": "Nouvelle news de test",
            "content": "Contenu.",
            "label": "real"
        })
        after = self.client.get("/status").get_json()["news_count"]
        self.assertEqual(after, before + 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

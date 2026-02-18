"""
tests/test_training.py
======================
Tests d'entraînement du modèle ML – TESE935

Vérifie que :
  - Le modèle s'entraîne correctement
  - Les prédictions sont cohérentes
  - Le fichier modèle est bien créé

Lancement :
    python -m unittest tests/test_training.py -v   (sans pytest)
    pytest tests/test_training.py -v               (avec pytest)
"""

import sys
import os
import sqlite3
import pickle
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.trainer import train_model, predict_news, load_data_from_db


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def create_test_db():
    """Crée une base SQLite temporaire avec des news d'entraînement."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, content TEXT, source TEXT,
            label TEXT, predicted TEXT,
            created DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    real_news = [
        ("COVID vaccine approved by FDA",
         "The FDA granted emergency use authorization for the new COVID-19 vaccine.", "real"),
        ("Scientists find new planet",
         "Astronomers discovered a habitable exoplanet using the James Webb telescope.", "real"),
        ("WHO launches global health initiative",
         "The World Health Organization announces a new program to fight malaria worldwide.", "real"),
        ("Stock market reaches all-time high",
         "The S&P 500 index surpassed 5000 points for the first time in history.", "real"),
        ("New treatment for Alzheimer approved",
         "A breakthrough drug shows significant reduction in Alzheimer disease progression.", "real"),
    ]
    fake_news = [
        ("Lizard people control government",
         "Secret reptilian overlords have been running world governments for centuries.", "fake"),
        ("Moon landing was filmed in Hollywood",
         "Anonymous sources reveal Stanley Kubrick faked the Apollo 11 moon landing.", "fake"),
        ("Microchips inserted via vaccines",
         "Government operatives are using COVID vaccines to inject tracking microchips.", "fake"),
        ("Sun revolves around flat Earth",
         "New research proves the Earth is flat and the Sun orbits around it.", "fake"),
        ("Eating magnets cures disease",
         "Holistic practitioners claim swallowing magnets cures all illness.", "fake"),
    ]
    for title, content, label in real_news + fake_news:
        conn.execute(
            "INSERT INTO news (title, content, label) VALUES (?, ?, ?)",
            (title, content, label)
        )
    conn.commit()
    conn.close()
    return fd, db_path


# ──────────────────────────────────────────────────────────────
# Tests d'entraînement
# ──────────────────────────────────────────────────────────────

class TestTraining(unittest.TestCase):

    def setUp(self):
        self.fd, self.db_path = create_test_db()
        mfd, self.model_path = tempfile.mkstemp(suffix=".pkl")
        os.close(mfd)
        os.unlink(self.model_path)

    def tearDown(self):
        os.close(self.fd)
        os.unlink(self.db_path)
        if os.path.exists(self.model_path):
            os.unlink(self.model_path)

    def test_load_data_returns_correct_count(self):
        """load_data_from_db doit retourner 10 entrées (5 real + 5 fake)."""
        texts, labels = load_data_from_db(self.db_path)
        self.assertEqual(len(texts), 10)
        self.assertEqual(len(labels), 10)

    def test_load_data_labels_are_valid(self):
        """Les labels doivent être uniquement 'real' ou 'fake'."""
        _, labels = load_data_from_db(self.db_path)
        for label in labels:
            self.assertIn(label, ("real", "fake"), f"Label inattendu : {label}")

    def test_train_creates_model_file(self):
        """L'entraînement doit créer le fichier modèle."""
        train_model(self.db_path, self.model_path)
        self.assertTrue(os.path.exists(self.model_path), "Le fichier modèle n'a pas été créé")

    def test_model_file_is_valid_pickle(self):
        """Le fichier modèle doit être un pickle valide."""
        train_model(self.db_path, self.model_path)
        with open(self.model_path, "rb") as f:
            model = pickle.load(f)
        self.assertIsNotNone(model)

    def test_model_has_predict_method(self):
        """Le modèle chargé doit avoir une méthode predict."""
        train_model(self.db_path, self.model_path)
        with open(self.model_path, "rb") as f:
            model = pickle.load(f)
        self.assertTrue(hasattr(model, "predict"))


# ──────────────────────────────────────────────────────────────
# Tests de prédiction
# ──────────────────────────────────────────────────────────────

class TestPrediction(unittest.TestCase):

    def setUp(self):
        self.fd, self.db_path = create_test_db()
        mfd, self.model_path = tempfile.mkstemp(suffix=".pkl")
        os.close(mfd)
        os.unlink(self.model_path)
        train_model(self.db_path, self.model_path)

    def tearDown(self):
        os.close(self.fd)
        os.unlink(self.db_path)
        if os.path.exists(self.model_path):
            os.unlink(self.model_path)

    def test_predict_returns_real_or_fake(self):
        """La prédiction doit retourner 'real' ou 'fake'."""
        result = predict_news("Scientists discover new treatment approved by WHO", self.model_path)
        self.assertIn(result, ("real", "fake"))

    def test_predict_without_model_returns_unknown(self):
        """Sans modèle, predict doit retourner 'unknown'."""
        result = predict_news("Some text", "/tmp/this_model_does_not_exist.pkl")
        self.assertEqual(result, "unknown")

    def test_predict_fake_text(self):
        """Un texte fake doit être prédit sans planter."""
        result = predict_news(
            "Lizard reptilian government fake moon conspiracy microchips", self.model_path
        )
        self.assertIn(result, ("real", "fake"))

    def test_predict_real_text(self):
        """Un texte réel doit être prédit sans planter."""
        result = predict_news(
            "FDA approved vaccine WHO health organization clinical trial research scientists",
            self.model_path
        )
        self.assertIn(result, ("real", "fake"))

    def test_predict_empty_string(self):
        """La prédiction doit gérer un texte vide sans planter."""
        result = predict_news("", self.model_path)
        self.assertIn(result, ("real", "fake"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

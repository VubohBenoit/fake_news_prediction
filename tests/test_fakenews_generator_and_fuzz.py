"""
tests/test_fakenews_generator_and_fuzz.py
=========================================
1. Génération automatique de fausses news à partir de news réelles (mélange)
2. Fuzz Tests : soumettre des données aléatoires à l'application

TESE935 – Gaël Roustan, Argonaultes 2026

Lancement :
    python -m unittest tests/test_fakenews_generator_and_fuzz.py -v
    pytest tests/test_fakenews_generator_and_fuzz.py -v
"""

import sys
import os
import random
import string
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module
from app import app


# ──────────────────────────────────────────────────────────────
# Pool de vraies news pour générer des fausses
# ──────────────────────────────────────────────────────────────

REAL_NEWS_POOL = [
    {
        "title": "Scientists confirm water on Mars",
        "content": "NASA researchers found evidence of liquid water beneath the Martian surface using radar data."
    },
    {
        "title": "WHO approves new malaria vaccine",
        "content": "The World Health Organization endorsed a new malaria vaccine for children in sub-Saharan Africa."
    },
    {
        "title": "Stock market reaches record high",
        "content": "The S&P 500 index surpassed 5000 points for the first time, driven by technology stocks."
    },
    {
        "title": "New AI model beats human experts at diagnosis",
        "content": "A deep learning model developed by researchers achieved 94% accuracy in detecting cancer from scans."
    },
    {
        "title": "Climate summit reaches landmark agreement",
        "content": "World leaders agreed to reduce carbon emissions by 50% before 2035 at the UN Climate Summit."
    },
]


# ──────────────────────────────────────────────────────────────
# Générateur de fausses news
# ──────────────────────────────────────────────────────────────

def generate_fake_from_real(news_pool: list, seed: int = 42) -> dict:
    """
    Crée une fausse news en mélangeant le titre d'une news
    avec le contenu d'une autre — technique de base de mélange.
    """
    rng = random.Random(seed)
    news_a, news_b = rng.sample(news_pool, 2)
    words_a = news_a["content"].split()
    words_b = news_b["content"].split()
    rng.shuffle(words_a)
    mixed_content = " ".join(words_a[:len(words_a)//2] + words_b[len(words_b)//2:])
    return {
        "title":   news_a["title"] + " — " + news_b["title"][:30] + "…",
        "content": mixed_content,
        "label":   "fake"
    }


def random_string(length: int, chars=None, seed=None) -> str:
    """Génère une chaîne aléatoire de longueur donnée."""
    rng = random.Random(seed)
    if chars is None:
        chars = string.printable
    return "".join(rng.choice(chars) for _ in range(length))


# Cas de fuzz définis – seeds fixes pour reproductibilité
FUZZ_CASES = [
    ("Très long titre (1000 chars)",
     random_string(1000, seed=1), "Normal content", "real"),
    ("Très long contenu (5000 chars)",
     "Normal title", random_string(5000, seed=2), "fake"),
    ("Titre avec XSS",
     "<script>alert('xss')</script>", "Content", "real"),
    ("SQL injection dans le titre",
     "'; DROP TABLE news; --", "Content", "fake"),
    ("Titre unicode / emojis",
     "🔥🚀💉🦠🤖 Titre bizarre 中文 العربية", "Contenu normal", "real"),
    ("Contenu vide (doit être rejeté)",
     "Titre valide", "", "real"),
    ("Titre vide (doit être rejeté)",
     "", "Contenu valide", "fake"),
    ("Label invalide",
     "Titre", "Contenu", "INVALID_LABEL"),
    ("Très grands nombres en titre",
     str(10**100), "Content", "real"),
]


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def make_client():
    app.config["TESTING"] = True
    fd, db_path = tempfile.mkstemp(suffix=".db")
    original_db = app_module.DB_PATH
    app_module.DB_PATH = db_path
    app_module.init_db()
    return app.test_client(), fd, db_path, original_db


def teardown_client(fd, db_path, original_db):
    app_module.DB_PATH = original_db
    os.close(fd)
    os.unlink(db_path)


# ──────────────────────────────────────────────────────────────
# Tests du générateur de fausses news
# ──────────────────────────────────────────────────────────────

class TestFakeNewsGenerator(unittest.TestCase):

    def setUp(self):
        self.client, self.fd, self.db_path, self.orig_db = make_client()

    def tearDown(self):
        teardown_client(self.fd, self.db_path, self.orig_db)

    def test_generator_returns_dict(self):
        """Le générateur doit retourner un dictionnaire."""
        result = generate_fake_from_real(REAL_NEWS_POOL)
        self.assertIsInstance(result, dict)

    def test_generator_has_required_keys(self):
        """Le résultat doit avoir title, content et label."""
        result = generate_fake_from_real(REAL_NEWS_POOL)
        self.assertIn("title", result)
        self.assertIn("content", result)
        self.assertIn("label", result)

    def test_generator_label_is_fake(self):
        """La news générée doit être étiquetée 'fake'."""
        result = generate_fake_from_real(REAL_NEWS_POOL)
        self.assertEqual(result["label"], "fake")

    def test_generator_content_not_empty(self):
        """Le contenu généré ne doit pas être vide."""
        result = generate_fake_from_real(REAL_NEWS_POOL)
        self.assertGreater(len(result["content"]), 0)

    def test_generator_different_seeds_give_different_results(self):
        """Deux graines différentes doivent produire des résultats différents."""
        r1 = generate_fake_from_real(REAL_NEWS_POOL, seed=1)
        r2 = generate_fake_from_real(REAL_NEWS_POOL, seed=2)
        self.assertTrue(r1["title"] != r2["title"] or r1["content"] != r2["content"])

    def test_generated_fake_can_be_submitted(self):
        """Une fausse news générée peut être soumise à l'application."""
        fake = generate_fake_from_real(REAL_NEWS_POOL, seed=42)
        response = self.client.post("/add", data={
            "title":   fake["title"],
            "content": fake["content"],
            "source":  "https://generated-fake.test",
            "label":   fake["label"]
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_multiple_fakes_can_be_generated_and_submitted(self):
        """Générer et soumettre 5 fausses news doit fonctionner."""
        for seed in range(5):
            fake = generate_fake_from_real(REAL_NEWS_POOL, seed=seed * 10)
            response = self.client.post("/add", data={
                "title":   fake["title"][:200],
                "content": fake["content"],
                "label":   "fake"
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)


# ──────────────────────────────────────────────────────────────
# Fuzz Tests
# ──────────────────────────────────────────────────────────────

class TestFuzz(unittest.TestCase):

    def setUp(self):
        self.client, self.fd, self.db_path, self.orig_db = make_client()

    def tearDown(self):
        teardown_client(self.fd, self.db_path, self.orig_db)

    def test_fuzz_app_never_crashes(self):
        """
        L'application ne doit JAMAIS retourner 500 (erreur serveur),
        quelle que soit la donnée soumise.
        """
        results = []
        for desc, title, content, label in FUZZ_CASES:
            response = self.client.post("/add", data={
                "title":   title,
                "content": content,
                "label":   label
            }, follow_redirects=True)
            results.append({
                "case":        desc,
                "status_code": response.status_code,
                "crashed":     response.status_code == 500
            })

        print("\n\n=== RAPPORT FUZZ TESTS ===")
        for r in results:
            status = "✅ OK" if not r["crashed"] else "❌ CRASH"
            print(f"  [{status}] {r['case']} → HTTP {r['status_code']}")

        crashes = [r for r in results if r["crashed"]]
        self.assertEqual(len(crashes), 0,
            f"L'app a crashé sur {len(crashes)} cas : {[c['case'] for c in crashes]}")

    def test_fuzz_homepage_always_works(self):
        """La page d'accueil doit rester accessible après des soumissions folles."""
        for _, title, content, label in FUZZ_CASES:
            self.client.post("/add", data={
                "title": title, "content": content, "label": label
            })
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_fuzz_status_always_works(self):
        """L'endpoint /status doit rester stable après des soumissions folles."""
        for _, title, content, label in FUZZ_CASES:
            self.client.post("/add", data={
                "title": title, "content": content, "label": label
            })
        response = self.client.get("/status")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "ok")

    def test_fuzz_random_get_routes(self):
        """Accéder à des routes aléatoires ne doit pas faire crasher le serveur."""
        rng = random.Random(42)
        random_routes = [
            "/" + random_string(rng.randint(1, 30), chars=string.ascii_letters + "/", seed=i)
            for i in range(10)
        ]
        for route in random_routes:
            response = self.client.get(route)
            self.assertNotEqual(response.status_code, 500,
                f"Crash HTTP 500 sur la route : {route}")

    def test_fuzz_predict_nonexistent_ids(self):
        """Prédire sur des IDs inexistants ne doit pas planter le serveur."""
        rng = random.Random(42)
        for _ in range(5):
            fake_id = rng.randint(9999, 999999)
            response = self.client.get(f"/predict/{fake_id}", follow_redirects=True)
            self.assertIn(response.status_code, (200, 302, 404))


if __name__ == "__main__":
    unittest.main(verbosity=2)

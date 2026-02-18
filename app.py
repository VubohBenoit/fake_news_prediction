"""
Application Flask - Détecteur de Fausses Informations
TESE935 - Gaël Roustan, Argonaultes 2026
"""

from flask import Flask, request, render_template, redirect, url_for, flash
import sqlite3
import os
import threading
import time
import pickle
import logging

from ml.trainer import train_model, predict_news

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = "tese935_secret"

# Chemin absolu du dossier contenant app.py — robuste peu importe le CWD
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(BASE_DIR, "news.db")
MODEL_PATH = os.path.join(BASE_DIR, "model", "model.pkl")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Base de données
# ---------------------------------------------------------------------------

def init_db():
    """Crée la table si elle n'existe pas et insère quelques exemples."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            title     TEXT NOT NULL,
            content   TEXT NOT NULL,
            source    TEXT,
            label     TEXT NOT NULL DEFAULT 'unknown',
            predicted TEXT DEFAULT NULL,
            created   DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Données de démonstration si la table est vide
    c.execute("SELECT COUNT(*) FROM news")
    if c.fetchone()[0] == 0:
        samples = [
            ("Scientists discover water on Mars",
             "NASA researchers confirm the presence of liquid water beneath the Martian surface.",
             "https://nasa.gov", "real"),
            ("Aliens landed in Paris last night",
             "Thousands of extraterrestrials reportedly held a concert at the Eiffel Tower.",
             "https://fake-news-example.com", "fake"),
            ("New vaccine approved by WHO",
             "The World Health Organization has approved a new vaccine for widespread distribution.",
             "https://who.int", "real"),
            ("Chocolate cures cancer, doctors say",
             "Eating 10 bars of chocolate daily eliminates all forms of cancer, claim anonymous sources.",
             "https://tabloid-example.com", "fake"),
        ]
        c.executemany(
            "INSERT INTO news (title, content, source, label) VALUES (?, ?, ?, ?)",
            samples
        )
    conn.commit()
    conn.close()


def get_all_news():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM news ORDER BY created DESC").fetchall()
    conn.close()
    return rows


def insert_news(title, content, source, label):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO news (title, content, source, label) VALUES (?, ?, ?, ?)",
        (title, content, source, label)
    )
    conn.commit()
    conn.close()


def update_predictions():
    """Met à jour la colonne predicted pour toutes les news via le modèle."""
    if not os.path.exists(MODEL_PATH):
        return
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT id, title, content FROM news").fetchall()
    for row in rows:
        text = row[1] + " " + row[2]
        pred = predict_news(text, MODEL_PATH)
        conn.execute("UPDATE news SET predicted=? WHERE id=?", (pred, row[0]))
    conn.commit()
    conn.close()

# ---------------------------------------------------------------------------
# Thread d'entraînement périodique
# ---------------------------------------------------------------------------

def training_thread(interval_seconds: int = 60):
    """
    Thread daemon qui ré-entraîne le modèle toutes les `interval_seconds` secondes
    et met à jour les prédictions en base.
    """
    logger.info("Training thread started (interval=%ds)", interval_seconds)
    while True:
        try:
            logger.info("Starting model training…")
            train_model(DB_PATH, MODEL_PATH)
            logger.info("Model saved → %s", MODEL_PATH)
            update_predictions()
            logger.info("Predictions updated in DB")
        except Exception as exc:
            logger.error("Training failed: %s", exc)
        time.sleep(interval_seconds)

# ---------------------------------------------------------------------------
# Routes Flask
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Page d'accueil : liste toutes les news."""
    news_list = get_all_news()
    model_ready = os.path.exists(MODEL_PATH)
    return render_template("index.html", news_list=news_list, model_ready=model_ready)


@app.route("/add", methods=["GET", "POST"])
def add_news():
    """Formulaire d'ajout d'une news avec annotation humaine."""
    if request.method == "POST":
        title   = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        source  = request.form.get("source", "").strip()
        label   = request.form.get("label", "real")

        if not title or not content:
            flash("Le titre et le contenu sont obligatoires.", "danger")
            return redirect(url_for("add_news"))

        insert_news(title, content, source, label)

        # Prédiction immédiate si le modèle est disponible
        if os.path.exists(MODEL_PATH):
            update_predictions()

        flash("News ajoutée avec succès !", "success")
        return redirect(url_for("index"))

    return render_template("add_news.html")


@app.route("/predict/<int:news_id>")
def predict_single(news_id):
    """Prédit le label d'une news via le modèle ML."""
    if not os.path.exists(MODEL_PATH):
        flash("Le modèle n'est pas encore disponible. Patientez…", "warning")
        return redirect(url_for("index"))

    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT title, content FROM news WHERE id=?", (news_id,)).fetchone()
    if row:
        text = row[0] + " " + row[1]
        pred = predict_news(text, MODEL_PATH)
        conn.execute("UPDATE news SET predicted=? WHERE id=?", (pred, news_id))
        conn.commit()
        flash(f"Prédiction ML : {pred.upper()}", "info")
    conn.close()
    return redirect(url_for("index"))


@app.route("/predict_all")
def predict_all():
    """Prédit le label de TOUTES les news en une seule fois."""
    if not os.path.exists(MODEL_PATH):
        flash("Le modèle n\'est pas encore disponible. Patientez…", "warning")
        return redirect(url_for("index"))
    update_predictions()
    flash("✅ Toutes les prédictions ont été mises à jour !", "success")
    return redirect(url_for("index"))


@app.route("/status")
def status():
    """Endpoint JSON simple pour les tests de charge/navigation."""
    model_ready = os.path.exists(MODEL_PATH)
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM news").fetchone()[0]
    conn.close()
    return {"status": "ok", "news_count": count, "model_ready": model_ready}


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    os.makedirs("model", exist_ok=True)
    init_db()

    # Lancer le thread d'entraînement
    t = threading.Thread(target=training_thread, args=(30,), daemon=True)
    t.start()

    app.run(debug=False, port=5000)
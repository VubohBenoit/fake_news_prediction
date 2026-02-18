"""
Module ML – Entraînement et prédiction
Utilise CountVectorizer + MultinomialNB (scikit-learn)
TESE935
"""

import sqlite3
import pickle
import os
import logging

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

logger = logging.getLogger(__name__)


def load_data_from_db(db_path: str):
    """
    Charge les news dont le label humain est 'real' ou 'fake'.
    Retourne (texts, labels).
    """
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT title, content, label FROM news WHERE label IN ('real', 'fake')"
    ).fetchall()
    conn.close()

    texts  = [row[0] + " " + row[1] for row in rows]
    labels = [row[2] for row in rows]
    return texts, labels


def train_model(db_path: str, model_path: str) -> None:
    """
    Entraîne un pipeline CountVectorizer → MultinomialNB
    sur les données de la base et sauvegarde le modèle.
    """
    texts, labels = load_data_from_db(db_path)
    n = len(texts)
    n_classes = len(set(labels))

    if n < 4:
        logger.warning("Pas assez de données pour entraîner (min 4). Skipped.")
        return

    if n_classes < 2:
        logger.warning("Il faut au moins 1 news 'real' ET 1 news 'fake'. Skipped.")
        return

    # Création du pipeline scikit-learn
    pipeline = Pipeline([
        ("vectorizer", CountVectorizer(
            ngram_range=(1, 2),   # unigrams + bigrams
            stop_words="english",
            max_features=5000
        )),
        ("classifier", MultinomialNB(alpha=1.0))  # alpha = lissage de Laplace
    ])

    # --- Split adaptatif ---
    # Avec peu de données, 20% peut donner moins d'exemples que le nb de classes.
    # On s'assure d'avoir au moins n_classes exemples dans le test set.
    test_size = max(n_classes, int(n * 0.2))

    if test_size >= n:
        # Trop peu de données : on entraîne sur tout sans évaluation
        logger.warning("Données insuffisantes pour splitter — entraînement sur tout le jeu.")
        pipeline.fit(texts, labels)
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels,
            test_size=test_size,
            random_state=42,
            stratify=labels
        )
        pipeline.fit(X_train, y_train)

        # Évaluation
        y_pred = pipeline.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        logger.info("Accuracy sur le jeu de test : %.2f%%", acc * 100)
        logger.info("\n%s", classification_report(y_test, y_pred, zero_division=0))

    # Sauvegarde
    os.makedirs(os.path.dirname(model_path) or ".", exist_ok=True)
    with open(model_path, "wb") as f:
        pickle.dump(pipeline, f)

    logger.info("Modèle sauvegardé dans %s (%d exemples)", model_path, n)


def predict_news(text: str, model_path: str) -> str:
    """
    Charge le modèle depuis le disque et retourne 'real' ou 'fake'.
    """
    if not os.path.exists(model_path):
        return "unknown"

    with open(model_path, "rb") as f:
        pipeline = pickle.load(f)

    prediction = pipeline.predict([text])[0]
    return prediction

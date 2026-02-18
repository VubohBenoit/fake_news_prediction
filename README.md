# FakeNews Detector – TESE935

> Projet d'évaluation — Réalisation et analyse de tests  
> Supervise par Gaël Roustan, Argonaultes 2026
> Realise par Benoit Vuboh

---

## Structure du projet

```
fakenews_detector/
│
├── app.py                  ← Application Flask principale
├── requirements.txt        ← Dépendances Python
│
├── ml/
│   ├── __init__.py
│   └── trainer.py          ← Entraînement MultinomialNB + CountVectorizer
│
├── templates/
│   ├── base.html           ← Template HTML de base
│   ├── index.html          ← Liste des news
│   └── add_news.html       ← Formulaire d'ajout
│
├── static/css/
│   └── style.css           ← Feuille de style
│
├── model/
│   └── model.pkl           ← Modèle entraîné (généré automatiquement)
│
└── tests/
    ├── conftest.py
    ├── test_navigation.py              ← Tests de navigation HTTP
    ├── test_training.py                ← Tests d'entraînement ML
    └── test_fakenews_generator_and_fuzz.py  ← Génération + Fuzz tests
```

---

## Installation et lancement

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Lancer l'application
python app.py

# 3. Ouvrir dans le navigateur
# http://localhost:5000
```

---

## Fonctionnalités

### Application Flask (app.py)

| Route       | Méthode | Description                              |
|-------------|---------|------------------------------------------|
| `/`         | GET     | Liste toutes les news avec leur statut   |
| `/add`      | GET/POST| Formulaire d'ajout avec annotation       |
| `/predict/<id>` | GET | Prédit le label d'une news via ML    |
| `/status`   | GET     | Endpoint JSON — état de l'application    |

### Modèle ML (ml/trainer.py)

- **CountVectorizer** : transforme le texte en matrice de fréquences de mots
  - `ngram_range=(1,2)` : unigrammes + bigrammes
  - `stop_words="english"` : supprime les mots vides
  - `max_features=5000` : limite le vocabulaire
- **MultinomialNB** : classifieur Naive Bayes adapté au texte
- **Pipeline scikit-learn** : chaîne les deux étapes

### Thread d'entraînement

Un `threading.Thread` daemon tourne en arrière-plan et :
1. Entraîne le modèle toutes les 60 secondes
2. Sauvegarde le modèle dans `model/model.pkl`
3. Met à jour les prédictions en base de données

---

## Tests automatisés

```bash
# Lancer tous les tests
pytest tests/ -v

# Tests de navigation uniquement
pytest tests/test_navigation.py -v

# Tests ML uniquement
pytest tests/test_training.py -v

# Tests fuzz + générateur
pytest tests/test_fakenews_generator_and_fuzz.py -v
```

### test_navigation.py — Tests de navigation
- Vérifie que chaque route retourne le bon code HTTP
- Teste l'ajout de news (real et fake)
- Vérifie que les news apparaissent dans la liste

### test_training.py — Tests d'entraînement
- Vérifie que le modèle est bien créé
- Teste que les prédictions retournent 'real' ou 'fake'
- Gestion des cas limites (texte vide, modèle absent)

### test_fakenews_generator_and_fuzz.py — Génération + Fuzz
- **Générateur** : mélange titre + contenu de vraies news pour créer des fausses
- **Fuzz tests** : soumet des données aléatoires/malveillantes pour crasher l'app
  - Très longues chaînes (1000–5000 chars)
  - Injections XSS et SQL
  - Emojis et Unicode
  - Labels invalides
  - Routes aléatoires
  - IDs inexistants

---

## Présentation (5 minutes)

1. **Architecture** (1 min) : Flask + SQLite + ML thread
2. **Demo** (2 min) : ajouter une news, voir la prédiction
3. **Tests** (2 min) : lancer pytest, montrer les résultats

---

## Jeu de données

L'application est conçue pour être entraînée sur le dataset **FakeNews** disponible sur Kaggle.  
Sans le dataset Kaggle, elle s'entraîne automatiquement sur les news saisies dans l'interface.

Pour utiliser le dataset Kaggle :
1. Télécharger [FakeNewsNet](https://www.kaggle.com/datasets/clmentbisaillon/fake-and-real-news-dataset)
2. Importer les news dans la base SQLite avec le script d'import (voir `ml/trainer.py`)
# fake_news_prediction

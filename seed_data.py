"""
seed_data.py
============
Peuple automatiquement la base de données avec :
  - Des vraies news (real)
  - Des fausses news générées automatiquement par mélange (fake)

TESE935 - À lancer UNE FOIS avant app.py, ou appelé automatiquement au démarrage.
"""

import sqlite3
import random
import os

# Pool de vraies news de base
REAL_NEWS = [
    {
        "title": "NASA confirms black hole image captured",
        "content": "Scientists at NASA and ESA successfully captured the first high-resolution image of a black hole using the Event Horizon Telescope network across multiple continents.",
        "source": "https://nasa.gov"
    },
    {
        "title": "WHO declares end of COVID-19 global emergency",
        "content": "The World Health Organization officially declared the end of COVID-19 as a global health emergency after reviewing infection and mortality data from countries worldwide.",
        "source": "https://who.int"
    },
    {
        "title": "Electric vehicles sales surpass 10 million units",
        "content": "Global electric vehicle sales reached a record 10 million units driven by falling battery costs and strong government incentives across Europe and Asia.",
        "source": "https://iea.org"
    },
    {
        "title": "Scientists develop new antibiotic after 40 years",
        "content": "Researchers at Harvard University developed a new class of antibiotics capable of killing drug-resistant bacteria, the first major antibiotic discovery in four decades.",
        "source": "https://harvard.edu"
    },
    {
        "title": "New Alzheimer treatment shows 35% progression reduction",
        "content": "A breakthrough drug developed by pharmaceutical researchers shows a significant 35% reduction in Alzheimer disease progression in clinical trials across 20 countries.",
        "source": "https://nih.gov"
    },
    {
        "title": "James Webb telescope discovers 7 new exoplanets",
        "content": "The James Webb Space Telescope identified seven new exoplanets in a distant solar system, three of which are located in the habitable zone and could support liquid water.",
        "source": "https://nasa.gov/webb"
    },
    {
        "title": "Global renewable energy capacity breaks record",
        "content": "The International Energy Agency reports that global renewable energy capacity reached a new record, with solar and wind power now accounting for 30% of global electricity generation.",
        "source": "https://iea.org/renewables"
    },
    {
        "title": "Oxford University develops universal flu vaccine",
        "content": "Oxford University researchers announced the successful development of a universal influenza vaccine that targets all known flu strains, offering up to 10 years of protection.",
        "source": "https://oxford.ac.uk"
    },
]

# Pool de vraies fausses news écrites à la main
HANDCRAFTED_FAKE = [
    {
        "title": "Bill Gates admits microchips hidden in vaccines",
        "content": "In a leaked secret video, Bill Gates confesses that all COVID vaccines contain GPS microchips designed to track and control the global population without consent.",
        "source": "https://conspiracynews.fake"
    },
    {
        "title": "5G towers proven to cause cancer and mind control",
        "content": "Anonymous doctors reveal that 5G electromagnetic towers are deliberately engineered to cause cancer and alter human brain functions for secret government control programs.",
        "source": "https://antennafake.com"
    },
    {
        "title": "Moon landing was entirely staged by Hollywood",
        "content": "Newly discovered classified documents prove that Stanley Kubrick was hired by the CIA to film the fake Apollo 11 moon landing in a secret studio located in Nevada.",
        "source": "https://fakespace.net"
    },
    {
        "title": "Drinking bleach daily cures all known diseases",
        "content": "A group of anonymous physicians claim that drinking diluted bleach every morning permanently eliminates cancer, diabetes and all known viruses within 48 hours.",
        "source": "https://fakeremedies.com"
    },
]


def generate_fake_from_real(news_pool: list, seed: int = 42) -> dict:
    """
    Génère une fausse news en mélangeant titre + contenu de deux vraies news.
    Technique demandée par le sujet : mélange de plusieurs news véridiques.
    """
    rng = random.Random(seed)
    news_a, news_b = rng.sample(news_pool, 2)

    # Mélange des mots du contenu des deux news
    words_a = news_a["content"].split()
    words_b = news_b["content"].split()
    rng.shuffle(words_a)
    mixed_content = " ".join(words_a[:len(words_a) // 2] + words_b[len(words_b) // 2:])

    # Titre composite : début du titre A + fin du titre B
    title = news_a["title"] + " — " + " ".join(news_b["title"].split()[-3:])

    return {
        "title":   title,
        "content": mixed_content,
        "source":  "https://auto-generated-fake.test",
        "label":   "fake"
    }


def seed_database(db_path: str, force: bool = False) -> int:
    """
    Insère les données dans la base si elle est vide (ou si force=True).
    Retourne le nombre de news insérées.
    """
    conn = sqlite3.connect(db_path)

    # Vérifier si la base est déjà peuplée
    count = conn.execute("SELECT COUNT(*) FROM news").fetchone()[0]
    if count >= 10 and not force:
        conn.close()
        return 0

    inserted = 0

    # 1. Insérer les vraies news
    for news in REAL_NEWS:
        conn.execute(
            "INSERT INTO news (title, content, source, label) VALUES (?, ?, ?, ?)",
            (news["title"], news["content"], news["source"], "real")
        )
        inserted += 1

    # 2. Insérer les fausses news écrites à la main
    for news in HANDCRAFTED_FAKE:
        conn.execute(
            "INSERT INTO news (title, content, source, label) VALUES (?, ?, ?, ?)",
            (news["title"], news["content"], news["source"], "fake")
        )
        inserted += 1

    # 3. Générer automatiquement 6 fausses news par mélange de vraies (seeds différents)
    for seed in range(6):
        fake = generate_fake_from_real(REAL_NEWS, seed=seed * 7 + 42)
        conn.execute(
            "INSERT INTO news (title, content, source, label) VALUES (?, ?, ?, ?)",
            (fake["title"], fake["content"], fake["source"], "fake")
        )
        inserted += 1

    conn.commit()
    conn.close()
    return inserted


if __name__ == "__main__":
    # Permet aussi de lancer le script directement : python seed_data.py
    from app import DB_PATH, init_db
    init_db()
    n = seed_database(DB_PATH, force=True)
    print(f"✅ {n} news insérées dans la base.")
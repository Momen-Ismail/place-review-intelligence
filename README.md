# Place Review Intelligence — v1

A generic Google Maps review collection system built with Python, Apify, and SQLite.

The project is intentionally **not restaurant-specific**.

Every business or location is stored as a `place`, so the same system can later support:

- Restaurants
- Hotels
- Gyms
- Clinics
- Stores
- Cafés
- Tourist attractions
- Salons
- Car dealerships
- Schools
- Other Google Maps places

---

## What v1 currently does

- Accepts one or multiple Google Maps place URLs
- Uses Apify's `compass/google-maps-reviews-scraper`
- Collects Google-native reviews
- Can collect all available reviews or a limited number
- Supports multilingual reviews
- Preserves the original review language
- Preserves translated review text when available
- Collects the full review text
- Collects the main star rating
- Collects detailed ratings such as Food, Service, Atmosphere when available
- Collects additional review context such as meal type, price, parking, reservation, etc.
- Collects review image URLs when available
- Collects owner responses
- Collects review publication date/time
- Stores places and reviews separately in SQLite
- Deduplicates reviews using `review_id`
- Updates existing reviews when collected again
- Stores the complete raw Apify review JSON so unknown fields are not lost
- Keeps reviewer personal data disabled by default
- Can export collected reviews to CSV
- Provides basic rating statistics

---

## 1. Requirements

Install:

- Python 3.11 or newer
- Visual Studio Code
- An Apify account

Create an Apify account and get your API token from:

Apify Console → API & Integrations

---

## 2. Project structure

```text
place-review-intelligence/
│
├── collection/
│   ├── collectors/
│   │   └── apify_google.py
│   ├── core/
│   │   ├── database.py
│   │   └── normalizer.py
│   └── collect.py
│
├── analysis/
│   ├── common/
│   └── restaurants/
│
├── businesses/
│   └── restaurants/
│       └── al_assiel/
│           ├── data/
│           │   ├── reviews.db
│           │   └── exports/
│           ├── analysis/
│           └── reports/
│
├── config.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

Run the collection CLI from the project root with:

```bash
python -m collection.collect ...
```

`collection/` contains review collection and storage code, `analysis/` is
reserved for shared and restaurant-specific analysis code, and `businesses/`
contains each business's data and generated outputs.

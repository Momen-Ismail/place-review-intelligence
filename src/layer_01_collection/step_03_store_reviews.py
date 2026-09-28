from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Iterable
from config import DATABASE_PATH

class ReviewDatabase:

    def __init__(self, path: Path | str=DATABASE_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys = ON;')
        self._create_tables()
        self._upgrade_existing_tables()
        self._create_indexes()

    def close(self):
        """
        Close the SQLite connection.
        """
        self.conn.close()

    def _create_tables(self):
        """
        Create the main tables if this is a new database.
        """
        self.conn.executescript('\n            CREATE TABLE IF NOT EXISTS places (\n                place_id TEXT PRIMARY KEY,\n\n                cid TEXT,\n                fid TEXT,\n                kgmid TEXT,\n                business_profile_id TEXT,\n\n                title TEXT,\n                category TEXT,\n                categories_json TEXT,\n\n                address TEXT,\n                neighborhood TEXT,\n                street TEXT,\n                city TEXT,\n                state TEXT,\n                country_code TEXT,\n                postal_code TEXT,\n\n                latitude REAL,\n                longitude REAL,\n\n                total_score REAL,\n                reviews_count INTEGER,\n\n                price TEXT,\n\n                google_maps_url TEXT,\n                input_url TEXT,\n\n                image_url TEXT,\n\n                hotel_stars REAL,\n\n                permanently_closed INTEGER,\n                temporarily_closed INTEGER,\n                is_advertisement INTEGER,\n\n                updated_at TEXT\n            );\n\n\n            CREATE TABLE IF NOT EXISTS reviews (\n                review_id TEXT PRIMARY KEY,\n\n                place_id TEXT NOT NULL,\n\n                source TEXT,\n\n                reviewer_id TEXT,\n                reviewer_name TEXT,\n                reviewer_url TEXT,\n                reviewer_number_of_reviews INTEGER,\n                reviewer_photo_url TEXT,\n                is_local_guide INTEGER,\n\n                review_url TEXT,\n\n                rating REAL,\n\n                text_original TEXT,\n                text_translated TEXT,\n\n                published_at TEXT,\n                published_relative TEXT,\n\n                visited_in TEXT,\n\n                original_language TEXT,\n                translated_language TEXT,\n\n                likes_count INTEGER,\n\n                owner_response_text TEXT,\n                owner_response_date TEXT,\n\n                review_context_json TEXT,\n                detailed_ratings_json TEXT,\n                review_images_json TEXT,\n\n                scraped_at TEXT,\n\n                raw_json TEXT,\n\n                FOREIGN KEY(place_id)\n                    REFERENCES places(place_id)\n                    ON DELETE CASCADE\n            );\n            ')
        self.conn.commit()

    def _get_existing_columns(self, table_name: str) -> set[str]:
        """
        Return all column names currently existing
        in a SQLite table.
        """
        rows = self.conn.execute(f'PRAGMA table_info({table_name})').fetchall()
        return {row['name'] for row in rows}

    def _add_missing_columns(self, table_name: str, required_columns: dict[str, str]):
        """
        Add newly introduced columns to an older database.

        This allows us to improve the project later without
        deleting reviews.db every time the schema changes.
        """
        existing_columns = self._get_existing_columns(table_name)
        for column_name, column_type in required_columns.items():
            if column_name in existing_columns:
                continue
            self.conn.execute(f'\n                ALTER TABLE {table_name}\n                ADD COLUMN {column_name} {column_type}\n                ')
            print(f'Database upgraded: added {table_name}.{column_name}')
        self.conn.commit()

    def _upgrade_existing_tables(self):
        """
        Upgrade databases created by older versions
        of this project.
        """
        place_columns = {'cid': 'TEXT', 'fid': 'TEXT', 'kgmid': 'TEXT', 'business_profile_id': 'TEXT', 'title': 'TEXT', 'category': 'TEXT', 'categories_json': 'TEXT', 'address': 'TEXT', 'neighborhood': 'TEXT', 'street': 'TEXT', 'city': 'TEXT', 'state': 'TEXT', 'country_code': 'TEXT', 'postal_code': 'TEXT', 'latitude': 'REAL', 'longitude': 'REAL', 'total_score': 'REAL', 'reviews_count': 'INTEGER', 'price': 'TEXT', 'google_maps_url': 'TEXT', 'input_url': 'TEXT', 'image_url': 'TEXT', 'hotel_stars': 'REAL', 'permanently_closed': 'INTEGER', 'temporarily_closed': 'INTEGER', 'is_advertisement': 'INTEGER', 'updated_at': 'TEXT'}
        review_columns = {'source': 'TEXT', 'reviewer_id': 'TEXT', 'reviewer_name': 'TEXT', 'reviewer_url': 'TEXT', 'reviewer_number_of_reviews': 'INTEGER', 'reviewer_photo_url': 'TEXT', 'is_local_guide': 'INTEGER', 'review_url': 'TEXT', 'rating': 'REAL', 'text_original': 'TEXT', 'text_translated': 'TEXT', 'published_at': 'TEXT', 'published_relative': 'TEXT', 'visited_in': 'TEXT', 'original_language': 'TEXT', 'translated_language': 'TEXT', 'likes_count': 'INTEGER', 'owner_response_text': 'TEXT', 'owner_response_date': 'TEXT', 'review_context_json': 'TEXT', 'detailed_ratings_json': 'TEXT', 'review_images_json': 'TEXT', 'scraped_at': 'TEXT', 'raw_json': 'TEXT'}
        self._add_missing_columns('places', place_columns)
        self._add_missing_columns('reviews', review_columns)

    def _create_indexes(self):
        """
        Create indexes used frequently during analysis.

        These become useful when the database contains
        thousands or hundreds of thousands of reviews.
        """
        self.conn.executescript('\n            CREATE INDEX IF NOT EXISTS idx_reviews_place_id\n            ON reviews(place_id);\n\n\n            CREATE INDEX IF NOT EXISTS idx_reviews_published_at\n            ON reviews(published_at);\n\n\n            CREATE INDEX IF NOT EXISTS idx_reviews_rating\n            ON reviews(rating);\n\n\n            CREATE INDEX IF NOT EXISTS idx_reviews_language\n            ON reviews(original_language);\n\n\n            CREATE INDEX IF NOT EXISTS idx_reviews_reviewer_id\n            ON reviews(reviewer_id);\n            ')
        self.conn.commit()

    def upsert_places(self, places: Iterable[dict]) -> int:
        """
        Insert new places.

        If the place already exists,
        refresh its information.
        """
        rows = list(places)
        if not rows:
            return 0
        sql = '\n        INSERT INTO places (\n            place_id,\n\n            cid,\n            fid,\n            kgmid,\n            business_profile_id,\n\n            title,\n            category,\n            categories_json,\n\n            address,\n            neighborhood,\n            street,\n            city,\n            state,\n            country_code,\n            postal_code,\n\n            latitude,\n            longitude,\n\n            total_score,\n            reviews_count,\n\n            price,\n\n            google_maps_url,\n            input_url,\n\n            image_url,\n\n            hotel_stars,\n\n            permanently_closed,\n            temporarily_closed,\n            is_advertisement,\n\n            updated_at\n        )\n        VALUES (\n            :place_id,\n\n            :cid,\n            :fid,\n            :kgmid,\n            :business_profile_id,\n\n            :title,\n            :category,\n            :categories_json,\n\n            :address,\n            :neighborhood,\n            :street,\n            :city,\n            :state,\n            :country_code,\n            :postal_code,\n\n            :latitude,\n            :longitude,\n\n            :total_score,\n            :reviews_count,\n\n            :price,\n\n            :google_maps_url,\n            :input_url,\n\n            :image_url,\n\n            :hotel_stars,\n\n            :permanently_closed,\n            :temporarily_closed,\n            :is_advertisement,\n\n            :updated_at\n        )\n\n        ON CONFLICT(place_id)\n        DO UPDATE SET\n\n            cid = excluded.cid,\n            fid = excluded.fid,\n            kgmid = excluded.kgmid,\n            business_profile_id = excluded.business_profile_id,\n\n            title = excluded.title,\n            category = excluded.category,\n            categories_json = excluded.categories_json,\n\n            address = excluded.address,\n            neighborhood = excluded.neighborhood,\n            street = excluded.street,\n            city = excluded.city,\n            state = excluded.state,\n            country_code = excluded.country_code,\n            postal_code = excluded.postal_code,\n\n            latitude = excluded.latitude,\n            longitude = excluded.longitude,\n\n            total_score = excluded.total_score,\n            reviews_count = excluded.reviews_count,\n\n            price = excluded.price,\n\n            google_maps_url = excluded.google_maps_url,\n            input_url = excluded.input_url,\n\n            image_url = excluded.image_url,\n\n            hotel_stars = excluded.hotel_stars,\n\n            permanently_closed = excluded.permanently_closed,\n            temporarily_closed = excluded.temporarily_closed,\n            is_advertisement = excluded.is_advertisement,\n\n            updated_at = excluded.updated_at\n        '
        self.conn.executemany(sql, rows)
        self.conn.commit()
        return len(rows)

    def upsert_reviews(self, reviews: Iterable[dict]) -> tuple[int, int]:
        """
        Insert new reviews.

        If a review already exists,
        refresh its information instead.

        Returns:

            inserted_count
            updated_count
        """
        rows = list(reviews)
        if not rows:
            return (0, 0)
        inserted = 0
        updated = 0
        sql = '\n        INSERT INTO reviews (\n            review_id,\n            place_id,\n\n            source,\n\n            reviewer_id,\n            reviewer_name,\n            reviewer_url,\n            reviewer_number_of_reviews,\n            reviewer_photo_url,\n            is_local_guide,\n\n            review_url,\n\n            rating,\n\n            text_original,\n            text_translated,\n\n            published_at,\n            published_relative,\n\n            visited_in,\n\n            original_language,\n            translated_language,\n\n            likes_count,\n\n            owner_response_text,\n            owner_response_date,\n\n            review_context_json,\n            detailed_ratings_json,\n            review_images_json,\n\n            scraped_at,\n\n            raw_json\n        )\n        VALUES (\n            :review_id,\n            :place_id,\n\n            :source,\n\n            :reviewer_id,\n            :reviewer_name,\n            :reviewer_url,\n            :reviewer_number_of_reviews,\n            :reviewer_photo_url,\n            :is_local_guide,\n\n            :review_url,\n\n            :rating,\n\n            :text_original,\n            :text_translated,\n\n            :published_at,\n            :published_relative,\n\n            :visited_in,\n\n            :original_language,\n            :translated_language,\n\n            :likes_count,\n\n            :owner_response_text,\n            :owner_response_date,\n\n            :review_context_json,\n            :detailed_ratings_json,\n            :review_images_json,\n\n            :scraped_at,\n\n            :raw_json\n        )\n\n        ON CONFLICT(review_id)\n        DO UPDATE SET\n\n            place_id = excluded.place_id,\n\n            source = excluded.source,\n\n            reviewer_id = excluded.reviewer_id,\n            reviewer_name = excluded.reviewer_name,\n            reviewer_url = excluded.reviewer_url,\n            reviewer_number_of_reviews =\n                excluded.reviewer_number_of_reviews,\n            reviewer_photo_url =\n                excluded.reviewer_photo_url,\n            is_local_guide =\n                excluded.is_local_guide,\n\n            review_url = excluded.review_url,\n\n            rating = excluded.rating,\n\n            text_original = excluded.text_original,\n            text_translated = excluded.text_translated,\n\n            published_at = excluded.published_at,\n            published_relative = excluded.published_relative,\n\n            visited_in = excluded.visited_in,\n\n            original_language = excluded.original_language,\n            translated_language = excluded.translated_language,\n\n            likes_count = excluded.likes_count,\n\n            owner_response_text = excluded.owner_response_text,\n            owner_response_date = excluded.owner_response_date,\n\n            review_context_json = excluded.review_context_json,\n            detailed_ratings_json = excluded.detailed_ratings_json,\n            review_images_json = excluded.review_images_json,\n\n            scraped_at = excluded.scraped_at,\n\n            raw_json = excluded.raw_json\n        '
        for row in rows:
            existed = self.conn.execute('\n                SELECT 1\n                FROM reviews\n                WHERE review_id = ?\n                ', (row['review_id'],)).fetchone()
            self.conn.execute(sql, row)
            if existed:
                updated += 1
            else:
                inserted += 1
        self.conn.commit()
        return (inserted, updated)

    def list_places(self):
        """
        Return all stored places together with
        basic review statistics.
        """
        return self.conn.execute('\n            SELECT\n                p.*,\n\n                COUNT(r.review_id)\n                    AS stored_reviews,\n\n                ROUND(\n                    AVG(r.rating),\n                    2\n                )\n                    AS stored_avg_rating\n\n            FROM places p\n\n            LEFT JOIN reviews r\n                ON r.place_id = p.place_id\n\n            GROUP BY p.place_id\n\n            ORDER BY p.title\n            ').fetchall()

    def place_stats(self, place_id: str):
        """
        Return basic statistics for one place.
        """
        summary = self.conn.execute('\n            SELECT\n\n                p.place_id,\n                p.title,\n                p.category,\n\n                p.city,\n                p.state,\n                p.country_code,\n\n                p.total_score\n                    AS google_score,\n\n                p.reviews_count\n                    AS google_review_count,\n\n                COUNT(r.review_id)\n                    AS stored_reviews,\n\n                ROUND(\n                    AVG(r.rating),\n                    2\n                )\n                    AS stored_avg_rating,\n\n                MIN(r.published_at)\n                    AS oldest_review,\n\n                MAX(r.published_at)\n                    AS newest_review\n\n            FROM places p\n\n            LEFT JOIN reviews r\n                ON r.place_id = p.place_id\n\n            WHERE p.place_id = ?\n\n            GROUP BY p.place_id\n            ', (place_id,)).fetchone()
        distribution = self.conn.execute('\n            SELECT\n\n                rating,\n\n                COUNT(*)\n                    AS count\n\n            FROM reviews\n\n            WHERE place_id = ?\n\n            GROUP BY rating\n\n            ORDER BY rating DESC\n            ', (place_id,)).fetchall()
        return (summary, distribution)

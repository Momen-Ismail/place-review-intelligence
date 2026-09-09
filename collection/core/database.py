from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from config import DATABASE_PATH


class ReviewDatabase:
    def __init__(
        self,
        path: Path | str = DATABASE_PATH,
    ):
        self.path = Path(path)

        # Make sure the data folder exists.
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Connect to SQLite.
        self.conn = sqlite3.connect(self.path)

        # Allows:
        # row["title"]
        # instead of:
        # row[0]
        self.conn.row_factory = sqlite3.Row

        # Enable foreign-key support.
        self.conn.execute(
            "PRAGMA foreign_keys = ON;"
        )

        self._create_tables()
        self._upgrade_existing_tables()
        self._create_indexes()

    def close(self):
        """
        Close the SQLite connection.
        """
        self.conn.close()

    # =========================================================
    # DATABASE STRUCTURE
    # =========================================================

    def _create_tables(self):
        """
        Create the main tables if this is a new database.
        """

        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS places (
                place_id TEXT PRIMARY KEY,

                cid TEXT,
                fid TEXT,
                kgmid TEXT,
                business_profile_id TEXT,

                title TEXT,
                category TEXT,
                categories_json TEXT,

                address TEXT,
                neighborhood TEXT,
                street TEXT,
                city TEXT,
                state TEXT,
                country_code TEXT,
                postal_code TEXT,

                latitude REAL,
                longitude REAL,

                total_score REAL,
                reviews_count INTEGER,

                price TEXT,

                google_maps_url TEXT,
                input_url TEXT,

                image_url TEXT,

                hotel_stars REAL,

                permanently_closed INTEGER,
                temporarily_closed INTEGER,
                is_advertisement INTEGER,

                updated_at TEXT
            );


            CREATE TABLE IF NOT EXISTS reviews (
                review_id TEXT PRIMARY KEY,

                place_id TEXT NOT NULL,

                source TEXT,

                reviewer_id TEXT,
                reviewer_name TEXT,
                reviewer_url TEXT,
                reviewer_number_of_reviews INTEGER,
                reviewer_photo_url TEXT,
                is_local_guide INTEGER,

                review_url TEXT,

                rating REAL,

                text_original TEXT,
                text_translated TEXT,

                published_at TEXT,
                published_relative TEXT,

                visited_in TEXT,

                original_language TEXT,
                translated_language TEXT,

                likes_count INTEGER,

                owner_response_text TEXT,
                owner_response_date TEXT,

                review_context_json TEXT,
                detailed_ratings_json TEXT,
                review_images_json TEXT,

                scraped_at TEXT,

                raw_json TEXT,

                FOREIGN KEY(place_id)
                    REFERENCES places(place_id)
                    ON DELETE CASCADE
            );
            """
        )

        self.conn.commit()

    # =========================================================
    # AUTOMATIC DATABASE UPGRADES
    # =========================================================

    def _get_existing_columns(
        self,
        table_name: str,
    ) -> set[str]:
        """
        Return all column names currently existing
        in a SQLite table.
        """

        rows = self.conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()

        return {
            row["name"]
            for row in rows
        }

    def _add_missing_columns(
        self,
        table_name: str,
        required_columns: dict[str, str],
    ):
        """
        Add newly introduced columns to an older database.

        This allows us to improve the project later without
        deleting reviews.db every time the schema changes.
        """

        existing_columns = self._get_existing_columns(
            table_name
        )

        for column_name, column_type in required_columns.items():

            if column_name in existing_columns:
                continue

            self.conn.execute(
                f"""
                ALTER TABLE {table_name}
                ADD COLUMN {column_name} {column_type}
                """
            )

            print(
                f"Database upgraded: "
                f"added {table_name}.{column_name}"
            )

        self.conn.commit()

    def _upgrade_existing_tables(self):
        """
        Upgrade databases created by older versions
        of this project.
        """

        place_columns = {
            "cid": "TEXT",
            "fid": "TEXT",
            "kgmid": "TEXT",
            "business_profile_id": "TEXT",

            "title": "TEXT",
            "category": "TEXT",
            "categories_json": "TEXT",

            "address": "TEXT",
            "neighborhood": "TEXT",
            "street": "TEXT",
            "city": "TEXT",
            "state": "TEXT",
            "country_code": "TEXT",
            "postal_code": "TEXT",

            "latitude": "REAL",
            "longitude": "REAL",

            "total_score": "REAL",
            "reviews_count": "INTEGER",

            "price": "TEXT",

            "google_maps_url": "TEXT",
            "input_url": "TEXT",

            "image_url": "TEXT",

            "hotel_stars": "REAL",

            "permanently_closed": "INTEGER",
            "temporarily_closed": "INTEGER",
            "is_advertisement": "INTEGER",

            "updated_at": "TEXT",
        }

        review_columns = {
            "source": "TEXT",

            # Reviewer Google profile information
            "reviewer_id": "TEXT",
            "reviewer_name": "TEXT",
            "reviewer_url": "TEXT",
            "reviewer_number_of_reviews": "INTEGER",
            "reviewer_photo_url": "TEXT",
            "is_local_guide": "INTEGER",

            "review_url": "TEXT",

            "rating": "REAL",

            "text_original": "TEXT",
            "text_translated": "TEXT",

            "published_at": "TEXT",
            "published_relative": "TEXT",

            "visited_in": "TEXT",

            "original_language": "TEXT",
            "translated_language": "TEXT",

            "likes_count": "INTEGER",

            "owner_response_text": "TEXT",
            "owner_response_date": "TEXT",

            "review_context_json": "TEXT",
            "detailed_ratings_json": "TEXT",
            "review_images_json": "TEXT",

            "scraped_at": "TEXT",

            # Complete original Apify record
            "raw_json": "TEXT",
        }

        self._add_missing_columns(
            "places",
            place_columns,
        )

        self._add_missing_columns(
            "reviews",
            review_columns,
        )

    # =========================================================
    # INDEXES
    # =========================================================

    def _create_indexes(self):
        """
        Create indexes used frequently during analysis.

        These become useful when the database contains
        thousands or hundreds of thousands of reviews.
        """

        self.conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_reviews_place_id
            ON reviews(place_id);


            CREATE INDEX IF NOT EXISTS idx_reviews_published_at
            ON reviews(published_at);


            CREATE INDEX IF NOT EXISTS idx_reviews_rating
            ON reviews(rating);


            CREATE INDEX IF NOT EXISTS idx_reviews_language
            ON reviews(original_language);


            CREATE INDEX IF NOT EXISTS idx_reviews_reviewer_id
            ON reviews(reviewer_id);
            """
        )

        self.conn.commit()

    # =========================================================
    # PLACES
    # =========================================================

    def upsert_places(
        self,
        places: Iterable[dict],
    ) -> int:
        """
        Insert new places.

        If the place already exists,
        refresh its information.
        """

        rows = list(places)

        if not rows:
            return 0

        sql = """
        INSERT INTO places (
            place_id,

            cid,
            fid,
            kgmid,
            business_profile_id,

            title,
            category,
            categories_json,

            address,
            neighborhood,
            street,
            city,
            state,
            country_code,
            postal_code,

            latitude,
            longitude,

            total_score,
            reviews_count,

            price,

            google_maps_url,
            input_url,

            image_url,

            hotel_stars,

            permanently_closed,
            temporarily_closed,
            is_advertisement,

            updated_at
        )
        VALUES (
            :place_id,

            :cid,
            :fid,
            :kgmid,
            :business_profile_id,

            :title,
            :category,
            :categories_json,

            :address,
            :neighborhood,
            :street,
            :city,
            :state,
            :country_code,
            :postal_code,

            :latitude,
            :longitude,

            :total_score,
            :reviews_count,

            :price,

            :google_maps_url,
            :input_url,

            :image_url,

            :hotel_stars,

            :permanently_closed,
            :temporarily_closed,
            :is_advertisement,

            :updated_at
        )

        ON CONFLICT(place_id)
        DO UPDATE SET

            cid = excluded.cid,
            fid = excluded.fid,
            kgmid = excluded.kgmid,
            business_profile_id = excluded.business_profile_id,

            title = excluded.title,
            category = excluded.category,
            categories_json = excluded.categories_json,

            address = excluded.address,
            neighborhood = excluded.neighborhood,
            street = excluded.street,
            city = excluded.city,
            state = excluded.state,
            country_code = excluded.country_code,
            postal_code = excluded.postal_code,

            latitude = excluded.latitude,
            longitude = excluded.longitude,

            total_score = excluded.total_score,
            reviews_count = excluded.reviews_count,

            price = excluded.price,

            google_maps_url = excluded.google_maps_url,
            input_url = excluded.input_url,

            image_url = excluded.image_url,

            hotel_stars = excluded.hotel_stars,

            permanently_closed = excluded.permanently_closed,
            temporarily_closed = excluded.temporarily_closed,
            is_advertisement = excluded.is_advertisement,

            updated_at = excluded.updated_at
        """

        self.conn.executemany(
            sql,
            rows,
        )

        self.conn.commit()

        return len(rows)

    # =========================================================
    # REVIEWS
    # =========================================================

    def upsert_reviews(
        self,
        reviews: Iterable[dict],
    ) -> tuple[int, int]:
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
            return 0, 0

        inserted = 0
        updated = 0

        sql = """
        INSERT INTO reviews (
            review_id,
            place_id,

            source,

            reviewer_id,
            reviewer_name,
            reviewer_url,
            reviewer_number_of_reviews,
            reviewer_photo_url,
            is_local_guide,

            review_url,

            rating,

            text_original,
            text_translated,

            published_at,
            published_relative,

            visited_in,

            original_language,
            translated_language,

            likes_count,

            owner_response_text,
            owner_response_date,

            review_context_json,
            detailed_ratings_json,
            review_images_json,

            scraped_at,

            raw_json
        )
        VALUES (
            :review_id,
            :place_id,

            :source,

            :reviewer_id,
            :reviewer_name,
            :reviewer_url,
            :reviewer_number_of_reviews,
            :reviewer_photo_url,
            :is_local_guide,

            :review_url,

            :rating,

            :text_original,
            :text_translated,

            :published_at,
            :published_relative,

            :visited_in,

            :original_language,
            :translated_language,

            :likes_count,

            :owner_response_text,
            :owner_response_date,

            :review_context_json,
            :detailed_ratings_json,
            :review_images_json,

            :scraped_at,

            :raw_json
        )

        ON CONFLICT(review_id)
        DO UPDATE SET

            place_id = excluded.place_id,

            source = excluded.source,

            reviewer_id = excluded.reviewer_id,
            reviewer_name = excluded.reviewer_name,
            reviewer_url = excluded.reviewer_url,
            reviewer_number_of_reviews =
                excluded.reviewer_number_of_reviews,
            reviewer_photo_url =
                excluded.reviewer_photo_url,
            is_local_guide =
                excluded.is_local_guide,

            review_url = excluded.review_url,

            rating = excluded.rating,

            text_original = excluded.text_original,
            text_translated = excluded.text_translated,

            published_at = excluded.published_at,
            published_relative = excluded.published_relative,

            visited_in = excluded.visited_in,

            original_language = excluded.original_language,
            translated_language = excluded.translated_language,

            likes_count = excluded.likes_count,

            owner_response_text = excluded.owner_response_text,
            owner_response_date = excluded.owner_response_date,

            review_context_json = excluded.review_context_json,
            detailed_ratings_json = excluded.detailed_ratings_json,
            review_images_json = excluded.review_images_json,

            scraped_at = excluded.scraped_at,

            raw_json = excluded.raw_json
        """

        for row in rows:

            existed = self.conn.execute(
                """
                SELECT 1
                FROM reviews
                WHERE review_id = ?
                """,
                (
                    row["review_id"],
                ),
            ).fetchone()

            self.conn.execute(
                sql,
                row,
            )

            if existed:
                updated += 1
            else:
                inserted += 1

        self.conn.commit()

        return inserted, updated

    # =========================================================
    # PLACE LIST
    # =========================================================

    def list_places(self):
        """
        Return all stored places together with
        basic review statistics.
        """

        return self.conn.execute(
            """
            SELECT
                p.*,

                COUNT(r.review_id)
                    AS stored_reviews,

                ROUND(
                    AVG(r.rating),
                    2
                )
                    AS stored_avg_rating

            FROM places p

            LEFT JOIN reviews r
                ON r.place_id = p.place_id

            GROUP BY p.place_id

            ORDER BY p.title
            """
        ).fetchall()

    # =========================================================
    # PLACE STATISTICS
    # =========================================================

    def place_stats(
        self,
        place_id: str,
    ):
        """
        Return basic statistics for one place.
        """

        summary = self.conn.execute(
            """
            SELECT

                p.place_id,
                p.title,
                p.category,

                p.city,
                p.state,
                p.country_code,

                p.total_score
                    AS google_score,

                p.reviews_count
                    AS google_review_count,

                COUNT(r.review_id)
                    AS stored_reviews,

                ROUND(
                    AVG(r.rating),
                    2
                )
                    AS stored_avg_rating,

                MIN(r.published_at)
                    AS oldest_review,

                MAX(r.published_at)
                    AS newest_review

            FROM places p

            LEFT JOIN reviews r
                ON r.place_id = p.place_id

            WHERE p.place_id = ?

            GROUP BY p.place_id
            """,
            (
                place_id,
            ),
        ).fetchone()

        distribution = self.conn.execute(
            """
            SELECT

                rating,

                COUNT(*)
                    AS count

            FROM reviews

            WHERE place_id = ?

            GROUP BY rating

            ORDER BY rating DESC
            """,
            (
                place_id,
            ),
        ).fetchall()

        return summary, distribution
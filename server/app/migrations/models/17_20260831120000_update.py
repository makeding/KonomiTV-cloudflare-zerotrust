from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "series_aliases" (
            "normalized_title" VARCHAR(512) NOT NULL PRIMARY KEY,
            "series_id" INT NOT NULL REFERENCES "series" ("id") ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS "idx_series_aliases_series_id" ON "series_aliases" ("series_id");

        -- 統合対象に限らず全 Series の主タイトルを登録し、以後の統合を同じ表で扱う。
        INSERT INTO "series_aliases" ("normalized_title", "series_id")
        SELECT "normalized_title", "id" FROM "series";

        -- 同じ Bangumi 条目を持つ既存 Series は、最も ID が小さいレコードへ自動的に収束させる。
        CREATE TEMPORARY TABLE "series_merge_map" (
            "source_series_id" INT NOT NULL PRIMARY KEY,
            "canonical_series_id" INT NOT NULL
        );
        INSERT INTO "series_merge_map" ("source_series_id", "canonical_series_id")
        SELECT "id", "canonical_series_id"
        FROM (
            SELECT
                "id",
                MIN("id") OVER (PARTITION BY "bangumi_subject_id") AS "canonical_series_id"
            FROM "series"
            WHERE "bangumi_subject_id" IS NOT NULL
        )
        WHERE "id" != "canonical_series_id";

        UPDATE "series_aliases"
        SET "series_id" = (
            SELECT "canonical_series_id"
            FROM "series_merge_map"
            WHERE "source_series_id" = "series_aliases"."series_id"
        )
        WHERE "series_id" IN (SELECT "source_series_id" FROM "series_merge_map");

        -- 放送期間は統合後の Series とチャンネルごとに最も古い 1 件を残す。
        CREATE TEMPORARY TABLE "series_period_merge_map" (
            "source_period_id" INT NOT NULL PRIMARY KEY,
            "canonical_period_id" INT NOT NULL,
            "canonical_series_id" INT NOT NULL,
            "merged_start_date" DATE NOT NULL,
            "merged_end_date" DATE NOT NULL
        );
        INSERT INTO "series_period_merge_map" (
            "source_period_id",
            "canonical_period_id",
            "canonical_series_id",
            "merged_start_date",
            "merged_end_date"
        )
        SELECT
            "periods"."id",
            MIN("periods"."id") OVER (
                PARTITION BY COALESCE("mapping"."canonical_series_id", "periods"."series_id"), "periods"."channel_id"
            ),
            COALESCE("mapping"."canonical_series_id", "periods"."series_id"),
            MIN("periods"."start_date") OVER (
                PARTITION BY COALESCE("mapping"."canonical_series_id", "periods"."series_id"), "periods"."channel_id"
            ),
            MAX("periods"."end_date") OVER (
                PARTITION BY COALESCE("mapping"."canonical_series_id", "periods"."series_id"), "periods"."channel_id"
            )
        FROM "series_broadcast_periods" AS "periods"
        LEFT JOIN "series_merge_map" AS "mapping" ON "mapping"."source_series_id" = "periods"."series_id"
        WHERE "periods"."series_id" IN (
            SELECT "source_series_id" FROM "series_merge_map"
            UNION
            SELECT "canonical_series_id" FROM "series_merge_map"
        );

        UPDATE "recorded_programs"
        SET "series_broadcast_period_id" = (
            SELECT "canonical_period_id"
            FROM "series_period_merge_map"
            WHERE "source_period_id" = "recorded_programs"."series_broadcast_period_id"
        )
        WHERE "series_broadcast_period_id" IN (SELECT "source_period_id" FROM "series_period_merge_map");

        DELETE FROM "series_broadcast_periods"
        WHERE "id" IN (
            SELECT "source_period_id"
            FROM "series_period_merge_map"
            WHERE "source_period_id" != "canonical_period_id"
        );

        UPDATE "series_broadcast_periods"
        SET
            "series_id" = (
                SELECT "canonical_series_id"
                FROM "series_period_merge_map"
                WHERE "canonical_period_id" = "series_broadcast_periods"."id"
                LIMIT 1
            ),
            "start_date" = (
                SELECT "merged_start_date"
                FROM "series_period_merge_map"
                WHERE "canonical_period_id" = "series_broadcast_periods"."id"
                LIMIT 1
            ),
            "end_date" = (
                SELECT "merged_end_date"
                FROM "series_period_merge_map"
                WHERE "canonical_period_id" = "series_broadcast_periods"."id"
                LIMIT 1
            )
        WHERE "id" IN (SELECT "canonical_period_id" FROM "series_period_merge_map");

        UPDATE "recorded_programs"
        SET
            "series_id" = (
                SELECT "canonical_series_id"
                FROM "series_merge_map"
                WHERE "source_series_id" = "recorded_programs"."series_id"
            ),
            "series_title" = (
                SELECT "canonical"."title"
                FROM "series_merge_map"
                INNER JOIN "series" AS "canonical" ON "canonical"."id" = "series_merge_map"."canonical_series_id"
                WHERE "series_merge_map"."source_series_id" = "recorded_programs"."series_id"
            )
        WHERE "series_id" IN (SELECT "source_series_id" FROM "series_merge_map");

        DELETE FROM "series" WHERE "id" IN (SELECT "source_series_id" FROM "series_merge_map");
        DROP TABLE "series_period_merge_map";
        DROP TABLE "series_merge_map";

        CREATE UNIQUE INDEX IF NOT EXISTS "series_bangumi_subject_id"
        ON "series" ("bangumi_subject_id")
        WHERE "bangumi_subject_id" IS NOT NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "series_bangumi_subject_id";
        DROP INDEX IF EXISTS "idx_series_aliases_series_id";
        DROP TABLE IF EXISTS "series_aliases";
    """

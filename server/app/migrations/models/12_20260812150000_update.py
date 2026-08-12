from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "series" ADD COLUMN "normalized_title" VARCHAR(512) NOT NULL DEFAULT '';
        UPDATE "series" SET "normalized_title" = 'legacy:' || "id" WHERE "normalized_title" = '';
        CREATE UNIQUE INDEX "series_normalized_title" ON "series" ("normalized_title");
        CREATE UNIQUE INDEX "series_broadcast_period_unique" ON "series_broadcast_periods" ("series_id", "channel_id");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "series_broadcast_period_unique";
        DROP INDEX IF EXISTS "series_normalized_title";
        ALTER TABLE "series" DROP COLUMN "normalized_title";
    """

from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "device_auth" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            "device_code_hash" VARCHAR(64) NOT NULL UNIQUE,
            "user_code" VARCHAR(8) NOT NULL UNIQUE,
            "device_name" TEXT NOT NULL,
            "expires_at" TIMESTAMP NOT NULL,
            "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "user_id" INT REFERENCES "users" ("id") ON DELETE CASCADE
        );
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return 'DROP TABLE IF EXISTS "device_auth";'

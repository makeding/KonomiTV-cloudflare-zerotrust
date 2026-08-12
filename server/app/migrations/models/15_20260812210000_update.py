from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "recorded_programs" ADD COLUMN "bangumi_subject_id" INT;
        ALTER TABLE "recorded_programs" ADD COLUMN "bangumi_episode_id" INT;
        CREATE TABLE IF NOT EXISTS "bangumi_episode_completions" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            "bangumi_episode_id" INT NOT NULL,
            "completed_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "source_recorded_program_id" INT REFERENCES "recorded_programs" ("id") ON DELETE SET NULL,
            "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
        );
        CREATE UNIQUE INDEX "bangumi_episode_completion_unique"
            ON "bangumi_episode_completions" ("user_id", "bangumi_episode_id");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "bangumi_episode_completion_unique";
        DROP TABLE IF EXISTS "bangumi_episode_completions";
        ALTER TABLE "recorded_programs" DROP COLUMN "bangumi_episode_id";
        ALTER TABLE "recorded_programs" DROP COLUMN "bangumi_subject_id";
    """

from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" ADD COLUMN "bangumi_user_id" INT;
        ALTER TABLE "users" ADD COLUMN "bangumi_user_name" TEXT;
        ALTER TABLE "users" ADD COLUMN "bangumi_user_nickname" TEXT;
        ALTER TABLE "users" ADD COLUMN "bangumi_user_avatar_url" TEXT;
        ALTER TABLE "users" ADD COLUMN "bangumi_access_token" TEXT;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" DROP COLUMN "bangumi_user_id";
        ALTER TABLE "users" DROP COLUMN "bangumi_user_name";
        ALTER TABLE "users" DROP COLUMN "bangumi_user_nickname";
        ALTER TABLE "users" DROP COLUMN "bangumi_user_avatar_url";
        ALTER TABLE "users" DROP COLUMN "bangumi_access_token";
    """

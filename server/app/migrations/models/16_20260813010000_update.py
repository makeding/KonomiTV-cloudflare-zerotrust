from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "series" ADD COLUMN "bangumi_subject_id" INT;
        ALTER TABLE "series" ADD COLUMN "bangumi_subject_name" TEXT;
        ALTER TABLE "series" ADD COLUMN "bangumi_subject_name_cn" TEXT;
        ALTER TABLE "series" ADD COLUMN "bangumi_subject_summary" TEXT;
        ALTER TABLE "series" ADD COLUMN "bangumi_subject_image_url" TEXT;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "series" DROP COLUMN "bangumi_subject_image_url";
        ALTER TABLE "series" DROP COLUMN "bangumi_subject_summary";
        ALTER TABLE "series" DROP COLUMN "bangumi_subject_name_cn";
        ALTER TABLE "series" DROP COLUMN "bangumi_subject_name";
        ALTER TABLE "series" DROP COLUMN "bangumi_subject_id";
    """

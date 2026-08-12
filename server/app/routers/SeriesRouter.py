
import json
import re
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Path, Query, status
from tortoise import connections

from app import logging, schemas
from app.models.Series import Series


# ルーター
router = APIRouter(
    tags = ['Series'],
    prefix = '/api/series',
)

# ページングで一度に取得するシリーズ番組の数
PAGE_SIZE = 50

# EPG の公式情報欄から番組公式サイトだけを選び、SNS や配信サービスへのリンクは除外する。
OFFICIAL_WEBSITE_URL_PATTERN = re.compile(r'https?://[^\s<>"\'）)】]+')
NON_OFFICIAL_WEBSITE_HOSTS = {
    'bs4.jp',
    'instagram.com',
    'tiktok.com',
    'tver.jp',
    'video.tv-tokyo.co.jp',
    'x.com',
    'youtube.com',
}


def ExtractOfficialWebsiteURL(sources: list[str]) -> str | None:
    """
    EPG の公式情報欄から作品または番組の公式 Web サイトを抽出する。

    Args:
        sources (list[str]): 公式ページ系の detail フィールド値。優先度が高い順に並ぶ。

    Returns:
        str | None: SNS・動画配信サイト以外で最初に見つかった HTTP(S) URL。
    """

    for source in sources:
        for match in OFFICIAL_WEBSITE_URL_PATTERN.finditer(source):
            url = match.group(0).rstrip('。、,;')
            host = url.split('/', maxsplit=3)[2].lower().removeprefix('www.')
            if any(host == excluded_host or host.endswith(f'.{excluded_host}') for excluded_host in NON_OFFICIAL_WEBSITE_HOSTS):
                continue
            return url
    return None


@router.get(
    '',
    summary = 'シリーズ番組一覧 API',
    response_description = 'シリーズ番組のリスト。',
    response_model = schemas.SeriesSummaryList,
)
async def SeriesListAPI(
    order: Annotated[Literal['desc', 'asc'], Query(description='ソート順序 (desc or asc) 。')] = 'desc',
    page: Annotated[int, Query(description='ページ番号。')] = 1,
):
    """
    すべてのシリーズ番組を一度に 50 件ずつ取得する。<br>
    order には "desc" か "asc" を指定する。<br>
    page (ページ番号) には 1 以上の整数を指定する。
    """

    return await GetSeriesSummaries(order=order, page=page)


@router.get(
    '/search',
    summary = 'シリーズ番組検索 API',
    response_description = '検索条件に一致するシリーズ番組のリスト。',
    response_model = schemas.SeriesSummaryList,
)
async def SeriesSearchAPI(
    query: Annotated[str, Query(description='検索キーワード。title または description のいずれかに部分一致するシリーズ番組を検索する。')] = '',
    order: Annotated[Literal['desc', 'asc'], Query(description='ソート順序 (desc or asc) 。')] = 'desc',
    page: Annotated[int, Query(description='ページ番号。')] = 1,
):
    """
    指定されたキーワードでシリーズ番組を一度に 50 件ずつ検索する。<br>
    キーワードは title または description のいずれかに部分一致するシリーズ番組を検索する。<br>
    order には "desc" か "asc" を指定する。<br>
    page (ページ番号) には 1 以上の整数を指定する。
    """

    return await GetSeriesSummaries(query=query, order=order, page=page)


async def GetSeriesSummaries(
    query: str = '',
    order: Literal['desc', 'asc'] = 'desc',
    page: int = 1,
    series_id: int | None = None,
) -> schemas.SeriesSummaryList:
    """シリーズ一覧用の軽量な概要だけを取得する。"""

    filter_clauses: list[str] = []
    filter_params: list[Any] = []
    if query:
        filter_clauses.append('(LOWER(s.title) LIKE LOWER(?) OR LOWER(s.description) LIKE LOWER(?))')
        filter_params.extend([f'%{query}%', f'%{query}%'])
    if series_id is not None:
        filter_clauses.append('s.id = ?')
        filter_params.append(series_id)
    where_clause = f'WHERE {" AND ".join(filter_clauses)}' if filter_clauses else ''

    series_query = f"""
        SELECT
            s.id,
            s.title,
            s.description,
            s.genres,
            s.bangumi_subject_id,
            s.bangumi_subject_name,
            s.bangumi_subject_name_cn,
            s.bangumi_subject_summary,
            s.bangumi_subject_image_url,
            COALESCE((
                SELECT JSON_GROUP_ARRAY(recent_recorded_programs.id)
                FROM (
                    SELECT rp_thumbnail.id
                    FROM recorded_programs rp_thumbnail
                    WHERE rp_thumbnail.series_id = s.id
                    ORDER BY rp_thumbnail.start_time DESC, rp_thumbnail.id DESC
                    LIMIT 3
                ) AS recent_recorded_programs
            ), '[]') AS thumbnail_recorded_program_ids,
            COALESCE((
                SELECT JSON_GROUP_ARRAY(series_channels.channel_id)
                FROM (
                    SELECT rp_channel.channel_id
                    FROM recorded_programs rp_channel
                    WHERE rp_channel.series_id = s.id
                      AND rp_channel.channel_id IS NOT NULL
                    GROUP BY rp_channel.channel_id
                    ORDER BY MAX(rp_channel.start_time) DESC
                ) AS series_channels
            ), '[]') AS channel_ids,
            COALESCE((
                SELECT JSON_GROUP_ARRAY(official_details.value)
                FROM (
                    SELECT DISTINCT detail_entry.value AS value,
                        CASE detail_entry.key
                            WHEN 'ホームページ' THEN 1
                            WHEN '公式サイト' THEN 2
                            WHEN '公式HP' THEN 3
                            WHEN '公式ページ' THEN 4
                            WHEN '番組HP' THEN 5
                            WHEN '番組ホームページ' THEN 6
                            ELSE 7
                        END AS priority
                    FROM recorded_programs rp_website, JSON_EACH(rp_website.detail) AS detail_entry
                    WHERE rp_website.series_id = s.id
                      AND detail_entry.key IN (
                          'ホームページ', '公式サイト', '公式HP', '公式ページ', '番組HP',
                          '番組ホームページ'
                      )
                      AND detail_entry.value LIKE '%http%'
                    ORDER BY priority, rp_website.start_time DESC
                ) AS official_details
            ), '[]') AS official_website_sources,
            COUNT(rp.id) AS recorded_programs_count,
            MAX(rv.file_created_at) AS latest_video_file_created_at,
            s.created_at,
            s.updated_at
        FROM series s
        LEFT JOIN recorded_programs rp ON rp.series_id = s.id
        LEFT JOIN recorded_videos rv ON rv.recorded_program_id = rp.id
        {where_clause}
        GROUP BY s.id
        ORDER BY latest_video_file_created_at {'DESC' if order == 'desc' else 'ASC'},
                 s.id {'DESC' if order == 'desc' else 'ASC'}
        LIMIT ? OFFSET ?
    """
    total_query = f'SELECT COUNT(*) AS count FROM series s {where_clause}'

    try:
        conn = connections.get('default')
        rows = await conn.execute_query(
            series_query,
            [*filter_params, str(PAGE_SIZE), str((page - 1) * PAGE_SIZE)],
        )
        total_result = await conn.execute_query(total_query, filter_params)

        series_list: list[schemas.SeriesSummary] = []
        for row in rows[1]:
            genres = json.loads(row['genres'])
            series_list.append(schemas.SeriesSummary.model_validate({
                **row,
                'genres': genres,
                'thumbnail_recorded_program_ids': json.loads(row['thumbnail_recorded_program_ids']),
                'channel_ids': json.loads(row['channel_ids']),
                'official_website_url': ExtractOfficialWebsiteURL(json.loads(row['official_website_sources'])),
            }))

        return schemas.SeriesSummaryList(
            total = total_result[1][0]['count'],
            series_list = series_list,
        )
    except Exception as ex:
        logging.error('[GetSeriesSummaries] Failed to execute raw SQL query:', exc_info=ex)
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = 'Failed to execute raw SQL query',
        )


@router.get(
    '/{series_id}/summary',
    summary = 'シリーズ番組概要 API',
    response_description = 'シリーズ番組の概要。',
    response_model = schemas.SeriesSummary,
)
async def SeriesSummaryAPI(
    series_id: Annotated[int, Path(description='シリーズ番組の ID 。')],
):
    """指定されたシリーズの概要だけを取得する。"""

    result = await GetSeriesSummaries(series_id=series_id)
    if not result.series_list:
        logging.warning(f'[SeriesRouter][SeriesSummaryAPI] Specified series_id was not found. [series_id: {series_id}]')
        raise HTTPException(
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail = 'Specified series_id was not found',
        )
    return result.series_list[0]


@router.get(
    '/{series_id}',
    summary = 'シリーズ番組 API',
    response_description = 'シリーズ番組。',
    response_model = schemas.Series,
)
async def SeriesAPI(
    series_id: Annotated[int, Path(description='シリーズ番組の ID 。')],
):
    """
    指定されたシリーズ番組を取得する。
    """

    series = await Series.all() \
        .select_related('broadcast_periods') \
        .select_related('broadcast_periods__channel') \
        .select_related('broadcast_periods__recorded_programs') \
        .select_related('broadcast_periods__recorded_programs__recorded_video') \
        .select_related('broadcast_periods__recorded_programs__channel') \
        .get_or_none(id=series_id)
    if series is None:
        logging.warning(f'[SeriesRouter][SeriesAPI] Specified series_id was not found. [series_id: {series_id}]')
        raise HTTPException(
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail = 'Specified series_id was not found',
        )

    return series

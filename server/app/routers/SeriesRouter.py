
import json
import re
from collections import Counter
from datetime import datetime, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Path, Query, status
from tortoise import connections

from app import logging, schemas
from app.constants import JST
from app.metadata.SeriesIndexer import NormalizeSeriesTitle, ParseSeriesTitle
from app.models.Series import Series
from app.utils import ParseDatetimeStringToJST


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
REPEAT_BROADCAST_TITLE_PATTERN = re.compile(r'(?:\[再\]|【再】|再放送)')
ON_AIR_SERIES_GENRES = {'アニメ・特撮', 'ドラマ', 'バラエティ'}


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


@router.get(
    '/on-air',
    summary = '放送中シリーズ一覧 API',
    response_description = 'ローカル録画から推定した曜日別の放送中シリーズ。',
    response_model = schemas.OnAirSeriesList,
)
async def OnAirSeriesListAPI():
    """
    最近の非再放送録画から、各 Series の通常放送曜日と時刻を推定する。

    Returns:
        schemas.OnAirSeriesList: 直近 21 日以内に通常放送がある Series の一覧。
    """

    now = datetime.now(JST)

    # 各 Series の直近 12 件を Python 側で集計できる最小限の列だけ取得する。
    ## 一時的な時刻変更や特番 1 件より、繰り返し現れる通常枠を優先する。
    connection = connections.get('default')
    _, rows = await connection.execute_query(
        """
        SELECT rp.series_id, s.title AS series_title, s.genres, rp.title AS program_title,
               rp.id, rp.channel_id, rp.start_time
        FROM recorded_programs rp
        INNER JOIN series s ON s.id = rp.series_id
        WHERE rp.series_id IS NOT NULL
          AND rp.title NOT LIKE '%[再]%'
          AND rp.title NOT LIKE '%【再】%'
          AND rp.title NOT LIKE '%再放送%'
        ORDER BY rp.series_id, rp.start_time DESC, rp.id DESC
        """,
    )
    samples_by_series: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        series_id = int(row['series_id'])
        samples = samples_by_series.setdefault(series_id, [])
        if len(samples) < 12 and REPEAT_BROADCAST_TITLE_PATTERN.search(str(row['program_title'])) is None:
            samples.append(row)

    # 初回放送直後のアニメ・ドラマ・バラエティも掲載するため、未来 EPG の明示的な話数を
    # SeriesIndexer と同じ規則で解析し、次回放送が確認できる Series を控える。
    _, future_program_rows = await connection.execute_query(
        """
        SELECT title, description, genres, start_time
        FROM programs
        WHERE start_time > ? AND start_time <= ?
        ORDER BY start_time ASC
        """,
        [now.isoformat(), (now + timedelta(days=8)).isoformat()],
    )
    future_schedule_by_series_title: dict[str, datetime] = {}
    for future_program_row in future_program_rows:
        genres = json.loads(str(future_program_row['genres']))
        if {str(genre['major']) for genre in genres}.isdisjoint(ON_AIR_SERIES_GENRES):
            continue
        parsed_title = ParseSeriesTitle(
            str(future_program_row['title']),
            genres,
            str(future_program_row['description']),
        )
        if parsed_title is not None and parsed_title.normalized_title not in future_schedule_by_series_title:
            future_schedule_by_series_title[parsed_title.normalized_title] = ParseDatetimeStringToJST(
                str(future_program_row['start_time']),
            )

    cutoff = now - timedelta(days=21)
    on_air_series: list[schemas.OnAirSeries] = []
    for series_id, samples in samples_by_series.items():
        # 1 件だけでは周期放送か判断できない。また On Air は作品を追うための一覧なので、
        # 単発の映画・紀行・ドキュメンタリーなどは Series に登録されていても対象外にする。
        genres = json.loads(str(samples[0]['genres']))
        major_genres = {str(genre['major']) for genre in genres}
        if major_genres.isdisjoint(ON_AIR_SERIES_GENRES):
            continue
        parsed_samples = [(sample, ParseDatetimeStringToJST(str(sample['start_time']))) for sample in samples]
        latest_broadcast_at = parsed_samples[0][1]
        if latest_broadcast_at < cutoff:
            continue

        # 5 分単位へ丸めて、放送設備由来の数分の揺れを同じ通常枠として数える。
        schedule_counts = Counter(
            (start_time.weekday(), start_time.hour, (start_time.minute // 5) * 5)
            for _, start_time in parsed_samples
        )
        if max(schedule_counts.values()) >= 2:
            weekday, hour, minute = max(
                schedule_counts,
                key = lambda schedule: (
                    schedule_counts[schedule],
                    max(start_time for _, start_time in parsed_samples if (
                        start_time.weekday(), start_time.hour, (start_time.minute // 5) * 5
                    ) == schedule),
                ),
            )
        else:
            # 録画がまだ 1 件しかない新番組は、未来 EPG に同じ作品の次回話数がある場合だけ掲載する。
            next_broadcast_at = future_schedule_by_series_title.get(NormalizeSeriesTitle(str(samples[0]['series_title'])))
            if next_broadcast_at is None:
                continue
            weekday = next_broadcast_at.weekday()
            hour = next_broadcast_at.hour
            minute = (next_broadcast_at.minute // 5) * 5
        on_air_series.append(schemas.OnAirSeries(
            id = series_id,
            title = str(samples[0]['series_title']),
            thumbnail_recorded_program_ids = [int(sample['id']) for sample in samples[:3]],
            channel_ids = list(dict.fromkeys(
                str(sample['channel_id']) for sample in samples if sample['channel_id'] is not None
            )),
            recorded_programs_count = len(samples),
            weekday = weekday,
            broadcast_time = f'{hour:02d}:{minute:02d}',
            latest_broadcast_at = latest_broadcast_at,
        ))
    on_air_series.sort(key=lambda series: (series.weekday, series.broadcast_time, series.title))
    return schemas.OnAirSeriesList(series_list=on_air_series)


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
            COALESCE((
                SELECT NULLIF(TRIM(rp_description.description), '')
                FROM recorded_programs rp_description
                WHERE rp_description.series_id = s.id
                  AND TRIM(rp_description.description) != ''
                ORDER BY rp_description.start_time DESC, rp_description.id DESC
                LIMIT 1
            ), s.description) AS description,
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
    '/{series_id}/list-position',
    summary = 'シリーズ番組一覧位置 API',
    response_description = '指定した一覧条件におけるシリーズ番組のページ番号。',
    response_model = schemas.SeriesListPosition,
)
async def SeriesListPositionAPI(
    series_id: Annotated[int, Path(description='シリーズ番組の ID 。')],
    query: Annotated[str, Query(description='検索キーワード。')] = '',
    order: Annotated[Literal['desc', 'asc'], Query(description='ソート順序 (desc or asc) 。')] = 'desc',
):
    """
    シリーズ一覧と同じ検索・並び順におけるページ番号を取得する。

    Args:
        series_id (int): ページ番号を調べるシリーズ番組の ID。
        query (str): シリーズ一覧に適用する検索キーワード。
        order (Literal['desc', 'asc']): シリーズ一覧に適用するソート順序。

    Returns:
        schemas.SeriesListPosition: 指定したシリーズ番組が含まれるページ番号。
    """

    # 深いリンクから開いた場合も一覧と完全に同じ位置へ到達できるよう、
    # 一覧 API と同じ検索条件・最終録画ファイル日時・ID の順序で行番号を付ける。
    filter_clause = ''
    filter_params: list[Any] = []
    if query:
        filter_clause = 'WHERE LOWER(s.title) LIKE LOWER(?) OR LOWER(s.description) LIKE LOWER(?)'
        filter_params.extend([f'%{query}%', f'%{query}%'])
    direction = 'DESC' if order == 'desc' else 'ASC'
    connection = connections.get('default')
    _, rows = await connection.execute_query(
        f"""
        WITH ordered_series AS (
            SELECT
                s.id,
                ROW_NUMBER() OVER (
                    ORDER BY MAX(rv.file_created_at) {direction}, s.id {direction}
                ) AS row_number
            FROM series s
            LEFT JOIN recorded_programs rp ON rp.series_id = s.id
            LEFT JOIN recorded_videos rv ON rv.recorded_program_id = rp.id
            {filter_clause}
            GROUP BY s.id
        )
        SELECT row_number
        FROM ordered_series
        WHERE id = ?
        """,
        [*filter_params, series_id],
    )
    if len(rows) == 0:
        logging.warning(
            f'[SeriesRouter][SeriesListPositionAPI] Specified series_id was not found in the list. '
            f'[series_id: {series_id}]',
        )
        raise HTTPException(
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail = 'Specified series_id was not found in the list',
        )
    return schemas.SeriesListPosition(page=((int(rows[0]['row_number']) - 1) // PAGE_SIZE) + 1)


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

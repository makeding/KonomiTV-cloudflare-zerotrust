
import json
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
PAGE_SIZE = 30


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
    すべてのシリーズ番組を一度に 30 件ずつ取得する。<br>
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
    指定されたキーワードでシリーズ番組を一度に 30 件ずつ検索する。<br>
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
            COUNT(rp.id) AS recorded_programs_count,
            s.created_at,
            s.updated_at
        FROM series s
        LEFT JOIN recorded_programs rp ON rp.series_id = s.id
        {where_clause}
        GROUP BY s.id
        ORDER BY s.updated_at {'DESC' if order == 'desc' else 'ASC'}, s.id {'DESC' if order == 'desc' else 'ASC'}
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
            series_list.append(schemas.SeriesSummary.model_validate({
                **row,
                'genres': json.loads(row['genres']),
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

from typing import Annotated, Any, cast

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, status

from app import logging, schemas
from app.constants import API_REQUEST_HEADERS, HTTPX_CLIENT
from app.models.User import User
from app.routers.UsersRouter import GetCurrentUser


# ルーター
router = APIRouter(
    tags = ['Bangumi'],
    prefix = '/api/bangumi',
)


@router.post(
    '/auth',
    summary = 'Bangumi 個人アクセストークン認証 API',
    status_code = status.HTTP_204_NO_CONTENT,
)
async def BangumiAuthAPI(
    auth_request: Annotated[schemas.BangumiAuthRequest, Body(description='Bangumi 認証リクエスト。')],
    current_user: Annotated[User, Depends(GetCurrentUser)],
):
    """
    指定された個人アクセストークンで Bangumi 連携を行い、ログイン中のユーザーアカウントへ紐づける。<br>
    JWT エンコードされたアクセストークンが Authorization: Bearer に設定されていないとアクセスできない。

    Args:
        auth_request (schemas.BangumiAuthRequest): Bangumi 個人アクセストークン。
        current_user (User): ログイン中の KonomiTV ユーザー。

    Returns:
        None: 連携が完了した場合。

    Raises:
        HTTPException: Bangumi API への接続、認証、またはレスポンス形式の検証に失敗した場合。
    """

    # 前後の空白や改行はコピー時に混入しやすいため除去してから検証する
    access_token = auth_request.access_token.strip()
    if access_token == '':
        raise HTTPException(
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail = 'Bangumi access token is empty',
        )

    try:
        # 個人アクセストークンに対応するユーザーを取得し、有効なトークンであることとプロフィールを同時に確認する
        async with HTTPX_CLIENT() as httpx_client:
            user_api_response = await httpx_client.get(
                url = 'https://api.bgm.tv/v0/me',
                headers = {**API_REQUEST_HEADERS, 'Authorization': f'Bearer {access_token}'},
            )
    except (httpx.NetworkError, httpx.TimeoutException) as ex:
        logging.error('[BangumiRouter][BangumiAuthAPI] Failed to get user information. (Connection Timeout)')
        raise HTTPException(
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE,
            detail = 'Failed to get Bangumi user information (Connection Timeout)',
        ) from ex

    # 認証エラーは入力したトークンが無効または期限切れであることをクライアントへ明示する
    if user_api_response.status_code == status.HTTP_401_UNAUTHORIZED:
        logging.warning('[BangumiRouter][BangumiAuthAPI] Bangumi access token is invalid or expired.')
        raise HTTPException(
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail = 'Bangumi access token is invalid or expired',
        )

    # Bangumi API 側の障害や仕様外レスポンスを認証エラーと混同しない
    if user_api_response.status_code != status.HTTP_200_OK:
        logging.error(
            f'[BangumiRouter][BangumiAuthAPI] Failed to get user information. (HTTP Error {user_api_response.status_code})',
        )
        raise HTTPException(
            status_code = status.HTTP_502_BAD_GATEWAY,
            detail = f'Failed to get Bangumi user information (HTTP Error {user_api_response.status_code})',
        )

    try:
        user_api_response_json = cast(dict[str, Any], user_api_response.json())
        bangumi_user_id = int(user_api_response_json['id'])
        bangumi_user_name = str(user_api_response_json['username'])
        bangumi_user_nickname = str(user_api_response_json['nickname'])
        avatar = cast(dict[str, Any], user_api_response_json['avatar'])
        bangumi_user_avatar_url = str(avatar['large'])
    except (KeyError, TypeError, ValueError) as ex:
        logging.error('[BangumiRouter][BangumiAuthAPI] Bangumi user information is invalid.', exc_info=ex)
        raise HTTPException(
            status_code = status.HTTP_502_BAD_GATEWAY,
            detail = 'Bangumi user information is invalid',
        ) from ex

    # すべての外部 API 検証が完了してから、公開プロフィールと暗号化済みトークンをまとめて保存する
    current_user.bangumi_user_id = bangumi_user_id
    current_user.bangumi_user_name = bangumi_user_name
    current_user.bangumi_user_nickname = bangumi_user_nickname
    current_user.bangumi_user_avatar_url = bangumi_user_avatar_url
    current_user.bangumi_access_token = current_user.encryptBangumiAccessToken(access_token)
    await current_user.save()

    logging.info(
        f'[BangumiRouter][BangumiAuthAPI] Linked Bangumi account. '
        f'[konomitv_user_id: {current_user.id}, bangumi_user_id: {bangumi_user_id}]',
    )


@router.delete(
    '/logout',
    summary = 'Bangumi アカウント連携解除 API',
    status_code = status.HTTP_204_NO_CONTENT,
)
async def BangumiAccountLogoutAPI(
    current_user: Annotated[User, Depends(GetCurrentUser)],
):
    """
    現在ログイン中のユーザーアカウントに紐づく Bangumi アカウントとの連携を解除する。<br>
    JWT エンコードされたアクセストークンが Authorization: Bearer に設定されていないとアクセスできない。

    Args:
        current_user (User): ログイン中の KonomiTV ユーザー。

    Returns:
        None: 連携解除が完了した場合。
    """

    # 公開プロフィールと認証情報をすべて消去し、部分的な連携状態を残さない
    current_user.bangumi_user_id = None
    current_user.bangumi_user_name = None
    current_user.bangumi_user_nickname = None
    current_user.bangumi_user_avatar_url = None
    current_user.bangumi_access_token = None
    await current_user.save()

    logging.info(f'[BangumiRouter][BangumiAccountLogoutAPI] Unlinked Bangumi account. [konomitv_user_id: {current_user.id}]')

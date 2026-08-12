import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)

from app import logging, schemas
from app.constants import JST
from app.models.User import User
from app.routers.UsersRouter import GetCurrentUser


router = APIRouter(tags=['Remote Control'], prefix='/api/remote')


@dataclass
class RemoteDeviceConnection:
    """HonomiTV Server の現在のプロセスに接続中の Komorebi を表す。"""

    # 複数台のテレビへ正確に配送するため、Komorebi のインストールごとの UUID を保持する。
    device_id: str
    # Web クライアントへ人が判別できる名称を表示するため、接続時に申告された端末名を保持する。
    device_name: str
    # 同じ HonomiTV ユーザー以外から操作されないよう、認証済みユーザー ID を保持する。
    user_id: int
    # REST API から届いたコマンドを現在の受信機へ即時転送するため、WebSocket を保持する。
    websocket: WebSocket
    # 一覧で接続の新鮮さを判断できるよう、最後に受信した時刻を保持する。
    last_seen_at: datetime = field(default_factory=lambda: datetime.now(JST))
    # Web クライアントへ最後に受信した再生状態を返すため、プロセス内だけで状態を保持する。
    state: dict[str, Any] | None = None


# オンライン状態は WebSocket の生存期間だけに対応するため、DB へ保存せずプロセス内で管理する。
REMOTE_DEVICE_CONNECTIONS: dict[tuple[int, str], RemoteDeviceConnection] = {}
REMOTE_DEVICE_CONNECTIONS_LOCK = asyncio.Lock()


def GetBearerToken(authorization: str | None) -> str | None:
    """
    Authorization ヘッダーから Bearer トークンを取得する。

    Args:
        authorization (str | None): Authorization ヘッダーの値。

    Returns:
        str | None: Bearer トークン。形式が異なる場合は None。
    """

    if authorization is None:
        return None
    scheme, separator, token = authorization.partition(' ')
    if separator == '' or scheme.lower() != 'bearer' or token.strip() == '':
        return None
    return token.strip()


@router.websocket('/receiver/{device_id}')
async def RemoteControlReceiverAPI(
    websocket: WebSocket,
    device_id: Annotated[str, Path(min_length=1, max_length=128)],
    device_name: Annotated[str, Query(min_length=1, max_length=100)],
):
    """
    Komorebi をリモート操作対象として現在の HonomiTV Server プロセスへ登録する。

    Args:
        websocket (WebSocket): Komorebi との双方向接続。
        device_id (str): Komorebi のインストールごとに固定された UUID。
        device_name (str): Web クライアントに表示するテレビ名。

    Returns:
        None: WebSocket 切断まで接続と状態更新を処理する。
    """

    token = GetBearerToken(websocket.headers.get('Authorization'))
    if token is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason='Authorization required')
        return
    try:
        current_user = await GetCurrentUser(token)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason='Invalid authorization')
        return

    await websocket.accept()
    connection = RemoteDeviceConnection(
        device_id=device_id,
        device_name=device_name,
        user_id=current_user.id,
        websocket=websocket,
    )
    connection_key = (current_user.id, device_id)
    async with REMOTE_DEVICE_CONNECTIONS_LOCK:
        previous_connection = REMOTE_DEVICE_CONNECTIONS.get(connection_key)
        REMOTE_DEVICE_CONNECTIONS[connection_key] = connection
    if previous_connection is not None and previous_connection.websocket is not websocket:
        await previous_connection.websocket.close(code=status.WS_1000_NORMAL_CLOSURE, reason='Replaced by a new connection')

    logging.info(f'[RemoteControlRouter] Remote device connected. [device_id: {device_id}, user_id: {current_user.id}]')
    try:
        while True:
            message = await websocket.receive_json()
            connection.last_seen_at = datetime.now(JST)
            if message.get('type') == 'State':
                connection.state = message
    except WebSocketDisconnect:
        pass
    finally:
        # 新しい再接続で置き換え済みの場合は、新しい接続を古い finally で消さない。
        async with REMOTE_DEVICE_CONNECTIONS_LOCK:
            if REMOTE_DEVICE_CONNECTIONS.get(connection_key) is connection:
                del REMOTE_DEVICE_CONNECTIONS[connection_key]
        logging.info(f'[RemoteControlRouter] Remote device disconnected. [device_id: {device_id}]')


@router.get('/devices', response_model=schemas.RemoteDeviceList)
async def RemoteDeviceListAPI(current_user: Annotated[User, Depends(GetCurrentUser)]):
    """
    現在ログイン中のユーザーが操作できるオンライン Komorebi の一覧を取得する。

    Args:
        current_user (User): JWT から解決したログイン中のユーザー。

    Returns:
        schemas.RemoteDeviceList: 現在の Server プロセスへ接続中のテレビ一覧。
    """

    async with REMOTE_DEVICE_CONNECTIONS_LOCK:
        devices = [
            schemas.RemoteDevice(
                device_id=connection.device_id,
                device_name=connection.device_name,
                last_seen_at=connection.last_seen_at,
                state=connection.state,
            )
            for connection in REMOTE_DEVICE_CONNECTIONS.values()
            if connection.user_id == current_user.id
        ]
    return schemas.RemoteDeviceList(devices=sorted(devices, key=lambda device: device.device_name))


@router.post('/devices/{device_id}/commands', response_model=schemas.RemoteCommandAccepted)
async def RemoteCommandAPI(
    command: schemas.RemoteCommand,
    current_user: Annotated[User, Depends(GetCurrentUser)],
    device_id: Annotated[str, Path(min_length=1, max_length=128)],
):
    """
    指定したオンライン Komorebi へコマンドを即時転送する。

    Args:
        command (schemas.RemoteCommand): Komorebi に実行させる操作。
        current_user (User): JWT から解決したログイン中のユーザー。
        device_id (str): 操作対象の Komorebi ID。

    Returns:
        schemas.RemoteCommandAccepted: 転送したコマンドの一意 ID。
    """

    async with REMOTE_DEVICE_CONNECTIONS_LOCK:
        connection = REMOTE_DEVICE_CONNECTIONS.get((current_user.id, device_id))
    if connection is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Remote device is offline')

    command_id = str(uuid.uuid4())
    try:
        await connection.websocket.send_json({
            'type': 'Command',
            'command_id': command_id,
            'command': command.model_dump(mode='json'),
        })
    except (RuntimeError, WebSocketDisconnect) as ex:
        logging.warning(f'[RemoteControlRouter] Failed to send remote command. [device_id: {device_id}]', exc_info=ex)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Remote device is offline') from ex
    return schemas.RemoteCommandAccepted(command_id=command_id)

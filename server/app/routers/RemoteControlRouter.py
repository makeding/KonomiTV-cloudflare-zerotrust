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
# ブラウザ側はユーザーごとの部屋へ参加し、同じユーザーの Komorebi の状態変化だけを受信する。
REMOTE_DEVICE_SUBSCRIBERS: dict[int, set[WebSocket]] = {}
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


def BuildRemoteDeviceList(user_id: int) -> schemas.RemoteDeviceList:
    """
    指定したユーザーが操作できるオンライン Komorebi の一覧を構築する。

    Args:
        user_id (int): 一覧を取得するユーザー ID。

    Returns:
        schemas.RemoteDeviceList: 現在の Server プロセスへ接続中のテレビ一覧。
    """

    devices = [
        schemas.RemoteDevice(
            device_id=connection.device_id,
            device_name=connection.device_name,
            last_seen_at=connection.last_seen_at,
            state=connection.state,
        )
        for connection in REMOTE_DEVICE_CONNECTIONS.values()
        if connection.user_id == user_id
    ]
    return schemas.RemoteDeviceList(devices=sorted(devices, key=lambda device: device.device_name))


async def BroadcastRemoteDeviceList(user_id: int) -> None:
    """
    指定したユーザーのブラウザへ最新のオンライン Komorebi 一覧を配信する。

    Args:
        user_id (int): 配信先となるユーザー ID。

    Returns:
        None: 配信完了後に戻る。
    """

    # WebSocket 送信中に接続一覧の更新を止めないよう、ロック内ではスナップショットだけを作る。
    async with REMOTE_DEVICE_CONNECTIONS_LOCK:
        subscribers = list(REMOTE_DEVICE_SUBSCRIBERS.get(user_id, set()))
        device_list = BuildRemoteDeviceList(user_id)

    disconnected_subscribers: list[WebSocket] = []
    for subscriber in subscribers:
        try:
            await subscriber.send_json(device_list.model_dump(mode='json'))
        except (RuntimeError, WebSocketDisconnect):
            disconnected_subscribers.append(subscriber)

    # 配信中に切断を検出した購読者だけをユーザーの部屋から取り除く。
    if len(disconnected_subscribers) > 0:
        async with REMOTE_DEVICE_CONNECTIONS_LOCK:
            current_subscribers = REMOTE_DEVICE_SUBSCRIBERS.get(user_id)
            if current_subscribers is not None:
                current_subscribers.difference_update(disconnected_subscribers)
                if len(current_subscribers) == 0:
                    del REMOTE_DEVICE_SUBSCRIBERS[user_id]


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
    await BroadcastRemoteDeviceList(current_user.id)
    try:
        while True:
            message = await websocket.receive_json()
            connection.last_seen_at = datetime.now(JST)
            if message.get('type') == 'State':
                connection.state = message
                await BroadcastRemoteDeviceList(current_user.id)
    except WebSocketDisconnect:
        pass
    finally:
        # 新しい再接続で置き換え済みの場合は、新しい接続を古い finally で消さない。
        async with REMOTE_DEVICE_CONNECTIONS_LOCK:
            if REMOTE_DEVICE_CONNECTIONS.get(connection_key) is connection:
                del REMOTE_DEVICE_CONNECTIONS[connection_key]
        logging.info(f'[RemoteControlRouter] Remote device disconnected. [device_id: {device_id}]')
        await BroadcastRemoteDeviceList(current_user.id)


@router.websocket('/devices/ws')
async def RemoteDeviceSubscriberAPI(websocket: WebSocket):
    """
    ブラウザをログイン中ユーザーのリモートデバイス更新部屋へ参加させる。

    Args:
        websocket (WebSocket): Web クライアントとの購読接続。

    Returns:
        None: WebSocket 切断まで最新状態を配信する。
    """

    # ブラウザの WebSocket API は Authorization ヘッダーを設定できないため、接続後の最初のメッセージで認証する。
    await websocket.accept()
    try:
        authentication_message = await asyncio.wait_for(websocket.receive_json(), timeout=10)
    except TimeoutError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason='Authentication required')
        return
    except WebSocketDisconnect:
        return

    token: object = authentication_message.get('token') if authentication_message.get('type') == 'Authenticate' else None
    if not isinstance(token, str):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason='Authentication required')
        return
    try:
        current_user = await GetCurrentUser(token)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason='Invalid authorization')
        return

    # 認証できた接続だけを同じユーザーの部屋へ追加し、初期スナップショットを直ちに返す。
    async with REMOTE_DEVICE_CONNECTIONS_LOCK:
        REMOTE_DEVICE_SUBSCRIBERS.setdefault(current_user.id, set()).add(websocket)
    await BroadcastRemoteDeviceList(current_user.id)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        async with REMOTE_DEVICE_CONNECTIONS_LOCK:
            subscribers = REMOTE_DEVICE_SUBSCRIBERS.get(current_user.id)
            if subscribers is not None:
                subscribers.discard(websocket)
                if len(subscribers) == 0:
                    del REMOTE_DEVICE_SUBSCRIBERS[current_user.id]


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
        return BuildRemoteDeviceList(current_user.id)


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

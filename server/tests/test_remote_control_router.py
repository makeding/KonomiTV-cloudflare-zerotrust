import unittest
from datetime import datetime
from unittest.mock import MagicMock

from app.constants import JST
from app.routers.RemoteControlRouter import (
    REMOTE_DEVICE_CONNECTIONS,
    BuildRemoteDeviceList,
    GetBearerToken,
    RemoteDeviceConnection,
)


class RemoteControlRouterTest(unittest.TestCase):
    def test_bearer_token_is_parsed_case_insensitively(self) -> None:
        """正しい Bearer ヘッダーだけからトークンを取得する。"""

        self.assertEqual(GetBearerToken('Bearer token-value'), 'token-value')
        self.assertEqual(GetBearerToken('bearer token-value'), 'token-value')
        self.assertIsNone(GetBearerToken('Basic token-value'))
        self.assertIsNone(GetBearerToken(None))

    def test_connection_keeps_independent_device_identity_and_state(self) -> None:
        """同じユーザーの複数テレビを device_id ごとに区別できる。"""

        living_room = RemoteDeviceConnection(
            device_id='living-room',
            device_name='リビング',
            user_id=1,
            websocket=MagicMock(),
            last_seen_at=datetime.now(JST),
            state={'type': 'State', 'content_type': 'Live'},
        )
        bedroom = RemoteDeviceConnection(
            device_id='bedroom',
            device_name='寝室',
            user_id=1,
            websocket=MagicMock(),
            last_seen_at=datetime.now(JST),
            state={'type': 'State', 'content_type': 'Recorded'},
        )

        self.assertNotEqual(living_room.device_id, bedroom.device_id)
        self.assertNotEqual(living_room.state, bedroom.state)

    def test_device_list_contains_only_requested_user_room(self) -> None:
        """ユーザーごとの部屋に別ユーザーのテレビを混在させない。"""

        user_device = RemoteDeviceConnection(
            device_id='living-room',
            device_name='リビング',
            user_id=1,
            websocket=MagicMock(),
            last_seen_at=datetime.now(JST),
        )
        other_user_device = RemoteDeviceConnection(
            device_id='bedroom',
            device_name='寝室',
            user_id=2,
            websocket=MagicMock(),
            last_seen_at=datetime.now(JST),
        )

        REMOTE_DEVICE_CONNECTIONS[(1, user_device.device_id)] = user_device
        REMOTE_DEVICE_CONNECTIONS[(2, other_user_device.device_id)] = other_user_device
        try:
            device_list = BuildRemoteDeviceList(1)
        finally:
            REMOTE_DEVICE_CONNECTIONS.clear()

        self.assertEqual([device.device_id for device in device_list.devices], ['living-room'])

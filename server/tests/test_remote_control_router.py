import unittest
from datetime import datetime
from unittest.mock import MagicMock

from app.constants import JST
from app.routers.RemoteControlRouter import GetBearerToken, RemoteDeviceConnection


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

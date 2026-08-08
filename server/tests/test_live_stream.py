import pytest

from app.streams.LiveStream import LiveStream, LiveStreamClient


@pytest.mark.parametrize('client_count', [1, 2, 5])
def test_disconnect_all_notifies_every_client(client_count: int) -> None:
    """disconnectAll() が接続クライアント全員へ終了を通知することを検証する。"""

    live_stream = object.__new__(LiveStream)
    live_stream.live_stream_id = 'gr999-240p'
    live_stream._clients = [LiveStreamClient(live_stream, 'mpegts') for _ in range(client_count)]
    clients = live_stream._clients.copy()

    live_stream.disconnectAll()

    assert live_stream._clients == []
    assert [client._queue.get_nowait() for client in clients] == [None] * client_count


def test_write_stream_data_does_not_skip_clients_after_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """timeout client の削除後も残りの全クライアントへデータを配信することを検証する。"""

    now = 100.0
    monkeypatch.setattr('app.streams.LiveStream.time.time', lambda: now)

    live_stream = object.__new__(LiveStream)
    live_stream.live_stream_id = 'gr999-240p'
    live_stream._stream_data_written_at = 0.0
    live_stream._clients = [LiveStreamClient(live_stream, 'mpegts') for _ in range(4)]
    timed_out_clients = live_stream._clients[::2]
    active_clients = live_stream._clients[1::2]
    for client in timed_out_clients:
        client._stream_data_read_at = now - 11

    live_stream.writeStreamData(b'chunk')

    assert live_stream._clients == active_clients
    assert all(client._queue.empty() is True for client in timed_out_clients)
    assert [client._queue.get_nowait() for client in active_clients] == [b'chunk', b'chunk']

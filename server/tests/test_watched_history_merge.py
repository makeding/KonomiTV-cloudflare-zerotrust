from app.WatchedHistory import MergeWatchedHistory


def history(video_id: int, position: float, created_at: float, updated_at: float) -> dict[str, int | float]:
    return {
        'video_id': video_id,
        'last_playback_position': position,
        'created_at': created_at,
        'updated_at': updated_at,
    }


def test_merge_watched_history_keeps_latest_per_video() -> None:
    merged = MergeWatchedHistory(
        [history(1, 30, 10, 30), history(2, 20, 20, 20)],
        [history(1, 15, 15, 15), history(2, 40, 25, 40), history(3, 50, 50, 50)],
        50,
    )

    assert [(item['video_id'], item['last_playback_position']) for item in merged] == [
        (3, 50),
        (2, 40),
        (1, 30),
    ]
    assert merged[1]['created_at'] == 20


def test_merge_watched_history_limits_oldest_updates() -> None:
    merged = MergeWatchedHistory([], [history(i, i, i + 1, i + 1) for i in range(4)], 2)
    assert [item['video_id'] for item in merged] == [3, 2]

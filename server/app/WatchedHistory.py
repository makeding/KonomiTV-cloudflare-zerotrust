from typing import Any


def MergeWatchedHistory(
    current_history: list[dict[str, Any]],
    incoming_history: list[dict[str, Any]],
    max_count: int,
) -> list[dict[str, Any]]:
    """Merge playback positions per video without overwriting newer device updates."""
    merged = {int(item['video_id']): item for item in current_history}
    for item in incoming_history:
        video_id = int(item['video_id'])
        current = merged.get(video_id)
        if current is None or float(item['updated_at']) >= float(current['updated_at']):
            updated = dict(item)
            if current is not None:
                updated['created_at'] = min(float(current['created_at']), float(item['created_at']))
            merged[video_id] = updated
    return sorted(merged.values(), key=lambda item: float(item['updated_at']), reverse=True)[:max_count]

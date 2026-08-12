from typing import Any


def MergeWatchedHistory(
    current_history: list[dict[str, Any]],
    incoming_history: list[dict[str, Any]],
    max_count: int,
) -> list[dict[str, Any]]:
    """
    端末ごとの視聴履歴を、録画番組 ID ごとの最終更新時刻を基準にマージする。

    Args:
        current_history (list[dict[str, Any]]): サーバーに保存済みの視聴履歴。
        incoming_history (list[dict[str, Any]]): 端末から受信した視聴履歴。
        max_count (int): 保存する視聴履歴の最大件数。

    Returns:
        list[dict[str, Any]]: 最終更新時刻の降順で整理したマージ済み視聴履歴。
    """

    # 同一録画番組の履歴を O(1) で比較できるよう、録画番組 ID ごとの辞書に変換する
    merged = {int(item['video_id']): item for item in current_history}
    for item in incoming_history:
        video_id = int(item['video_id'])
        current = merged.get(video_id)

        # 複数端末から古い再生位置が遅れて届いても、新しい再生位置を巻き戻さない
        if current is None or float(item['updated_at']) >= float(current['updated_at']):
            updated = dict(item)
            if current is not None:
                updated['created_at'] = min(float(current['created_at']), float(item['created_at']))
            merged[video_id] = updated

    # 設定された上限を超えた履歴は、最終更新時刻が古いものから破棄する
    return sorted(merged.values(), key=lambda item: float(item['updated_at']), reverse=True)[:max_count]

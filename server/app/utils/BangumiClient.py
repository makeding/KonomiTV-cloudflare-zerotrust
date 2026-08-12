from __future__ import annotations

import asyncio
from difflib import SequenceMatcher
from typing import Any, cast

import httpx

from app import logging
from app.constants import API_REQUEST_HEADERS, HTTPX_CLIENT
from app.metadata.SeriesIndexer import IsStrictSeriesTitlePrefix, NormalizeSeriesTitle
from app.models.RecordedProgram import RecordedProgram
from app.models.Series import Series
from app.models.User import User


class BangumiClient:
    """KonomiTV の録画番組を Bangumi の条目とエピソードへ照合する。"""

    API_BASE_URL = 'https://api.bgm.tv/v0'
    COLLECTION_PAGE_SIZE = 100
    EPISODE_PAGE_SIZE = 200
    _sync_tasks: set[asyncio.Task[None]] = set()


    @staticmethod
    def parseEpisodeNumber(episode_number: str | None) -> int | None:
        """
        自動同期で安全に扱える単一の正整数話数だけを取得する。

        Args:
            episode_number (str | None): EPG から抽出した話数。

        Returns:
            int | None: 単一の正整数であればその値、それ以外は None。
        """

        if episode_number is None or episode_number.isdecimal() is False:
            return None
        parsed_number = int(episode_number)
        return parsed_number if parsed_number > 0 else None


    @staticmethod
    def _normalizeSubjectTitle(title: str) -> str:
        """
        ローカル Series と Bangumi 条目のタイトル比較キーを生成する。

        Args:
            title (str): ローカル Series または Bangumi 条目のタイトル。

        Returns:
            str: Unicode・空白・末尾句読点の表記差を吸収した比較キー。
        """

        # EPG と Bangumi では長い作品名の末尾句点だけが欠けることがあるため、その差だけを追加で吸収する。
        return NormalizeSeriesTitle(title).rstrip('。.!！?？')


    @classmethod
    def _scoreSubjectTitle(cls, series_title: str, subject: dict[str, Any]) -> int:
        """
        ユーザーの收藏済みアニメからローカル Series の条目候補を採点する。

        Args:
            series_title (str): ローカル Series の表示タイトル。
            subject (dict[str, Any]): Bangumi 收藏一覧に含まれる条目概要。

        Returns:
            int: タイトル一致度。候補外の場合は 0。
        """

        local_title = cls._normalizeSubjectTitle(series_title)
        subject_titles = {
            cls._normalizeSubjectTitle(str(subject.get('name', ''))),
            cls._normalizeSubjectTitle(str(subject.get('name_cn', ''))),
        } - {''}
        if len(subject_titles) == 0:
            return 0
        if local_title in subject_titles:
            return 100

        # 放送局が副題を省略した表記は、安全な副題境界を持つ場合だけ弱い候補として認める。
        if any(
            IsStrictSeriesTitlePrefix(local_title, subject_title) or
            IsStrictSeriesTitlePrefix(subject_title, local_title)
            for subject_title in subject_titles
        ):
            return 80

        # 收藏一覧に絞った後も僅かな記号・転写差が残るため、長いタイトル同士だけ保守的に類似判定する。
        similarity = max(
            (SequenceMatcher(None, local_title, subject_title).ratio() for subject_title in subject_titles),
            default = 0.0,
        )
        if min([len(local_title), *(len(subject_title) for subject_title in subject_titles)]) >= 8 and similarity >= 0.9:
            return int(similarity * 75)
        return 0


    @staticmethod
    def isPlaybackCompleted(playback_position: float, duration: float) -> bool:
        """
        プレイヤーが報告した実再生時間から Bangumi の視聴完了を判定する。

        Args:
            playback_position (float): 現在の再生位置 (秒)。
            duration (float): プレイヤーが解決した録画時間 (秒)。

        Returns:
            bool: 90% 以上を再生済みなら True。
        """

        return playback_position / duration >= 0.9


    @classmethod
    def findSubject(cls, series_title: str, subjects: list[dict[str, Any]]) -> dict[str, Any] | None:
        """
        用户の在看・看過收藏からローカル Series に対応する条目を一意に選ぶ。

        Args:
            series_title (str): ローカル Series の表示タイトル。
            subjects (list[dict[str, Any]]): 在看・看過のアニメ条目一覧。

        Returns:
            dict[str, Any] | None: 十分に一意な最高得点候補。
        """

        candidates = sorted(
            (
                (cls._scoreSubjectTitle(series_title, subject), subject)
                for subject in subjects
            ),
            key = lambda candidate: candidate[0],
            reverse = True,
        )
        if len(candidates) == 0 or candidates[0][0] < 67:
            return None
        if len(candidates) >= 2 and candidates[0][0] - candidates[1][0] < 10:
            return None
        return candidates[0][1]


    @classmethod
    async def _getCollectionSubjects(cls, user: User) -> list[dict[str, Any]]:
        """
        連携ユーザーの「在看」「看過」アニメ条目を收藏一覧から一括取得する。

        Args:
            user (User): Bangumi アカウント連携済みの KonomiTV ユーザー。

        Returns:
            list[dict[str, Any]]: 条目 ID ごとに重複を除いた收藏済みアニメ概要。

        Raises:
            httpx.HTTPError: Bangumi API への接続または HTTP エラーが発生した場合。
        """

        assert user.bangumi_user_name is not None
        access_token = user.decryptBangumiAccessToken()
        headers = {**API_REQUEST_HEADERS, 'Authorization': f'Bearer {access_token}'}
        subjects: dict[int, dict[str, Any]] = {}
        offset = 0
        async with HTTPX_CLIENT() as httpx_client:
            while True:
                # 收藏状態を API 側で分割せず全件取得し、在看・看過だけをローカルで選ぶ。
                ## これにより、ユーザーごとの候補一覧はページ数分のリクエストだけで揃う。
                response = await httpx_client.get(
                    url = f'{cls.API_BASE_URL}/users/{user.bangumi_user_name}/collections',
                    headers = headers,
                    params = {
                        'subject_type': 2,
                        'limit': cls.COLLECTION_PAGE_SIZE,
                        'offset': offset,
                    },
                )
                response.raise_for_status()
                payload = cast(dict[str, Any], response.json())
                collections = cast(list[dict[str, Any]], payload.get('data', []))
                for collection in collections:
                    if int(collection.get('type', -1)) not in {2, 3}:
                        continue
                    subject = collection.get('subject')
                    if not isinstance(subject, dict) or int(subject.get('type', -1)) != 2:
                        continue
                    subjects[int(subject['id'])] = cast(dict[str, Any], subject)

                offset += len(collections)
                if offset >= int(payload.get('total', 0)) or len(collections) == 0:
                    break
        return list(subjects.values())


    @classmethod
    async def _getEpisodes(cls, subject_id: int, access_token: str) -> list[dict[str, Any]]:
        """
        照合済み Bangumi 条目の通常エピソードを全ページ取得する。

        Args:
            subject_id (int): Bangumi 条目 ID。
            access_token (str): Bangumi 個人アクセストークン。

        Returns:
            list[dict[str, Any]]: 条目に属する通常エピソード。

        Raises:
            httpx.HTTPError: Bangumi API への接続または HTTP エラーが発生した場合。
        """

        episodes: list[dict[str, Any]] = []
        offset = 0
        async with HTTPX_CLIENT() as httpx_client:
            while True:
                response = await httpx_client.get(
                    url = f'{cls.API_BASE_URL}/episodes',
                    # NSFW 条目は匿名アクセスを 404 に偽装するため、收藏一覧と同じ認証を必ず引き継ぐ。
                    headers = {**API_REQUEST_HEADERS, 'Authorization': f'Bearer {access_token}'},
                    params = {
                        'subject_id': subject_id,
                        'type': 0,
                        'limit': cls.EPISODE_PAGE_SIZE,
                        'offset': offset,
                    },
                )
                # 認証後も閲覧できない条目、または削除済み条目だけ episode 未照合として扱う。
                if response.status_code == 404:
                    logging.warning(
                        f'[BangumiClient][_getEpisodes] Bangumi subject was not found. '
                        f'[subject_id: {subject_id}]',
                    )
                    return []
                response.raise_for_status()
                payload = cast(dict[str, Any], response.json())
                page_episodes = cast(list[dict[str, Any]], payload.get('data', []))
                episodes.extend(page_episodes)
                offset += len(page_episodes)
                if offset >= int(payload.get('total', 0)) or len(page_episodes) == 0:
                    break
        return episodes


    @classmethod
    async def syncUserCollections(cls, user: User) -> int:
        """
        連携ユーザーの收藏一覧を候補プールとしてローカル Series と全録画を照合する。

        Args:
            user (User): Bangumi アカウント連携済みの KonomiTV ユーザー。

        Returns:
            int: 今回 Bangumi 条目へ照合できた Series 数。

        Raises:
            httpx.HTTPError: Bangumi API への接続または HTTP エラーが発生した場合。
        """

        anime_series = [
            series for series in await Series.all()
            if any(genre['major'] == 'アニメ・特撮' for genre in series.genres)
        ]
        # ローカルにアニメ・特撮の Series が一件もなければ、Bangumi API 自体へアクセスしない。
        if len(anime_series) == 0:
            return 0

        subjects = await cls._getCollectionSubjects(user)
        access_token = user.decryptBangumiAccessToken()
        episodes_by_subject_id: dict[int, list[dict[str, Any]]] = {}
        matched_series_count = 0

        for series in anime_series:
            # すでに条目が確定している Series は、別ユーザーの收藏表記で上書きしない。
            subject = next(
                (subject for subject in subjects if int(subject['id']) == series.bangumi_subject_id),
                None,
            ) if series.bangumi_subject_id is not None else cls.findSubject(series.title, subjects)
            if subject is None:
                continue
            subject_id = int(subject['id'])
            matched_series_count += 1

            # 收藏一覧が返す SlimSubject を Series へ保存し、一覧・詳細画面を外部 API なしで描画できるようにする。
            images = subject.get('images')
            image_url = str(images.get('large') or images.get('common') or '') if isinstance(images, dict) else ''
            series.bangumi_subject_id = subject_id
            series.bangumi_subject_name = str(subject.get('name', '')) or None
            series.bangumi_subject_name_cn = str(subject.get('name_cn', '')) or None
            series.bangumi_subject_summary = str(subject.get('short_summary', '')) or None
            series.bangumi_subject_image_url = image_url or None
            await series.save(update_fields=[
                'bangumi_subject_id',
                'bangumi_subject_name',
                'bangumi_subject_name_cn',
                'bangumi_subject_summary',
                'bangumi_subject_image_url',
            ])

            recorded_programs = await RecordedProgram.filter(series_id=series.id).all()
            if all(
                recorded_program.bangumi_subject_id == subject_id and
                recorded_program.bangumi_episode_id is not None
                for recorded_program in recorded_programs
                if cls.parseEpisodeNumber(recorded_program.episode_number) is not None
            ):
                continue
            if subject_id not in episodes_by_subject_id:
                episodes_by_subject_id[subject_id] = await cls._getEpisodes(subject_id, access_token)
            episodes = episodes_by_subject_id[subject_id]

            # 一覧取得時に確定した条目の中だけで、各録画の自然話数を対応する Bangumi episode ID へ結び付ける。
            for recorded_program in recorded_programs:
                episode_number = cls.parseEpisodeNumber(recorded_program.episode_number)
                if episode_number is None:
                    continue
                episode = cls._findEpisode(episodes, episode_number)
                if episode is None:
                    continue
                recorded_program.bangumi_subject_id = subject_id
                recorded_program.bangumi_episode_id = int(episode['id'])
                await recorded_program.save(update_fields=['bangumi_subject_id', 'bangumi_episode_id'])
        return matched_series_count


    @classmethod
    async def syncAllLinkedUsers(cls) -> None:
        """
        Bangumi 連携済みユーザーごとに收藏一覧を取得し、ローカル Series へ反映する。

        Returns:
            None
        """

        users = await User.all().exclude(bangumi_user_name=None).exclude(bangumi_access_token=None)
        for user in users:
            try:
                matched_series_count = await cls.syncUserCollections(user)
                logging.info(
                    f'[BangumiClient][syncAllLinkedUsers] Synchronized Bangumi collections. '
                    f'[konomitv_user_id: {user.id}, matched_series: {matched_series_count}]',
                )
            except (httpx.HTTPError, ValueError) as ex:
                logging.error(
                    f'[BangumiClient][syncAllLinkedUsers] Failed to synchronize Bangumi collections. '
                    f'[konomitv_user_id: {user.id}]',
                    exc_info = ex,
                )


    @classmethod
    def scheduleUserCollectionSync(cls, user: User) -> None:
        """
        アカウント連携直後の收藏一覧同期を API レスポンスと切り離して開始する。

        Args:
            user (User): Bangumi アカウント連携済みの KonomiTV ユーザー。

        Returns:
            None
        """

        async def Sync() -> None:
            try:
                matched_series_count = await cls.syncUserCollections(user)
                logging.info(
                    f'[BangumiClient][scheduleUserCollectionSync] Synchronized Bangumi collections. '
                    f'[konomitv_user_id: {user.id}, matched_series: {matched_series_count}]',
                )
            except (httpx.HTTPError, ValueError) as ex:
                logging.error(
                    f'[BangumiClient][scheduleUserCollectionSync] Failed to synchronize Bangumi collections. '
                    f'[konomitv_user_id: {user.id}]',
                    exc_info = ex,
                )

        # 実行中タスクへの強参照を保持し、完了時だけ集合から取り除く。
        task = asyncio.create_task(Sync())
        cls._sync_tasks.add(task)
        task.add_done_callback(cls._sync_tasks.discard)


    @staticmethod
    def _findEpisode(episodes: list[dict[str, Any]], episode_number: int) -> dict[str, Any] | None:
        """
        Bangumi の対象条目から EPG 話数に対応する通常エピソードを取得する。

        Args:
            episodes (list[dict[str, Any]]): Bangumi 条目のエピソード。
            episode_number (int): EPG から抽出した話数。

        Returns:
            dict[str, Any] | None: ep または通し番号 sort + 1 が一致する通常エピソード。
        """

        # 分割クールでは ep が 1 に戻る一方、sort が前クールから続く場合がある
        matched_episodes = [
            episode for episode in episodes
            if int(episode.get('type', -1)) == 0 and (
                float(episode.get('ep', -1)) == episode_number or
                float(episode.get('sort', -2)) + 1 == episode_number
            )
        ]
        if len(matched_episodes) != 1:
            return None
        return matched_episodes[0]

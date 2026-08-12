from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, cast

from app.constants import API_REQUEST_HEADERS, HTTPX_CLIENT
from app.metadata.SeriesIndexer import NormalizeSeriesTitle
from app.models.RecordedProgram import RecordedProgram


@dataclass(slots=True)
class BangumiEpisodeMatch:
    """Bangumi の条目とエピソードの確定した照合結果を保持する。"""

    subject_id: int
    episode_id: int
    score: int


class BangumiClient:
    """KonomiTV の録画番組を Bangumi の条目とエピソードへ照合する。"""

    API_BASE_URL = 'https://api.bgm.tv/v0'
    MINIMUM_MATCH_SCORE = 90
    MINIMUM_SCORE_MARGIN = 20


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


    @staticmethod
    def _getDateScore(recorded_date: date, airdate: str) -> int:
        """
        録画日と Bangumi のエピソード放送日の近さをスコア化する。

        Args:
            recorded_date (date): KonomiTV 上の番組開始日。
            airdate (str): Bangumi 上のエピソード放送日。

        Returns:
            int: 日付の近さに応じたスコア。
        """

        try:
            date_difference = abs((recorded_date - date.fromisoformat(airdate)).days)
        except ValueError:
            return 0
        if date_difference <= 14:
            return 30
        if date_difference <= 120:
            return 15
        return 0


    @classmethod
    def scoreCandidate(
        cls,
        recorded_program: RecordedProgram,
        related_programs: list[RecordedProgram],
        subject: dict[str, Any],
        episodes: list[dict[str, Any]],
    ) -> BangumiEpisodeMatch | None:
        """
        タイトル、話数列、各話名、放送日から Bangumi 候補をスコア化する。

        Args:
            recorded_program (RecordedProgram): 同期対象の録画番組。
            related_programs (list[RecordedProgram]): 同じローカル Series の録画番組。
            subject (dict[str, Any]): Bangumi 条目候補。
            episodes (list[dict[str, Any]]): 候補条目のエピソード。

        Returns:
            BangumiEpisodeMatch | None: 対象話が一意に定まる場合の候補。
        """

        episode_number = cls.parseEpisodeNumber(recorded_program.episode_number)
        if episode_number is None:
            return None
        target_episode = cls._findEpisode(episodes, episode_number)
        if target_episode is None:
            return None

        # 日本の EPG と Bangumi で英語 / カタカナ表記が異なることがあるため、検索候補自体にも最低点を与える
        # ただしタイトル不一致候補は、日付・各話名・話数列まで整合しなければ閾値に届かない
        local_title = NormalizeSeriesTitle(recorded_program.series_title or '')
        subject_name = NormalizeSeriesTitle(str(subject.get('name', '')))
        subject_name_cn = NormalizeSeriesTitle(str(subject.get('name_cn', '')))
        if local_title == subject_name:
            score = 70
        elif local_title == subject_name_cn:
            score = 50
        else:
            score = 30

        score += cls._getDateScore(recorded_program.start_time.date(), str(target_episode.get('airdate', '')))

        # 各話の副題が一致する場合は、同名・分割クールの強い識別材料になる
        local_subtitle = NormalizeSeriesTitle(recorded_program.subtitle or '')
        if local_subtitle != '' and local_subtitle in {
            NormalizeSeriesTitle(str(target_episode.get('name', ''))),
            NormalizeSeriesTitle(str(target_episode.get('name_cn', ''))),
        }:
            score += 25

        # 同じ Series の他の録画も候補条目の ep / sort 列に乗るか確かめ、分割クールを話数の並びで識別する
        aligned_programs_count = 0
        for related_program in related_programs:
            related_episode_number = cls.parseEpisodeNumber(related_program.episode_number)
            if related_episode_number is None:
                continue
            related_episode = cls._findEpisode(episodes, related_episode_number)
            if related_episode is None:
                continue
            aligned_programs_count += 1
        score += min(aligned_programs_count, 4) * 5

        return BangumiEpisodeMatch(
            subject_id = int(subject['id']),
            episode_id = int(target_episode['id']),
            score = score,
        )


    @classmethod
    async def matchRecordedProgram(cls, recorded_program: RecordedProgram) -> BangumiEpisodeMatch | None:
        """
        録画番組を Bangumi の条目と通常エピソードへ自動照合する。

        Args:
            recorded_program (RecordedProgram): 照合対象の録画番組。

        Returns:
            BangumiEpisodeMatch | None: 最高スコア候補が十分に一意な場合のみ照合結果。

        Raises:
            httpx.HTTPError: Bangumi API への接続または HTTP エラーが発生した場合。
        """

        if recorded_program.series_id is None or cls.parseEpisodeNumber(recorded_program.episode_number) is None:
            return None

        # タイトルだけでなく、同じ Series の話数列と放送日も候補の裁定に利用する
        related_programs = await RecordedProgram.filter(series_id=recorded_program.series_id).all()
        async with HTTPX_CLIENT() as httpx_client:
            search_response = await httpx_client.post(
                url = f'{cls.API_BASE_URL}/search/subjects?limit=20&offset=0',
                headers = API_REQUEST_HEADERS,
                json = {
                    'keyword': recorded_program.series_title,
                    'sort': 'match',
                    'filter': {'type': [2]},
                },
            )
            search_response.raise_for_status()
            search_payload = cast(dict[str, Any], search_response.json())

            matches: list[BangumiEpisodeMatch] = []
            for subject in cast(list[dict[str, Any]], search_payload.get('data', [])):
                # 検索結果がアニメ以外を含む場合に備え、条目種別を再確認する
                if int(subject.get('type', -1)) != 2:
                    continue
                episodes_response = await httpx_client.get(
                    url = f'{cls.API_BASE_URL}/episodes',
                    headers = API_REQUEST_HEADERS,
                    params = {'subject_id': int(subject['id']), 'type': 0, 'limit': 100, 'offset': 0},
                )
                episodes_response.raise_for_status()
                episodes_payload = cast(dict[str, Any], episodes_response.json())
                match = cls.scoreCandidate(
                    recorded_program,
                    related_programs,
                    subject,
                    cast(list[dict[str, Any]], episodes_payload.get('data', [])),
                )
                if match is not None:
                    matches.append(match)

        # 誤同期は手動修正が難しいため、十分なスコアと次点との差がある場合だけ自動確定する
        matches.sort(key=lambda match: match.score, reverse=True)
        if len(matches) == 0 or matches[0].score < cls.MINIMUM_MATCH_SCORE:
            return None
        if len(matches) >= 2 and matches[0].score - matches[1].score < cls.MINIMUM_SCORE_MARGIN:
            return None
        return matches[0]

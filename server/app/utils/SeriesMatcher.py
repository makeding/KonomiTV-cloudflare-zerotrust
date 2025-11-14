
import re
from typing import TypedDict

from app import schemas


class SeriesMatchBreakdown(TypedDict):
    """シリーズマッチングのスコア明細"""
    title: int
    time: int
    channel: int
    metadata: int


class SeriesMatchResult(TypedDict):
    """シリーズマッチング結果"""
    program: schemas.RecordedProgram
    score: int
    breakdown: SeriesMatchBreakdown


class SeriesMatcher:
    """シリーズ番組マッチングユーティリティクラス"""

    @staticmethod
    def get_enclosed_characters_removal_patterns() -> list[re.Pattern]:
        """
        ARIB 外字記号を除去するための正規表現パターンを取得する
        （ProgramUtils.getEnclosedCharactersRemovalPatterns() から移植）

        Returns:
            list[re.Pattern]: 記号除去用の正規表現パターンのリスト
        """
        # 本来 ARIB 外字である記号の一覧
        mark = ('新|終|再|交|映|手|声|多|副|字|文|CC|OP|二|S|B|SS|無|無料|'
                'C|S1|S2|S3|MV|双|デ|D|N|W|P|H|HV|SD|天|解|料|前|後|初|生|販|吹|PPV|'
                '演|移|他|収|・|英|韓|中|字/日|字/日英|3D|2ndScr|2K|4K|8K|5.1|7.1|22.2|60P|120P|d|HC|HDR|Hi-Res|Lossless|SHV|UHD|VOD|配|初')

        # 正規表現を作成
        pattern1 = re.compile(r'\((二|字|再)\)')  # 通常の括弧で囲まれている記号
        pattern2 = re.compile(rf'\[({mark})\]')

        return [pattern1, pattern2]

    @staticmethod
    def remove_enclosed_characters(title: str) -> str:
        """
        タイトルから enclosed_characters（囲み記号）を除去する

        Args:
            title: 元のタイトル

        Returns:
            str: 除去後のタイトル
        """
        patterns = SeriesMatcher.get_enclosed_characters_removal_patterns()
        result = title
        for pattern in patterns:
            result = pattern.sub('', result)
        return result.strip()

    @staticmethod
    def extract_base_title(title: str) -> str:
        """
        エピソード番号前のベースタイトルを抽出する

        Args:
            title: 元のタイトル

        Returns:
            str: ベースタイトル
        """
        base = title

        # まず副標題を除去（「」『』の中身を削除）
        base = re.sub(r'[「『].*?[」』]', '', base).strip()

        # エピソード番号パターンを除去
        patterns = [
            r'\(\d+\)',       # xxx(1)
            r'#\d+',          # xxx#1
            r'第\d+話',       # xxx第1話
            r'第\d+回',       # xxx第1回
            r'【\d+】',       # xxx【1】
            r'\s+\d+\s*$',    # xxx 1 (末尾の数字)
        ]

        for pattern in patterns:
            match = re.search(pattern, base)
            if match:
                base = base[:match.start()].strip()
                break

        return base

    @staticmethod
    def extract_keywords(title: str) -> list[str]:
        """
        キーワードを抽出（2文字以上の単語）

        Args:
            title: 元のタイトル

        Returns:
            list[str]: キーワードリスト
        """
        # スペースで分割
        words = [word.strip() for word in re.split(r'[\s\u3000]+', title) if len(word.strip()) >= 2]
        return words

    @staticmethod
    def calculate_keyword_match_rate(keywords: list[str], target: str) -> float:
        """
        キーワードマッチ率を計算

        Args:
            keywords: キーワードリスト
            target: 対象文字列

        Returns:
            float: マッチ率 (0.0 ~ 1.0)
        """
        if not keywords:
            return 0.0

        matched = sum(1 for keyword in keywords if keyword in target)
        return matched / len(keywords)

    @staticmethod
    def calculate_string_similarity(str1: str, str2: str) -> float:
        """
        文字列類似度を計算（簡易版）

        Args:
            str1: 文字列1
            str2: 文字列2

        Returns:
            float: 類似度 (0.0 ~ 1.0)
        """
        if str1 == str2:
            return 1.0
        if not str1 or not str2:
            return 0.0

        # 共通部分の長さ / 長い方の長さ
        longer = str1 if len(str1) > len(str2) else str2
        shorter = str2 if len(str1) > len(str2) else str1

        if shorter in longer:
            return len(shorter) / len(longer)

        # 共通文字数をカウント
        chars1 = set(str1)
        chars2 = set(str2)
        common = len(chars1 & chars2)
        total = max(len(chars1), len(chars2))

        return common / total if total > 0 else 0.0

    @staticmethod
    def calculate_title_score(current_title: str, target_title: str) -> int:
        """
        タイトルマッチングスコアを計算（最大60点）

        Args:
            current_title: 現在の番組タイトル
            target_title: 対象番組タイトル

        Returns:
            int: タイトルスコア (0 ~ 60)
        """
        # enclosed_characters を除去
        clean_current = SeriesMatcher.remove_enclosed_characters(current_title)
        clean_target = SeriesMatcher.remove_enclosed_characters(target_title)

        # エピソード番号前のベースタイトルを抽出
        current_base = SeriesMatcher.extract_base_title(clean_current)
        target_base = SeriesMatcher.extract_base_title(clean_target)

        # 完全一致
        if current_base == target_base and current_base:
            return 60

        # 文字列類似度計算
        similarity = SeriesMatcher.calculate_string_similarity(current_base, target_base)
        if similarity >= 0.9:
            return 55
        if similarity >= 0.8:
            return 50
        if similarity >= 0.7:
            return 40

        # キーワードマッチング
        keywords = SeriesMatcher.extract_keywords(current_base)
        if not keywords:
            return 0

        match_rate = SeriesMatcher.calculate_keyword_match_rate(keywords, target_base)
        if match_rate >= 0.8:
            return 35
        if match_rate >= 0.6:
            return 25
        if match_rate >= 0.4:
            return 15
        if match_rate >= 0.2:
            return 8

        return 0

    @staticmethod
    def calculate_time_score(current: schemas.RecordedProgram, target: schemas.RecordedProgram) -> int:
        """
        時間帯マッチングスコアを計算（最大20点）

        Args:
            current: 現在の録画番組
            target: 対象録画番組

        Returns:
            int: 時間スコア (0 ~ 20)
        """
        current_time = current.start_time
        target_time = target.start_time

        # 日付の差分（絶対値）
        date_diff = abs((current_time - target_time).days)

        # 曜日の差分（0-6）
        day_diff = abs((current_time.weekday() - target_time.weekday() + 7) % 7)

        # 時間の差分（分単位）
        hour_diff = abs(current_time.hour - target_time.hour)
        minute_diff = abs(current_time.minute - target_time.minute)
        total_minute_diff = hour_diff * 60 + minute_diff

        # 連続放送パターン（毎日放送、例：朝ドラ、帯番組）
        # 日付差が1-7日以内で時間がほぼ同じ
        if 1 <= date_diff <= 7:
            if total_minute_diff <= 5:
                return 20  # ほぼ同時刻
            if total_minute_diff <= 15:
                return 18  # 15分以内
            if total_minute_diff <= 30:
                return 16  # 30分以内

        # 週間番組パターン（同じ曜日・時間、7日間隔の可能性高い）
        if day_diff == 0:
            if total_minute_diff <= 5:
                return 20
            if total_minute_diff <= 15:
                return 18
            if total_minute_diff <= 30:
                return 15
            if total_minute_diff <= 60:
                return 10

        # それ以外で時間が近い場合（日間番組の可能性）
        if total_minute_diff <= 15:
            return 12
        if total_minute_diff <= 30:
            return 8
        if total_minute_diff <= 60:
            return 5

        return 0

    @staticmethod
    def get_channel_type(channel_number: str) -> str:
        """
        チャンネルタイプを取得

        Args:
            channel_number: チャンネル番号

        Returns:
            str: チャンネルタイプ ('terrestrial', 'bs', 'cs', 'other')
        """
        try:
            num = int(channel_number)
            if 1 <= num <= 12:
                return 'terrestrial'  # 地上波
            if 101 <= num <= 999:
                return 'bs'  # BS
            if num >= 1000:
                return 'cs'  # CS
        except ValueError:
            pass
        return 'other'

    @staticmethod
    def calculate_channel_score(current: schemas.RecordedProgram, target: schemas.RecordedProgram) -> int:
        """
        チャンネルマッチングスコアを計算（最大10点）

        Args:
            current: 現在の録画番組
            target: 対象録画番組

        Returns:
            int: チャンネルスコア (0 ~ 10)
        """
        if not current.channel or not target.channel:
            return 0

        # 同一チャンネル
        if current.channel.id == target.channel.id:
            return 10

        # 同一ネットワーク系列
        if current.channel.network_id and target.channel.network_id and \
           current.channel.network_id == target.channel.network_id:
            return 6

        # チャンネルタイプが同じ（地上波同士、BS同士など）
        current_type = SeriesMatcher.get_channel_type(current.channel.channel_number)
        target_type = SeriesMatcher.get_channel_type(target.channel.channel_number)
        if current_type == target_type:
            return 3

        return 0

    @staticmethod
    def calculate_metadata_score(current: schemas.RecordedProgram, target: schemas.RecordedProgram) -> int:
        """
        メタデータマッチングスコアを計算（最大10点）

        Args:
            current: 現在の録画番組
            target: 対象録画番組

        Returns:
            int: メタデータスコア (0 ~ 10)
        """
        score = 0

        # EPGのシリーズID一致（最重要）
        if current.series_id and current.series_id == target.series_id:
            return 10

        # ジャンル一致
        if current.genres and target.genres:
            # major と middle が完全一致
            exact_match = any(
                g1['major'] == g2['major'] and g1['middle'] == g2['middle']
                for g1 in current.genres
                for g2 in target.genres
            )

            if exact_match:
                # 連続物ジャンル（アニメ、ドラマ等）は高配点
                series_genres = ['アニメ・特撮', 'ドラマ', '情報・ワイドショー']
                is_series_genre = any(g['major'] in series_genres for g in current.genres)
                score += 5 if is_series_genre else 4
            else:
                # major のみ一致
                major_match = any(
                    g1['major'] == g2['major']
                    for g1 in current.genres
                    for g2 in target.genres
                )
                if major_match:
                    score += 2

        # 番組の長さが近い（±5分）
        duration_diff = abs(current.duration - target.duration)
        if duration_diff <= 300:
            score += 3
        elif duration_diff <= 600:
            score += 2
        elif duration_diff <= 900:
            score += 1

        return min(score, 10)

    @staticmethod
    def calculate_series_match(current: schemas.RecordedProgram, target: schemas.RecordedProgram) -> SeriesMatchResult:
        """
        シリーズマッチングのスコアを計算

        Args:
            current: 現在の録画番組
            target: 対象録画番組

        Returns:
            SeriesMatchResult: マッチング結果（番組情報、スコア、明細）
        """
        title_score = SeriesMatcher.calculate_title_score(current.title, target.title)
        time_score = SeriesMatcher.calculate_time_score(current, target)
        channel_score = SeriesMatcher.calculate_channel_score(current, target)
        metadata_score = SeriesMatcher.calculate_metadata_score(current, target)

        return {
            'program': target,
            'score': title_score + time_score + channel_score + metadata_score,
            'breakdown': {
                'title': title_score,
                'time': time_score,
                'channel': channel_score,
                'metadata': metadata_score,
            }
        }

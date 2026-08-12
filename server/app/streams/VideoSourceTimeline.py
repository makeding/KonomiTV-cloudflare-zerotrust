from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.models.RecordedProgram import RecordedProgram


@dataclass(frozen=True, slots=True)
class VideoSourceCandidate:
    """仮想番組時間軸へ割り当て可能な、1つの録画ファイルの有効範囲を表す。"""

    recorded_program_id: int
    recorded_video_id: int
    file_path: str
    recording_start_time: datetime
    recording_end_time: datetime
    source_duration_seconds: float
    recording_start_margin: float
    recording_end_margin: float


@dataclass(frozen=True, slots=True)
class VideoSourceSpan:
    """仮想番組時間軸の連続区間と、その区間を供給する録画ファイル内の範囲を表す。"""

    recorded_program_id: int
    recorded_video_id: int
    file_path: str
    timeline_start_seconds: float
    timeline_end_seconds: float
    source_start_seconds: float
    source_end_seconds: float


@dataclass(frozen=True, slots=True)
class VideoSourceGap:
    """どの録画ファイルからも復元できない仮想番組時間軸上の欠落区間を表す。"""

    timeline_start_seconds: float
    timeline_end_seconds: float


@dataclass(frozen=True, slots=True)
class VideoSourceTimeline:
    """同一話の複数録画ファイルから構成した仮想番組時間軸を表す。"""

    duration_seconds: float
    spans: tuple[VideoSourceSpan, ...]
    gaps: tuple[VideoSourceGap, ...]

    @property
    def is_continuous(self) -> bool:
        """仮想番組時間軸の全範囲を録画ファイルで復元できるかを返す。"""

        return len(self.spans) > 0 and len(self.gaps) == 0


class VideoSourceTimelineResolver:
    """同一話の録画ファイル群を、重複のない仮想番組時間軸へ解決する。"""

    # ファイルシステムやコンテナ解析で得る録画時刻にはごく小さな丸め差があり得るため、
    # 1秒以内の境界差だけは同一地点として扱う。番組本編の実欠落を隠さないよう、HLS セグメント長ほどは許容しない。
    BOUNDARY_TOLERANCE_SECONDS = 1.0

    @classmethod
    async def findCandidates(cls, anchor: RecordedProgram) -> list[RecordedProgram]:
        """
        指定された録画と同じ局・同じ話に属する、再生可能な録画ファイルを取得する。

        Args:
            anchor (RecordedProgram): 仮想時間軸の番組範囲と同一話判定の基準にする録画番組。

        Returns:
            list[RecordedProgram]: 録画開始時刻、終了時刻、ID の順で安定ソートした候補。
        """

        # Series に所属しない単発番組や局情報が失われた録画は、安全に同一話と断定できない。
        if anchor.series_id is None or anchor.channel_id is None:
            return [anchor]

        query = RecordedProgram.filter(
            series_id = anchor.series_id,
            channel_id = anchor.channel_id,
            recorded_video__status = 'Recorded',
        )

        # Bangumi の永続 Episode ID が双方にある場合は、EPG 表記揺れより強い同一話の根拠として使う。
        # 未照合の場合は、SeriesIndexer が正規化した話数に加えて同一 EPG 枠であることまで要求する。
        if anchor.bangumi_episode_id is not None:
            query = query.filter(bangumi_episode_id = anchor.bangumi_episode_id)
        elif anchor.episode_number is not None:
            query = query.filter(
                episode_number = anchor.episode_number,
                start_time = anchor.start_time,
                end_time = anchor.end_time,
            )
        else:
            return [anchor]

        candidates = await query.select_related('recorded_video').all()
        if all(candidate.id != anchor.id for candidate in candidates):
            candidates.append(anchor)
        return sorted(
            candidates,
            key = lambda candidate: (
                candidate.recorded_video.recording_start_time or candidate.start_time,
                candidate.recorded_video.recording_end_time or candidate.end_time,
                candidate.id,
            ),
        )

    @classmethod
    def build(
        cls,
        program_start_time: datetime,
        program_end_time: datetime,
        candidates: list[VideoSourceCandidate],
    ) -> VideoSourceTimeline:
        """
        複数の録画ファイルを番組開始からの仮想時間軸へ割り当てる。

        Args:
            program_start_time (datetime): 仮想時間軸の 0 秒に対応する EPG 上の番組開始時刻。
            program_end_time (datetime): 仮想時間軸の終端に対応する EPG 上の番組終了時刻。
            candidates (list[VideoSourceCandidate]): 同一局・同一話と確認済みの録画ファイル候補。

        Returns:
            VideoSourceTimeline: 重複を除去したソース区間と、復元できない欠落区間。
        """

        duration_seconds = max((program_end_time - program_start_time).total_seconds(), 0.0)
        normalized_candidates: list[tuple[float, float, VideoSourceCandidate]] = []

        # 各ファイルの実録画時刻を EPG 上の番組範囲で切り詰め、番組開始からの秒数へ正規化する。
        # recording_start_margin / recording_end_margin は番組外の余白であり、欠落した本編範囲の根拠には使わない。
        for candidate in candidates:
            coverage_start_time = max(program_start_time, candidate.recording_start_time)
            coverage_end_time = min(program_end_time, candidate.recording_end_time)
            if coverage_end_time <= coverage_start_time:
                continue

            timeline_start_seconds = (coverage_start_time - program_start_time).total_seconds()
            timeline_end_seconds = (coverage_end_time - program_start_time).total_seconds()
            source_start_seconds = max((coverage_start_time - candidate.recording_start_time).total_seconds(), 0.0)
            source_available_seconds = max(candidate.source_duration_seconds - source_start_seconds, 0.0)
            timeline_end_seconds = min(timeline_end_seconds, timeline_start_seconds + source_available_seconds)
            if timeline_end_seconds <= timeline_start_seconds:
                continue
            normalized_candidates.append((timeline_start_seconds, timeline_end_seconds, candidate))

        spans: list[VideoSourceSpan] = []
        gaps: list[VideoSourceGap] = []
        cursor_seconds = 0.0

        # 現在位置を覆う候補のうち最も遠くまで到達できるファイルを選び、時間軸を左から右へ確定する。
        # 同じ終端なら録画余白が広い候補、さらに同率なら ID が小さい候補を選び、毎回同じ結果になるようにする。
        while cursor_seconds < duration_seconds - cls.BOUNDARY_TOLERANCE_SECONDS:
            covering_candidates = [
                candidate
                for candidate in normalized_candidates
                if candidate[0] <= cursor_seconds + cls.BOUNDARY_TOLERANCE_SECONDS and
                candidate[1] > cursor_seconds + cls.BOUNDARY_TOLERANCE_SECONDS
            ]
            if len(covering_candidates) == 0:
                next_start_seconds = min(
                    (
                        candidate[0]
                        for candidate in normalized_candidates
                        if candidate[0] > cursor_seconds + cls.BOUNDARY_TOLERANCE_SECONDS
                    ),
                    default = duration_seconds,
                )
                gaps.append(VideoSourceGap(
                    timeline_start_seconds = cursor_seconds,
                    timeline_end_seconds = min(next_start_seconds, duration_seconds),
                ))
                cursor_seconds = min(next_start_seconds, duration_seconds)
                continue

            timeline_start_seconds, timeline_end_seconds, selected_candidate = max(
                covering_candidates,
                key = lambda candidate: (
                    candidate[1],
                    candidate[2].recording_start_margin + candidate[2].recording_end_margin,
                    -candidate[2].recorded_program_id,
                ),
            )
            assigned_start_seconds = cursor_seconds
            assigned_end_seconds = min(timeline_end_seconds, duration_seconds)
            source_start_seconds = max(
                assigned_start_seconds - timeline_start_seconds +
                max(
                    (
                        max(program_start_time, selected_candidate.recording_start_time) -
                        selected_candidate.recording_start_time
                    ).total_seconds(),
                    0.0,
                ),
                0.0,
            )
            spans.append(VideoSourceSpan(
                recorded_program_id = selected_candidate.recorded_program_id,
                recorded_video_id = selected_candidate.recorded_video_id,
                file_path = selected_candidate.file_path,
                timeline_start_seconds = assigned_start_seconds,
                timeline_end_seconds = assigned_end_seconds,
                source_start_seconds = source_start_seconds,
                source_end_seconds = source_start_seconds + (assigned_end_seconds - assigned_start_seconds),
            ))
            cursor_seconds = assigned_end_seconds

        # 末尾の1秒以内だけが丸め差で残った場合は、最後の実ソース区間へ吸収して連続扱いにする。
        if 0.0 < duration_seconds - cursor_seconds <= cls.BOUNDARY_TOLERANCE_SECONDS and len(spans) > 0:
            last_span = spans[-1]
            extension_seconds = duration_seconds - last_span.timeline_end_seconds
            spans[-1] = VideoSourceSpan(
                recorded_program_id = last_span.recorded_program_id,
                recorded_video_id = last_span.recorded_video_id,
                file_path = last_span.file_path,
                timeline_start_seconds = last_span.timeline_start_seconds,
                timeline_end_seconds = duration_seconds,
                source_start_seconds = last_span.source_start_seconds,
                source_end_seconds = last_span.source_end_seconds + extension_seconds,
            )
        elif cursor_seconds < duration_seconds:
            gaps.append(VideoSourceGap(
                timeline_start_seconds = cursor_seconds,
                timeline_end_seconds = duration_seconds,
            ))

        return VideoSourceTimeline(
            duration_seconds = duration_seconds,
            spans = tuple(spans),
            gaps = tuple(gaps),
        )

    @classmethod
    def buildFromRecordedPrograms(
        cls,
        anchor: RecordedProgram,
        candidates: list[RecordedProgram],
    ) -> VideoSourceTimeline:
        """
        ORM の録画番組群から仮想番組時間軸を生成する。

        Args:
            anchor (RecordedProgram): EPG 上の番組開始・終了時刻を提供する録画番組。
            candidates (list[RecordedProgram]): 同一話候補として取得済みの録画番組。

        Returns:
            VideoSourceTimeline: 実録画時刻が取得できたファイルだけで構成した仮想時間軸。
        """

        source_candidates: list[VideoSourceCandidate] = []
        for candidate in candidates:
            recorded_video = candidate.recorded_video
            if recorded_video.recording_start_time is None or recorded_video.recording_end_time is None:
                continue
            source_candidates.append(VideoSourceCandidate(
                recorded_program_id = candidate.id,
                recorded_video_id = recorded_video.id,
                file_path = recorded_video.file_path,
                recording_start_time = recorded_video.recording_start_time,
                recording_end_time = recorded_video.recording_end_time,
                source_duration_seconds = recorded_video.duration,
                recording_start_margin = candidate.recording_start_margin,
                recording_end_margin = candidate.recording_end_margin,
            ))
        return cls.build(anchor.start_time, anchor.end_time, source_candidates)

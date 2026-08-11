from __future__ import annotations

from dataclasses import dataclass

from app.config import Config
from app.constants import (
    LIVE_QUALITY_TYPES,
    QUALITY,
    QUALITY_TYPES,
    VIDEO_QUALITY_TYPES,
)


@dataclass(frozen=True)
class StreamEncodingOptions:
    """
    ライブ/録画ストリームでベース画質に追加するエンコードオプションを表す

    Args:
        is_hevc_10bit_enabled (bool): HEVC 10bit を要求するクライアント向けのストリームかどうか
        is_24fps_mode_enabled (bool): 24fps モードを適用するストリームかどうか
    """

    # HEVC 10bit を要求するクライアント向けのストリームかどうか
    ## --fallback-bitdepth により、GPU 側が HEVC 10bit 非対応の場合でも 8bit へフォールバックされるため、
    ## 値の意味は「HEVC 10bit を要求」であり「HEVC 10bit 出力の保証」ではない
    is_hevc_10bit_enabled: bool = False

    # 24fps モードを適用するストリームかどうか
    ## 1080p-60fps では 60fps 化を優先し、24fps モードの要求があってもここでは無効にする
    is_24fps_mode_enabled: bool = False

    @classmethod
    def fromRequest(
        cls,
        quality: QUALITY_TYPES,
        is_hevc_10bit_requested: bool,
        is_24fps_mode_requested: bool,
    ) -> StreamEncodingOptions:
        """
        API で指定されたオプションから、実際に使うストリームオプションを作る

        Args:
            quality (QUALITY_TYPES): ベース画質
            is_hevc_10bit_requested (bool): クライアントが HEVC 10bit を要求しているかどうか
            is_24fps_mode_requested (bool): クライアントが 24fps モードを要求しているかどうか

        Returns:
            StreamEncodingOptions: 実際のストリーム生成に使うエンコードオプション
        """

        # HEVC 10bit は通信節約モードで使う HEVC 画質かつ QSVEncC / NVEncC の場合だけ有効化する
        ## VCEEncC は HEVC 10bit 対応の機種かを判定できず、rkmppenc は HEVC 10bit エンコード自体に非対応のため設定しない
        is_hevc_10bit_enabled = (
            is_hevc_10bit_requested is True and
            QUALITY[quality].is_hevc is True and
            Config().general.encoder in ['QSVEncC', 'NVEncC']
        )

        # 24fps モードは 60fps 画質以外で有効化する
        ## 1080p-60fps では 60i を 60p 化するユーザー意図が明確なので、24fps モードより 60fps 化を優先する
        is_24fps_mode_enabled = (
            is_24fps_mode_requested is True and
            QUALITY[quality].is_60fps is False
        )

        return cls(
            is_hevc_10bit_enabled = is_hevc_10bit_enabled,
            is_24fps_mode_enabled = is_24fps_mode_enabled,
        )

    def buildSuffix(self) -> str:
        """
        ライブストリーム ID の末尾に付ける文字列を組み立てる

        Returns:
            str: ライブストリーム ID の末尾に付ける文字列
        """

        suffix = ''

        # -10bit は -24fps より先に付け、ビット深度からフレームレートの順で並べる
        if self.is_hevc_10bit_enabled is True:
            suffix += '-10bit'

        # 24fps モードが有効なストリームだけ -24fps を付ける
        if self.is_24fps_mode_enabled is True:
            suffix += '-24fps'

        return suffix


@dataclass(frozen=True)
class StreamQualityWithOptions:
    """
    API パスの品質指定を、ベース画質と追加エンコードオプションへ分解した結果を表す

    Args:
        quality (VIDEO_QUALITY_TYPES): 録画ストリーミングで利用する画質
        encoding_options (StreamEncodingOptions): ベース画質に追加するエンコードオプション
    """

    # 録画ストリーミングで利用する画質
    ## copy は QUALITY に含まれず、FFmpeg stream copy を使う録画専用の特殊な品質として扱う
    quality: VIDEO_QUALITY_TYPES

    # ベース画質に追加するエンコードオプション
    ## HEVC 10bit や 24fps モードは、ベース画質から分けてストリーム ID やエンコード引数へ渡す
    encoding_options: StreamEncodingOptions


@dataclass(frozen=True)
class LiveStreamQualityWithOptions:
    """
    ライブ API パスの品質指定を、ベース画質と追加エンコードオプションへ分解した結果を表す

    Args:
        quality (LIVE_QUALITY_TYPES): ライブストリームで利用する画質
        encoding_options (StreamEncodingOptions): ベース画質に追加するエンコードオプション
    """

    # ライブストリームで利用する画質
    ## raw-mmts は BS4K の MMTS 透過配信専用の特殊な品質で、QUALITY には存在しない
    quality: LIVE_QUALITY_TYPES

    # ベース画質に追加するエンコードオプション
    ## raw-mmts ではエンコードを行わないため、常にデフォルト値のまま使われる
    encoding_options: StreamEncodingOptions


def SplitQualityAndEncodingOptions(quality: str) -> StreamQualityWithOptions | None:
    """
    API パスの品質指定 (例: 720p-hevc-10bit-24fps) を、ベース画質 (720p-hevc) と追加オプション (-10bit / -24fps) に分解する

    Args:
        quality (str): API パスで指定された品質

    Returns:
        StreamQualityWithOptions | None: 分解結果 (不正な品質指定の場合は None)
    """

    # MPEG-TS パススルーは画質変換を一切行わない録画専用の品質として扱う
    ## エンコードオプションは元映像の変換を要求する値なので、常にデフォルト値のまま使う
    if quality == 'copy':
        return StreamQualityWithOptions(
            quality = 'copy',
            encoding_options = StreamEncodingOptions(),
        )

    # -10bit / -24fps は buildSuffix() と同じ順序でのみ受け付ける
    ## 末尾から剥がすことで、1080p-60fps-hevc のようにベース画質自体が -hevc を含むケースを安全に扱う
    base_quality = quality
    is_24fps_mode_requested = False
    if base_quality.endswith('-24fps') is True:
        base_quality = base_quality[:-len('-24fps')]
        is_24fps_mode_requested = True

    is_hevc_10bit_requested = False
    if base_quality.endswith('-10bit') is True:
        base_quality = base_quality[:-len('-10bit')]
        is_hevc_10bit_requested = True

    # ベース画質が QUALITY に存在しない場合は、ルーター側で従来通り 422 を返す
    if base_quality not in QUALITY:
        return None

    # 画質とサーバー側の対応状況を見て、実際に使えるオプションだけを残す
    ## HEVC 10bit 非対応エンコーダーや 1080p-60fps の 24fps モード要求はここで無効化される
    encoding_options = StreamEncodingOptions.fromRequest(
        base_quality,
        is_hevc_10bit_requested,
        is_24fps_mode_requested,
    )
    return StreamQualityWithOptions(
        quality = base_quality,
        encoding_options = encoding_options,
    )


def SplitLiveQualityAndEncodingOptions(quality: str) -> LiveStreamQualityWithOptions | None:
    """
    ライブ API パスの品質指定を、ベース画質と追加オプションに分解する

    Args:
        quality (str): API パスで指定された品質

    Returns:
        LiveStreamQualityWithOptions | None: 分解結果 (不正な品質指定の場合は None)
    """

    # BS4K Raw MMTS はエンコードを伴わないライブ専用品質として扱う
    ## 既存の QUALITY はエンコード引数を組み立てるためのメタデータなので、raw-mmts はそこへ含めない
    if quality == 'raw-mmts':
        return LiveStreamQualityWithOptions(
            quality = 'raw-mmts',
            encoding_options = StreamEncodingOptions(),
        )

    # 通常のライブ品質は録画配信と同じ分解ロジックを利用する
    stream_quality = SplitQualityAndEncodingOptions(quality)
    if stream_quality is None or stream_quality.quality == 'copy':
        return None

    return LiveStreamQualityWithOptions(
        quality = stream_quality.quality,
        encoding_options = stream_quality.encoding_options,
    )

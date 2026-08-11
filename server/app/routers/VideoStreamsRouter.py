
import asyncio
import json
import pathlib
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import FileResponse, Response
from sse_starlette.sse import EventSourceResponse

from app import logging
from app.models.RecordedProgram import RecordedProgram
from app.streams.StreamEncodingOptions import (
    SplitQualityAndEncodingOptions,
    StreamQualityWithOptions,
)
from app.streams.VideoStream import VideoStream


# ルーター
router = APIRouter(
    tags = ['Streams'],
    prefix = '/api/streams/video',
)


async def ValidateVideoID(video_id: Annotated[int, Path(description='録画番組の ID 。')]) -> RecordedProgram:
    """ 録画番組 ID のバリデーション """

    # 指定された video_id が存在するか確認
    recorded_program = await RecordedProgram.filter(id=video_id).get_or_none() \
        .select_related('recorded_video') \
        .select_related('channel')
    if recorded_program is None:
        logging.error(f'[VideoStreamsRouter][ValidateVideoID] Specified video_id was not found. [video_id: {video_id}]')
        raise HTTPException(
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail = 'Specified video_id was not found',
        )

    # 録画中ファイルは再生中もファイルサイズが伸び続けるため、差分検出をそのまま適用すると
    ## 追いかけ再生のセグメント要求ごとに自動再解析が走り、エンコード入力と同じ TS への I/O が競合してしまう。
    ## 録画完了後だけ転码検出用の軽量チェックを行う。
    if recorded_program.recorded_video.status != 'Recording':
        # 被動検出: ファイルサイズの差異をチェックし、大きく変化している場合は自動的に再解析
        # (例: HEVC 転码で 50% 以上ファイルサイズが縮小された場合など)
        import anyio

        from app.metadata.RecordedScanTask import RecordedScanTask

        file_path = anyio.Path(recorded_program.recorded_video.file_path)
        try:
            if await file_path.is_file():
                actual_file_size = (await file_path.stat()).st_size
                db_file_size = recorded_program.recorded_video.file_size

                # ファイルサイズの差異が 20% 以上の場合、転码された可能性が高い
                if db_file_size > 0:
                    size_diff_ratio = abs(actual_file_size - db_file_size) / db_file_size
                    if size_diff_ratio > 0.20:  # 20% 以上の差異
                        logging.info(
                            f'[VideoStreamsRouter][ValidateVideoID] File size changed significantly '
                            f'(DB: {db_file_size:,} bytes → Actual: {actual_file_size:,} bytes, '
                            f'diff: {size_diff_ratio*100:.1f}%). Triggering automatic reanalysis...'
                        )
                        # バックグラウンドで再解析を実行（files_only=True でメタデータのみ更新）
                        # 再生開始を遅延させないため await せずにバックグラウンドタスクとして実行
                        import asyncio
                        background_task = asyncio.create_task(RecordedScanTask().processRecordedFile(
                            file_path = file_path,
                            force_update = True,
                            files_only = True,  # CM 解析・サムネイル生成はスキップ
                        ))
                        background_task.add_done_callback(lambda task: task.exception() if task.cancelled() is False else None)
        except Exception as ex:
            # ファイルサイズチェックに失敗しても再生は継続できるようエラーをログに出力するのみ
            logging.warning(f'[VideoStreamsRouter][ValidateVideoID] Failed to check file size: {ex}')

    return recorded_program


async def ValidateQuality(quality: Annotated[str, Path(description='映像の品質。ex: 1080p')]) -> StreamQualityWithOptions:
    """ 映像の品質のバリデーション """

    # 指定された品質が存在するか確認
    ## 品質の指定に -10bit や -24fps が付いていれば分解する
    stream_quality = SplitQualityAndEncodingOptions(quality)
    if stream_quality is None:
        logging.error(f'[VideoStreamsRouter][ValidateQuality] Specified quality was not found. [quality: {quality}]')
        raise HTTPException(
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail = 'Specified quality was not found',
        )

    return stream_quality


def ValidateVideoCopyQuality(recorded_program: RecordedProgram, stream_quality: StreamQualityWithOptions) -> None:
    """
    MPEG-TS パススルー品質を利用できる録画か検証する

    Args:
        recorded_program (RecordedProgram): 配信対象の録画番組
        stream_quality (StreamQualityWithOptions): リクエストされた録画ストリーミング品質

    Returns:
        None
    """

    # 通常の再エンコード品質では追加の制約を設けない
    if stream_quality.quality != 'copy':
        return

    recorded_video = recorded_program.recorded_video
    is_copy_compatible = (
        recorded_video.status == 'Recorded' and
        recorded_video.container_format == 'MPEG-TS' and
        recorded_video.video_codec in ['H.264', 'H.265'] and
        recorded_video.video_scan_type == 'Progressive' and
        recorded_video.has_video_stream_changes is False
    )
    if is_copy_compatible is False:
        logging.error(
            f'[VideoStreamsRouter][ValidateVideoCopyQuality] Specified video is not compatible with stream copy. '
            f'[video_id: {recorded_program.id}, status: {recorded_video.status}, '
            f'container_format: {recorded_video.container_format}, video_codec: {recorded_video.video_codec}, '
            f'video_scan_type: {recorded_video.video_scan_type}, '
            f'has_video_stream_changes: {recorded_video.has_video_stream_changes}]'
        )
        raise HTTPException(
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail = 'Specified video is not compatible with stream copy',
        )


@router.get(
    '/{video_id}/raw-mmts/mpegts',
    summary = '録画番組 Raw MMTS ストリーム API',
    response_class = FileResponse,
    responses = {
        status.HTTP_200_OK: {
            'description': '録画ファイルに保存されている MMT/TLV データ。',
            'content': {'video/mp2t': {}},
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            'description': '指定された録画番組は Raw MMTS 直通配信に対応していない。',
        },
    },
)
async def VideoRawMMTSStreamAPI(
    recorded_program: Annotated[RecordedProgram, Depends(ValidateVideoID)],
):
    """
    MMT/TLV 形式で保存されている録画ファイルを、変換せずにそのまま配信する。<br>
    ブラウザ側では mpegts.js の MMTS demuxer がこのストリームを直接解析する。
    """

    # Raw MMTS 直通配信は MMT/TLV の録画ファイル専用の経路
    # MPEG-TS / MPEG-4 は既存の HLS エンコード経路で扱う
    if recorded_program.recorded_video.container_format != 'MMT/TLV':
        logging.error(
            f'[VideoStreamsRouter][VideoRawMMTSStreamAPI] Specified video_id is not an MMT/TLV file. '
            f'[video_id: {recorded_program.id}, container_format: {recorded_program.recorded_video.container_format}]'
        )
        raise HTTPException(
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail = 'Specified video is not an MMT/TLV file',
        )

    # 録画ファイルの存在を確認する
    file_path = pathlib.Path(recorded_program.recorded_video.file_path)
    if file_path.is_file() is False:
        logging.error(
            f'[VideoStreamsRouter][VideoRawMMTSStreamAPI] Recorded video file was not found. '
            f'[video_id: {recorded_program.id}, file_path: {file_path}]'
        )
        raise HTTPException(
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail = 'Recorded video file was not found',
        )

    return FileResponse(
        path = file_path,
        media_type = 'video/mp2t',
        headers = {
            'Cache-Control': 'no-store',
        },
    )


@router.get(
    '/{video_id}/{quality}/playlist',
    summary = '録画番組 HLS M3U8 プレイリスト API',
    response_class = Response,
    responses = {
        status.HTTP_200_OK: {
            'description': '録画番組の HLS M3U8 プレイリスト。',
            'content': {'application/vnd.apple.mpegurl': {}},
        }
    }
)
async def VideoHLSPlaylistAPI(
    recorded_program: Annotated[RecordedProgram, Depends(ValidateVideoID)],
    stream_quality: Annotated[StreamQualityWithOptions, Depends(ValidateQuality)],
    session_id: Annotated[str, Query(description='セッション ID（クライアント側で適宜生成したランダム値を指定する）。')],
    cache_key: Annotated[str | None, Query(description='キャッシュ制御用のキー。')] = None,
):
    """
    指定された画質に対応する、録画番組のストリーミング用 HLS M3U8 プレイリストを返す。<br>
    この M3U8 プレイリストは仮想的なもので、すべてのセグメントデータがエンコード済みとは限らない。セグメントはリクエストされ次第随時生成される。
    """

    # MPEG-TS パススルー品質では、元映像をそのまま配信できる録画だけを受け付ける
    ValidateVideoCopyQuality(recorded_program, stream_quality)

    # 品質とオプション指定に対応する録画視聴セッションを作成または取得
    video_stream = VideoStream(
        session_id,
        recorded_program,
        stream_quality.quality,
        stream_quality.encoding_options,
        is_new_session_allowed = True,
    )

    # 仮想 HLS M3U8 プレイリストを取得
    virtual_playlist = await video_stream.getVirtualPlaylist(cache_key)
    return Response(
        content = virtual_playlist,
        media_type = 'application/vnd.apple.mpegurl',
        headers = {
            'Cache-Control': 'max-age=0',
        },
    )


@router.get(
    '/{video_id}/{quality}/segment',
    summary = '録画番組 HLS セグメント API',
    response_class = Response,
    responses = {
        status.HTTP_200_OK: {
            'description': 'HLS セグメントとして分割された MPEG-TS データ。',
            'content': {'video/mp2t': {}},
        }
    }
)
async def VideoHLSSegmentAPI(
    recorded_program: Annotated[RecordedProgram, Depends(ValidateVideoID)],
    stream_quality: Annotated[StreamQualityWithOptions, Depends(ValidateQuality)],
    session_id: Annotated[str, Query(description='セッション ID（クライアント側で適宜生成したランダム値を指定する）。')],
    sequence: Annotated[int, Query(description='HLS セグメントの 0 スタートのシーケンス番号。')],
    cache_key: Annotated[str | None, Query(description='キャッシュ制御用のキー。')],
):
    """
    指定された画質に対応する、録画番組のストリーミング用 HLS セグメントを返す。<br>
    呼び出された時点でエンコードされていない場合は既存のエンコードタスクが終了され、<br>
    sequence の HLS セグメントが含まれる範囲から新たにエンコードタスクが開始される。
    """

    # MPEG-TS パススルー品質では、元映像をそのまま配信できる録画だけを受け付ける
    ValidateVideoCopyQuality(recorded_program, stream_quality)

    # 品質とオプション指定に対応する録画視聴セッションを取得
    video_stream = VideoStream(session_id, recorded_program, stream_quality.quality, stream_quality.encoding_options)

    # セグメントを取得（キャッシュキーはブラウザキャッシュ避けのための ID なので特に使わない）
    segment_data = await video_stream.getSegment(sequence)
    if segment_data is None:
        logging.error(
            f'{video_stream.log_prefix} Specified sequence segment was not found. '
            f'[sequence: {sequence}]'
        )
        raise HTTPException(
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail = 'Specified sequence segment was not found',
        )

    # 取得した MPEG-TS データを返す
    return Response(
        content = segment_data,
        media_type = 'video/mp2t',
        headers = {
            # キャッシュ有効期間を3時間に設定
            'Cache-Control': 'max-age=10800',
        },
    )


@router.get(
    '/{video_id}/{quality}/buffer',
    summary = '録画番組 HLS バッファ範囲 API',
    response_class = Response,
    responses = {
        status.HTTP_200_OK: {
            'description': '録画番組の HLS バッファ範囲が随時配信されるイベントストリーム。',
            'content': {'text/event-stream': {}},
        }
    }
)
async def VideoHLSBufferAPI(
    recorded_program: Annotated[RecordedProgram, Depends(ValidateVideoID)],
    stream_quality: Annotated[StreamQualityWithOptions, Depends(ValidateQuality)],
    session_id: Annotated[str, Query(description='セッション ID（クライアント側で適宜生成したランダム値を指定する）。')],
):
    """
    録画番組の HLS バッファ範囲を Server-Sent Events で随時配信する。

    イベントには、
    - バッファ範囲の更新を示す **buffer_range_update**
    の1種類がある。

    どのイベントでも配信される JSON 構造は同じ。<br>
    エンコードタスクが終了した場合は、接続を終了する。
    """

    # MPEG-TS パススルー品質では、元映像をそのまま配信できる録画だけを受け付ける
    ValidateVideoCopyQuality(recorded_program, stream_quality)

    # 品質とオプション指定に対応する録画視聴セッションを取得
    video_stream = VideoStream(session_id, recorded_program, stream_quality.quality, stream_quality.encoding_options)

    # バッファ範囲の変更を監視し、変更があればバッファ範囲をイベントストリームとして出力する
    async def generator():
        """イベントストリームを出力するジェネレーター"""

        # 初期値
        previous_buffer_range = video_stream.getBufferRange()

        # 初回接続時に必ず現在のバッファ範囲を返す
        yield {
            'event': 'buffer_range_update',  # buffer_range_update イベントを設定
            'data': json.dumps({
                'begin': previous_buffer_range[0],
                'end': previous_buffer_range[1],
            }),
        }

        while True:

            # 現在のバッファ範囲を取得
            buffer_range = video_stream.getBufferRange()

            # 以前の結果と異なっている場合のみレスポンスを返す
            if previous_buffer_range != buffer_range:
                logging.info(f'{video_stream.log_prefix} Buffer range updated. [begin: {buffer_range[0]}, end: {buffer_range[1]}]')
                yield {
                    'event': 'buffer_range_update',  # buffer_range_update イベントを設定
                    'data': json.dumps({
                        'begin': buffer_range[0],
                        'end': buffer_range[1],
                    }),
                }

                # 取得結果を保存
                previous_buffer_range = buffer_range

            # ビジーにならないように、0.1秒ごとにチェックする
            await asyncio.sleep(0.1)

    # EventSourceResponse でイベントストリームを配信する
    return EventSourceResponse(generator())


@router.put(
    '/{video_id}/{quality}/keep-alive',
    summary = '録画番組 HLS Keep-Alive API',
    status_code = status.HTTP_204_NO_CONTENT,
)
async def VideoHLSKeepAliveAPI(
    recorded_program: Annotated[RecordedProgram, Depends(ValidateVideoID)],
    stream_quality: Annotated[StreamQualityWithOptions, Depends(ValidateQuality)],
    session_id: Annotated[str, Query(description='セッション ID（クライアント側で適宜生成したランダム値を指定する）。')],
):
    """
    録画番組のストリーミング用 HLS セグメントの生成を継続するための API 。<br>
    ストリーミングセッションを維持するために、この API は録画番組の視聴を続けている間、定期的に呼び出さなければならない。<br>
    この API が定期的に呼び出されなくなった場合、一定時間後にストリーミング用 HLS セグメントの生成が停止され、メモリ上のデータが破棄される。
    """

    # MPEG-TS パススルー品質では、元映像をそのまま配信できる録画だけを受け付ける
    ValidateVideoCopyQuality(recorded_program, stream_quality)

    # 品質とオプション指定に対応する録画視聴セッションを取得
    video_stream = VideoStream(session_id, recorded_program, stream_quality.quality, stream_quality.encoding_options)

    # セッションのアクティブ状態を維持する
    video_stream.keepAlive()

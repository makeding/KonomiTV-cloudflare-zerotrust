import asyncio
import faulthandler
import sys
from typing import TextIO

from app import logging
from app.utils.LogRotation import DailyRotatingFileHandler


EVENT_LOOP_HEARTBEAT_INTERVAL_SECONDS = 1.0
EVENT_LOOP_BLOCK_TIMEOUT_SECONDS = 5.0

# 監視タスクが GC で破棄されず、起動・終了時に同じタスクを確実に管理できるよう強参照を保持する。
event_loop_block_detector_task: asyncio.Task[None] | None = None


def GetServerLogStream() -> TextIO:
    """
    イベントループ停止中のスレッドダンプを書き込むストリームを取得する。

    Returns:
        TextIO: 通常は KonomiTV サーバーログ、ファイルハンドラーがない場合は標準エラー出力。
    """

    # faulthandler は Python のロギング処理を経由せず直接ファイルへ書き込むため、
    # 通常の KonomiTV サーバーログを所有するハンドラーのストリームを明示的に渡す。
    for handler in logging.logger.handlers:
        if isinstance(handler, DailyRotatingFileHandler) and handler.stream is not None:
            return handler.stream

    # テストや特殊な起動構成でファイルハンドラーがない場合も、診断自体は標準エラー出力へ残す。
    return sys.stderr


async def MonitorEventLoopBlocking() -> None:
    """
    asyncio イベントループのハートビートを監視し、長時間停止時に全 Python スレッドのスタックを記録する。

    Returns:
        None: タスクがキャンセルされるまで監視を継続する。
    """

    loop = asyncio.get_running_loop()
    try:
        while True:
            # faulthandler の監視は CPython 内部の独立した watchdog が担当する。
            # このためイベントループだけでなく、Python の別監視スレッドが GIL を取得できない停止でもダンプを残せる。
            faulthandler.cancel_dump_traceback_later()
            faulthandler.dump_traceback_later(
                EVENT_LOOP_BLOCK_TIMEOUT_SECONDS,
                repeat=False,
                file=GetServerLogStream(),
            )

            heartbeat_started_at = loop.time()
            await asyncio.sleep(EVENT_LOOP_HEARTBEAT_INTERVAL_SECONDS)
            heartbeat_elapsed_seconds = loop.time() - heartbeat_started_at
            faulthandler.cancel_dump_traceback_later()

            # タイムアウト後にイベントループが復帰した場合は、直前の生スレッドダンプと対応する復帰時刻を通常ログへ残す。
            if heartbeat_elapsed_seconds >= EVENT_LOOP_BLOCK_TIMEOUT_SECONDS:
                logging.error(
                    '[EventLoopBlockDetector] Event loop responsiveness recovered. '
                    f'[heartbeat_elapsed: {heartbeat_elapsed_seconds:.3f}s]',
                )
    finally:
        # 正常終了時に古いタイマーが残り、シャットダウン処理を誤検知しないよう必ず解除する。
        faulthandler.cancel_dump_traceback_later()


def StartEventLoopBlockDetector() -> None:
    """
    イベントループ停止検出タスクを開始する。

    Returns:
        None: 既に監視中の場合は何も変更しない。
    """

    global event_loop_block_detector_task

    # startup イベントが重複して呼ばれても監視タスクを二重起動しない。
    if event_loop_block_detector_task is not None and event_loop_block_detector_task.done() is False:
        return
    event_loop_block_detector_task = asyncio.create_task(
        MonitorEventLoopBlocking(),
        name='EventLoopBlockDetector',
    )
    logging.info(
        '[EventLoopBlockDetector] Started. '
        f'[timeout: {EVENT_LOOP_BLOCK_TIMEOUT_SECONDS:.1f}s]',
    )


async def StopEventLoopBlockDetector() -> None:
    """
    イベントループ停止検出タスクを終了する。

    Returns:
        None: 監視タスクのキャンセル完了後に戻る。
    """

    global event_loop_block_detector_task

    detector_task = event_loop_block_detector_task
    event_loop_block_detector_task = None
    if detector_task is None or detector_task.done() is True:
        faulthandler.cancel_dump_traceback_later()
        return

    detector_task.cancel()
    try:
        await detector_task
    except asyncio.CancelledError:
        pass



import asyncio
import pathlib
import sys

from app import logging
from app.constants import LIBRARY_PATH


# サーバー起動時に検出した VAAPI render device を保持する。
## CM 解析のたびに /dev/dri の列挙や FFmpeg の初期化確認を繰り返さず、全解析で同じ検出結果を参照する。
_vaapi_hardware_devices: tuple[str, ...] = ()
_is_vaapi_hardware_devices_initialized = False


async def InitializeVAAPIHardwareDevices(
    dri_directory: pathlib.Path = pathlib.Path('/dev/dri'),
    ffmpeg_path: pathlib.Path = pathlib.Path(LIBRARY_PATH['FFmpeg']),
) -> None:
    """
    Linux の DRI render node を列挙し、VAAPI を初期化できるデバイスをキャッシュする。

    Args:
        dri_directory (pathlib.Path): DRI render node が配置されているディレクトリ。
        ffmpeg_path (pathlib.Path): VAAPI の初期化確認に使う FFmpeg のパス。

    Returns:
        None
    """

    global _is_vaapi_hardware_devices_initialized, _vaapi_hardware_devices

    # FastAPI の startup イベントが重複して呼ばれても、ハードウェア検出は起動中に一度だけ実行する。
    if _is_vaapi_hardware_devices_initialized is True:
        return
    _is_vaapi_hardware_devices_initialized = True

    # VAAPI と DRI render node は Linux 固有なので、他の OS では CPU 解析を利用する。
    if sys.platform != 'linux' or dri_directory.is_dir() is False or ffmpeg_path.is_file() is False:
        logging.info('[HardwareDevice] No VAAPI hardware device is available. CM analysis will use CPU.')
        return

    available_devices: list[str] = []
    for render_device in sorted(dri_directory.glob('renderD*')):
        # ファイル名だけ存在する無効なノードを採用しないよう、FFmpeg で VAAPI device と surface を実際に初期化する。
        device_name = f'vaapi:{render_device}'
        try:
            process = await asyncio.create_subprocess_exec(
                str(ffmpeg_path),
                '-hide_banner', '-loglevel', 'error', '-nostdin',
                '-init_hw_device', f'vaapi=va:{render_device}',
                '-filter_hw_device', 'va',
                '-f', 'lavfi', '-i', 'color=size=16x16:rate=1',
                '-vf', 'format=nv12,hwupload',
                '-frames:v', '1', '-f', 'null', '-',
                stdout = asyncio.subprocess.DEVNULL,
                stderr = asyncio.subprocess.PIPE,
            )
            try:
                _, stderr = await asyncio.wait_for(process.communicate(), timeout=10)
            except TimeoutError:
                process.kill()
                await process.wait()
                logging.warning(f'[HardwareDevice] VAAPI probe timed out. [device: {render_device}]')
                continue
        except OSError as ex:
            logging.warning(f'[HardwareDevice] Failed to start VAAPI probe. [device: {render_device}]', exc_info=ex)
            continue

        if process.returncode == 0:
            available_devices.append(device_name)
            logging.info(f'[HardwareDevice] VAAPI hardware device is available. [device: {render_device}]')
            continue

        error_message = stderr.decode('utf-8', errors='replace').strip()
        logging.warning(
            f'[HardwareDevice] VAAPI hardware device is unavailable. [device: {render_device}] '
            f'[error: {error_message or f"FFmpeg exited with code {process.returncode}."}]'
        )

    _vaapi_hardware_devices = tuple(available_devices)
    if len(_vaapi_hardware_devices) == 0:
        logging.info('[HardwareDevice] No VAAPI hardware device passed probing. CM analysis will use CPU.')


def GetVAAPIHardwareDevices() -> tuple[str, ...]:
    """
    サーバー起動時に利用可能と判定された VAAPI hardware device を返す。

    Returns:
        tuple[str, ...]: FFMS2 に渡せる VAAPI hardware device の一覧。
    """

    return _vaapi_hardware_devices

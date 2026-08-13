
import asyncio
import pathlib

import pytest

from app.utils import HardwareDevice


class FakeProcess:
    """VAAPI 初期化確認プロセスの終了状態と標準エラーだけを再現する。"""

    def __init__(self, returncode: int, stderr: bytes) -> None:
        """
        Args:
            returncode (int): FFmpeg の終了コード。
            stderr (bytes): FFmpeg の標準エラー。

        Returns:
            None
        """

        self.returncode = returncode
        self.stderr = stderr


    async def communicate(self) -> tuple[bytes, bytes]:
        """
        Returns:
            tuple[bytes, bytes]: 空の標準出力と設定済みの標準エラー。
        """

        return b'', self.stderr


def test_vaapi_devices_are_probed_once_and_cached(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """起動時に全 render node を検証し、成功したデバイスだけを一度だけキャッシュする。"""

    dri_directory = tmp_path / 'dri'
    dri_directory.mkdir()
    (dri_directory / 'renderD128').touch()
    (dri_directory / 'renderD129').touch()
    ffmpeg_path = tmp_path / 'ffmpeg.elf'
    ffmpeg_path.touch()
    processes = [
        FakeProcess(1, b'failed to initialise VAAPI'),
        FakeProcess(0, b''),
    ]
    commands: list[tuple[str, ...]] = []

    async def CreateSubprocessExec(*command: str, **kwargs: object) -> FakeProcess:
        del kwargs
        commands.append(command)
        return processes[len(commands) - 1]

    monkeypatch.setattr(HardwareDevice.sys, 'platform', 'linux')
    monkeypatch.setattr(HardwareDevice.asyncio, 'create_subprocess_exec', CreateSubprocessExec)
    monkeypatch.setattr(HardwareDevice, '_is_vaapi_hardware_devices_initialized', False)
    monkeypatch.setattr(HardwareDevice, '_vaapi_hardware_devices', ())

    asyncio.run(HardwareDevice.InitializeVAAPIHardwareDevices(dri_directory, ffmpeg_path))
    asyncio.run(HardwareDevice.InitializeVAAPIHardwareDevices(dri_directory, ffmpeg_path))

    assert len(commands) == 2
    assert '/dev/dri' not in ' '.join(commands[0])
    assert f'vaapi=va:{dri_directory}/renderD128' in commands[0]
    assert f'vaapi=va:{dri_directory}/renderD129' in commands[1]
    assert HardwareDevice.GetVAAPIHardwareDevices() == (f'vaapi:{dri_directory}/renderD129',)

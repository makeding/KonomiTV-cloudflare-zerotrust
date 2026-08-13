# pyright: reportPrivateUsage=false

import asyncio
import errno
import json
import sys
from collections.abc import Mapping
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from typing import cast

import pytest

from app.metadata.CMAnalyzer import (
    CMAnalyzerRequest,
    GenericCMAnalyzer,
    _PreparedMedia,
    _ProcessResult,
)


def CreateRuntime(tmp_path: Path) -> GenericCMAnalyzer:
    runtime = tmp_path / 'runtime'
    (runtime / 'JL').mkdir(parents=True)
    for relative_path in (
        'libffms2.so',
        'ffmsindex',
        'chapter_exe',
        'logoframe',
        'join_logo_scp',
        'JL/JL_標準.txt',
    ):
        (runtime / relative_path).write_bytes(b'test')
    (runtime / 'Runtime-Manifest.json').write_text(
        '{"schema_version":1,"components":{},"patches":{}}\n',
        encoding='utf-8',
    )
    ffmpeg = tmp_path / 'ffmpeg8.elf'
    ffprobe = tmp_path / 'ffprobe8.elf'
    ffmpeg.write_bytes(b'test')
    ffprobe.write_bytes(b'test')
    return GenericCMAnalyzer(runtime_directory=runtime, ffmpeg_path=ffmpeg, ffprobe_path=ffprobe)


def CreateRequest(
    tmp_path: Path,
    *,
    service_id: int | None = None,
    logo_paths: tuple[Path, ...] = (),
    hardware_device: str | None = None,
) -> CMAnalyzerRequest:
    recorded = tmp_path / 'recording.mkv'
    recorded.write_bytes(b'media')
    (tmp_path / 'work').mkdir(exist_ok=True)
    return CMAnalyzerRequest(
        recorded_file_path=recorded,
        work_directory=tmp_path / 'work',
        service_id=service_id,
        logo_paths=logo_paths,
        hardware_devices=(hardware_device,) if hardware_device is not None else (),
        duration_seconds=60.0,
    )


def ProbePayload(*, format_name: str = 'matroska,webm', codec: str = 'av1') -> dict[str, object]:
    return {
        'format': {'format_name': format_name, 'duration': '60.06'},
        'streams': [
            {
                'index': 0,
                'codec_type': 'video',
                'codec_name': codec,
                'pix_fmt': 'yuv420p10le',
                'width': 3840,
                'height': 2160,
                'field_order': 'progressive',
                'time_base': '1/1000',
                'start_time': '1.500',
                'avg_frame_rate': '24000/1001',
                'disposition': {'default': 1},
            },
            {
                'index': 1,
                'codec_type': 'audio',
                'codec_name': 'opus',
                'time_base': '1/48000',
                'start_time': '1.600',
                'disposition': {'default': 1},
            },
        ],
        'programs': [],
    }


def WriteFFmpegOutputs(command: tuple[str, ...]) -> None:
    """テスト用FFmpeg commandの明示された各outputを生成する。"""

    for index, argument in enumerate(command[:-2]):
        if argument == '-f' and command[index + 1] in ('matroska', 'wav'):
            Path(command[index + 2]).write_bytes(b'prepared-output')


def PreparedVideoPayload(payload: dict[str, object]) -> dict[str, object]:
    return {'streams': [cast(list[dict[str, object]], payload['streams'])[0]]}


def PreparedAudioPayload(payload: dict[str, object]) -> dict[str, object]:
    source_audio = cast(list[dict[str, object]], payload['streams'])[1]
    return {'streams': [{**source_audio, 'index': 0}]}


def InstallSuccessfulProcesses(
    analyzer: GenericCMAnalyzer,
    payload: dict[str, object],
    commands: list[tuple[str, ...]],
) -> None:
    async def RunProcess(command: tuple[str, ...], environment: Mapping[str, str]) -> _ProcessResult:
        del environment
        commands.append(command)
        if command[0] == str(analyzer.ffprobe_path):
            if command[-1].endswith('prepared-media.cmwork'):
                return _ProcessResult(0, json.dumps(PreparedVideoPayload(payload)))
            if command[-1].endswith('prepared-audio.wav'):
                return _ProcessResult(0, json.dumps(PreparedAudioPayload(payload)))
            return _ProcessResult(0, json.dumps(payload))
        if command[0] == str(analyzer.ffmpeg_path):
            WriteFFmpegOutputs(command)
            return _ProcessResult(0, '')
        if command[0] == str(analyzer.ffmsindex_path):
            Path(command[-1]).write_bytes(b'ffindex')
            return _ProcessResult(0, '')
        if command[0] == str(analyzer.chapter_executable_path):
            Path(command[command.index('-o') + 1]).write_text('# SCPos: 1799 0\n', encoding='utf-8')
            return _ProcessResult(0, 'Video Frames: 1800')
        if command[0] == str(analyzer.logoframe_path):
            analysis_path = Path(command[command.index('-oa') + 1])
            result_path = analysis_path.with_name('selected-logo.txt')
            result_path.write_text('0 S 0 ALL\n900 E 0 ALL\n', encoding='utf-8')
            analysis_path.with_name(f'{analysis_path.stem}_list.ini').write_text(
                '\n'.join((
                    '[logodata]',
                    'LogoTotalN=1',
                    'FrameTotal=1800',
                    'LogoName_N1=logo.lgd',
                    f'oaFileName_N1={result_path}',
                )),
                encoding='utf-8',
            )
            return _ProcessResult(0, '')
        trim_path = Path(command[command.index('-o') + 1])
        trim_path.write_text('Trim(0,899) ++ Trim(1200,1799)\n', encoding='utf-8')
        return _ProcessResult(0, '')

    analyzer._runProcess = RunProcess  # type: ignore[method-assign]


def test_descriptor_selects_sid_program_and_ignores_attached_picture(tmp_path: Path) -> None:
    analyzer = CreateRuntime(tmp_path)
    request = CreateRequest(tmp_path, service_id=101)
    payload = {
        'format': {'format_name': 'mpegts', 'duration': '120'},
        'streams': [
            {
                'index': 0,
                'codec_type': 'video',
                'codec_name': 'mjpeg',
                'width': 4000,
                'height': 3000,
                'disposition': {'attached_pic': 1, 'default': 1},
            },
            {'index': 1, 'codec_type': 'video', 'codec_name': 'h264', 'width': 1920, 'height': 1080},
            {'index': 2, 'codec_type': 'audio', 'codec_name': 'aac'},
            {'index': 3, 'codec_type': 'video', 'codec_name': 'hevc', 'width': 3840, 'height': 2160},
            {'index': 4, 'codec_type': 'audio', 'codec_name': 'aac'},
        ],
        'programs': [
            {'program_id': 101, 'streams': [{'index': 1}, {'index': 2}]},
            {'program_id': 202, 'streams': [{'index': 3}, {'index': 4}]},
        ],
    }

    async def RunProcess(command: tuple[str, ...], environment: Mapping[str, str]) -> _ProcessResult:
        del command, environment
        return _ProcessResult(0, json.dumps(payload))

    analyzer._runProcess = RunProcess  # type: ignore[method-assign]
    descriptor = asyncio.run(analyzer.resolveInputDescriptor(request))

    assert descriptor.video_stream_index == 1
    assert descriptor.audio_stream_index == 2
    assert descriptor.video_codec_name == 'h264'
    assert descriptor.program_id == 101
    assert descriptor.service_id == 101


def test_descriptor_never_mixes_video_and_audio_from_different_programs(tmp_path: Path) -> None:
    """SID番組に映像がなければ、実際に選んだ映像番組の音声を組み合わせる。"""

    analyzer = CreateRuntime(tmp_path)
    payload = {
        'format': {'format_name': 'mpegts', 'duration': '60'},
        'streams': [
            {'index': 2, 'codec_type': 'audio', 'codec_name': 'aac'},
            {'index': 3, 'codec_type': 'video', 'codec_name': 'av1', 'width': 1920, 'height': 1080},
            {'index': 4, 'codec_type': 'audio', 'codec_name': 'opus'},
        ],
        'programs': [
            {'program_id': 101, 'streams': [{'index': 2}]},
            {'program_id': 202, 'streams': [{'index': 3}, {'index': 4}]},
        ],
    }

    async def RunProcess(command: tuple[str, ...], environment: Mapping[str, str]) -> _ProcessResult:
        del command, environment
        return _ProcessResult(0, json.dumps(payload))

    analyzer._runProcess = RunProcess  # type: ignore[method-assign]
    descriptor = asyncio.run(analyzer.resolveInputDescriptor(CreateRequest(tmp_path, service_id=101)))

    assert descriptor.video_stream_index == 3
    assert descriptor.audio_stream_index == 4
    assert descriptor.program_id == 202
    script = analyzer._buildAviSynthScript(
        descriptor,
        _PreparedMedia(
            media_path=tmp_path / 'prepared-media.cmwork',
            index_path=tmp_path / 'prepared.ffindex',
            video_stream_index=0,
            audio_path=tmp_path / 'prepared-audio.wav',
            audio_index_path=tmp_path / 'prepared-audio.ffindex',
            audio_stream_index=0,
        ),
        None,
        for_chapter=True,
    )
    assert 'FFVideoSource' in script
    assert 'track=0' in script
    assert 'FFAudioSource' in script


@pytest.mark.parametrize(
    ('format_name', 'codec'),
    [
        ('mpegts', 'h264'),
        ('mpegts', 'hevc'),
        ('mpegts', 'av1'),
        ('mov,mp4,m4a,3gp,3g2,mj2', 'hevc'),
        ('matroska,webm', 'vp9'),
        ('ogg', 'theora'),
    ],
)
def test_registered_container_and_codec_names_do_not_gate_analysis(
    tmp_path: Path,
    format_name: str,
    codec: str,
) -> None:
    analyzer = CreateRuntime(tmp_path)
    commands: list[tuple[str, ...]] = []
    InstallSuccessfulProcesses(analyzer, ProbePayload(format_name=format_name, codec=codec), commands)

    result = asyncio.run(analyzer.analyze(CreateRequest(tmp_path, service_id=None)))

    assert result.status == 'completed'
    assert result.descriptor is not None
    assert result.descriptor.format_name == format_name
    assert result.descriptor.video_codec_name == codec
    assert result.descriptor.service_id is None
    assert result.sections == ({'start_time': 30.03, 'end_time': 40.04},)
    assert all('Amatsukaze' not in argument for command in commands for argument in command)


def test_audio_only_input_is_stably_unsupported(tmp_path: Path) -> None:
    analyzer = CreateRuntime(tmp_path)

    async def RunProcess(command: tuple[str, ...], environment: Mapping[str, str]) -> _ProcessResult:
        del command, environment
        return _ProcessResult(0, json.dumps({
            'format': {'format_name': 'ogg', 'duration': '60'},
            'streams': [{'index': 0, 'codec_type': 'audio', 'codec_name': 'opus'}],
        }))

    analyzer._runProcess = RunProcess  # type: ignore[method-assign]
    result = asyncio.run(analyzer.analyze(CreateRequest(tmp_path)))

    assert result.status == 'unsupported'
    assert result.error_code == 'VideoStreamUnavailable'


def test_video_without_audio_is_stably_unsupported_without_synthesized_silence(tmp_path: Path) -> None:
    analyzer = CreateRuntime(tmp_path)
    payload = ProbePayload()
    payload['streams'] = cast(list[dict[str, object]], payload['streams'])[:1]

    async def RunProcess(command: tuple[str, ...], environment: Mapping[str, str]) -> _ProcessResult:
        del command, environment
        return _ProcessResult(0, json.dumps(payload))

    analyzer._runProcess = RunProcess  # type: ignore[method-assign]
    result = asyncio.run(analyzer.analyze(CreateRequest(tmp_path)))

    assert result.status == 'unsupported'
    assert result.error_code == 'AudioStreamUnavailable'


def test_variable_video_format_is_rejected_before_frames_can_be_silently_dropped(tmp_path: Path) -> None:
    analyzer = CreateRuntime(tmp_path)
    commands: list[tuple[str, ...]] = []
    InstallSuccessfulProcesses(analyzer, ProbePayload(), commands)
    request = replace(CreateRequest(tmp_path), has_variable_video_format=True)

    result = asyncio.run(analyzer.analyze(request))

    assert result.status == 'unsupported'
    assert result.error_code == 'VariableVideoFormat'
    assert all(command[0] != str(analyzer.chapter_executable_path) for command in commands)


def test_variable_audio_stream_is_rejected_before_audio_can_be_silently_dropped(tmp_path: Path) -> None:
    analyzer = CreateRuntime(tmp_path)
    commands: list[tuple[str, ...]] = []
    InstallSuccessfulProcesses(analyzer, ProbePayload(), commands)
    descriptor = asyncio.run(analyzer.resolveInputDescriptor(CreateRequest(tmp_path)))
    request = replace(
        CreateRequest(tmp_path),
        input_descriptor=replace(descriptor, has_variable_audio_stream=True),
    )

    result = asyncio.run(analyzer.analyze(request))

    assert result.status == 'unsupported'
    assert result.error_code == 'VariableAudioStream'
    assert all(command[0] != str(analyzer.ffmpeg_path) for command in commands)


def test_preparation_separates_shared_cfr_video_and_chapter_pcm_without_codec_or_bs4k_branch(
    tmp_path: Path,
) -> None:
    analyzer = CreateRuntime(tmp_path)
    descriptor_payload = ProbePayload(format_name='mpegts', codec='hevc')
    commands: list[tuple[str, ...]] = []
    InstallSuccessfulProcesses(analyzer, descriptor_payload, commands)
    result = asyncio.run(analyzer.analyze(CreateRequest(tmp_path, service_id=101)))

    assert result.status == 'completed'
    chapter_script = (tmp_path / 'work/cpu/chapter.avs').read_text(encoding='utf-8')
    logo_free_script = chapter_script
    assert 'FFVideoSource(' in chapter_script
    assert 'track=0' in chapter_script
    assert 'prepared-media.cmwork' in chapter_script
    assert 'prepared.ffindex' in chapter_script
    assert 'FFAudioSource(' in chapter_script
    assert 'prepared-audio.wav' in chapter_script
    assert 'prepared-audio.ffindex' in chapter_script
    assert 'clip = AudioDubEx(video, audio)' in chapter_script
    assert 'clip = DelayAudio(clip, 0.100000000)' in chapter_script
    assert 'fpsnum=30000, fpsden=1001' in chapter_script
    assert 'ConvertBits(clip, 8)' in chapter_script
    assert 'ConvertToYV12(clip)' in chapter_script
    assert 'Spline36Resize(clip, 1920, 1080)' in chapter_script
    prepare_command = next(
        command for command in commands
        if command[0] == str(analyzer.ffmpeg_path) and str(tmp_path / 'recording.mkv') in command
    )
    mapped_streams = [
        prepare_command[index + 1]
        for index, argument in enumerate(prepare_command[:-1])
        if argument == '-map'
    ]
    assert mapped_streams == ['0:0', '0:1']
    assert prepare_command[prepare_command.index('-c:v') + 1] == 'copy'
    assert [
        prepare_command[index + 1]
        for index, argument in enumerate(prepare_command[:-1])
        if argument == '-f'
    ] == ['matroska', 'wav']
    video_output_index = prepare_command.index(str(tmp_path / 'work/prepared-media.cmwork.partial'))
    assert '-an' in prepare_command[:video_output_index]
    assert prepare_command[prepare_command.index('-ac') + 1] == '1'
    assert prepare_command[prepare_command.index('-ar') + 1] == '48000'
    assert prepare_command[prepare_command.index('-c:a') + 1] == 'pcm_s16le'
    assert prepare_command[prepare_command.index('-rf64') + 1] == 'auto'
    index_commands = [command for command in commands if command[0] == str(analyzer.ffmsindex_path)]
    assert len(index_commands) == 2
    assert {command[-2] for command in index_commands} == {
        str(tmp_path / 'work/prepared-media.cmwork'),
        str(tmp_path / 'work/prepared-audio.wav'),
    }
    chapter_command = next(
        command for command in commands if command[0] == str(analyzer.chapter_executable_path)
    )
    assert '-a' not in chapter_command
    assert len([command for command in commands if command[0] == str(analyzer.ffmpeg_path)]) == 1
    assert 'BlankClip' not in chapter_script
    assert 'Amatsukaze' not in logo_free_script


def test_negative_audio_start_offset_is_restored_after_timestamp_reset(tmp_path: Path) -> None:
    analyzer = CreateRuntime(tmp_path)
    payload = ProbePayload()
    streams = cast(list[dict[str, object]], payload['streams'])
    streams[1]['start_time'] = '1.400'
    commands: list[tuple[str, ...]] = []
    InstallSuccessfulProcesses(analyzer, payload, commands)

    result = asyncio.run(analyzer.analyze(CreateRequest(tmp_path)))

    assert result.status == 'completed'
    chapter_script = (tmp_path / 'work/cpu/chapter.avs').read_text(encoding='utf-8')
    assert 'clip = DelayAudio(clip, -0.100000000)' in chapter_script
    assert len([command for command in commands if command[0] == str(analyzer.ffmpeg_path)]) == 1


def test_equal_audio_and_video_start_omits_delay_without_extra_ffmpeg_pass(tmp_path: Path) -> None:
    analyzer = CreateRuntime(tmp_path)
    payload = ProbePayload()
    streams = cast(list[dict[str, object]], payload['streams'])
    streams[1]['start_time'] = streams[0]['start_time']
    commands: list[tuple[str, ...]] = []
    InstallSuccessfulProcesses(analyzer, payload, commands)

    result = asyncio.run(analyzer.analyze(CreateRequest(tmp_path)))

    assert result.status == 'completed'
    ffmpeg_commands = [command for command in commands if command[0] == str(analyzer.ffmpeg_path)]
    assert len(ffmpeg_commands) == 1
    assert (tmp_path / 'work/prepared-audio.wav').is_file()
    chapter_script = (tmp_path / 'work/cpu/chapter.avs').read_text(encoding='utf-8')
    assert 'FFAudioSource(' in chapter_script
    assert 'DelayAudio(' not in chapter_script


def test_missing_audio_output_publishes_neither_prepared_output(tmp_path: Path) -> None:
    analyzer = CreateRuntime(tmp_path)
    payload = ProbePayload()

    async def RunProcess(command: tuple[str, ...], environment: Mapping[str, str]) -> _ProcessResult:
        del environment
        if command[0] == str(analyzer.ffprobe_path):
            return _ProcessResult(0, json.dumps(payload))
        if command[0] == str(analyzer.ffmpeg_path):
            video_output_index = command.index('-f') + 2
            Path(command[video_output_index]).write_bytes(b'prepared-video')
            return _ProcessResult(0, '')
        raise AssertionError(f'Unexpected command after failed preparation: {command}')

    analyzer._runProcess = RunProcess  # type: ignore[method-assign]

    result = asyncio.run(analyzer.analyze(CreateRequest(tmp_path)))

    assert result.status == 'analysis_failed'
    assert result.error_code == 'MediaPreparationFailed'
    assert result.error_message is not None
    assert result.error_message.endswith('FFmpeg did not produce both prepared video and audio.')
    assert (tmp_path / 'work/prepared-media.cmwork').exists() is False
    assert (tmp_path / 'work/prepared-audio.wav').exists() is False
    assert list((tmp_path / 'work').glob('*.partial*')) == []


def test_logo_frame_uses_shared_index_and_parallel_ranges_before_passing_match_to_jls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analyzer = CreateRuntime(tmp_path)
    monkeypatch.setattr(GenericCMAnalyzer, '_effectiveCPUCount', staticmethod(lambda: 12))
    logo = tmp_path / 'logo.lgd'
    logo.write_bytes(b'logo')
    commands: list[tuple[str, ...]] = []
    InstallSuccessfulProcesses(analyzer, ProbePayload(), commands)

    result = asyncio.run(analyzer.analyze(CreateRequest(tmp_path, logo_paths=(logo,))))

    assert result.status == 'completed'
    assert result.matched_logo == 'logo.lgd'
    logo_commands = [command for command in commands if command[0] == str(analyzer.logoframe_path)]
    assert len(logo_commands) == 1
    logo_command = logo_commands[0]
    assert '-oa' in logo_command
    assert '-o' not in logo_command
    assert logo_command[logo_command.index('-parallel') + 1] == '3'
    assert logo_command[logo_command.index('-logo1') + 1] == str(logo)
    chapter_script = (tmp_path / 'work/cpu/chapter.avs').read_text(encoding='utf-8')
    logo_script = (tmp_path / 'work/cpu/logo.avs').read_text(encoding='utf-8')
    shared_media = str(tmp_path / 'work/prepared-media.cmwork')
    shared_index = str(tmp_path / 'work/prepared.ffindex')
    assert shared_media in chapter_script and shared_media in logo_script
    assert f'cachefile="{shared_index}"' in chapter_script
    assert f'cachefile="{shared_index}"' in logo_script
    assert 'prepared-audio.wav' in chapter_script
    assert 'prepared-audio.ffindex' in chapter_script
    assert 'prepared-audio' not in logo_script
    assert 'threads=12' in chapter_script
    assert 'threads=4' in logo_script
    assert 'colorspace=' not in logo_script
    assert 'ConvertBits' not in logo_script and 'ConvertToYV12' not in logo_script
    chapter_index = next(
        index for index, command in enumerate(commands)
        if command[0] == str(analyzer.chapter_executable_path)
    )
    logo_index = next(
        index for index, command in enumerate(commands)
        if command[0] == str(analyzer.logoframe_path)
    )
    assert chapter_index < logo_index
    jls_command = next(command for command in commands if command[0] == str(analyzer.join_logo_scp_path))
    assert '-inlogo' in jls_command
    assert jls_command[jls_command.index('-inlogo') + 1].endswith('selected-logo.txt')


@pytest.mark.parametrize('pixel_format', ['yuv420p', 'yuv420p10le', 'yuv420p12le', 'yuv420p14le', 'yuv420p16le'])
def test_logo_script_preserves_ffms2_native_luma_format_and_range(
    tmp_path: Path,
    pixel_format: str,
) -> None:
    analyzer = CreateRuntime(tmp_path)
    logo = tmp_path / 'logo.lgd'
    logo.write_bytes(b'logo')
    payload = ProbePayload()
    streams = cast(list[dict[str, object]], payload['streams'])
    streams[0]['pix_fmt'] = pixel_format
    commands: list[tuple[str, ...]] = []
    InstallSuccessfulProcesses(analyzer, payload, commands)

    result = asyncio.run(analyzer.analyze(CreateRequest(tmp_path, logo_paths=(logo,))))

    assert result.status == 'completed'
    logo_script = (tmp_path / 'work/cpu/logo.avs').read_text(encoding='utf-8')
    assert 'colorspace=' not in logo_script
    assert 'ConvertBits' not in logo_script
    assert 'ConvertToYV12' not in logo_script


def test_parallel_logo_decode_stays_on_cpu_when_chapter_uses_hardware(tmp_path: Path) -> None:
    analyzer = CreateRuntime(tmp_path)
    logo = tmp_path / 'logo.lgd'
    logo.write_bytes(b'logo')
    commands: list[tuple[str, ...]] = []
    InstallSuccessfulProcesses(analyzer, ProbePayload(), commands)

    result = asyncio.run(analyzer.analyze(CreateRequest(
        tmp_path,
        logo_paths=(logo,),
        hardware_device='vaapi:/dev/dri/renderD128',
    )))

    assert result.status == 'completed'
    assert result.decode_mode == 'Hardware'
    chapter_script = (tmp_path / 'work/hardware-1/chapter.avs').read_text(encoding='utf-8')
    logo_script = (tmp_path / 'work/hardware-1/logo.avs').read_text(encoding='utf-8')
    assert 'hwdevice="vaapi:/dev/dri/renderD128"' in chapter_script
    assert 'hwdevice=' not in logo_script


@pytest.mark.parametrize(
    ('processor_count', 'total_frames', 'expected_workers'),
    [
        (12, 299, 1),
        (12, 300, 1),
        (12, 899, 1),
        (12, 900, 2),
        (12, 1800, 3),
        (12, 108_000, 6),
        (16, 108_000, 8),
        (48, 108_000, 12),
        (1, 108_000, 1),
    ],
)
def test_logo_frame_worker_count_matches_amatsukaze_balancing(
    monkeypatch: pytest.MonkeyPatch,
    processor_count: int,
    total_frames: int,
    expected_workers: int,
) -> None:
    monkeypatch.setattr(GenericCMAnalyzer, '_effectiveCPUCount', staticmethod(lambda: processor_count))

    assert GenericCMAnalyzer._logoFrameWorkerCount(total_frames) == expected_workers


@pytest.mark.parametrize(
    ('processor_count', 'worker_count', 'expected_chapter_threads', 'expected_logo_threads'),
    [
        (1, 1, 1, 1),
        (4, 1, 4, 4),
        (12, 3, 12, 4),
        (16, 8, 16, 2),
        (48, 12, 16, 4),
        (64, 2, 16, 16),
    ],
)
def test_decoder_threads_follow_actual_process_parallelism(
    monkeypatch: pytest.MonkeyPatch,
    processor_count: int,
    worker_count: int,
    expected_chapter_threads: int,
    expected_logo_threads: int,
) -> None:
    monkeypatch.setattr(GenericCMAnalyzer, '_effectiveCPUCount', staticmethod(lambda: processor_count))

    assert GenericCMAnalyzer._chapterDecoderThreadCount() == expected_chapter_threads
    assert GenericCMAnalyzer._logoDecoderThreadCount(worker_count) == expected_logo_threads


def test_logo_and_chapter_frame_count_must_match(tmp_path: Path) -> None:
    analyzer = CreateRuntime(tmp_path)
    logo = tmp_path / 'logo.lgd'
    logo.write_bytes(b'logo')
    commands: list[tuple[str, ...]] = []
    InstallSuccessfulProcesses(analyzer, ProbePayload(), commands)
    original_run = analyzer._runProcess

    async def RunProcess(command: tuple[str, ...], environment: Mapping[str, str]) -> _ProcessResult:
        result = await original_run(command, environment)
        if command[0] == str(analyzer.logoframe_path):
            analysis_path = Path(command[command.index('-oa') + 1])
            list_path = analysis_path.with_name(f'{analysis_path.stem}_list.ini')
            list_path.write_text(list_path.read_text(encoding='utf-8').replace('1800', '1799'), encoding='utf-8')
        return result

    analyzer._runProcess = RunProcess  # type: ignore[method-assign]
    result = asyncio.run(analyzer.analyze(CreateRequest(tmp_path, logo_paths=(logo,))))

    assert result.status == 'analysis_failed'
    assert result.error_code == 'AnalyzerFrameCountMismatch'


def test_hardware_initialization_failure_falls_back_to_cpu_once(tmp_path: Path) -> None:
    analyzer = CreateRuntime(tmp_path)
    payload = ProbePayload()
    chapter_attempts = 0
    prepare_attempts = 0
    index_attempts = 0

    async def RunProcess(command: tuple[str, ...], environment: Mapping[str, str]) -> _ProcessResult:
        nonlocal chapter_attempts, prepare_attempts, index_attempts
        del environment
        if command[0] == str(analyzer.ffprobe_path):
            if command[-1].endswith('prepared-media.cmwork'):
                return _ProcessResult(0, json.dumps(PreparedVideoPayload(payload)))
            if command[-1].endswith('prepared-audio.wav'):
                return _ProcessResult(0, json.dumps(PreparedAudioPayload(payload)))
            return _ProcessResult(0, json.dumps(payload))
        if command[0] == str(analyzer.ffmpeg_path):
            if str(tmp_path / 'recording.mkv') in command:
                prepare_attempts += 1
            WriteFFmpegOutputs(command)
            return _ProcessResult(0, '')
        if command[0] == str(analyzer.ffmsindex_path):
            index_attempts += 1
            Path(command[-1]).write_bytes(b'ffindex')
            return _ProcessResult(0, '')
        if command[0] == str(analyzer.chapter_executable_path):
            chapter_attempts += 1
            script = Path(command[command.index('-v') + 1]).read_text(encoding='utf-8')
            if 'hwdevice=' in script:
                Path(command[command.index('-o') + 1]).write_text('0 0\n', encoding='utf-8')
                return _ProcessResult(
                    0,
                    'Avisynth ERROR: FFVideoSource: FFMS2-HW: failed to create device /dev/dri/renderD128',
                    'Movie data\nVideo Frames: 0',
                )
            Path(command[command.index('-o') + 1]).write_text('# SCPos: 1799 0\n', encoding='utf-8')
            return _ProcessResult(0, 'Video Frames: 1800')
        Path(command[command.index('-o') + 1]).write_text('Trim(0,1799)\n', encoding='utf-8')
        return _ProcessResult(0, '')

    analyzer._runProcess = RunProcess  # type: ignore[method-assign]
    result = asyncio.run(analyzer.analyze(CreateRequest(tmp_path, hardware_device='vaapi:/dev/dri/renderD128')))

    assert result.status == 'completed'
    assert result.decode_mode == 'CPU'
    assert result.warnings[0] == 'HardwareDecodeFallback'
    assert chapter_attempts == 2
    assert prepare_attempts == 1
    assert index_attempts == 2
    assert 'hwdevice=' in (tmp_path / 'work/hardware-1/chapter.avs').read_text(encoding='utf-8')
    assert 'hwdevice=' not in (tmp_path / 'work/cpu/chapter.avs').read_text(encoding='utf-8')


def test_chapter_exe_failure_tries_next_hardware_device(tmp_path: Path) -> None:
    """最初の render node で chapter_exe が失敗した場合、次の検出済みデバイスを試す。"""

    analyzer = CreateRuntime(tmp_path)
    payload = ProbePayload()
    commands: list[tuple[str, ...]] = []
    InstallSuccessfulProcesses(analyzer, payload, commands)
    original_run = analyzer._runProcess

    async def RunProcess(command: tuple[str, ...], environment: Mapping[str, str]) -> _ProcessResult:
        if command[0] == str(analyzer.chapter_executable_path):
            script = Path(command[command.index('-v') + 1]).read_text(encoding='utf-8')
            if 'renderD128' in script:
                return _ProcessResult(134, '', "basic_string::_M_construct null not valid")
        return await original_run(command, environment)

    analyzer._runProcess = RunProcess  # type: ignore[method-assign]
    request = replace(
        CreateRequest(tmp_path),
        hardware_devices=('vaapi:/dev/dri/renderD128', 'vaapi:/dev/dri/renderD129'),
    )
    result = asyncio.run(analyzer.analyze(request))

    assert result.status == 'completed'
    assert result.decode_mode == 'Hardware'
    assert result.warnings[0] == 'HardwareDecodeFallback'
    assert 'renderD128' in (tmp_path / 'work/hardware-1/chapter.avs').read_text(encoding='utf-8')
    assert 'renderD129' in (tmp_path / 'work/hardware-2/chapter.avs').read_text(encoding='utf-8')


def test_stage_callback_reports_shared_pipeline_and_hardware_fallback(tmp_path: Path) -> None:
    analyzer = CreateRuntime(tmp_path)
    payload = ProbePayload()
    logo = tmp_path / 'logo.lgd'
    logo.write_bytes(b'logo')
    commands: list[tuple[str, ...]] = []
    InstallSuccessfulProcesses(analyzer, payload, commands)
    original_run = analyzer._runProcess

    async def RunProcess(command: tuple[str, ...], environment: Mapping[str, str]) -> _ProcessResult:
        if command[0] == str(analyzer.chapter_executable_path):
            script = Path(command[command.index('-v') + 1]).read_text(encoding='utf-8')
            if 'hwdevice=' in script:
                return _ProcessResult(1, '', 'FFMS2-HW: test device initialization failed')
        return await original_run(command, environment)

    stages: list[tuple[str, float | None]] = []

    async def StageCallback(stage: str, progress: float | None) -> None:
        stages.append((stage, progress))

    analyzer._runProcess = RunProcess  # type: ignore[method-assign]
    request = replace(
        CreateRequest(tmp_path, logo_paths=(logo,), hardware_device='cuda:0'),
        stage_callback=StageCallback,  # type: ignore[arg-type]
    )

    result = asyncio.run(analyzer.analyze(request))

    assert result.status == 'completed'
    assert [stage for stage, _ in stages] == [
        'PreparingMedia', 'IndexingMedia', 'ChapterAnalyzing', 'HardwareFallback',
        'ChapterAnalyzing', 'LogoAnalyzing', 'CombiningCM',
    ]
    numeric_progress = [progress for _, progress in stages if progress is not None]
    assert numeric_progress == sorted(numeric_progress)


def test_hardware_chapter_exe_failure_is_retried_on_cpu(tmp_path: Path) -> None:
    analyzer = CreateRuntime(tmp_path)
    chapter_attempts = 0

    async def RunProcess(command: tuple[str, ...], environment: Mapping[str, str]) -> _ProcessResult:
        nonlocal chapter_attempts
        del environment
        if command[0] == str(analyzer.ffprobe_path):
            payload = ProbePayload()
            if command[-1].endswith('prepared-media.cmwork'):
                return _ProcessResult(0, json.dumps(PreparedVideoPayload(payload)))
            if command[-1].endswith('prepared-audio.wav'):
                return _ProcessResult(0, json.dumps(PreparedAudioPayload(payload)))
            return _ProcessResult(0, json.dumps(payload))
        if command[0] == str(analyzer.ffmpeg_path):
            WriteFFmpegOutputs(command)
            return _ProcessResult(0, '')
        if command[0] == str(analyzer.ffmsindex_path):
            Path(command[-1]).write_bytes(b'ffindex')
            return _ProcessResult(0, '')
        if command[0] == str(analyzer.chapter_executable_path):
            chapter_attempts += 1
            script = Path(command[command.index('-v') + 1]).read_text(encoding='utf-8')
            if 'hwdevice=' in script:
                return _ProcessResult(1, '', 'chapter algorithm rejected the input')
            Path(command[command.index('-o') + 1]).write_text('# SCPos: 1799 0\n', encoding='utf-8')
            return _ProcessResult(0, 'Video Frames: 1800')
        Path(command[command.index('-o') + 1]).write_text('Trim(0,1799)\n', encoding='utf-8')
        return _ProcessResult(0, '')

    analyzer._runProcess = RunProcess  # type: ignore[method-assign]
    result = asyncio.run(analyzer.analyze(CreateRequest(tmp_path, hardware_device='cuda:0')))

    assert result.status == 'completed'
    assert result.decode_mode == 'CPU'
    assert chapter_attempts == 2


def test_cpu_decoder_unavailable_is_stably_unsupported(tmp_path: Path) -> None:
    analyzer = CreateRuntime(tmp_path)

    async def RunProcess(command: tuple[str, ...], environment: Mapping[str, str]) -> _ProcessResult:
        del environment
        if command[0] == str(analyzer.ffprobe_path):
            return _ProcessResult(0, json.dumps(ProbePayload(codec='unknown_codec')))
        return _ProcessResult(1, '', 'decoder not found for unknown_codec')

    analyzer._runProcess = RunProcess  # type: ignore[method-assign]
    result = asyncio.run(analyzer.analyze(CreateRequest(tmp_path)))

    assert result.status == 'unsupported'
    assert result.error_code == 'DecoderUnavailable'


def test_runtime_enospc_is_normalized_to_temporary_storage_error(tmp_path: Path) -> None:
    analyzer = CreateRuntime(tmp_path)

    async def RunProcess(command: tuple[str, ...], environment: Mapping[str, str]) -> _ProcessResult:
        del environment
        if command[0] == str(analyzer.ffprobe_path):
            return _ProcessResult(0, json.dumps(ProbePayload()))
        return _ProcessResult(1, '', 'av_interleaved_write_frame(): No space left on device')

    analyzer._runProcess = RunProcess  # type: ignore[method-assign]

    result = asyncio.run(analyzer.analyze(CreateRequest(tmp_path)))

    assert result.status == 'analysis_failed'
    assert result.error_code == 'TemporaryStorageInsufficient'


def test_native_stage_enospc_is_normalized_to_temporary_storage_error(tmp_path: Path) -> None:
    analyzer = CreateRuntime(tmp_path)
    payload = ProbePayload()

    async def RunProcess(command: tuple[str, ...], environment: Mapping[str, str]) -> _ProcessResult:
        del environment
        if command[0] == str(analyzer.ffprobe_path):
            if command[-1].endswith('prepared-media.cmwork'):
                return _ProcessResult(0, json.dumps(PreparedVideoPayload(payload)))
            if command[-1].endswith('prepared-audio.wav'):
                return _ProcessResult(0, json.dumps(PreparedAudioPayload(payload)))
            return _ProcessResult(0, json.dumps(payload))
        if command[0] == str(analyzer.ffmpeg_path):
            WriteFFmpegOutputs(command)
            return _ProcessResult(0, '')
        if command[0] == str(analyzer.ffmsindex_path):
            Path(command[-1]).write_bytes(b'ffindex')
            return _ProcessResult(0, '')
        return _ProcessResult(1, '', 'failed to write output: Disk quota exceeded')

    analyzer._runProcess = RunProcess  # type: ignore[method-assign]

    result = asyncio.run(analyzer.analyze(CreateRequest(tmp_path)))

    assert result.status == 'analysis_failed'
    assert result.error_code == 'TemporaryStorageInsufficient'


def test_audio_index_enospc_is_normalized_before_native_analysis(tmp_path: Path) -> None:
    analyzer = CreateRuntime(tmp_path)
    payload = ProbePayload()

    async def RunProcess(command: tuple[str, ...], environment: Mapping[str, str]) -> _ProcessResult:
        del environment
        if command[0] == str(analyzer.ffprobe_path):
            return _ProcessResult(0, json.dumps(payload))
        if command[0] == str(analyzer.ffmpeg_path):
            WriteFFmpegOutputs(command)
            return _ProcessResult(0, '')
        if command[0] == str(analyzer.ffmsindex_path):
            if command[-2].endswith('prepared-audio.wav'):
                return _ProcessResult(1, '', 'audio index: No space left on device')
            Path(command[-1]).write_bytes(b'video-index')
            return _ProcessResult(0, '')
        raise AssertionError(f'Native analysis must not start after index failure: {command}')

    analyzer._runProcess = RunProcess  # type: ignore[method-assign]

    result = asyncio.run(analyzer.analyze(CreateRequest(tmp_path)))

    assert result.status == 'analysis_failed'
    assert result.error_code == 'TemporaryStorageInsufficient'
    assert result.error_message is not None
    assert result.error_message.endswith('audio index: No space left on device')


def test_python_output_enospc_is_normalized_to_temporary_storage_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analyzer = CreateRuntime(tmp_path)
    commands: list[tuple[str, ...]] = []
    InstallSuccessfulProcesses(analyzer, ProbePayload(), commands)
    original_write_text = Path.write_text

    def WriteText(
        path: Path,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        if path.name == 'chapter.avs':
            raise OSError(errno.ENOSPC, 'No space left on device')
        return original_write_text(path, data, encoding=encoding, errors=errors, newline=newline)

    monkeypatch.setattr(Path, 'write_text', WriteText)

    result = asyncio.run(analyzer.analyze(CreateRequest(tmp_path)))

    assert result.status == 'analysis_failed'
    assert result.error_code == 'TemporaryStorageInsufficient'


def test_generated_chapter_enospc_is_normalized_to_temporary_storage_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analyzer = CreateRuntime(tmp_path)
    commands: list[tuple[str, ...]] = []
    InstallSuccessfulProcesses(analyzer, ProbePayload(), commands)
    original_write_text = Path.write_text

    def WriteText(
        path: Path,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        if path.name == 'generated.cmchapter':
            raise OSError(errno.ENOSPC, 'No space left on device')
        return original_write_text(path, data, encoding=encoding, errors=errors, newline=newline)

    monkeypatch.setattr(Path, 'write_text', WriteText)

    result = asyncio.run(analyzer.analyze(CreateRequest(tmp_path)))

    assert result.status == 'analysis_failed'
    assert result.error_code == 'TemporaryStorageInsufficient'


def test_analyzer_requires_precreated_private_workspace(tmp_path: Path) -> None:
    analyzer = CreateRuntime(tmp_path)
    request = CreateRequest(tmp_path)
    request.work_directory.rmdir()

    async def RunProcess(command: tuple[str, ...], environment: Mapping[str, str]) -> _ProcessResult:
        del command, environment
        return _ProcessResult(0, json.dumps(ProbePayload()))

    analyzer._runProcess = RunProcess  # type: ignore[method-assign]

    result = asyncio.run(analyzer.analyze(request))

    assert result.status == 'analysis_failed'
    assert result.error_code == 'TemporaryStorageUnavailable'


def test_tlv_input_forces_libaribtlv_for_probe_and_media_preparation(tmp_path: Path) -> None:
    analyzer = CreateRuntime(tmp_path)
    payload = ProbePayload(format_name='libaribtlv', codec='hevc')
    commands: list[tuple[str, ...]] = []
    InstallSuccessfulProcesses(analyzer, payload, commands)
    request = replace(CreateRequest(tmp_path), container_format='MMT/TLV')

    result = asyncio.run(analyzer.analyze(request))

    assert result.status == 'completed'
    source_probe = next(command for command in commands if command[0] == str(analyzer.ffprobe_path))
    media_preparation = next(command for command in commands if command[0] == str(analyzer.ffmpeg_path))
    assert source_probe[source_probe.index('-f') + 1] == 'libaribtlv'
    assert media_preparation[media_preparation.index('-f') + 1] == 'libaribtlv'
    assert media_preparation[media_preparation.index('-c:v') + 1] == 'copy'


def test_jls_output_requires_ordered_determinate_trim_ranges() -> None:
    assert GenericCMAnalyzer._parseCMSections(
        'Trim(0,899) ++ Trim(1200,1799)',
        1800,
        Fraction(30_000, 1001),
    ) == [{'start_time': 30.03, 'end_time': 40.04}]
    with pytest.raises(ValueError, match='determinate'):
        GenericCMAnalyzer._parseCMSections('', 1800, Fraction(30_000, 1001))
    with pytest.raises(ValueError, match='overlap'):
        GenericCMAnalyzer._parseCMSections(
            'Trim(100,500) ++ Trim(400,900)',
            1800,
            Fraction(30_000, 1001),
        )


def test_missing_runtime_is_reported_as_stable_unavailable(tmp_path: Path) -> None:
    result = asyncio.run(GenericCMAnalyzer(runtime_directory=tmp_path / 'missing').analyze(CreateRequest(tmp_path)))

    assert result.status == 'unsupported'
    assert result.error_code == 'AnalyzerUnavailable'


def test_runtime_manifest_content_invalidates_attempt_fingerprint(tmp_path: Path) -> None:
    analyzer = CreateRuntime(tmp_path)
    before = analyzer.runtimeFingerprint
    analyzer.runtime_manifest_path.write_text(
        '{"schema_version":1,"components":{"chapter_exe":{"commit":"new"}},"patches":{}}\n',
        encoding='utf-8',
    )
    after = analyzer.runtimeFingerprint

    assert before['native_runtime_manifest_sha256'] != after['native_runtime_manifest_sha256']
    assert after['native_runtime_manifest_error'] is None


def test_playback_ffmpeg_environment_never_loads_private_cm_ffmpeg_libraries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analyzer = CreateRuntime(tmp_path)
    monkeypatch.setenv('LD_LIBRARY_PATH', '/host/libraries')
    request = replace(CreateRequest(tmp_path), hardware_environment={'LIBVA_DRIVER_NAME': 'test'})

    media_environment = analyzer._buildMediaEnvironment(request)  # pyright: ignore[reportPrivateUsage]
    native_environment = analyzer._buildEnvironment(request)  # pyright: ignore[reportPrivateUsage]

    assert media_environment['LD_LIBRARY_PATH'] == '/host/libraries'
    assert str(analyzer.runtime_directory) not in media_environment['LD_LIBRARY_PATH']
    assert native_environment['LD_LIBRARY_PATH'] == f'{analyzer.runtime_directory}:/host/libraries'
    assert media_environment['LIBVA_DRIVER_NAME'] == 'test'


def test_native_environment_supplies_private_home_for_systemd_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analyzer = CreateRuntime(tmp_path)
    request = CreateRequest(tmp_path)
    monkeypatch.delenv('HOME', raising=False)

    media_environment = analyzer._buildMediaEnvironment(request)  # pyright: ignore[reportPrivateUsage]
    native_environment = analyzer._buildEnvironment(request)  # pyright: ignore[reportPrivateUsage]

    assert 'HOME' not in media_environment
    assert native_environment['HOME'] == str(request.work_directory)


def test_process_diagnostic_preserves_complete_command_output_and_log(tmp_path: Path) -> None:
    analyzer = CreateRuntime(tmp_path)
    diagnostic_log_path = tmp_path / 'work/processes.log'
    diagnostic_log_path.parent.mkdir()
    stdout_text = 'stdout-start\n' + ('x' * 5000) + '\nstdout-end'
    stderr_text = 'stderr-start\n' + ('y' * 5000) + '\nstderr-end'
    command = (
        sys.executable,
        '-c',
        f'import sys; print({stdout_text!r}); print({stderr_text!r}, file=sys.stderr)',
    )

    result = asyncio.run(analyzer._runProcessWithDiagnostics(  # pyright: ignore[reportPrivateUsage]
        command,
        {'PATH': '/test/path', 'LC_ALL': 'C.UTF-8'},
        diagnostic_log_path,
    ))

    assert result.return_code == 0
    assert result.output == stdout_text
    assert result.error_output == stderr_text
    assert result.command == command
    assert result.started_at is not None
    assert result.elapsed_seconds is not None
    assert stdout_text in result.diagnostic
    assert stderr_text in result.diagnostic
    diagnostic_log = diagnostic_log_path.read_text(encoding='utf-8')
    assert f'Command: {sys.executable}' in diagnostic_log
    assert 'Exit code: 0' in diagnostic_log
    assert 'PATH=/test/path' in diagnostic_log
    assert stdout_text in diagnostic_log
    assert stderr_text in diagnostic_log


def test_invalid_runtime_manifest_is_stably_unavailable(tmp_path: Path) -> None:
    analyzer = CreateRuntime(tmp_path)
    analyzer.runtime_manifest_path.write_text('{}\n', encoding='utf-8')

    result = asyncio.run(analyzer.analyze(CreateRequest(tmp_path)))

    assert result.status == 'unsupported'
    assert result.error_code == 'RuntimeManifestInvalid'


import asyncio
import json
import pathlib
import tempfile

import typer

from app.metadata.CMAnalyzer import (
    CMAnalysisStage,
    CMAnalyzerRequest,
    CMContainerFormat,
    GenericCMAnalyzer,
)


async def RunAnalysis(
    file_path: pathlib.Path,
    service_id: int | None,
    container_format: CMContainerFormat,
    hardware_device: str | None,
    work_directory: pathlib.Path,
) -> bool:
    """
    HonomiTV 本体と同じ GenericCMAnalyzer で CM 解析を実行する。

    Args:
        file_path (pathlib.Path): 解析対象の録画ファイル。
        service_id (int | None): MPEG-TS 内で選択するサービス ID。
        container_format (CMContainerFormat): 録画ファイルのコンテナ形式。
        hardware_device (str | None): FFMS2 に渡すハードウェアデコードデバイス。
        work_directory (pathlib.Path): 中間ファイルを保持する作業ディレクトリ。

    Returns:
        bool: CM 解析が最後まで正常に完了した場合は True。
    """

    async def ReportStage(stage: CMAnalysisStage, progress: float | None) -> None:
        """
        解析中のステージを標準出力へ表示する。

        Args:
            stage (CMAnalysisStage): 現在の解析ステージ。
            progress (float | None): 現在の進捗率。

        Returns:
            None
        """

        progress_text = '' if progress is None else f' ({progress * 100:.0f}%)'
        typer.echo(f'[{stage}]{progress_text}')

    analyzer = GenericCMAnalyzer()
    result = await analyzer.analyze(CMAnalyzerRequest(
        recorded_file_path = file_path,
        work_directory = work_directory,
        service_id = service_id,
        hardware_devices = (hardware_device,) if hardware_device is not None else (),
        container_format = container_format,
        stage_callback = ReportStage,
    ))

    # chapter_exe の stderr を含む構造化結果と、再実行に使える作業ディレクトリを必ず表示する。
    typer.echo(json.dumps(result.toJSON(), ensure_ascii=False, indent=2))
    typer.echo(f'Work directory kept at: {work_directory}')
    return result.status == 'completed'


def Main(
    file_path: pathlib.Path = typer.Argument(
        ...,
        exists = True,
        file_okay = True,
        dir_okay = False,
        readable = True,
        resolve_path = True,
        help = 'CM 解析する録画ファイル。',
    ),
    service_id: int | None = typer.Option(
        None,
        help = 'MPEG-TS 内で選択するサービス ID。',
    ),
    container_format: CMContainerFormat = typer.Option(
        'MPEG-TS',
        help = '録画ファイルのコンテナ形式。',
    ),
    hardware_device: str | None = typer.Option(
        None,
        help = 'FFMS2 のハードウェアデコードデバイス。未指定時は CPU で解析する。',
    ),
    work_directory: pathlib.Path | None = typer.Option(
        None,
        file_okay = False,
        resolve_path = True,
        help = '中間ファイルの保存先。未指定時は /tmp 以下へ新規作成する。',
    ),
) -> None:
    """
    DB を更新せず、CM 解析の中間ファイルと chapter_exe の診断結果を保存する。

    Args:
        file_path (pathlib.Path): 解析対象の録画ファイル。
        service_id (int | None): MPEG-TS 内で選択するサービス ID。
        container_format (CMContainerFormat): 録画ファイルのコンテナ形式。
        hardware_device (str | None): FFMS2 に渡すハードウェアデコードデバイス。
        work_directory (pathlib.Path | None): 中間ファイルを保存する新規ディレクトリ。

    Returns:
        None
    """

    # 失敗時の現場を残すため、CMSectionsDetector の一時ディレクトリとは別の専用領域を使う。
    if work_directory is None:
        work_directory = pathlib.Path(tempfile.mkdtemp(prefix=f'{file_path.stem}.konomitv-cm-debug-'))
    else:
        work_directory.mkdir(parents=True, exist_ok=False)

    if asyncio.run(RunAnalysis(
        file_path,
        service_id,
        container_format,
        hardware_device,
        work_directory,
    )) is False:
        raise typer.Exit(code=1)


if __name__ == '__main__':
    typer.run(Main)

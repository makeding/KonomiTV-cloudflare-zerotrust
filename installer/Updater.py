
import os
import platform
import py7zr
import requests
import ruamel.yaml
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from rich import print
from rich.padding import Padding
from typing import cast, Literal

from Utils import CreateBasicInfiniteProgress
from Utils import CreateDownloadProgress
from Utils import CreateDownloadInfiniteProgress
from Utils import CreateTable
from Utils import CustomPrompt
from Utils import GetNetworkInterfaceInformation
from Utils import IsDockerComposeV2
from Utils import IsDockerInstalled
from Utils import IsGitInstalled
from Utils import RemoveEmojiIfLegacyTerminal
from Utils import RunKonomiTVServiceWaiter
from Utils import RunSubprocess
from Utils import RunSubprocessDirectLogOutput
from Utils import SaveConfigYaml
from Utils import ShowPanel
from Utils import ShowSubProcessErrorLog


def Updater(version: str) -> None:
    """
    KonomiTV のアップデーターの実装

    Args:
        version (str): KonomiTV をアップデートするバージョン
    """

    ShowPanel([
        '[yellow]注意: このアップデーターは現時点では動作しない可能性が高いです。',
        'KonomiTV は開発中のため、破壊的な構成変更が頻繁に行われています。',
        '破壊的変更が続く中アップデーターの機能を維持することは難しいため、',
        '安定版リリースまでの当面の間、アップデーターの今後の改修は放置されています。',
        'お手数をおかけしますが、現時点では DB や設定ファイルなどをバックアップの上で',
        '一旦アンインストールし、新規でインストールし直すことをおすすめします。[/yellow]',
    ])

    # 設定データの対話的な取得とエンコーダーの動作確認を行わない以外は、インストーラーの処理内容と大体同じ

    # プラットフォームタイプ
    ## Windows・Linux・Linux (Docker)
    platform_type: Literal['Windows', 'Linux', 'Linux-Docker'] = 'Windows' if os.name == 'nt' else 'Linux'

    # ARM デバイスかどうか
    is_arm_device = platform.machine() == 'aarch64'

    # ***** アップデート対象の KonomiTV のフォルダのパス *****

    table_02 = CreateTable()
    table_02.add_column('02. アップデート対象の KonomiTV のフォルダのパスを入力してください。')
    if platform_type == 'Windows':
        table_02.add_row('例: C:\\DTV\\KonomiTV')
    elif platform_type == 'Linux' or platform_type == 'Linux-Docker':
        table_02.add_row('例: /opt/KonomiTV')
    print(Padding(table_02, (1, 2, 1, 2)))

    # アップデート対象の KonomiTV のフォルダを取得
    update_path: Path
    while True:

        # 入力プロンプト (バリデーションに失敗し続ける限り何度でも表示される)
        update_path = Path(CustomPrompt.ask('アップデート対象の KonomiTV のフォルダのパス'))

        # バリデーション
        if update_path.is_absolute() is False:
            print(Padding('[red]アップデート対象の KonomiTV のフォルダは絶対パスで入力してください。', (0, 2, 0, 2)))
            continue
        if update_path.exists() is False:
            print(Padding('[red]アップデート対象の KonomiTV のフォルダが存在しません。', (0, 2, 0, 2)))
            continue

        # 指定されたフォルダが KonomiTV のフォルダ/ファイル配置と異なる
        ## 大まかにフォルダ/ファイル配置をチェック (すべてのファイル、フォルダがあれば OK)
        if not (
            (update_path / 'config.example.yaml').exists() and
            (update_path / 'License.txt').exists() and
            (update_path / 'Readme.md').exists() and
            (update_path / 'client/').exists() and
            (update_path / 'installer/').exists() and
            (update_path / 'server/').exists() and
            (update_path / 'server/app/').exists() and
            (update_path / 'server/data/').exists() and
            (update_path / 'server/logs/').exists() and
            (update_path / 'server/static/').exists() and
            (update_path / 'server/thirdparty/').exists()
        ):
            print(Padding('[red]指定されたフォルダは KonomiTV のフォルダ/ファイル配置と異なります。', (0, 2, 0, 2)))
            continue

        # すべてのバリデーションを通過したのでループを抜ける
        break

    # Linux: インストールフォルダに docker-compose.yaml があれば
    # Docker でインストールしたことが推測されるので、プラットフォームタイプを Linux-Docker に切り替える
    ## インストーラーで Docker を使わずにインストールした場合は docker-compose.yaml は生成されないことを利用している
    if platform_type == 'Linux' and is_arm_device is False and Path(update_path / 'docker-compose.yaml').exists():

        # 前回 Docker を使ってインストールされているが、今 Docker がインストールされていない
        if IsDockerInstalled() is False:
            ShowPanel([
                '[yellow]この KonomiTV をアップデートするには、Docker のインストールが必要です。[/yellow]',
                'この KonomiTV は Docker を使ってインストールされていますが、現在 Docker が',
                'インストールされていないため、アップデートすることができません。',
            ])
            return  # 処理中断

        # プラットフォームタイプを Linux-Docker にセット
        platform_type = 'Linux-Docker'

        # Docker がインストールされているものの Docker サービスが停止している場合に備え、Docker サービスを起動しておく
        ## すでに起動している場合は何も起こらない
        subprocess.run(
            args = ['systemctl', 'start', 'docker'],
            stdout = subprocess.DEVNULL,  # 標準出力を表示しない
            stderr = subprocess.DEVNULL,  # 標準エラー出力を表示しない
        )

    # Docker Compose V2 かどうかでコマンド名を変える
    ## Docker Compose V1 は docker-compose 、V2 は docker compose という違いがある
    ## Docker がインストールされていない場合は V1 のコマンドが代入されるが、そもそも非 Docker インストールでは参照されない
    docker_compose_command = ['docker', 'compose'] if IsDockerComposeV2() else ['docker-compose']

    # Python の実行ファイルのパス (Windows と Linux で異なる)
    ## Linux-Docker では利用されない
    python_executable_path = ''
    if platform_type == 'Windows':
        python_executable_path = update_path / 'server/thirdparty/Python/python.exe'
    elif platform_type == 'Linux':
        python_executable_path = update_path / 'server/thirdparty/Python/bin/python'

    # ***** Windows: 起動中の Windows サービスの終了 *****

    if platform_type == 'Windows':

        # Windows サービスを終了
        print(Padding('起動中の Windows サービスを終了しています…', (1, 2, 0, 2)))
        progress = CreateBasicInfiniteProgress()
        progress.add_task('', total=None)
        with progress:
            service_stop_result = subprocess.run(
                args = [python_executable_path, '-m', 'pipenv', 'run', 'python', 'KonomiTV-Service.py', 'stop'],
                cwd = update_path / 'server/',  # カレントディレクトリを KonomiTV サーバーのベースディレクトリに設定
                stdout = subprocess.PIPE,  # 標準出力をキャプチャする
                stderr = subprocess.DEVNULL,  # 標準エラー出力を表示しない
                text = True,  # 出力をテキストとして取得する
            )
        # 1062: ERROR_SERVICE_NOT_ACTIVE はサービスが起動していない場合に発生するエラーのため無視する
        if 'Error stopping service' in service_stop_result.stdout and '(1062)' not in service_stop_result.stdout:
            ShowSubProcessErrorLog(
                error_message = '起動中の Windows サービスの終了中に予期しないエラーが発生しました。',
                error_log = service_stop_result.stdout.strip(),
            )
            return  # 処理中断

    # ***** Linux: 起動中の PM2 サービスの終了 *****

    elif platform_type == 'Linux':

        # PM2 サービスを終了
        result = RunSubprocess(
            '起動中の PM2 サービスを終了しています…',
            ['/usr/bin/env', 'pm2', 'stop', 'KonomiTV'],
            cwd = update_path / 'server/',  # カレントディレクトリを KonomiTV サーバーのベースディレクトリに設定
            error_message = '起動中の PM2 サービスの終了中に予期しないエラーが発生しました。',
            error_log_name = 'PM2 のエラーログ',
        )
        if result is False:
            return  # 処理中断

    # ***** Linux-Docker: 起動中の Docker コンテナの終了 *****

    elif platform_type == 'Linux-Docker':

        # docker compose stop で Docker コンテナを終了
        result = RunSubprocess(
            '起動中の Docker コンテナを終了しています…',
            [*docker_compose_command, 'stop'],
            cwd = update_path,  # カレントディレクトリを KonomiTV のアンインストールフォルダに設定
            error_message = '起動中の Docker コンテナの終了中に予期しないエラーが発生しました。',
            error_log_name = 'PM2 のエラーログ',
        )
        if result is False:
            return  # 処理中断

    # ***** ソースコードの更新 *****

    # Git を使ってインストールされているか
    ## Git のインストール状況に関わらず、.git フォルダが存在する場合は Git を使ってインストールされていると判断する
    is_installed_by_git = Path(update_path / '.git').exists()

    # Git を使ってインストールされている場合: git fetch & git checkout でソースコードを更新
    if is_installed_by_git is True:

        # 前回 Git を使ってインストールされているが、今 Git がインストールされていない
        if IsGitInstalled() is False:
            ShowPanel([
                '[yellow]この KonomiTV をアップデートするには、Git のインストールが必要です。[/yellow]',
                'KonomiTV は初回インストール時に Git がインストールされている場合は、',
                '自動的に Git を使ってインストールされます。',
                'この KonomiTV は Git を使ってインストールされていますが、現在 Git が',
                'インストールされていないため、アップデートすることができません。',
            ])
            return  # 処理中断

        # リモートの変更内容とタグを取得
        result = RunSubprocess(
            'KonomiTV のソースコードを Git でダウンロードしています…',
            ['git', 'fetch', 'origin', '--tags'],
            cwd = update_path,  # カレントディレクトリを KonomiTV のインストールフォルダに設定
            error_message = 'KonomiTV のソースコードのダウンロード中に予期しないエラーが発生しました。',
            error_log_name = 'Git のエラーログ',
        )
        if result is False:
            return  # 処理中断

        # 新しいバージョンのコードをチェックアウト
        result = RunSubprocess(
            'KonomiTV のソースコードを更新しています…',
            ['git', 'checkout', '--force', f'v{version}'],
            cwd = update_path,  # カレントディレクトリを KonomiTV のインストールフォルダに設定
            error_message = 'KonomiTV のソースコードの更新中に予期しないエラーが発生しました。',
            error_log_name = 'Git のエラーログ',
        )
        if result is False:
            return  # 処理中断

    # Git を使ってインストールされていない場合: zip からソースコードを更新
    else:

        # 以前のバージョンにはあったものの、現在のバージョンにはないファイルを削除する
        ## 事前に config.yaml・venv の仮想環境・ユーザーデータ・ログ以外のファイル/フォルダをすべて削除してから、
        ## ダウンロードした新しいソースコードで上書き更新する
        ## Git でインストールされている場合は、作業ツリーの更新を Git がよしなにやってくれるため不要
        shutil.rmtree(update_path / '.github/', ignore_errors=True)
        shutil.rmtree(update_path / '.vscode/', ignore_errors=True)
        shutil.rmtree(update_path / 'client/', ignore_errors=True)
        shutil.rmtree(update_path / 'installer/', ignore_errors=True)
        shutil.rmtree(update_path / 'server/app/', ignore_errors=True)
        shutil.rmtree(update_path / 'server/misc/', ignore_errors=True)
        shutil.rmtree(update_path / 'server/static/', ignore_errors=True)
        Path(update_path / 'server/KonomiTV.py').unlink(missing_ok=True)
        Path(update_path / 'server/KonomiTV-Service.py').unlink(missing_ok=True)
        Path(update_path / 'server/Pipfile').unlink(missing_ok=True)
        Path(update_path / 'server/Pipfile.lock').unlink(missing_ok=True)
        Path(update_path / 'server/pyproject.toml').unlink(missing_ok=True)
        Path(update_path / '.dockerignore').unlink(missing_ok=True)
        Path(update_path / '.editorconfig').unlink(missing_ok=True)
        Path(update_path / '.gitignore').unlink(missing_ok=True)
        Path(update_path / 'config.example.yaml').unlink(missing_ok=True)
        Path(update_path / 'docker-compose.example.yaml').unlink(missing_ok=True)
        Path(update_path / 'Dockerfile').unlink(missing_ok=True)
        Path(update_path / 'License.txt').unlink(missing_ok=True)
        Path(update_path / 'Readme.md').unlink(missing_ok=True)
        Path(update_path / 'vetur.config.js').unlink(missing_ok=True)

        # ソースコードを随時ダウンロードし、進捗を表示
        # ref: https://github.com/Textualize/rich/blob/master/examples/downloader.py
        print(Padding('KonomiTV のソースコードを更新しています…', (1, 2, 0, 2)))
        progress = CreateDownloadInfiniteProgress()

        # GitHub からソースコードをダウンロード
        source_code_response = requests.get(f'https://codeload.github.com/tsukumijima/KonomiTV/zip/refs/tags/v{version}')
        task_id = progress.add_task('', total=None)

        # ダウンロードしたデータを随時一時ファイルに書き込む
        source_code_file = tempfile.NamedTemporaryFile(mode='wb', delete=False)
        with progress:
            for chunk in source_code_response.iter_content(chunk_size=1024):
                source_code_file.write(chunk)
                progress.update(task_id, advance=len(chunk))
            source_code_file.seek(0, os.SEEK_END)
            progress.update(task_id, total=source_code_file.tell())
        source_code_file.close()  # 解凍する前に close() してすべて書き込ませておくのが重要

        # ソースコードを解凍して展開
        shutil.unpack_archive(source_code_file.name, update_path.parent, format='zip')
        shutil.copytree(update_path.parent / f'KonomiTV-{version}/', update_path, dirs_exist_ok=True)
        shutil.rmtree(update_path.parent / f'KonomiTV-{version}/', ignore_errors=True)
        Path(source_code_file.name).unlink()

    # ***** サーバー設定ファイル (config.yaml) の更新 *****

    # サーバーのリッスンポート
    server_port: int = 7000

    print(Padding('サーバー設定ファイル (config.yaml) を更新しています…', (1, 2, 0, 2)))
    progress = CreateBasicInfiniteProgress()
    progress.add_task('', total=None)
    with progress:

        # 旧バージョンの config.yaml の設定値を取得
        ## config.yaml の上書き更新前に行うのが重要
        config_data: dict[str, dict[str, int | float | bool | str | None]]
        with open(update_path / 'config.yaml', mode='r', encoding='utf-8') as fp:
            config_data = dict(ruamel.yaml.YAML().load(fp))

        # サーバーのリッスンポートの設定値を取得
        server_port = cast(int, config_data['server']['port'])

        # 新しい config.example.yaml を config.yaml に上書きコピーし、新しいフォーマットに更新
        shutil.copyfile(update_path / 'config.example.yaml', update_path / 'config.yaml')

        # 旧バージョンの config.yaml の設定値を復元
        SaveConfigYaml(update_path / 'config.yaml', config_data)

    # Windows・Linux: KonomiTV のアップデート処理
    ## Linux-Docker では Docker イメージの再構築時に各種アップデート処理も行われるため、実行の必要がない
    if platform_type == 'Windows' or platform_type == 'Linux':

        # ***** サードパーティーライブラリの更新 *****

        # サードパーティーライブラリを随時ダウンロードし、進捗を表示
        # ref: https://github.com/Textualize/rich/blob/master/examples/downloader.py
        print(Padding('サードパーティーライブラリをダウンロードしています…', (1, 2, 0, 2)))
        progress = CreateDownloadProgress()

        # GitHub からサードパーティーライブラリをダウンロード
        thirdparty_file = 'thirdparty-windows.7z'
        if platform_type == 'Linux' and is_arm_device is False:
            thirdparty_file = 'thirdparty-linux.tar.xz'
        elif platform_type == 'Linux' and is_arm_device is True:
            thirdparty_file = 'thirdparty-linux-arm.tar.xz'
        thirdparty_base_url = f'https://github.com/tsukumijima/KonomiTV/releases/download/v{version}/'
        thirdparty_url = thirdparty_base_url + thirdparty_file
        thirdparty_response = requests.get(thirdparty_url, stream=True)
        task_id = progress.add_task('', total=float(thirdparty_response.headers['Content-length']))

        # ダウンロードしたデータを随時一時ファイルに書き込む
        thirdparty_file = tempfile.NamedTemporaryFile(mode='wb', delete=False)
        with progress:
            for chunk in thirdparty_response.iter_content(chunk_size=1048576):  # サイズが大きいので1MBごとに読み込み
                thirdparty_file.write(chunk)
                progress.update(task_id, advance=len(chunk))
        thirdparty_file.close()  # 解凍する前に close() してすべて書き込ませておくのが重要

        # サードパーティーライブラリを解凍して展開
        print(Padding('サードパーティーライブラリを更新しています… (数秒～数十秒かかります)', (1, 2, 0, 2)))
        progress = CreateBasicInfiniteProgress()
        progress.add_task('', total=None)
        with progress:

            # 更新前に、前バージョンの古いサードパーティーライブラリを削除
            shutil.rmtree(update_path / 'server/thirdparty/', ignore_errors=True)

            if platform_type == 'Windows':
                # Windows: 7-Zip 形式のアーカイブを解凍
                with py7zr.SevenZipFile(thirdparty_file.name, mode='r') as seven_zip:
                    seven_zip.extractall(update_path / 'server/')
            elif platform_type == 'Linux':
                # Linux: tar.xz 形式のアーカイブを解凍
                ## 7-Zip だと (おそらく) ファイルパーミッションを保持したまま圧縮することができない？ため、あえて tar.xz を使っている
                with tarfile.open(thirdparty_file.name, mode='r:xz') as tar_xz:
                    tar_xz.extractall(update_path / 'server/')
            Path(thirdparty_file.name).unlink()
            # server/thirdparty/.gitkeep が消えてたらもう一度作成しておく
            if Path(update_path / 'server/thirdparty/.gitkeep').exists() is False:
                Path(update_path / 'server/thirdparty/.gitkeep').touch()

        # ***** 依存パッケージの更新 *****

        # pipenv --rm を実行
        ## すでに仮想環境があると稀に更新がうまく行かないことがあるため、アップデート毎に作り直す
        result = RunSubprocess(
            '既存の依存パッケージを削除しています…',
            [python_executable_path, '-m', 'pipenv', '--rm'],
            cwd = update_path / 'server/',  # カレントディレクトリを KonomiTV サーバーのベースディレクトリに設定
            error_message = '既存の依存パッケージの削除中に予期しないエラーが発生しました。'
        )
        if result is False:
            return  # 処理中断

        # pipenv sync を実行
        ## server/.venv/ に pipenv の仮想環境を構築するため、PIPENV_VENV_IN_PROJECT 環境変数をセットした状態で実行している
        environment = os.environ.copy()
        environment['PIPENV_VENV_IN_PROJECT'] = 'true'
        result = RunSubprocessDirectLogOutput(
            '依存パッケージを更新しています…',
            [python_executable_path, '-m', 'pipenv', 'sync', f'--python={python_executable_path}'],
            cwd = update_path / 'server/',  # カレントディレクトリを KonomiTV サーバーのベースディレクトリに設定
            environment = environment,  # 環境変数を設定
            error_message = '依存パッケージの更新中に予期しないエラーが発生しました。',
        )
        if result is False:
            return  # 処理中断

        # ***** データベースのアップグレード *****

        result = RunSubprocess(
            'データベースをアップグレードしています…',
            [python_executable_path, '-m', 'pipenv', 'run', 'aerich', 'upgrade'],
            cwd = update_path / 'server/',  # カレントディレクトリを KonomiTV サーバーのベースディレクトリに設定
            error_message = 'データベースのアップグレード中に予期しないエラーが発生しました。'
        )
        if result is False:
            return  # 処理中断

    # Linux-Docker: Docker イメージを再ビルド
    elif platform_type == 'Linux-Docker':

        # docker compose build --no-cache --pull で Docker イメージをビルド
        ## 万が一以前ビルドしたキャッシュが残っていたときに備え、キャッシュを使わずにビルドさせる
        result = RunSubprocessDirectLogOutput(
            'Docker イメージを再ビルドしています… (数分～数十分かかります)',
            [*docker_compose_command, 'build', '--no-cache', '--pull'],
            cwd = update_path,  # カレントディレクトリを KonomiTV のインストールフォルダに設定
            error_message = 'Docker イメージの再ビルド中に予期しないエラーが発生しました。',
        )
        if result is False:
            return  # 処理中断

    # ***** Windows: Windows サービスの起動 *****

    if platform_type == 'Windows':

        # Windows サービスを起動
        print(Padding('Windows サービスを起動しています…', (1, 2, 0, 2)))
        progress = CreateBasicInfiniteProgress()
        progress.add_task('', total=None)
        with progress:
            service_start_result = subprocess.run(
                args = [python_executable_path, '-m', 'pipenv', 'run', 'python', 'KonomiTV-Service.py', 'start'],
                cwd = update_path / 'server/',  # カレントディレクトリを KonomiTV サーバーのベースディレクトリに設定
                stdout = subprocess.PIPE,  # 標準出力をキャプチャする
                stderr = subprocess.DEVNULL,  # 標準エラー出力を表示しない
                text = True,  # 出力をテキストとして取得する
            )
        if 'Error starting service' in service_start_result.stdout:
            ShowSubProcessErrorLog(
                error_message = 'Windows サービスの起動中に予期しないエラーが発生しました。',
                error_log = service_start_result.stdout.strip(),
            )
            return  # 処理中断

    # ***** Linux: PM2 サービスの起動 *****

    elif platform_type == 'Linux':

        # PM2 サービスを起動
        result = RunSubprocess(
            'PM2 サービスを起動しています…',
            ['/usr/bin/env', 'pm2', 'start', 'KonomiTV'],
            cwd = update_path / 'server/',  # カレントディレクトリを KonomiTV サーバーのベースディレクトリに設定
            error_message = 'PM2 サービスの起動中に予期しないエラーが発生しました。',
            error_log_name = 'PM2 のエラーログ',
        )
        if result is False:
            return  # 処理中断

    # ***** Linux-Docker: Docker コンテナの起動 *****

    elif platform_type == 'Linux-Docker':

        # Docker コンテナを起動
        result = RunSubprocess(
            'Docker コンテナを起動しています…',
            [*docker_compose_command, 'up', '-d', '--force-recreate'],
            cwd = update_path,  # カレントディレクトリを KonomiTV のインストールフォルダに設定
            error_message = 'Docker コンテナの起動中に予期しないエラーが発生しました。',
            error_log_name = 'Docker Compose のエラーログ',
        )
        if result is False:
            return  # 処理中断

    # ***** サービスの起動を待機 *****

    # KonomiTV サービスの起動を監視して起動完了を待機する処理はインストーラーと共通
    RunKonomiTVServiceWaiter(platform_type, update_path)

    # ***** アップデート完了 *****

    # ループバックアドレスまたはリンクローカルアドレスでない IPv4 アドレスとインターフェイス名を取得
    nic_infos = GetNetworkInterfaceInformation()

    # アップデート完了メッセージを表示
    table_done = CreateTable()
    table_done.add_column(RemoveEmojiIfLegacyTerminal(
        'アップデートが完了しました！🎉🎊 すぐに使いはじめられます！🎈\n'
        '下記の URL から、KonomiTV の Web UI にアクセスしてみましょう！\n'
        'もし KonomiTV にアクセスできない場合は、ファイアウォールの設定を確認してみてください。',
    ))

    # アクセス可能な URL のリストを IP アドレスごとに表示
    ## ローカルホスト (127.0.0.1) だけは https://my.local.konomi.tv:7000/ というエイリアスが使える
    urls = [f'https://{nic_info[0].replace(".", "-")}.local.konomi.tv:{server_port}/' for nic_info in nic_infos]
    urls_max_length = max([len(url) for url in urls])  # URL の最大文字長を取得
    table_done.add_row(f'[bright_blue]{f"https://my.local.konomi.tv:{server_port}/": <{urls_max_length}}[/bright_blue] (ローカルホスト)')
    for index, url in enumerate(urls):
        table_done.add_row(f'[bright_blue]{url: <{urls_max_length}}[/bright_blue] ({nic_infos[index][1]})')

    print(Padding(table_done, (1, 2, 0, 2)))

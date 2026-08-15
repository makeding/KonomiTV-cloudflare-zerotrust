from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

import ariblib.constants

from app import logging, schemas
from app.constants import JST, PARTIALLY_RECORDED_TOLERANCE_SECONDS
from app.utils import NormalizeToJSTDatetime
from app.utils.TSInformation import TSInformation


_MMTSMediaType = Literal['video', 'audio', 'unknown']
_VideoScanType = Literal['Interlaced', 'Progressive']
_AudioChannel = Literal['Monaural', 'Stereo', '3ch', '4ch', '5ch', '5.1ch', '6.1ch', '7.1ch', '10.2ch', '22.2ch']


@dataclass(slots=True)
class _MMTSTable:
    """
    MMT-SI のテーブルデータ
    """

    table_id: int
    data: bytes


@dataclass(slots=True)
class _MMTSService:
    """
    MMT-SI から復元したサービス情報
    """

    network_id: int
    service_id: int
    transport_stream_id: int | None
    name: str


@dataclass(slots=True)
class _MMTSEvent:
    """
    MH-EIT から復元した番組情報
    """

    network_id: int
    service_id: int
    transport_stream_id: int | None
    event_id: int
    table_id: int
    section_number: int
    title: str
    description: str
    detail: dict[str, str]
    genres: list[schemas.Genre]
    start_time: datetime
    duration: float
    is_free: bool
    primary_audio_type: str | None
    primary_audio_language: str | None
    secondary_audio_type: str | None
    secondary_audio_language: str | None


@dataclass(slots=True)
class _MMTSMediaInfo:
    """
    MPT と MH-EIT から推定した録画ファイルのメディア情報
    """

    duration: float
    video_resolution_width: int
    video_resolution_height: int
    video_scan_type: _VideoScanType
    video_frame_rate: float
    primary_audio_channel: _AudioChannel
    primary_audio_sampling_rate: int
    secondary_audio_channel: _AudioChannel | None
    secondary_audio_sampling_rate: int | None


@dataclass(frozen=True, slots=True)
class _MMTSAudioComponentInfo:
    """
    MH-音声コンポーネント記述子から復元した音声情報
    """

    audio_type: str
    audio_channel: _AudioChannel
    sampling_rate: int
    language: str
    is_main: bool


@dataclass(slots=True)
class _MMTSSignalingFragment:
    """
    複数 MMTP パケットに分割された signaling message の再構築状態
    """

    packet_sequence_number: int
    fragment_counter: int
    data: bytearray


class MMTSInfoAnalyzer:
    """
    BS4K の MMT/TLV 録画ファイルから録画メタデータを解析するクラス
    """

    # TLV / MMT-SI はファイル先頭と末尾の短い範囲に十分繰り返し出現するため、
    # 大容量録画の全体走査を避ける目的で解析範囲を限定する。
    READ_WINDOW_SIZE = 64 * 1024 * 1024

    # TLV の packet_type。BS4K の MMT は Compressed IP Packet として運ばれる。
    TLV_SYNC_BYTE = 0x7F
    TLV_PACKET_TYPE_COMPRESSED_IP = 0x03

    # MMTP payload_type。
    MMTP_PAYLOAD_TYPE_MPU = 0x00
    MMTP_PAYLOAD_TYPE_CONTROL_MESSAGE = 0x02

    # MMT-SI message_id / table_id。
    MESSAGE_ID_PA = 0x0000
    MESSAGE_ID_M2_SECTION = 0x8000
    MESSAGE_ID_M2_SHORT_SECTION = 0x8002
    TABLE_ID_MPT_SUBSET_MIN = 0x11
    TABLE_ID_MPT = 0x20
    TABLE_ID_PLT = 0x80
    TABLE_ID_MH_EIT_PF = 0x8B
    TABLE_ID_MH_EIT_SCHEDULE_MIN = 0x8C
    TABLE_ID_MH_EIT_SCHEDULE_MAX = 0x9B
    TABLE_ID_MH_SDT = 0x9F
    TABLE_ID_MH_TOT = 0xA1

    # MH descriptor tag。
    DESCRIPTOR_VIDEO_COMPONENT = 0x8010
    DESCRIPTOR_CONTENT = 0x8012
    DESCRIPTOR_AUDIO_COMPONENT = 0x8014
    DESCRIPTOR_SERVICE = 0x8019
    DESCRIPTOR_SHORT_EVENT = 0xF001
    DESCRIPTOR_EXTENDED_EVENT = 0xF002

    def __init__(self, file_path: Path, selected_service_id: int | None = None) -> None:
        """
        MMT/TLV 録画ファイルの解析器を初期化する

        Args:
            file_path (Path): 解析対象の MMT/TLV 録画ファイルパス
            selected_service_id (int | None): 指定するサービスID（複数チャンネル選択用）
        """

        # 解析対象ファイルのパス。probe / table 抽出 / メディア情報推定の全メソッドで参照する。
        # Path は呼び出し元で存在確認済みであることを前提にする。
        self.file_path = file_path

        # 複数サービスを含む MMT/TLV でユーザーが指定したサービス ID。
        # 指定されている場合、MH-EIT / MH-SDT の選択時に最優先で使用する。
        self.selected_service_id = selected_service_id

    @classmethod
    def probe(cls, file_path: Path) -> bool:
        """
        指定ファイルが MMT/TLV として解析可能かを判定する

        Args:
            file_path (Path): 判定対象のファイルパス

        Returns:
            bool: MMT/TLV として解析できる可能性が高い場合 True
        """

        try:
            with file_path.open('rb') as file:
                data = file.read(4 * 1024 * 1024)
        except Exception as ex:
            logging.warning(f'{file_path}: Failed to read data for MMT/TLV probe:', exc_info=ex)
            return False

        # 少なくとも 1 個の TLV 0x03 + MMTP control message が取れれば MMT/TLV とみなす。
        for payload in cls.__iterTLVCompressedIPPayloads(data):
            mmtp_packet = cls.__parseMMTPPacket(payload)
            if mmtp_packet is None:
                continue
            payload_type, _, _, _ = mmtp_packet
            if payload_type == cls.MMTP_PAYLOAD_TYPE_CONTROL_MESSAGE:
                return True
        return False

    def analyze(self, file_hash: str, file_size: int, file_created_at: datetime, file_modified_at: datetime) -> schemas.RecordedProgram | None:
        """
        MMT/TLV 録画ファイルから録画番組メタデータを解析する

        Args:
            file_hash (str): 録画ファイルのハッシュ値
            file_size (int): 録画ファイルサイズ
            file_created_at (datetime): 録画ファイル作成日時
            file_modified_at (datetime): 録画ファイル更新日時

        Returns:
            schemas.RecordedProgram | None: 録画番組情報、取得できなかった場合は None
        """

        tables = self.__collectTables()
        if len(tables) == 0:
            logging.warning(f'{self.file_path}: MMT-SI tables were not found.')
            return None

        service = self.__selectService(tables)
        if service is None:
            logging.warning(f'{self.file_path}: MMT/TLV service information was not found.')
            return None

        # この解析器は現行の高度 BS デジタル放送（BS4K）だけを対象とする。
        ## 他方式の MMT/TLV を誤って BS4K チャンネルとして DB に登録しないよう、ONID を必ず検証する。
        if TSInformation.getNetworkType(service.network_id) != 'BS4K':
            logging.warning(
                f'{self.file_path}: Unsupported MMT/TLV network. '
                f'[network_id: {service.network_id}]'
            )
            return None

        events = self.__collectEvents(tables, service)
        if len(events) == 0:
            logging.warning(f'{self.file_path}: MMT/TLV event information was not found.')
            return None

        recording_time = self.__analyzeRecordingTime(tables)
        event = self.__selectBestEvent(events, file_modified_at, recording_time)
        event_end_time = event.start_time + timedelta(seconds=event.duration)

        # MH-TOT の先頭・末尾時刻を取得できた場合は、EPG 上の番組時間ではなく実際に収録された範囲を動画の時長とする。
        ## 番組の途中で録画が終了したファイルに MH-EIT の番組時長を流用すると、一覧表示やシーク位置が実ファイルより長くなる。
        if recording_time is not None:
            recording_start_time, recording_end_time = recording_time
            recorded_duration = (recording_end_time - recording_start_time).total_seconds()
        else:
            # MH-TOT を十分に取得できない場合だけ、従来どおり MH-EIT の番組時間を録画時間として使用する。
            recording_start_time = event.start_time
            recording_end_time = event_end_time
            recorded_duration = event.duration

        media_info = self.__analyzeMediaInfo(tables, recorded_duration)
        channel = self.__buildChannel(service)

        # MH-TOT と MH-EIT の数秒程度の境界ずれでは、実際に番組本編が欠けているとは限らない。
        ## 普通の MPEG-TS と同じ許容誤差を適用し、数十秒以上の欠落だけを部分録画として扱う。
        start_missing_seconds = (recording_start_time - event.start_time).total_seconds()
        end_missing_seconds = (event_end_time - recording_end_time).total_seconds()

        # MMT/TLV 本体は FFprobe で扱えないため、MPT と MH-EIT から KonomiTV が必要とする最小メディア情報を復元する。
        recorded_video = schemas.RecordedVideo(
            status = 'Recorded',
            file_path = str(self.file_path),
            file_hash = file_hash,
            file_size = file_size,
            file_created_at = file_created_at,
            file_modified_at = file_modified_at,
            recording_start_time = recording_start_time,
            recording_end_time = recording_end_time,
            duration = media_info.duration,
            container_format = 'MMT/TLV',
            video_codec = 'H.265',
            video_codec_profile = 'Main 10',
            video_scan_type = media_info.video_scan_type,
            video_frame_rate = media_info.video_frame_rate,
            video_resolution_width = media_info.video_resolution_width,
            video_resolution_height = media_info.video_resolution_height,
            has_video_stream_changes = False,
            primary_audio_codec = 'AAC-LC',
            primary_audio_channel = media_info.primary_audio_channel,
            primary_audio_sampling_rate = media_info.primary_audio_sampling_rate,
            secondary_audio_codec = 'AAC-LC' if media_info.secondary_audio_channel is not None else None,
            secondary_audio_channel = media_info.secondary_audio_channel,
            secondary_audio_sampling_rate = media_info.secondary_audio_sampling_rate,
            # 必須フィールドのため作成日時・更新日時は適当に現在時刻を入れている
            # この値は参照されず、DB の値は別途自動生成される
            created_at = datetime.now(tz=JST),
            updated_at = datetime.now(tz=JST),
        )

        recorded_program = schemas.RecordedProgram(
            recorded_video = recorded_video,
            channel = channel,
            network_id = service.network_id,
            service_id = service.service_id,
            event_id = event.event_id,
            title = event.title,
            description = event.description,
            detail = event.detail,
            genres = event.genres,
            start_time = event.start_time,
            end_time = event_end_time,
            duration = event.duration,
            is_free = event.is_free,
            secondary_audio_type = event.secondary_audio_type,
            secondary_audio_language = event.secondary_audio_language,
            recording_start_margin = max((event.start_time - recording_start_time).total_seconds(), 0.0),
            recording_end_margin = max((recording_end_time - event_end_time).total_seconds(), 0.0),
            is_partially_recorded = (
                start_missing_seconds > PARTIALLY_RECORDED_TOLERANCE_SECONDS or
                end_missing_seconds > PARTIALLY_RECORDED_TOLERANCE_SECONDS
            ),
            # 必須フィールドのため作成日時・更新日時は適当に現在時刻を入れている
            # この値は参照されず、DB の値は別途自動生成される
            created_at = datetime.now(tz=JST),
            updated_at = datetime.now(tz=JST),
        )

        # MH-EIT に主音声情報がない場合は RecordedProgram 側の安全なデフォルト値を維持する。
        ## Optional 値をそのまま必須フィールドへ渡さず、取得できた情報だけを上書きする。
        if event.primary_audio_type is not None:
            recorded_program.primary_audio_type = event.primary_audio_type
        if event.primary_audio_language is not None:
            recorded_program.primary_audio_language = event.primary_audio_language

        logging.info(
            f'{self.file_path}: MMT/TLV event selected. '
            f'[event_id: {event.event_id}, title: {event.title}, '
            f'start_time: {event.start_time}, duration: {event.duration}]'
        )
        return recorded_program

    def __collectTables(self) -> list[_MMTSTable]:
        """
        解析範囲から MMT-SI テーブルを収集する

        Returns:
            list[_MMTSTable]: 収集した MMT-SI テーブル
        """

        tables: list[_MMTSTable] = []
        for data in self.__readAnalysisWindows():
            # 先頭・末尾ウィンドウ間では MMTP のシーケンスが連続しないため、
            # signaling message の分割再構築状態はウィンドウごとに独立して保持する。
            signaling_fragments: dict[int, _MMTSSignalingFragment] = {}
            for payload in self.__iterTLVCompressedIPPayloads(data):
                mmtp_packet = self.__parseMMTPPacket(payload)
                if mmtp_packet is None:
                    continue
                payload_type, packet_id, packet_sequence_number, mmtp_payload = mmtp_packet
                if payload_type != self.MMTP_PAYLOAD_TYPE_CONTROL_MESSAGE:
                    continue
                tables.extend(self.__parseSignalingPayload(
                    mmtp_payload,
                    packet_id,
                    packet_sequence_number,
                    signaling_fragments,
                ))
        return tables

    def __readAnalysisWindows(self) -> list[bytes]:
        """
        ファイル先頭と末尾の解析ウィンドウを読み込む

        Returns:
            list[bytes]: 解析対象データ
        """

        file_size = self.file_path.stat().st_size
        windows: list[bytes] = []
        with self.file_path.open('rb') as file:
            windows.append(file.read(min(self.READ_WINDOW_SIZE, file_size)))
            if file_size > self.READ_WINDOW_SIZE:
                file.seek(max(file_size - self.READ_WINDOW_SIZE, 0))
                windows.append(file.read(self.READ_WINDOW_SIZE))
        return windows

    @classmethod
    def __iterTLVCompressedIPPayloads(cls, data: bytes) -> Iterator[bytes]:
        """
        TLV から Compressed IP packet payload を列挙する

        Args:
            data (bytes): TLV データ

        Yields:
            bytes: Compressed IP の MMTP payload 部分
        """

        offset = 0
        while offset + 4 <= len(data):
            if data[offset] != cls.TLV_SYNC_BYTE:
                offset += 1
                continue

            packet_type = data[offset + 1]
            packet_length = int.from_bytes(data[offset + 2:offset + 4], 'big')
            packet_end = offset + 4 + packet_length
            if packet_length <= 0 or packet_length > 65535 or packet_end > len(data):
                offset += 1
                continue

            payload = data[offset + 4:packet_end]
            offset = packet_end
            if packet_type != cls.TLV_PACKET_TYPE_COMPRESSED_IP:
                continue

            # ARIB STD-B32 第3部 3.7 に従い、12bit context_id + 4bit sequence + header_type を読み飛ばす。
            ## header_type ごとに後続する部分 IP / UDP ヘッダーの長さが異なるため、MMTP の開始位置を個別に求める。
            if len(payload) < 3:
                continue
            header_type = payload[2]
            payload_offset = 3
            if header_type == 0x20:
                payload_offset += 16 + 4  # 部分 IPv4 ヘッダー + 部分 UDP ヘッダー
            elif header_type == 0x21:
                payload_offset += 2  # IPv4 ヘッダー部の識別子
            elif header_type == 0x60:
                payload_offset += 38 + 4  # 部分 IPv6 ヘッダー + 部分 UDP ヘッダー
            elif header_type != 0x61:
                continue
            if payload_offset > len(payload):
                continue
            yield payload[payload_offset:]

    @classmethod
    def __parseMMTPPacket(cls, data: bytes) -> tuple[int, int, int, bytes] | None:
        """
        MMTP packet の最低限のヘッダーを解析する

        Args:
            data (bytes): MMTP packet データ

        Returns:
            tuple[int, int, int, bytes] | None: payload_type, packet_id, sequence_number, payload
        """

        if len(data) < 12:
            return None
        offset = 0
        first_byte = data[offset]
        offset += 1
        second_byte = data[offset]
        offset += 1
        payload_type = second_byte & 0x3F
        packet_id = int.from_bytes(data[offset:offset + 2], 'big')
        offset += 2
        offset += 4  # delivery_timestamp
        packet_sequence_number = int.from_bytes(data[offset:offset + 4], 'big')
        offset += 4

        if first_byte & 0x20:
            offset += 4
        if first_byte & 0x02:
            if offset + 4 > len(data):
                return None
            extension_header_length = int.from_bytes(data[offset + 2:offset + 4], 'big')
            offset += 4 + extension_header_length
        if offset > len(data):
            return None
        return (payload_type, packet_id, packet_sequence_number, data[offset:])

    def __parseSignalingPayload(
        self,
        payload: bytes,
        packet_id: int,
        packet_sequence_number: int,
        fragments: dict[int, _MMTSSignalingFragment],
    ) -> list[_MMTSTable]:
        """
        MMTP control message payload から MMT-SI テーブルを抽出する

        Args:
            payload (bytes): MMTP control message payload
            packet_id (int): MMTP packet_id
            packet_sequence_number (int): MMTP packet sequence number
            fragments (dict[int, _MMTSSignalingFragment]): packet_id ごとの分割再構築状態

        Returns:
            list[_MMTSTable]: 抽出したテーブル
        """

        if len(payload) < 2:
            return []

        # ARIB STD-B60 表6-1の signaling message payload header を解析する。
        ## length_extension_flag は aggregation 時の message_length が 16bit / 32bit のどちらかを示す。
        flags = payload[0]
        fragmentation_indicator = flags >> 6
        length_extension_flag = bool(flags & 0x02)
        aggregation_flag = bool(flags & 0x01)
        fragment_counter = payload[1]
        message_data = payload[2:]
        tables: list[_MMTSTable] = []

        # aggregation された payload は完全なメッセージだけを複数格納し、fragment_counter は 0 になる。
        if aggregation_flag is True:
            if fragmentation_indicator != 0 or fragment_counter != 0:
                return []
            fragments.pop(packet_id, None)
            length_size = 4 if length_extension_flag is True else 2
            offset = 0
            while offset + length_size <= len(message_data):
                message_length = int.from_bytes(message_data[offset:offset + length_size], 'big')
                offset += length_size
                if message_length <= 0 or offset + message_length > len(message_data):
                    break
                tables.extend(self.__parseSignalingMessage(message_data[offset:offset + message_length]))
                offset += message_length
            return tables

        # fragmentation_indicator=00 は、単一の完全な signaling message を示す。
        if fragmentation_indicator == 0:
            fragments.pop(packet_id, None)
            return self.__parseSignalingMessage(message_data)

        # fragmentation_indicator=01 は分割メッセージの先頭なので、同じ packet_id の古い状態を置き換える。
        if fragmentation_indicator == 1:
            fragments[packet_id] = _MMTSSignalingFragment(
                packet_sequence_number = packet_sequence_number,
                fragment_counter = fragment_counter,
                data = bytearray(message_data),
            )
            return []

        # 中間・最終フラグメントは packet_sequence_number と fragment_counter が連続する場合だけ連結する。
        fragment = fragments.get(packet_id)
        if fragment is None:
            return []
        expected_sequence_number = (fragment.packet_sequence_number + 1) & 0xFFFFFFFF
        expected_fragment_counter = (fragment.fragment_counter - 1) & 0xFF
        if packet_sequence_number != expected_sequence_number or fragment_counter != expected_fragment_counter:
            fragments.pop(packet_id, None)
            return []

        fragment.data.extend(message_data)
        fragment.packet_sequence_number = packet_sequence_number
        fragment.fragment_counter = fragment_counter
        if fragmentation_indicator == 2:
            return []

        # fragmentation_indicator=11 で最終フラグメントまで揃った場合だけ message として解析する。
        fragments.pop(packet_id, None)
        tables.extend(self.__parseSignalingMessage(bytes(fragment.data)))

        return tables

    def __parseSignalingMessage(self, message: bytes) -> list[_MMTSTable]:
        """
        signaling message から MMT-SI テーブルを抽出する

        Args:
            message (bytes): signaling message データ

        Returns:
            list[_MMTSTable]: 抽出したテーブル
        """

        if len(message) < 5:
            return []
        message_id = int.from_bytes(message[0:2], 'big')
        tables: list[_MMTSTable] = []

        if message_id in (self.MESSAGE_ID_M2_SECTION, self.MESSAGE_ID_M2_SHORT_SECTION):
            message_payload_length = int.from_bytes(message[3:5], 'big')
            table = message[5:5 + message_payload_length]
            if len(table) == message_payload_length and len(table) > 0:
                tables.append(_MMTSTable(table_id=table[0], data=table))

        elif message_id == self.MESSAGE_ID_PA and len(message) >= 7:
            payload_length = int.from_bytes(message[3:7], 'big')
            payload = message[7:7 + payload_length]
            if len(payload) != payload_length or len(payload) == 0:
                return tables

            # ARIB STD-B60 表7-1に従い、extension の table_id / table_length 一覧を先に読み取る。
            ## table_length は後続する各 table() 全体のバイト長なので、テーブル自身の length を再解釈しない。
            table_count = payload[0]
            offset = 1
            table_entries: list[tuple[int, int]] = []
            for _ in range(table_count):
                if offset + 4 > len(payload):
                    return tables
                table_id = payload[offset]
                table_length = int.from_bytes(payload[offset + 2:offset + 4], 'big')
                table_entries.append((table_id, table_length))
                offset += 4

            # extension に宣言された順序と長さで message_payload 内のテーブルを切り出す。
            for table_id, table_length in table_entries:
                table_end = offset + table_length
                if table_end > len(payload):
                    break
                table = payload[offset:table_end]
                if len(table) > 0 and table[0] == table_id:
                    tables.append(_MMTSTable(table_id=table_id, data=table))
                offset = table_end

        return tables

    def __selectService(self, tables: list[_MMTSTable]) -> _MMTSService | None:
        """
        MH-SDT / MH-EIT から対象サービスを選択する

        Args:
            tables (list[_MMTSTable]): MMT-SI テーブル

        Returns:
            _MMTSService | None: 選択されたサービス情報
        """

        services = self.__parseServices(tables)
        if self.selected_service_id is not None:
            for service in services:
                if service.service_id == self.selected_service_id:
                    return service

        # MH-SDT が取れない場合でも、MH-EIT のヘッダーから最低限の service_id / network_id は復元できる。
        if len(services) == 0:
            for table in tables:
                if self.__isEITTableID(table.table_id) is False:
                    continue
                if len(table.data) < 14:
                    continue
                if bool(table.data[5] & 0x01) is False:
                    continue
                network_id = int.from_bytes(table.data[10:12], 'big')
                service_id = int.from_bytes(table.data[3:5], 'big')
                transport_stream_id = int.from_bytes(table.data[8:10], 'big')
                return _MMTSService(
                    network_id = network_id,
                    service_id = service_id,
                    transport_stream_id = transport_stream_id,
                    name = f'BS4K {service_id}',
                )

        if len(services) == 0:
            return None
        return services[0]

    @classmethod
    def __isMPTTableID(cls, table_id: int) -> bool:
        """
        table_id が MPT または MPT subset の範囲かを判定する

        Args:
            table_id (int): 判定する table_id

        Returns:
            bool: MPT の table_id である場合 True
        """

        return cls.TABLE_ID_MPT_SUBSET_MIN <= table_id <= cls.TABLE_ID_MPT

    @classmethod
    def __isEITTableID(cls, table_id: int) -> bool:
        """
        table_id が MH-EIT p/f または schedule の範囲かを判定する

        Args:
            table_id (int): 判定する table_id

        Returns:
            bool: MH-EIT の table_id である場合 True
        """

        return (
            table_id == cls.TABLE_ID_MH_EIT_PF or
            cls.TABLE_ID_MH_EIT_SCHEDULE_MIN <= table_id <= cls.TABLE_ID_MH_EIT_SCHEDULE_MAX
        )

    def __parseServices(self, tables: list[_MMTSTable]) -> list[_MMTSService]:
        """
        MH-SDT からサービス情報を解析する

        Args:
            tables (list[_MMTSTable]): MMT-SI テーブル

        Returns:
            list[_MMTSService]: サービス情報一覧
        """

        services: list[_MMTSService] = []
        seen_service_ids: set[int] = set()

        for table in tables:
            if table.table_id != self.TABLE_ID_MH_SDT or len(table.data) < 16:
                continue
            data = table.data
            # current_next_indicator=0 の MH-SDT は次バージョンなので、現行サービス情報には使わない。
            if bool(data[5] & 0x01) is False:
                continue
            section_length = ((data[1] & 0x0F) << 8) | data[2]
            section_end = min(3 + section_length - 4, len(data))
            transport_stream_id = int.from_bytes(data[3:5], 'big')
            network_id = int.from_bytes(data[8:10], 'big')
            offset = 11
            while offset + 5 <= section_end:
                service_id = int.from_bytes(data[offset:offset + 2], 'big')
                descriptors_loop_length = ((data[offset + 3] & 0x0F) << 8) | data[offset + 4]
                descriptors = data[offset + 5:offset + 5 + descriptors_loop_length]
                service_name = self.__parseServiceName(descriptors)
                if service_name is not None and service_id not in seen_service_ids:
                    services.append(_MMTSService(
                        network_id = network_id,
                        service_id = service_id,
                        transport_stream_id = transport_stream_id,
                        name = service_name,
                    ))
                    seen_service_ids.add(service_id)
                offset += 5 + descriptors_loop_length
        return services

    def __parseServiceName(self, descriptors: bytes) -> str | None:
        """
        MH service descriptor からサービス名を解析する

        Args:
            descriptors (bytes): descriptor loop

        Returns:
            str | None: サービス名
        """

        for tag, payload in self.__iterDescriptors(descriptors):
            if tag != self.DESCRIPTOR_SERVICE or len(payload) < 3:
                continue
            provider_name_length = payload[1]
            service_name_length_offset = 2 + provider_name_length
            if service_name_length_offset >= len(payload):
                continue
            service_name_length = payload[service_name_length_offset]
            service_name = payload[service_name_length_offset + 1:service_name_length_offset + 1 + service_name_length]
            if len(service_name) == 0:
                continue
            return TSInformation.formatString(self.__decodeText(service_name))
        return None

    def __collectEvents(self, tables: list[_MMTSTable], service: _MMTSService) -> list[_MMTSEvent]:
        """
        MH-EIT から番組候補を収集する

        Args:
            tables (list[_MMTSTable]): MMT-SI テーブル
            service (_MMTSService): 対象サービス情報

        Returns:
            list[_MMTSEvent]: 番組候補一覧
        """

        events: list[_MMTSEvent] = []
        seen: set[tuple[int, int, datetime]] = set()
        for table in tables:
            if self.__isEITTableID(table.table_id) is False:
                continue
            for event in self.__parseEITTable(table.table_id, table.data):
                if event.service_id != service.service_id:
                    continue
                if event.network_id != service.network_id:
                    continue
                # 同一番組でも p/f と schedule では選択時の信頼度が異なるため、
                # table_id ごとに候補を保持して後段で正しく優先順位を付けられるようにする。
                key = (event.table_id, event.event_id, event.start_time)
                if key in seen:
                    continue
                seen.add(key)
                events.append(event)
        return events

    def __parseEITTable(self, table_id: int, data: bytes) -> list[_MMTSEvent]:
        """
        MH-EIT テーブルから番組情報を解析する

        Args:
            table_id (int): MH-EIT の table_id
            data (bytes): MH-EIT テーブル

        Returns:
            list[_MMTSEvent]: 番組情報一覧
        """

        if len(data) < 18:
            return []
        # current_next_indicator=0 は次バージョンの MH-EIT なので、録画番組候補には使わない。
        if bool(data[5] & 0x01) is False:
            return []
        section_length = ((data[1] & 0x0F) << 8) | data[2]
        section_end = min(3 + section_length - 4, len(data))
        service_id = int.from_bytes(data[3:5], 'big')
        section_number = data[6]
        transport_stream_id = int.from_bytes(data[8:10], 'big')
        network_id = int.from_bytes(data[10:12], 'big')
        offset = 14
        events: list[_MMTSEvent] = []
        while offset + 12 <= section_end:
            event_id = int.from_bytes(data[offset:offset + 2], 'big')
            start_time = self.__parseMJDTime(data[offset + 2:offset + 7])
            duration = self.__parseBCDDuration(data[offset + 7:offset + 10])
            is_free = not bool(data[offset + 10] & 0x10)
            descriptors_loop_length = ((data[offset + 10] & 0x0F) << 8) | data[offset + 11]
            descriptor_start = offset + 12
            descriptor_end = min(descriptor_start + descriptors_loop_length, section_end)
            descriptors = data[descriptor_start:descriptor_end]
            offset = descriptor_end

            if start_time is None or duration <= 0:
                continue

            event = self.__buildEventFromDescriptors(
                network_id = network_id,
                service_id = service_id,
                transport_stream_id = transport_stream_id,
                event_id = event_id,
                table_id = table_id,
                section_number = section_number,
                start_time = start_time,
                duration = duration,
                is_free = is_free,
                descriptors = descriptors,
            )
            events.append(event)
        return events

    def __buildEventFromDescriptors(
        self,
        network_id: int,
        service_id: int,
        transport_stream_id: int,
        event_id: int,
        table_id: int,
        section_number: int,
        start_time: datetime,
        duration: float,
        is_free: bool,
        descriptors: bytes,
    ) -> _MMTSEvent:
        """
        descriptor loop から番組情報を組み立てる

        Args:
            network_id (int): network_id
            service_id (int): service_id
            transport_stream_id (int): transport_stream_id
            event_id (int): event_id
            table_id (int): MH-EIT の table_id
            section_number (int): section_number
            start_time (datetime): 番組開始時刻
            duration (float): 番組長
            is_free (bool): 無料番組かどうか
            descriptors (bytes): descriptor loop

        Returns:
            _MMTSEvent: 番組情報
        """

        title = TSInformation.formatString(self.file_path.stem)
        description = ''
        detail: dict[str, str] = {}
        genres: list[schemas.Genre] = []
        primary_audio_type: str | None = None
        primary_audio_language: str | None = None
        secondary_audio_type: str | None = None
        secondary_audio_language: str | None = None

        for tag, payload in self.__iterDescriptors(descriptors):
            if tag == self.DESCRIPTOR_SHORT_EVENT:
                parsed_title, parsed_description = self.__parseShortEventDescriptor(payload)
                if parsed_title:
                    title = parsed_title
                if parsed_description:
                    description = parsed_description
            elif tag == self.DESCRIPTOR_EXTENDED_EVENT:
                # 複数の拡張形式イベント記述子に同じ見出しがある場合も、既存情報を上書きせず保持する。
                for head, text in self.__parseExtendedEventDescriptor(payload).items():
                    while head in detail:
                        head += '\t'
                    detail[head] = text
            elif tag == self.DESCRIPTOR_CONTENT:
                genres.extend(self.__parseContentDescriptor(payload))
            elif tag == self.DESCRIPTOR_AUDIO_COMPONENT:
                audio_info = self.__parseAudioComponentDescriptor(payload)
                if audio_info is None:
                    continue
                if audio_info.is_main is True and primary_audio_type is None:
                    primary_audio_type = audio_info.audio_type
                    primary_audio_language = audio_info.language
                elif audio_info.is_main is False and secondary_audio_type is None:
                    secondary_audio_type = audio_info.audio_type
                    secondary_audio_language = audio_info.language

        if description == '' and len(detail) > 0:
            description = next(iter(detail.values()))

        return _MMTSEvent(
            network_id = network_id,
            service_id = service_id,
            transport_stream_id = transport_stream_id,
            event_id = event_id,
            table_id = table_id,
            section_number = section_number,
            title = title,
            description = description,
            detail = detail,
            genres = genres,
            start_time = start_time,
            duration = duration,
            is_free = is_free,
            primary_audio_type = primary_audio_type,
            primary_audio_language = primary_audio_language,
            secondary_audio_type = secondary_audio_type,
            secondary_audio_language = secondary_audio_language,
        )

    def __analyzeRecordingTime(self, tables: list[_MMTSTable]) -> tuple[datetime, datetime] | None:
        """
        解析ウィンドウ内の MH-TOT から録画開始・終了時刻を復元する

        Args:
            tables (list[_MMTSTable]): MMT-SI テーブル

        Returns:
            tuple[datetime, datetime] | None: 録画開始・終了時刻、復元できない場合は None
        """

        tot_times: list[datetime] = []
        for table in tables:
            if table.table_id != self.TABLE_ID_MH_TOT or len(table.data) < 8:
                continue
            # ARIB STD-B60 表7-25では、MH-TOT の JST_time は section header 直後の5バイトに格納される。
            tot_time = self.__parseMJDTime(table.data[3:8])
            if tot_time is not None:
                tot_times.append(tot_time)

        # 先頭・末尾ウィンドウの双方から異なる時刻を取得できた場合だけ、録画時間範囲として採用する。
        if len(tot_times) < 2:
            return None
        recording_start_time = min(tot_times)
        recording_end_time = max(tot_times)
        if recording_start_time >= recording_end_time:
            return None
        return (recording_start_time, recording_end_time)

    def __selectBestEvent(
        self,
        events: list[_MMTSEvent],
        file_modified_at: datetime,
        recording_time: tuple[datetime, datetime] | None,
    ) -> _MMTSEvent:
        """
        録画ファイルに最も近い番組候補を選択する

        Args:
            events (list[_MMTSEvent]): 番組候補一覧
            file_modified_at (datetime): ファイル更新日時
            recording_time (tuple[datetime, datetime] | None): MH-TOT から復元した録画開始・終了時刻

        Returns:
            _MMTSEvent: 選択した番組情報
        """

        # MH-TOT は放送波に含まれる実時刻なので、録画時間と最も長く重なる EIT 候補を最優先する。
        if recording_time is not None:
            recording_start_time, recording_end_time = recording_time
            recording_duration = (recording_end_time - recording_start_time).total_seconds()
            recording_mid_time = recording_start_time + timedelta(seconds=recording_duration / 2)

            def ScoreByRecordingTime(event: _MMTSEvent) -> tuple[float, int, int, float]:
                """
                MH-TOT の録画時間との重なりで番組候補を評価する

                Args:
                    event (_MMTSEvent): 評価対象の番組候補

                Returns:
                    tuple[float, int, int, float]: 重複秒数、録画中点を含むか、p/fか、中心時刻との差
                """

                event_end_time = event.start_time + timedelta(seconds=event.duration)
                overlap_start_time = max(event.start_time, recording_start_time)
                overlap_end_time = min(event_end_time, recording_end_time)
                overlap_seconds = max((overlap_end_time - overlap_start_time).total_seconds(), 0.0)
                contains_mid_time = int(event.start_time <= recording_mid_time < event_end_time)
                is_present_following = int(event.table_id == self.TABLE_ID_MH_EIT_PF)
                event_mid_time = event.start_time + timedelta(seconds=event.duration / 2)
                center_distance_seconds = abs((event_mid_time - recording_mid_time).total_seconds())
                return (overlap_seconds, contains_mid_time, is_present_following, -center_distance_seconds)

            selected_event = max(events, key=ScoreByRecordingTime)
            overlap_seconds = ScoreByRecordingTime(selected_event)[0]
            if overlap_seconds > 0:
                logging.info(
                    f'{self.file_path}: Selected MMT/TLV event by MH-TOT recording time. '
                    f'[recording_start_time: {recording_start_time}, recording_end_time: {recording_end_time}, '
                    f'overlap_seconds: {overlap_seconds:.1f}, event_id: {selected_event.event_id}, '
                    f'title: {selected_event.title}]'
                )
                return selected_event

        # 録画ファイル名に開始時刻が含まれる場合、EIT 候補と時間的に一致する番組を次に優先する。
        ## 録画開始マージン中のファイル先頭には前番組の EIT[p/f] present が含まれるため、
        ## 単純に最初の present を選ぶと、番組境界をまたぐ録画で前番組を誤採用してしまう。
        filename_info = TSInformation.parseFilenameInfo(self.file_path.stem)
        filename_start_time = filename_info['start_time']
        if isinstance(filename_start_time, datetime):
            matching_events = [
                event for event in events
                if event.start_time <= filename_start_time < event.start_time + timedelta(seconds=event.duration)
            ]
            if len(matching_events) > 0:
                def ScoreByFilenameStartTime(event: _MMTSEvent) -> tuple[int, int, float]:
                    """
                    ファイル名の開始時刻との一致度で番組候補を評価する

                    Args:
                        event (_MMTSEvent): 評価対象の番組候補

                    Returns:
                        tuple[int, int, float]: 開始時刻の完全一致、p/f present、開始時刻との差
                    """

                    is_exact_start = int(event.start_time == filename_start_time)
                    is_present = int(
                        event.table_id == self.TABLE_ID_MH_EIT_PF and
                        event.section_number == 0
                    )
                    distance_seconds = abs((event.start_time - filename_start_time).total_seconds())
                    return (is_exact_start, is_present, -distance_seconds)

                selected_event = max(matching_events, key=ScoreByFilenameStartTime)
                logging.info(
                    f'{self.file_path}: Selected MMT/TLV event by filename start time. '
                    f'[filename_start_time: {filename_start_time}, event_id: {selected_event.event_id}, '
                    f'title: {selected_event.title}]'
                )
                return selected_event

            # コピー後の mtime など不確実な情報で誤選択するより、p/f による後段の選択へ安全にフォールバックする。
            logging.warning(
                f'{self.file_path}: No MMT/TLV event overlaps with the filename start time. '
                f'[filename_start_time: {filename_start_time}]'
            )

        # ファイル名から時刻を復元できない場合は、末尾側で最後に観測した p/f present を優先する。
        ## テーブルはファイル先頭・末尾の順に収集されるため、先頭マージン中の前番組ではなく、
        ## 録画本編または録画終了時点に最も近い present を選択できる。
        ## schedule の section_number も 0 になりうるため、table_id を必ず併せて判定する。
        present_events = [
            event for event in events
            if event.table_id == self.TABLE_ID_MH_EIT_PF and event.section_number == 0
        ]
        if len(present_events) > 0:
            return present_events[-1]

        # 長時間録画などで schedule しか取れない場合は、ファイル更新時刻から最も近い番組を選ぶ。
        return min(events, key=lambda event: abs((file_modified_at - event.start_time).total_seconds()))

    def __analyzeMediaInfo(self, tables: list[_MMTSTable], fallback_duration: float) -> _MMTSMediaInfo:
        """
        MPT からメディア情報を推定する

        Args:
            tables (list[_MMTSTable]): MMT-SI テーブル
            fallback_duration (float): MPT から時長を推定できない場合のフォールバック時長

        Returns:
            _MMTSMediaInfo: メディア情報
        """

        video_width = 3840
        video_height = 2160
        video_scan_type: _VideoScanType = 'Progressive'
        video_frame_rate = 59.94
        audio_components: list[_MMTSAudioComponentInfo] = []
        seen_audio_asset_ids: set[bytes] = set()

        for table in tables:
            if self.__isMPTTableID(table.table_id) is False:
                continue
            for asset_id, media_type, descriptor_payloads in self.__parseMPTAssets(table.data):
                if media_type == 'video':
                    for tag, payload in descriptor_payloads:
                        if tag != self.DESCRIPTOR_VIDEO_COMPONENT or len(payload) < 2:
                            continue
                        resolution_code = (payload[0] >> 4) & 0x0F
                        video_scan_type = 'Progressive' if bool(payload[1] & 0x80) is True else 'Interlaced'
                        frame_rate_code = payload[1] & 0x1F
                        video_width, video_height = self.__resolveVideoResolution(resolution_code)
                        video_frame_rate = self.__resolveVideoFrameRate(frame_rate_code)
                elif media_type == 'audio':
                    # 同一 asset_id の MPT は解析ウィンドウ内で何度も再送されるので、一度だけ音声情報を収集する。
                    ## descriptor が同じでも別 asset_id なら独立した音声ストリームとして保持する。
                    if asset_id in seen_audio_asset_ids:
                        continue
                    for tag, payload in descriptor_payloads:
                        if tag != self.DESCRIPTOR_AUDIO_COMPONENT:
                            continue
                        audio_info = self.__parseAudioComponentDescriptor(payload)
                        if audio_info is None:
                            continue
                        audio_components.append(audio_info)
                        seen_audio_asset_ids.add(asset_id)

        # main_component_flag が立つ音声を必ず主音声側へ配置し、残りの最初の音声だけを副音声として扱う。
        audio_components.sort(key=lambda audio_info: int(audio_info.is_main), reverse=True)
        primary_audio_channel = audio_components[0].audio_channel if len(audio_components) > 0 else 'Stereo'
        primary_audio_sampling_rate = audio_components[0].sampling_rate if len(audio_components) > 0 else 48000
        secondary_audio_channel = audio_components[1].audio_channel if len(audio_components) > 1 else None
        secondary_audio_sampling_rate = audio_components[1].sampling_rate if len(audio_components) > 1 else None

        return _MMTSMediaInfo(
            duration = fallback_duration,
            video_resolution_width = video_width,
            video_resolution_height = video_height,
            video_scan_type = video_scan_type,
            video_frame_rate = video_frame_rate,
            primary_audio_channel = primary_audio_channel,
            primary_audio_sampling_rate = primary_audio_sampling_rate,
            secondary_audio_channel = secondary_audio_channel,
            secondary_audio_sampling_rate = secondary_audio_sampling_rate,
        )

    def __parseMPTAssets(self, data: bytes) -> list[tuple[bytes, _MMTSMediaType, list[tuple[int, bytes]]]]:
        """
        MPT から asset type と descriptor loop を解析する

        Args:
            data (bytes): MPT table

        Returns:
            list[tuple[bytes, _MMTSMediaType, list[tuple[int, bytes]]]]: asset_id, media_type, descriptor 一覧
        """

        assets: list[tuple[bytes, _MMTSMediaType, list[tuple[int, bytes]]]] = []
        if len(data) < 8 or self.__isMPTTableID(data[0]) is False:
            return assets
        table_length = int.from_bytes(data[2:4], 'big')
        if len(data) < 4 + table_length:
            return assets
        payload = data[4:4 + table_length]
        if len(payload) < 2:
            return assets

        offset = 1
        package_id_length = payload[offset]
        offset += 1 + package_id_length
        if offset + 2 > len(payload):
            return assets
        descriptors_length = int.from_bytes(payload[offset:offset + 2], 'big')
        offset += 2 + descriptors_length
        if offset >= len(payload):
            return assets
        asset_count = payload[offset]
        offset += 1

        for _ in range(asset_count):
            if offset + 6 > len(payload):
                break
            offset += 5
            asset_id_length = payload[offset]
            offset += 1
            if offset + asset_id_length > len(payload):
                break
            asset_id = payload[offset:offset + asset_id_length]
            offset += asset_id_length
            if offset + 6 > len(payload):
                break
            asset_type = payload[offset:offset + 4].decode('ascii', errors='ignore')
            offset += 4
            offset += 1
            location_count = payload[offset]
            offset += 1
            for _ in range(location_count):
                offset = self.__skipLocation(payload, offset)
            if offset + 2 > len(payload):
                break
            descriptors_length = int.from_bytes(payload[offset:offset + 2], 'big')
            offset += 2
            descriptors = payload[offset:offset + descriptors_length]
            offset += descriptors_length

            if asset_type in ('hvc1', 'hev1'):
                media_type = 'video'
            elif asset_type == 'mp4a':
                media_type = 'audio'
            else:
                media_type = 'unknown'
            assets.append((asset_id, media_type, list(self.__iterDescriptors(descriptors))))
        return assets

    def __skipLocation(self, data: bytes, offset: int) -> int:
        """
        MMT location 情報をスキップする

        Args:
            data (bytes): MPT payload
            offset (int): location 開始位置

        Returns:
            int: location 終端位置
        """

        if offset >= len(data):
            return offset
        location_type = data[offset]
        offset += 1
        if location_type == 0x00:
            return min(offset + 2, len(data))
        if location_type == 0x01:
            return min(offset + 12, len(data))
        if location_type == 0x02:
            return min(offset + 36, len(data))
        if location_type == 0x03:
            return min(offset + 6, len(data))
        if location_type == 0x04:
            return min(offset + 36, len(data))
        if location_type == 0x05:
            if offset >= len(data):
                return offset
            url_length = data[offset]
            return min(offset + 1 + url_length, len(data))
        return len(data)

    def __buildChannel(self, service: _MMTSService) -> schemas.Channel:
        """
        MMT/TLV のサービス情報から Channel schema を構築する

        Args:
            service (_MMTSService): サービス情報

        Returns:
            schemas.Channel: チャンネル情報
        """

        # analyze() で ONID が高度 BS デジタル放送であることを検証済みなので、ここでは BS4K に固定できる。
        channel_type: Literal['BS4K'] = 'BS4K'
        remocon_id = TSInformation.calculateRemoconID(channel_type, service.service_id)
        channel_number = f'{remocon_id:03d}'
        channel = schemas.Channel(
            id = f'NID{service.network_id}-SID{service.service_id:03d}',
            display_channel_id = channel_type.lower() + channel_number,
            network_id = service.network_id,
            service_id = service.service_id,
            transport_stream_id = service.transport_stream_id,
            remocon_id = remocon_id,
            channel_number = channel_number,
            type = channel_type,
            name = service.name,
        )
        channel.is_subchannel = TSInformation.calculateIsSubchannel(channel.type, channel.service_id)
        channel.is_radiochannel = False
        channel.is_watchable = False
        return channel

    def __parseShortEventDescriptor(self, payload: bytes) -> tuple[str | None, str | None]:
        """
        MH short event descriptor を解析する

        Args:
            payload (bytes): descriptor payload

        Returns:
            tuple[str | None, str | None]: 番組名, 番組概要
        """

        if len(payload) < 6:
            return (None, None)
        offset = 3
        event_name_length = payload[offset]
        offset += 1
        if offset + event_name_length > len(payload):
            return (None, None)
        event_name = payload[offset:offset + event_name_length]
        offset += event_name_length
        if offset + 2 > len(payload):
            return (TSInformation.formatString(self.__decodeText(event_name)), None)
        # ARIB STD-B60 表7-45では text_length は 16bit。
        text_length = int.from_bytes(payload[offset:offset + 2], 'big')
        offset += 2
        text = payload[offset:offset + text_length]
        return (
            TSInformation.formatString(self.__decodeText(event_name)),
            TSInformation.formatString(self.__decodeText(text)).strip(),
        )

    def __parseExtendedEventDescriptor(self, payload: bytes) -> dict[str, str]:
        """
        MH extended event descriptor を解析する

        Args:
            payload (bytes): descriptor payload

        Returns:
            dict[str, str]: 見出しと本文
        """

        if len(payload) < 6:
            return {}
        detail: dict[str, str] = {}
        offset = 4
        items_length = int.from_bytes(payload[offset:offset + 2], 'big')
        offset += 2
        items_end = min(offset + items_length, len(payload))
        while offset < items_end:
            item_description_length = payload[offset]
            offset += 1
            if offset + item_description_length > items_end:
                break
            item_description = payload[offset:offset + item_description_length]
            offset += item_description_length
            if offset + 2 > items_end:
                break
            # ARIB STD-B60 表7-46では item_length は 16bit。
            item_length = int.from_bytes(payload[offset:offset + 2], 'big')
            offset += 2
            if offset + item_length > items_end:
                break
            item = payload[offset:offset + item_length]
            offset += item_length
            head = TSInformation.formatString(self.__decodeText(item_description)).replace('◇', '').strip(' \r\n')
            text = TSInformation.formatString(self.__decodeText(item)).strip()
            if head == '':
                head = '番組内容'
            while head in detail:
                head += '\t'
            if text != '':
                detail[head] = text

        # item loop 以外の text_char も fallback として拾う。
        offset = items_end
        if offset + 2 <= len(payload):
            text_length = int.from_bytes(payload[offset:offset + 2], 'big')
            text = payload[offset + 2:offset + 2 + text_length]
            if len(text) > 0 and '番組内容' not in detail:
                detail['番組内容'] = TSInformation.formatString(self.__decodeText(text)).strip()
        return detail

    def __parseContentDescriptor(self, payload: bytes) -> list[schemas.Genre]:
        """
        MH content descriptor からジャンル情報を解析する

        Args:
            payload (bytes): descriptor payload

        Returns:
            list[schemas.Genre]: 番組ジャンル一覧
        """

        genres: list[schemas.Genre] = []
        offset = 0
        while offset + 2 <= len(payload):
            content_nibble = payload[offset]
            user_nibble = payload[offset + 1]
            offset += 2
            content_nibble_level_1 = content_nibble >> 4
            content_nibble_level_2 = content_nibble & 0x0F
            genre_tuple = ariblib.constants.CONTENT_TYPE.get(content_nibble_level_1)
            if genre_tuple is None:
                continue

            genre: schemas.Genre = {
                'major': genre_tuple[0].replace('／', '・'),
                'middle': genre_tuple[1].get(content_nibble_level_2, '未定義').replace('／', '・'),
            }
            # 拡張ジャンルは「BS/地上デジタル放送用番組付属情報」だけ user_nibble で具体化する。
            if genre['major'] == '拡張':
                if genre['middle'] != 'BS/地上デジタル放送用番組付属情報':
                    continue
                genre['middle'] = ariblib.constants.USER_TYPE.get(user_nibble, '未定義')
            genres.append(genre)
        return genres

    def __parseAudioComponentDescriptor(self, payload: bytes) -> _MMTSAudioComponentInfo | None:
        """
        MH audio component descriptor を解析する

        Args:
            payload (bytes): descriptor payload

        Returns:
            _MMTSAudioComponentInfo | None: 音声形式・チャンネル・サンプリング周波数・言語・主音声フラグ
        """

        if len(payload) < 10:
            return None

        # 現行 BS4K の mp4a asset は MPEG-4 AAC (stream_content=0x03) として記述される。
        ## ALS などを AAC-LC と誤登録しないよう、別の stream_content はこの解析器では扱わない。
        stream_content = payload[0] & 0x0F
        if stream_content != 0x03:
            return None
        component_type = payload[1]
        audio_mode = component_type & 0x1F
        if not (0x01 <= audio_mode <= 0x11):
            return None
        flags = payload[6]
        is_multi_lingual = bool(flags & 0x80)
        is_main = bool(flags & 0x40)
        sampling_rate_code = (flags >> 1) & 0x07
        language = TSInformation.getISO639LanguageCodeName(payload[7:10].decode('ascii', errors='ignore'))

        # デュアルモノで ES_multi_lingual_flag=1 の場合だけ第2言語コードが続く。
        if audio_mode == 0x02:
            if is_multi_lingual is True and len(payload) >= 13:
                second_language = TSInformation.getISO639LanguageCodeName(payload[10:13].decode('ascii', errors='ignore'))
                language += '+' + second_language
            elif is_multi_lingual is False:
                language += '+副音声'

        return _MMTSAudioComponentInfo(
            audio_type = self.__resolveAudioType(audio_mode),
            audio_channel = self.__resolveAudioChannel(audio_mode),
            sampling_rate = self.__resolveAudioSamplingRate(sampling_rate_code),
            language = language,
            is_main = is_main,
        )

    def __iterDescriptors(self, descriptors: bytes) -> Iterator[tuple[int, bytes]]:
        """
        MMT-SI descriptor loop を列挙する

        Args:
            descriptors (bytes): descriptor loop

        Yields:
            tuple[int, bytes]: descriptor tag と payload
        """

        offset = 0
        while offset + 3 <= len(descriptors):
            tag = int.from_bytes(descriptors[offset:offset + 2], 'big')
            offset += 2
            length_bytes = 1
            if (0x4000 <= tag <= 0x6FFF) or tag >= 0xF000:
                length_bytes = 2
            elif 0x7000 <= tag <= 0x7FFF:
                length_bytes = 4
            if offset + length_bytes > len(descriptors):
                break
            if length_bytes == 1:
                length = descriptors[offset]
            elif length_bytes == 2:
                length = int.from_bytes(descriptors[offset:offset + 2], 'big')
            else:
                length = int.from_bytes(descriptors[offset:offset + 4], 'big')
            offset += length_bytes
            if offset + length > len(descriptors):
                break
            yield (tag, descriptors[offset:offset + length])
            offset += length

    def __parseMJDTime(self, data: bytes) -> datetime | None:
        """
        MJD + BCD の日時表現を datetime に変換する

        Args:
            data (bytes): 5 バイトの日時データ

        Returns:
            datetime | None: JST の datetime
        """

        if len(data) != 5 or data == b'\xff\xff\xff\xff\xff':
            return None
        if any(self.__isValidBCD(value) is False for value in data[2:5]):
            return None
        mjd = int.from_bytes(data[0:2], 'big')
        y = int((mjd - 15078.2) / 365.25)
        m = int((mjd - 14956.1 - int(y * 365.25)) / 30.6001)
        day = int(mjd - 14956 - int(y * 365.25) - int(m * 30.6001))
        k = 1 if m in (14, 15) else 0
        year = 1900 + y + k
        month = m - 1 - k * 12
        hour = self.__decodeBCD(data[2])
        minute = self.__decodeBCD(data[3])
        second = self.__decodeBCD(data[4])
        try:
            return NormalizeToJSTDatetime(datetime(year, month, day, hour, minute, second, tzinfo=JST))
        except ValueError:
            return None

    def __parseBCDDuration(self, data: bytes) -> float:
        """
        BCD の HH:MM:SS を秒数に変換する

        Args:
            data (bytes): 3 バイトの duration

        Returns:
            float: 秒数
        """

        if len(data) != 3 or any(self.__isValidBCD(value) is False for value in data):
            return 0.0
        hours = self.__decodeBCD(data[0])
        minutes = self.__decodeBCD(data[1])
        seconds = self.__decodeBCD(data[2])
        return float(hours * 3600 + minutes * 60 + seconds)

    def __decodeBCD(self, value: int) -> int:
        """
        BCD 1 バイトを整数に変換する

        Args:
            value (int): BCD 値

        Returns:
            int: 整数
        """

        return ((value >> 4) * 10) + (value & 0x0F)

    def __isValidBCD(self, value: int) -> bool:
        """
        1 バイトの値が有効な BCD 表現かを判定する

        Args:
            value (int): 判定する値

        Returns:
            bool: 上位・下位 nibble がともに 0～9 の場合 True
        """

        return (value >> 4) <= 9 and (value & 0x0F) <= 9

    def __resolveVideoResolution(self, resolution_code: int) -> tuple[int, int]:
        """
        video_component_descriptor の解像度コードを幅・高さに変換する

        Args:
            resolution_code (int): 解像度コード

        Returns:
            tuple[int, int]: 幅, 高さ
        """

        if resolution_code == 0x07:
            return (7680, 4320)
        if resolution_code == 0x06:
            return (3840, 2160)
        if resolution_code == 0x05:
            return (1920, 1080)
        return (3840, 2160)

    def __resolveVideoFrameRate(self, frame_rate_code: int) -> float:
        """
        video_component_descriptor のフレームレートコードを fps に変換する

        Args:
            frame_rate_code (int): フレームレートコード

        Returns:
            float: fps
        """

        # ARIB STD-B60 表7-50の定義をそのまま fps に変換する。
        frame_rates = {
            0x01: 15.0,
            0x02: 24 / 1.001,
            0x03: 24.0,
            0x04: 25.0,
            0x05: 30 / 1.001,
            0x06: 30.0,
            0x07: 50.0,
            0x08: 60 / 1.001,
            0x09: 60.0,
            0x0A: 100.0,
            0x0B: 120 / 1.001,
            0x0C: 120.0,
        }
        return round(frame_rates.get(frame_rate_code, 60 / 1.001), 2)

    def __resolveAudioType(self, audio_mode: int) -> str:
        """
        audio_component_descriptor の component_type を表示文字列に変換する

        Args:
            audio_mode (int): component_type の下位5bitに格納された音声モード

        Returns:
            str: 音声形式
        """

        # ARIB STD-B60 表7-60。component_type の上位3bitは dialog control / 障がい者用音声フラグなので、
        # 呼び出し元でマスクした下位5bitだけを音声モードとして解釈する。
        audio_types = {
            0x01: '1/0モード(シングルモノ)',
            0x02: '1/0+1/0モード(デュアルモノ)',
            0x03: '2/0モード(ステレオ)',
            0x04: '2/1モード',
            0x05: '3/0モード',
            0x06: '2/2モード',
            0x07: '3/1モード',
            0x08: '3/2モード',
            0x09: '3/2+LFEモード(5.1ch)',
            0x0A: '3/3.1モード(6.1ch)',
            0x0B: '2/0/0-2/0/2-0.1モード(6.1ch)',
            0x0C: '5/2.1モード(7.1ch)',
            0x0D: '3/2/2.1モード(7.1ch)',
            0x0E: '2/0/0-3/0/2-0.1モード(7.1ch)',
            0x0F: '0/2/0-3/0/2-0.1モード(7.1ch)',
            0x10: '2/0/0-3/2/3-0.2モード(10.2ch)',
            0x11: '3/3/3-5/2/3-3/0/0.2モード(22.2ch)',
        }
        return audio_types[audio_mode]

    def __resolveAudioChannel(self, audio_mode: int) -> _AudioChannel:
        """
        音声形式の表示文字列を RecordedVideo のチャンネル表現に変換する

        Args:
            audio_mode (int): component_type の下位5bitに格納された音声モード

        Returns:
            str: RecordedVideo 用の音声チャンネル
        """

        audio_channels: dict[int, _AudioChannel] = {
            0x01: 'Monaural',
            0x02: 'Stereo',
            0x03: 'Stereo',
            0x04: '3ch',
            0x05: '3ch',
            0x06: '4ch',
            0x07: '4ch',
            0x08: '5ch',
            0x09: '5.1ch',
            0x0A: '6.1ch',
            0x0B: '6.1ch',
            0x0C: '7.1ch',
            0x0D: '7.1ch',
            0x0E: '7.1ch',
            0x0F: '7.1ch',
            0x10: '10.2ch',
            0x11: '22.2ch',
        }
        return audio_channels[audio_mode]

    def __resolveAudioSamplingRate(self, sampling_rate_code: int) -> int:
        """
        MH audio component descriptor の sampling_rate を Hz に変換する

        Args:
            sampling_rate_code (int): 3bit の sampling_rate

        Returns:
            int: サンプリング周波数 (Hz)
        """

        # ARIB STD-B60 表7-62。BS4K の通常値は 0b111 (48kHz)。
        sampling_rates = {
            0b001: 16000,
            0b010: 22050,
            0b011: 24000,
            0b101: 32000,
            0b110: 44100,
            0b111: 48000,
        }
        return sampling_rates.get(sampling_rate_code, 48000)

    def __decodeText(self, data: bytes) -> str:
        """
        MH descriptor 内の UTF-8 文字列をデコードする

        Args:
            data (bytes): 文字列データ

        Returns:
            str: デコード済み文字列
        """

        return data.decode('utf-8', errors='ignore')

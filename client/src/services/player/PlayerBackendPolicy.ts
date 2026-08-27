import type { DPlayerType } from 'dplayer';


// mpeg2toh264 へ渡す映像は MPEG-2 のため、ブラウザデコーダーへの H.264 パススルーは利用しない
export const MPEG2TOH264_PASSTHROUGH = false;


/**
 * ライブ視聴向けの原始 MPEG-2 TS 画質を構築する。
 *
 * @param apiBaseURL KonomiTV API のベース URL
 * @param displayChannelID 表示用チャンネル ID
 * @returns DPlayer に渡す mpeg2toh264 画質
 */
export function buildLiveOriginalMPEG2Quality(apiBaseURL: string, displayChannelID: string): DPlayerType.VideoQuality {
    return {
        name: 'Original (MPEG-2)',
        type: 'mpeg2toh264',
        url: `${apiBaseURL}/streams/live/${displayChannelID}/original/mpegts`,
    };
}


/**
 * 録画再生向けの原始 MPEG-2 TS 画質を構築する。
 *
 * @param apiBaseURL KonomiTV API のベース URL
 * @param videoID 録画番組 ID
 * @returns DPlayer に渡す mpeg2toh264 画質
 */
export function buildRecordedOriginalMPEG2Quality(apiBaseURL: string, videoID: number): DPlayerType.VideoQuality {
    return {
        name: 'Original (MPEG-2)',
        type: 'mpeg2toh264',
        url: `${apiBaseURL}/videos/${videoID}/download`,
    };
}


/**
 * ライブ再生中に KonomiTV 側の強制同期が必要かを返す。
 * mpeg2toh264 と TLV は各バックエンドがバッファを管理するため、mpegts.js だけを対象にする。
 */
export function shouldForceLiveSync(backendType: string): boolean {
    return backendType === 'mpegts';
}


/**
 * 録画再生中にサーバー側 VideoStream セッションの維持が必要かを返す。
 * 原始ファイルを直接読む mpeg2toh264 / TLV には HLS セッションが存在しない。
 */
export function shouldKeepVideoStreamAlive(backendType: string): boolean {
    return backendType === 'hls';
}

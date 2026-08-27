import { describe, expect, it } from 'vitest';

import {
    buildLiveOriginalMPEG2Quality,
    buildRecordedOriginalMPEG2Quality,
    MPEG2TOH264_PASSTHROUGH,
    shouldForceLiveSync,
    shouldKeepVideoStreamAlive,
} from '@/services/player/PlayerBackendPolicy';


describe('原始 MPEG-2 TS 再生バックエンド契約', () => {

    it('ライブ視聴は original MPEG-TS URL を mpeg2toh264 へ直接渡す', () => {
        expect(buildLiveOriginalMPEG2Quality('https://konomi.example/api', 'gr011')).toEqual({
            name: 'Original (MPEG-2)',
            type: 'mpeg2toh264',
            url: 'https://konomi.example/api/streams/live/gr011/original/mpegts',
        });
    });

    it('録画再生は download URL を mpeg2toh264 へ直接渡す', () => {
        expect(buildRecordedOriginalMPEG2Quality('https://konomi.example/api', 42)).toEqual({
            name: 'Original (MPEG-2)',
            type: 'mpeg2toh264',
            url: 'https://konomi.example/api/videos/42/download',
        });
    });

    it('MPEG-2 映像を H.264 パススルーとして扱わない', () => {
        expect(MPEG2TOH264_PASSTHROUGH).toBe(false);
    });

    it('強制同期と Keep-Alive はそれぞれ所有するバックエンドだけで動作する', () => {
        expect(shouldForceLiveSync('mpegts')).toBe(true);
        expect(shouldForceLiveSync('mpeg2toh264')).toBe(false);
        expect(shouldForceLiveSync('tlv')).toBe(false);

        expect(shouldKeepVideoStreamAlive('hls')).toBe(true);
        expect(shouldKeepVideoStreamAlive('mpeg2toh264')).toBe(false);
        expect(shouldKeepVideoStreamAlive('tlv')).toBe(false);
    });
});

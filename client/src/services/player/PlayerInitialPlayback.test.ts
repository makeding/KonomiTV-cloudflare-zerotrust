import { describe, expect, it, vi } from 'vitest';

import type DPlayer from 'dplayer';

import { applyInitialPlaybackPosition } from '@/services/player/PlayerInitialPlayback';


describe('録画再生の初期位置反映', () => {

    it('初期 seek 自身だけを無通知にして、すでに表示された TLV notice を隠さない', () => {
        const seek = vi.fn();
        const set = vi.fn();
        const notice = vi.fn();
        const hideNotice = vi.fn();
        const play = vi.fn();
        const player = {
            seek,
            bar: { set },
            notice,
            hideNotice,
            play,
        } as unknown as DPlayer;

        applyInitialPlaybackPosition({
            player,
            playbackPositionSeconds: 5,
            recordedDurationSeconds: 100,
            recordingStartMarginSeconds: 5,
        });

        expect(seek).toHaveBeenCalledWith(5, true);
        expect(set).toHaveBeenCalledWith('played', 0.05, 'width');
        expect(hideNotice).not.toHaveBeenCalled();
        expect(notice).not.toHaveBeenCalled();
        expect(play).toHaveBeenCalledOnce();
    });

    it('视聴履歴の途中位置から再開するときだけ、その結果を notice に表示する', () => {
        const notice = vi.fn();
        const player = {
            seek: vi.fn(),
            bar: { set: vi.fn() },
            notice,
            play: vi.fn(),
        } as unknown as DPlayer;

        applyInitialPlaybackPosition({
            player,
            playbackPositionSeconds: 30,
            recordedDurationSeconds: 100,
            recordingStartMarginSeconds: 5,
        });

        expect(notice).toHaveBeenCalledWith('前回視聴した続きから再生します');
    });
});

import DPlayer, { DPlayerType } from 'dplayer';
import { beforeEach, describe, expect, it, vi } from 'vitest';


import TLVPlaybackNotification from '@/services/player/TLVPlaybackNotification';


const createDamage = (
    overrides: Partial<DPlayerType.TLVPlaybackDamage> = {},
): DPlayerType.TLVPlaybackDamage => ({
    code: 'TLV_SOURCE_DAMAGE',
    videoTrackId: 10n,
    startTimeUs: 10_000_000n,
    endTimeUs: 14_400_000n,
    recoveryTimeUs: 14_400_000n,
    startInputOffset: 100n,
    endInputOffset: 200n,
    recoveryInputOffset: 300n,
    recoveryRestartOffset: 280n,
    severity: 'severe',
    action: 'seek',
    ...overrides,
});

describe('TLV 再生障害の DPlayer notice 表示契約', () => {

    const notice = vi.fn();
    const player = { notice } as unknown as DPlayer;
    let notification: TLVPlaybackNotification;

    beforeEach(() => {
        notice.mockReset();
        notification = new TLVPlaybackNotification();
    });

    it('録画破損を DPlayer 左下の notice に表示し、同じ区間は重複表示しない', () => {
        const damage = createDamage();

        notification.notifyPlaybackDamage(player, damage, false);
        notification.notifyPlaybackDamage(player, damage, false);

        expect(notice).toHaveBeenCalledTimes(1);
        expect(notice).toHaveBeenCalledWith(
            '録画データの一部が破損しています。再生が停止した場合は、' +
            '約 4.4 秒先から自動的に再開します。[TLV_SOURCE_DAMAGE]',
            10_000,
            undefined,
            '#FFA86A',
        );
    });

    it('TLV エラーの原因とコードを DPlayer 左下の notice に保持する', () => {
        notification.notifyError(player, {
            code: 'DEMUXER_ERROR_COULD_NOT_OPEN',
            message: 'FFmpegDemuxer: open context failed',
        });

        expect(notice).toHaveBeenCalledWith(
            'TLV ストリームの再生に失敗しました。原因: FFmpegDemuxer: open context failed ' +
            '[DEMUXER_ERROR_COULD_NOT_OPEN] プレイヤーを再読み込みしてください。',
            10_000,
            undefined,
            '#FF6F6A',
        );
    });

    it('実際の DPlayer.notice() が .dplayer-notice の文字列と不透明度を更新する', () => {
        vi.useFakeTimers();
        const notice_element = document.createElement('div');
        notice_element.className = 'dplayer-notice';
        const actual_player = {
            template: { notice: notice_element },
            events: { trigger: vi.fn() },
            noticeTime: null,
            hideNotice: DPlayer.prototype.hideNotice,
        } as unknown as DPlayer;
        actual_player.notice = DPlayer.prototype.notice.bind(actual_player);

        notification.notifyError(actual_player, {
            code: 'DEMUXER_ERROR_COULD_NOT_OPEN',
            message: 'FFmpegDemuxer: open context failed',
        });

        expect(notice_element.textContent).toContain('FFmpegDemuxer: open context failed');
        expect(notice_element.textContent).toContain('[DEMUXER_ERROR_COULD_NOT_OPEN]');
        expect(notice_element.style.opacity).toBe('0.8');
        expect(notice_element.style.color).toBe('#FF6F6A');
        vi.clearAllTimers();
        vi.useRealTimers();
    });

    it('操作不要の warning はユーザー通知を出さない', () => {
        notification.notifyPlaybackDamage(player, createDamage({ severity: 'warning', action: 'none' }), false);

        expect(notice).not.toHaveBeenCalled();
    });
});

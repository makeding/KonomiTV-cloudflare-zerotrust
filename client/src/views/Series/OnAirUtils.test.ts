import { describe, expect, it } from 'vitest';

import { dayjsOriginal } from '@/utils';
import { getOnAirAttentionWindow, isOnAirSeriesInAttentionWindow } from '@/views/Series/OnAirUtils';

describe('放送中一覧のデフォルト注目枠', () => {

    it('深夜は昨夜 20:00 から当日 05:00 までの固定範囲になる', () => {
        const currentJST = dayjsOriginal.tz('2026-08-25 00:30:00', 'Asia/Tokyo');
        const attentionWindow = getOnAirAttentionWindow(currentJST);

        expect(attentionWindow.start.format('YYYY-MM-DD HH:mm')).toBe('2026-08-24 20:00');
        expect(attentionWindow.end.format('YYYY-MM-DD HH:mm')).toBe('2026-08-25 05:00');
        expect(attentionWindow.end.diff(attentionWindow.start, 'hour')).toBe(9);
    });

    it('05:00 から 20:00 までは従来どおり現在の 3 時間前から翌日 05:00 までになる', () => {
        const currentJST = dayjsOriginal.tz('2026-08-25 12:00:00', 'Asia/Tokyo');
        const attentionWindow = getOnAirAttentionWindow(currentJST);

        expect(attentionWindow.start.format('YYYY-MM-DD HH:mm')).toBe('2026-08-25 09:00');
        expect(attentionWindow.end.format('YYYY-MM-DD HH:mm')).toBe('2026-08-26 05:00');
    });

    it('20:00 以降は当日 20:00 から翌日 05:00 までの固定範囲になる', () => {
        const currentJST = dayjsOriginal.tz('2026-08-25 23:30:00', 'Asia/Tokyo');
        const attentionWindow = getOnAirAttentionWindow(currentJST);

        expect(attentionWindow.start.format('YYYY-MM-DD HH:mm')).toBe('2026-08-25 20:00');
        expect(attentionWindow.end.format('YYYY-MM-DD HH:mm')).toBe('2026-08-26 05:00');
        expect(attentionWindow.end.diff(attentionWindow.start, 'hour')).toBe(9);
    });

    it('04:59 から 05:00 で固定夜間枠から従来の日中枠へ切り替わる', () => {
        const beforeBoundary = getOnAirAttentionWindow(
            dayjsOriginal.tz('2026-08-25 04:59:00', 'Asia/Tokyo'),
        );
        const atBoundary = getOnAirAttentionWindow(
            dayjsOriginal.tz('2026-08-25 05:00:00', 'Asia/Tokyo'),
        );

        expect(beforeBoundary.start.format('YYYY-MM-DD HH:mm')).toBe('2026-08-24 20:00');
        expect(atBoundary.start.format('YYYY-MM-DD HH:mm')).toBe('2026-08-25 02:00');
        expect(atBoundary.end.format('YYYY-MM-DD HH:mm')).toBe('2026-08-26 05:00');
    });

    it('19:59 から 20:00 で従来の日中枠から固定夜間枠へ切り替わる', () => {
        const beforeBoundary = getOnAirAttentionWindow(
            dayjsOriginal.tz('2026-08-25 19:59:00', 'Asia/Tokyo'),
        );
        const atBoundary = getOnAirAttentionWindow(
            dayjsOriginal.tz('2026-08-25 20:00:00', 'Asia/Tokyo'),
        );

        expect(beforeBoundary.start.format('YYYY-MM-DD HH:mm')).toBe('2026-08-25 16:59');
        expect(atBoundary.start.format('YYYY-MM-DD HH:mm')).toBe('2026-08-25 20:00');
        expect(atBoundary.end.format('YYYY-MM-DD HH:mm')).toBe('2026-08-26 05:00');
    });

    it('深夜に翌日の夜まで誤って強調せず、20:00 と 05:00 の境界は含める', () => {
        const currentJST = dayjsOriginal.tz('2026-08-25 00:30:00', 'Asia/Tokyo');

        expect(isOnAirSeriesInAttentionWindow({weekday: 0, broadcast_time: '20:00'}, currentJST)).toBe(true);
        expect(isOnAirSeriesInAttentionWindow({weekday: 1, broadcast_time: '05:00'}, currentJST)).toBe(true);
        expect(isOnAirSeriesInAttentionWindow({weekday: 1, broadcast_time: '20:00'}, currentJST)).toBe(false);
        expect(isOnAirSeriesInAttentionWindow({weekday: 2, broadcast_time: '00:00'}, currentJST)).toBe(false);
    });

    it('日曜深夜から月曜早朝へ跨ぐ放送枠を同じ範囲として扱う', () => {
        const currentJST = dayjsOriginal.tz('2026-08-24 01:00:00', 'Asia/Tokyo');

        expect(isOnAirSeriesInAttentionWindow({weekday: 6, broadcast_time: '23:30'}, currentJST)).toBe(true);
        expect(isOnAirSeriesInAttentionWindow({weekday: 0, broadcast_time: '02:00'}, currentJST)).toBe(true);
        expect(isOnAirSeriesInAttentionWindow({weekday: 0, broadcast_time: '19:55'}, currentJST)).toBe(false);
    });
});

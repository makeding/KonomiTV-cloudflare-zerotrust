import type { Dayjs } from 'dayjs';

interface IWeeklyBroadcastSchedule {
    weekday: number;
    broadcast_time: string;
}

/**
 * 放送中一覧で強調表示する時間範囲を返す。
 *
 * @param currentJST 現在の日本時間
 * @returns 強調表示対象の開始・終了日時
 */
export const getOnAirAttentionWindow = (currentJST: Dayjs): {start: Dayjs; end: Dayjs} => {
    // 20:00〜05:00 は、暦日の境界を跨いでも同じ夜の放送枠として固定する。
    // 深夜に現在時刻基準で範囲を動かすと翌日の夜まで強調してしまうため、必ず 9 時間に収める。
    if (currentJST.hour() >= 20 || currentJST.hour() < 5) {
        const broadcastDate = currentJST.hour() < 5
            ? currentJST.subtract(1, 'day').startOf('day')
            : currentJST.startOf('day');
        return {
            start: broadcastDate.add(20, 'hour'),
            end: broadcastDate.add(1, 'day').add(5, 'hour'),
        };
    }

    // 05:00〜20:00 は従来どおり、直近 3 時間と次の深夜帯までを連続して確認できる範囲にする。
    return {
        start: currentJST.subtract(3, 'hour'),
        end: currentJST.add(1, 'day').startOf('day').add(5, 'hour'),
    };
};

/**
 * 週間放送枠が、現在の放送日の強調表示対象に含まれるかを判定する。
 *
 * @param series 曜日と放送開始時刻を持つシリーズ
 * @param currentJST 現在の日本時間
 * @returns 強調表示対象に含まれる場合は true
 */
export const isOnAirSeriesInAttentionWindow = (
    series: IWeeklyBroadcastSchedule,
    currentJST: Dayjs,
): boolean => {
    const attentionWindow = getOnAirAttentionWindow(currentJST);
    const currentWeekday = (currentJST.day() + 6) % 7;
    const weekStart = currentJST.startOf('day').subtract(currentWeekday, 'day');
    const [hour, minute] = series.broadcast_time.split(':').map(Number);
    const baseOccurrence = weekStart.add(series.weekday, 'day').hour(hour).minute(minute).second(0);

    // 日曜から月曜へ跨ぐ放送枠でも照合できるよう、前後週の同じ曜日・時刻も比較する。
    return [-7, 0, 7].some(dayOffset => {
        const occurrence = baseOccurrence.add(dayOffset, 'day');
        return occurrence.isBetween(attentionWindow.start, attentionWindow.end, null, '[]');
    });
};

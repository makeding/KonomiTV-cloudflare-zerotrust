import type DPlayer from 'dplayer';
import type { DPlayerType } from 'dplayer';


/**
 * DPlayer が通知する TLV 再生障害を、DPlayer 左下の notice 用メッセージに変換する。
 * 再生制御と復旧処理は DPlayer / tlvdemux に残し、このクラスは HonomiTV の文言と表示だけを担当する。
 */
export default class TLVPlaybackNotification {

    // 同じ破損区間から繰り返し届くコールバックで notice が何度も置き換わらないよう、
    // 現在の PlayerController.init() 世代ですでに通知した区間を保持する。
    private readonly notified_damage_keys = new Set<string>();

    // 同じ致命的エラーが複数の非同期経路から到着しても一度だけ表示するため、
    // 現在の PlayerController.init() 世代ですでに通知したエラーを保持する。
    private readonly notified_error_keys = new Set<string>();

    /** PlayerController.init() ごとに通知の重複排除状態を初期化する。 */
    public reset(): void {
        this.notified_damage_keys.clear();
        this.notified_error_keys.clear();
    }

    /** TLV の破損区間を、復旧方針に対応したユーザー向け通知として表示する。 */
    public notifyPlaybackDamage(
        player: DPlayer,
        damage: DPlayerType.TLVPlaybackDamage,
        is_live: boolean,
    ): void {
        // Warning は再生を妨げない診断イベントなので、DPlayer の公開イベントとしてだけ保持する。
        // ユーザーの操作が必要、または再生位置が変わりうる Severe だけを通知する。
        if (damage.severity !== 'severe') {
            return;
        }

        const damage_key = [
            damage.videoTrackId,
            damage.startInputOffset,
            damage.endInputOffset,
            damage.action,
            damage.severity,
        ].join(':');
        if (this.notified_damage_keys.has(damage_key)) {
            return;
        }
        this.notified_damage_keys.add(damage_key);

        // 復旧位置が判明している録画破損は、停止時に tlvdemux が自動復旧することを明示する。
        if (damage.action === 'seek' && damage.recoveryTimeUs !== null) {
            const damage_start_seconds = Number(damage.startTimeUs ?? damage.endTimeUs) / 1_000_000;
            const recovery_seconds = Number(damage.recoveryTimeUs) / 1_000_000;
            const skip_seconds = Math.max(0, recovery_seconds - damage_start_seconds).toFixed(1);
            player.notice(
                '録画データの一部が破損しています。再生が停止した場合は、' +
                `約 ${skip_seconds} 秒先から自動的に再開します。[${damage.code}]`,
                10_000,
                undefined,
                '#FFA86A',
            );
            return;
        }

        // ライブの復旧待ちと、回復点を持たない録画末尾の破損では、ユーザーが取れる次の行動が異なる。
        if (damage.action === 'wait-for-recovery') {
            if (is_live) {
                player.notice(
                    '受信中の放送ストリームが破損しています。復旧を待っています。' +
                    `そのままお待ちください。[${damage.code}]`,
                    10_000,
                    undefined,
                    '#FFA86A',
                );
            } else {
                player.notice(
                    '録画末尾のデータが破損しているため、これ以上再生できません。' +
                    `シークバーで前の位置へ戻ってください。[${damage.code}]`,
                    10_000,
                    undefined,
                    '#FF6F6A',
                );
            }
            return;
        }

        // 将来 Severe の action が追加されても無言にせず、再試行方法と安定コードを残す。
        player.notice(
            `${is_live ? '受信中の放送ストリーム' : '録画データ'}が破損し、再生を継続できません。` +
            `プレイヤーを再読み込みしてください。[${damage.code}]`,
            10_000,
            undefined,
            '#FF6F6A',
        );
    }

    /** TLV の致命的エラーを、具体的な原因を失わない DPlayer 左下の notice として表示する。 */
    public notifyError(player: DPlayer, error: unknown): void {
        const error_object = typeof error === 'object' && error !== null ? error as {
            code?: unknown;
            message?: unknown;
        } : null;
        const error_message = error instanceof Error ? error.message :
            typeof error_object?.message === 'string' ? error_object.message : String(error);
        const error_code = typeof error_object?.code === 'string' ? error_object.code : null;
        const error_key = `${error_code ?? ''}:${error_message}`;
        if (this.notified_error_keys.has(error_key)) {
            return;
        }
        this.notified_error_keys.add(error_key);

        // 元エラーの理由は書き換えず、コードが別フィールドにある場合だけ重複しない形で追記する。
        const error_code_suffix = error_code !== null && !error_message.includes(`[${error_code}]`) ?
            ` [${error_code}]` : '';
        player.notice(
            `TLV ストリームの再生に失敗しました。原因: ${error_message}` +
            `${error_code_suffix} プレイヤーを再読み込みしてください。`,
            10_000,
            undefined,
            '#FF6F6A',
        );
    }
}

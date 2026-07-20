
import DPlayer from 'dplayer';

import type { IRecordedVideo } from '@/services/Videos';

import PlayerManager from '@/services/player/PlayerManager';
import usePlayerStore from '@/stores/PlayerStore';
import useSettingsStore from '@/stores/SettingsStore';


type CMSection = NonNullable<IRecordedVideo['cm_sections']>[number];


/**
 * 録画再生中に自然再生で跨いだ CM 区間を自動スキップする PlayerManager
 */
class RecordedCMSkipManager implements PlayerManager {

    // ユーザー操作により DPlayer 側で画質が切り替わった際、この PlayerManager の再起動が必要かどうかを PlayerController に示す値
    // DPlayer のイベントは画質切り替え後の HTMLVideoElement にも引き継がれるため、再起動は不要
    public readonly restart_required_when_quality_switched = false;

    // DPlayer のインスタンス
    private readonly player: DPlayer;

    // 録画時間内に正規化し、開始時刻順に並べた CM 区間
    private cm_sections: CMSection[] = [];

    // 直前の timeupdate で観測した再生位置
    // CM 内から再生を開始・再開した場合に、その CM を自然通過したものと誤判定しないために保持する
    private previous_playback_position: number | null = null;

    // HTMLVideoElement がシーク中かどうか
    // 手動シークやプレイヤー再起動による位置復元を自然再生と区別するために保持する
    private is_seeking = false;

    // DPlayer が画質を切り替えている最中かどうか
    // 切り替え中は旧・新両方の HTMLVideoElement からイベントが転送されるため、自動スキップ判定を停止する
    private is_quality_switching = false;

    // 直近に自動スキップした CM 区間
    // HLS の境界丸めでシーク先が区間末尾よりわずかに手前になっても、同一区間を繰り返しスキップしないために保持する
    private last_skipped_cm_section: CMSection | null = null;

    /**
     * コンストラクタ
     * @param player DPlayer のインスタンス
     */
    constructor(player: DPlayer) {
        this.player = player;
    }


    /**
     * 指定位置が先頭の CM 区間内なら、その区間の終了位置を返す
     * 視聴履歴のない新規再生で、初期 HLS セグメントから CM を除外するために利用する
     * @param playback_position 録画先頭基準の再生位置（秒）
     * @param cm_sections CM 区間
     * @param duration 録画時間（秒）
     * @returns 先頭の CM 区間内ならスキップ先、区間外または有効な区間がなければ null
     */
    public static getInitialSkipTarget(
        playback_position: number,
        cm_sections: IRecordedVideo['cm_sections'],
        duration: number,
    ): number | null {

        // 非有限値は DPlayer のシーク先として利用できない
        if (Number.isFinite(playback_position) === false) {
            return null;
        }

        // 新規再生時の例外は先頭の CM 区間だけに限定し、途中の CM へ初期位置が入っても補正しない
        const section = RecordedCMSkipManager.normalizeCMSections(cm_sections, duration)[0];
        if (
            section === undefined ||
            playback_position < section.start_time ||
            section.end_time <= playback_position
        ) {
            return null;
        }
        return section.end_time;
    }


    /**
     * CM 区間と再生位置の監視を開始する
     */
    public async init(): Promise<void> {
        const player_store = usePlayerStore();
        const recorded_video = player_store.recorded_program.recorded_video;

        // PlayerManager が再初期化された場合も、現在の録画情報から状態を作り直す
        this.cm_sections = RecordedCMSkipManager.normalizeCMSections(
            recorded_video.cm_sections,
            recorded_video.duration,
        );
        this.previous_playback_position = null;
        this.is_seeking = false;
        this.is_quality_switching = false;
        this.last_skipped_cm_section = null;

        // 同じインスタンスに init() が重複して呼ばれても、イベントハンドラーを二重登録しない
        this.player.off('seeking', this.handleSeeking);
        this.player.off('seeked', this.handleSeeked);
        this.player.off('timeupdate', this.handleTimeUpdate);
        this.player.off('quality_start', this.handleQualityStart);
        this.player.off('quality_end', this.handleQualityEnd);
        this.player.on('seeking', this.handleSeeking);
        this.player.on('seeked', this.handleSeeked);
        this.player.on('timeupdate', this.handleTimeUpdate);
        this.player.on('quality_start', this.handleQualityStart);
        this.player.on('quality_end', this.handleQualityEnd);

        console.log('[RecordedCMSkipManager] Initialized.');
    }


    /**
     * CM 区間と再生位置の監視を終了する
     */
    public async destroy(): Promise<void> {

        // init() で登録したものと同じ関数参照を使い、DPlayer からイベントハンドラーを解除する
        this.player.off('seeking', this.handleSeeking);
        this.player.off('seeked', this.handleSeeked);
        this.player.off('timeupdate', this.handleTimeUpdate);
        this.player.off('quality_start', this.handleQualityStart);
        this.player.off('quality_end', this.handleQualityEnd);

        this.cm_sections = [];
        this.previous_playback_position = null;
        this.is_seeking = false;
        this.is_quality_switching = false;
        this.last_skipped_cm_section = null;

        console.log('[RecordedCMSkipManager] Destroyed.');
    }


    /**
     * API 由来の CM 区間を録画時間内へ収め、重複・隣接区間を結合する
     * @param cm_sections CM 区間
     * @param duration 録画時間（秒）
     * @returns 正規化済み CM 区間
     */
    private static normalizeCMSections(
        cm_sections: IRecordedVideo['cm_sections'],
        duration: number,
    ): CMSection[] {

        // 録画時間自体が不正なら、安全に自動スキップを無効化する
        if (Number.isFinite(duration) === false || duration <= 0) {
            return [];
        }

        const normalized_sections = (cm_sections ?? [])
            .filter((section) => (
                Number.isFinite(section.start_time) &&
                Number.isFinite(section.end_time)
            ))
            .map((section) => ({
                start_time: Math.max(0, Math.min(section.start_time, duration)),
                end_time: Math.max(0, Math.min(section.end_time, duration)),
            }))
            .filter((section) => section.start_time < section.end_time)
            .sort((left, right) => left.start_time - right.start_time || left.end_time - right.end_time);

        const merged_sections: CMSection[] = [];
        for (const section of normalized_sections) {
            const previous_section = merged_sections.at(-1);

            // 重複または隣接する CM 区間は一つにまとめ、途中へシークしてしまうことを防ぐ
            if (previous_section !== undefined && section.start_time <= previous_section.end_time) {
                previous_section.end_time = Math.max(previous_section.end_time, section.end_time);
                continue;
            }
            merged_sections.push({...section});
        }
        return merged_sections;
    }


    /**
     * HTMLVideoElement がシークを開始したときのイベントハンドラー
     */
    private readonly handleSeeking = (event?: Event): void => {
        if (event !== undefined && event.target !== this.player.video) return;

        this.is_seeking = true;
        const current_time = this.player.video.currentTime;
        if (Number.isFinite(current_time)) {
            this.previous_playback_position = current_time;
        }
    };


    /**
     * HTMLVideoElement のシークが完了したときのイベントハンドラー
     */
    private readonly handleSeeked = (event?: Event): void => {
        if (event !== undefined && event.target !== this.player.video) return;

        const current_time = this.player.video.currentTime;
        this.is_seeking = false;

        // シーク先を新しい比較基準にし、CM 内への手動シークを自動スキップしない
        if (Number.isFinite(current_time)) {
            this.previous_playback_position = current_time;

            // 直前にスキップした CM より前へ戻った場合は、自然再生で同じ CM を再度スキップ可能にする
            if (
                this.last_skipped_cm_section !== null &&
                current_time < this.last_skipped_cm_section.start_time
            ) {
                this.last_skipped_cm_section = null;
            }
        }
    };


    /**
     * DPlayer が画質切り替えを開始したときのイベントハンドラー
     */
    private readonly handleQualityStart = (): void => {
        this.is_quality_switching = true;
        this.previous_playback_position = null;
    };


    /**
     * DPlayer が画質切り替えを完了したときのイベントハンドラー
     */
    private readonly handleQualityEnd = (): void => {
        this.is_quality_switching = false;
        this.is_seeking = this.player.video.seeking;

        // 復元された位置を新しい比較基準にし、画質切り替えを自然再生と誤認しない
        const current_time = this.player.video.currentTime;
        this.previous_playback_position = Number.isFinite(current_time) ? current_time : null;
    };


    /**
     * HTMLVideoElement の再生位置が更新されたときのイベントハンドラー
     */
    private readonly handleTimeUpdate = (event?: Event): void => {
        if (event !== undefined && event.target !== this.player.video) return;

        const settings_store = useSettingsStore();
        const current_time = this.player.video.currentTime;

        // 非有限値は比較やシークに利用できない
        if (Number.isFinite(current_time) === false) {
            return;
        }

        // 画質切り替え中は旧・新両方の video 要素からイベントが届くため、比較基準を更新しない
        if (this.is_quality_switching === true || this.player.switchingQuality === true) {
            return;
        }

        // 直前にスキップした CM より前へ戻った場合は、同じ CM を再度スキップ可能にする
        if (
            this.last_skipped_cm_section !== null &&
            current_time < this.last_skipped_cm_section.start_time
        ) {
            this.last_skipped_cm_section = null;
        }

        // 初回観測位置やシーク中の位置は自然再生の比較基準として記録するだけに留める
        if (
            this.previous_playback_position === null ||
            this.is_seeking === true ||
            this.player.video.seeking === true
        ) {
            this.previous_playback_position = current_time;
            return;
        }

        const previous_time = this.previous_playback_position;
        this.previous_playback_position = current_time;

        // オフ・停止中・巻き戻し中は CM 開始を自然再生で跨いだ状態ではない
        if (
            settings_store.settings.video_auto_skip_cm === false ||
            this.player.video.paused === true ||
            current_time <= previous_time
        ) {
            return;
        }

        const section = this.cm_sections.find((candidate) => (
            previous_time < candidate.start_time &&
            candidate.start_time <= current_time &&
            current_time < candidate.end_time
        ));
        if (section === undefined) {
            return;
        }

        // HLS の境界丸めで同じ区間内へ戻っても、同一区間を連続して自動スキップしない
        if (
            this.last_skipped_cm_section?.start_time === section.start_time &&
            this.last_skipped_cm_section.end_time === section.end_time
        ) {
            return;
        }

        this.last_skipped_cm_section = section;
        this.previous_playback_position = section.end_time;
        this.player.seek(section.end_time, true);
    };
}

export default RecordedCMSkipManager;

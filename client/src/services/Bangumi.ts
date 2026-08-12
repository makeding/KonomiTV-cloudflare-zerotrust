import Message from '@/message';
import APIClient from '@/services/APIClient';


/** Bangumi アカウントと個人アクセストークンで連携するためのリクエストを表すインターフェイス */
export interface IBangumiAuthRequest {
    access_token: string;
}

/** Bangumi の視聴完了判定へ送信する録画再生進捗 */
export interface IBangumiPlaybackProgressRequest {
    playback_position: number;
    duration: number;
}


class Bangumi {

    /**
     * Bangumi アカウントと個人アクセストークンで連携する
     * @param auth_request Bangumi 個人アクセストークン
     * @returns 連携に成功した場合は true、失敗した場合は false
     */
    static async loginAccount(auth_request: IBangumiAuthRequest): Promise<boolean> {

        // API リクエストを実行
        const response = await APIClient.post('/bangumi/auth', auth_request);

        // 無効または期限切れの個人アクセストークンは、再発行が必要なことを明示する
        if (response.type === 'error') {
            if (response.data.detail === 'Bangumi access token is invalid or expired') {
                Message.error('Bangumi の個人アクセストークンが無効、または期限切れです。');
                return false;
            }
            APIClient.showGenericError(response, 'Bangumi アカウントとの連携に失敗しました。');
            return false;
        }

        return true;
    }


    /**
     * 現在ログイン中のユーザーアカウントに紐づく Bangumi アカウントとの連携を解除する
     * @returns 連携解除に成功した場合は true、失敗した場合は false
     */
    static async logoutAccount(): Promise<boolean> {

        // API リクエストを実行
        const response = await APIClient.delete('/bangumi/logout');

        // エラー処理
        if (response.type === 'error') {
            APIClient.showGenericError(response, 'Bangumi アカウントとの連携を解除できませんでした。');
            return false;
        }

        return true;
    }


    /**
     * 録画番組の再生進捗を送信し、バックエンドで Bangumi の視聴完了を判定する
     * @param video_id 録画番組 ID
     * @param progress_request プレイヤーが解決した再生位置と録画時間
     * @returns 同期 API が成功した場合は true、失敗した場合は false
     */
    static async updatePlaybackProgress(
        video_id: number,
        progress_request: IBangumiPlaybackProgressRequest,
    ): Promise<boolean> {

        const response = await APIClient.post(`/bangumi/videos/${video_id}/progress`, progress_request);
        if (response.type === 'error') {
            APIClient.showGenericError(response, 'Bangumi の視聴状態を更新できませんでした。');
            return false;
        }
        return true;
    }
}

export default Bangumi;

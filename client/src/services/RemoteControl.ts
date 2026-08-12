import Message from '@/message';
import APIClient from '@/services/APIClient';

export interface IRemoteDevice {
    device_id: string;
    device_name: string;
    last_seen_at: string;
    state: Record<string, unknown> | null;
}

export type RemoteOpenCommand =
    | {type: 'OpenLive'; display_channel_id: string;}
    | {type: 'OpenRecording'; recorded_program_id: number; position_seconds: number;};

class RemoteControl {
    static async fetchDevices(): Promise<IRemoteDevice[] | null> {
        const response = await APIClient.get<{devices: IRemoteDevice[];}>('/remote/devices');
        if (response.type === 'error') {
            APIClient.showGenericError(response, 'テレビの一覧を取得できませんでした。');
            return null;
        }
        return response.data.devices;
    }

    static async sendOpenCommand(deviceId: string, command: RemoteOpenCommand): Promise<boolean> {
        const response = await APIClient.post<{command_id: string;}>(
            `/remote/devices/${encodeURIComponent(deviceId)}/commands`,
            command,
        );
        if (response.type === 'error') {
            if (response.status === 409) {
                Message.error('選択したテレビはオフラインです。');
            } else {
                APIClient.showGenericError(response, 'テレビへ送信できませんでした。');
            }
            return false;
        }
        return true;
    }
}

export default RemoteControl;

import Message from '@/message';
import APIClient from '@/services/APIClient';
import Utils from '@/utils';

export interface IRemoteDevice {
    device_id: string;
    device_name: string;
    last_seen_at: string;
    state: Record<string, unknown> | null;
}

export type RemoteCommand =
    | {type: 'OpenLive'; display_channel_id: string;}
    | {type: 'OpenRecording'; recorded_program_id: number; position_seconds: number;}
    | {type: 'Play' | 'Pause' | 'Stop';}
    | {type: 'SeekRelative'; delta_seconds: number;}
    | {type: 'VolumeUp' | 'VolumeDown' | 'VolumeMute';};

class RemoteControl {
    static subscribeDevices(
        onDevices: (devices: IRemoteDevice[]) => void,
        onDisconnected: () => void,
    ): () => void {
        const accessToken = Utils.getAccessToken();
        if (accessToken === null) return () => {};

        const websocketURL = new URL(`${Utils.api_base_url}/remote/devices/ws`);
        websocketURL.protocol = websocketURL.protocol === 'https:' ? 'wss:' : 'ws:';
        const websocket = new WebSocket(websocketURL);
        let isDisposed = false;
        websocket.addEventListener('open', () => {
            websocket.send(JSON.stringify({type: 'Authenticate', token: accessToken}));
        });
        websocket.addEventListener('message', (event) => {
            const message: unknown = JSON.parse(event.data);
            if (typeof message === 'object' && message !== null && 'devices' in message && Array.isArray(message.devices)) {
                onDevices(message.devices as IRemoteDevice[]);
            }
        });
        websocket.addEventListener('close', () => {
            if (isDisposed === false) onDisconnected();
        });

        return () => {
            isDisposed = true;
            websocket.close();
        };
    }

    static async fetchDevices(): Promise<IRemoteDevice[] | null> {
        const response = await APIClient.get<{devices: IRemoteDevice[];}>('/remote/devices');
        if (response.type === 'error') {
            APIClient.showGenericError(response, 'テレビの一覧を取得できませんでした。');
            return null;
        }
        return response.data.devices;
    }

    static async sendCommand(deviceId: string, command: RemoteCommand): Promise<boolean> {
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

    static async sendOpenCommand(deviceId: string, command: Extract<RemoteCommand, {type: 'OpenLive' | 'OpenRecording'}>): Promise<boolean> {
        return this.sendCommand(deviceId, command);
    }
}

export default RemoteControl;

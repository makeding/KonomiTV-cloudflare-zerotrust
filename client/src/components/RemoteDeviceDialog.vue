<template>
    <v-menu v-if="isLoggedIn" v-model="isOpen"
        :target="remoteDeviceActivatorElement ?? undefined" location="bottom end" :close-on-content-click="false"
        :persistent="isPinned" no-click-animation
        :offset="8" transition="fade-transition">
        <v-list class="remote-device-menu" density="compact" elevation="8" bg-color="background-lighten-1">
            <v-list-item class="remote-device-menu__header" title="テレビで再生">
                <template #append>
                    <v-btn icon size="small" variant="text" :color="isPinned ? 'primary' : undefined"
                        :aria-label="isPinned ? 'テレビ操作メニューの固定を解除' : 'テレビ操作メニューを固定'" @click="togglePinned">
                        <Icon :icon="isPinned ? 'fluent:pin-20-filled' : 'fluent:pin-20-regular'" width="20px" />
                    </v-btn>
                    <v-btn icon size="small" variant="text" aria-label="テレビ一覧を更新" :loading="isLoading" @click="refreshDevices()">
                        <Icon icon="fluent:arrow-clockwise-20-regular" width="21px" />
                    </v-btn>
                </template>
            </v-list-item>

            <v-progress-linear v-if="isLoading" color="primary" indeterminate />
            <template v-else-if="devices.length > 0">
                <v-list-item v-for="device in devices" :key="device.device_id" :active="device.device_id === selectedDeviceId"
                    color="primary" @click="selectDevice(device)">
                    <template #prepend>
                        <Icon icon="fluent:tv-20-regular" width="23px" class="mr-3" />
                    </template>
                    <v-list-item-title>{{ device.device_name }}</v-list-item-title>
                    <v-list-item-subtitle>オンライン</v-list-item-subtitle>
                    <template #append>
                        <Icon v-if="device.device_id === selectedDeviceId" icon="fluent:checkmark-20-filled" width="21px" />
                    </template>
                </v-list-item>
            </template>
            <v-list-item v-else lines="two">
                <template #prepend>
                    <Icon icon="fluent:tv-off-20-regular" width="23px" class="mr-3" />
                </template>
                <v-list-item-title>オンラインのテレビがありません</v-list-item-title>
                <v-list-item-subtitle>Komorebi を起動してペアリングしてください</v-list-item-subtitle>
            </v-list-item>

            <template v-if="selectedDevice !== null && selectedPlaybackState.content_type !== 'Idle'">
                <v-divider class="my-2" />
                <div class="remote-device-menu__now-playing">
                    <div v-if="selectedPlaybackState.artwork_url" class="remote-device-menu__artwork">
                        <img :src="selectedPlaybackState.artwork_url" alt="" />
                    </div>
                    <div class="remote-device-menu__media-info">
                        <div class="remote-device-menu__section-title">
                            {{ selectedPlaybackState.content_type === 'Live' ? 'ライブ再生中' : '録画番組を再生中' }}
                        </div>
                        <div v-if="selectedPlaybackState.title" class="remote-device-menu__media-title">
                            {{ selectedPlaybackState.title }}
                        </div>
                        <div v-if="selectedPlaybackState.subtitle" class="remote-device-menu__media-subtitle">
                            {{ selectedPlaybackState.subtitle }}
                        </div>
                    </div>
                </div>
                <div class="remote-device-menu__controls">
                    <v-btn icon size="small" variant="text" :disabled="selectedPlaybackState.can_seek !== true" aria-label="10秒戻る"
                        @click="sendControl({type: 'SeekRelative', delta_seconds: -10})">
                        <Icon icon="fluent:arrow-counterclockwise-20-regular" width="22px" />
                    </v-btn>
                    <v-btn icon size="small" variant="text" :aria-label="selectedPlaybackState.is_playing ? '一時停止' : '再生'"
                        @click="sendControl({type: selectedPlaybackState.is_playing ? 'Pause' : 'Play'})">
                        <Icon :icon="selectedPlaybackState.is_playing ? 'fluent:pause-20-filled' : 'fluent:play-20-filled'" width="24px" />
                    </v-btn>
                    <v-btn icon size="small" variant="text" :disabled="selectedPlaybackState.can_seek !== true" aria-label="10秒進む"
                        @click="sendControl({type: 'SeekRelative', delta_seconds: 10})">
                        <Icon icon="fluent:arrow-clockwise-20-regular" width="22px" />
                    </v-btn>
                    <v-btn icon size="small" variant="text" aria-label="停止" @click="sendControl({type: 'Stop'})">
                        <Icon icon="fluent:stop-20-filled" width="22px" />
                    </v-btn>
                </div>
            </template>

            <template v-if="selectedDevice !== null">
                <v-divider class="my-2" />
                <div class="remote-device-menu__volume">
                    <div class="remote-device-menu__section-title">音量</div>
                    <div class="remote-device-menu__controls">
                        <v-btn icon size="small" variant="text" :disabled="selectedPlaybackState.can_adjust_volume === false" aria-label="音量を下げる"
                            @click="sendControl({type: 'VolumeDown'})">
                            <Icon icon="fluent:speaker-1-20-filled" width="22px" />
                        </v-btn>
                        <v-btn icon size="small" variant="text" :disabled="selectedPlaybackState.can_adjust_volume === false" aria-label="ミュートを切り替える"
                            @click="sendControl({type: 'VolumeMute'})">
                            <Icon icon="fluent:speaker-mute-20-filled" width="22px" />
                        </v-btn>
                        <v-btn icon size="small" variant="text" :disabled="selectedPlaybackState.can_adjust_volume === false" aria-label="音量を上げる"
                            @click="sendControl({type: 'VolumeUp'})">
                            <Icon icon="fluent:speaker-2-20-filled" width="22px" />
                        </v-btn>
                    </div>
                    <div v-if="selectedPlaybackState.can_adjust_volume === false" class="remote-device-menu__volume-unavailable">
                        テレビが固定音量として報告しています。テレビまたはオーディオ機器側で音量を操作してください。
                    </div>
                </div>
            </template>

            <template v-if="selectedDeviceId !== null">
                <v-divider class="my-2" />
                <v-list-item title="接続を解除" @click="disconnect">
                    <template #prepend>
                        <Icon icon="fluent:link-dismiss-20-regular" width="22px" class="mr-3" />
                    </template>
                </v-list-item>
            </template>
        </v-list>
    </v-menu>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';

import RemoteControl, { type IRemoteDevice, type RemoteCommand } from '@/services/RemoteControl';
import {
    remoteDeviceActivatorElement,
    remoteDeviceMenuOpenRequest,
    selectedRemoteDeviceName,
} from '@/services/RemoteControlUI';
import useSettingsStore from '@/stores/SettingsStore';
import Utils from '@/utils';

interface IRemotePlaybackState {
    content_type: 'Idle' | 'Live' | 'Recorded';
    title?: string;
    subtitle?: string;
    artwork_url?: string;
    is_playing?: boolean;
    can_seek?: boolean;
    can_adjust_volume?: boolean;
}

const settingsStore = useSettingsStore();
const isOpen = ref(false);
const isLoading = ref(false);
const devices = ref<IRemoteDevice[]>([]);
const isLoggedIn = computed(() => Utils.getAccessToken() !== null);
const selectedDeviceId = computed(() => settingsStore.settings.selected_remote_device_id);
const isPinned = computed(() => settingsStore.settings.remote_control_menu_pinned);
const selectedDevice = computed(() => devices.value.find((device) => device.device_id === selectedDeviceId.value) ?? null);
const selectedDeviceName = computed(() => selectedDevice.value?.device_name ?? null);
const selectedPlaybackState = computed<IRemotePlaybackState>(() => {
    return selectedDevice.value?.state as unknown as IRemotePlaybackState ?? {content_type: 'Idle'};
});
let unsubscribeDevices: (() => void) | null = null;
let reconnectTimer: number | null = null;
let refreshInProgress = false;
let isAwaitingDeviceSnapshot = false;

async function refreshDevices(): Promise<void> {
    if (refreshInProgress === true) return;
    refreshInProgress = true;
    isLoading.value = devices.value.length === 0;
    try {
        const fetchedDevices = await RemoteControl.fetchDevices();
        // 通信失敗時は直前の成功結果を維持し、一瞬だけ「オフライン」に切り替わるのを防ぐ。
        if (fetchedDevices === null) return;
        devices.value = fetchedDevices;
        isAwaitingDeviceSnapshot = false;
    } finally {
        isLoading.value = isAwaitingDeviceSnapshot && devices.value.length === 0;
        refreshInProgress = false;
    }
}

function disconnectDeviceSubscription(): void {
    if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }
    unsubscribeDevices?.();
    unsubscribeDevices = null;
    isAwaitingDeviceSnapshot = false;
    isLoading.value = false;
}

function connectDeviceSubscription(): void {
    disconnectDeviceSubscription();
    isAwaitingDeviceSnapshot = devices.value.length === 0;
    isLoading.value = devices.value.length === 0;
    unsubscribeDevices = RemoteControl.subscribeDevices((fetchedDevices) => {
        devices.value = fetchedDevices;
        isAwaitingDeviceSnapshot = false;
        isLoading.value = false;
    }, () => {
        unsubscribeDevices = null;
        // 一時的な切断時だけ3秒後に同じユーザーの部屋へ入り直す。
        if (isOpen.value === true && remoteDeviceActivatorElement.value !== null) {
            isLoading.value = isAwaitingDeviceSnapshot && devices.value.length === 0;
            reconnectTimer = window.setTimeout(connectDeviceSubscription, 3_000);
        } else {
            isAwaitingDeviceSnapshot = false;
            isLoading.value = false;
        }
    });
}

function selectDevice(device: IRemoteDevice): void {
    settingsStore.settings.selected_remote_device_id = device.device_id;
}

async function sendControl(command: Exclude<RemoteCommand, {type: 'OpenLive' | 'OpenRecording'}>): Promise<void> {
    if (selectedDeviceId.value === null) return;
    await RemoteControl.sendCommand(selectedDeviceId.value, command);
}

function disconnect(): void {
    settingsStore.settings.selected_remote_device_id = null;
    isOpen.value = false;
}

function togglePinned(): void {
    settingsStore.settings.remote_control_menu_pinned = !isPinned.value;
}

onBeforeUnmount(() => {
    disconnectDeviceSubscription();
});

watch(selectedDeviceName, (deviceName) => {
    selectedRemoteDeviceName.value = deviceName;
}, {immediate: true});

// 投影ボタンから isOpen を直接変更した場合も含め、メニューの実際の開閉状態へ購読寿命を一致させる。
watch(isOpen, (visible) => {
    if (visible) {
        connectDeviceSubscription();
        // 初回表示では WebSocket の参加と同時に現在のスナップショットも取得し、手動更新を不要にする。
        void refreshDevices();
    } else {
        disconnectDeviceSubscription();
    }
});

watch(remoteDeviceMenuOpenRequest, () => {
    if (remoteDeviceActivatorElement.value !== null) isOpen.value = true;
});
</script>

<style scoped lang="scss">
.remote-device-menu {
    width: min(320px, calc(100vw - 24px));
    padding: 8px;

    &__header {
        min-height: 46px;
    }

    &__section-title {
        margin-bottom: 4px;
        color: rgb(var(--v-theme-text-darken-1));
        font-size: 12px;
    }

    &__now-playing {
        display: flex;
        gap: 12px;
        align-items: center;
        padding: 4px 12px 10px;
    }

    &__artwork {
        width: 96px;
        height: 54px;
        overflow: hidden;
        flex: 0 0 auto;
        border-radius: 4px;
        background: rgb(var(--v-theme-background));

        img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
    }

    &__media-info {
        min-width: 0;
    }

    &__media-title,
    &__media-subtitle {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    &__media-title {
        font-size: 14px;
        font-weight: 500;
    }

    &__media-subtitle {
        margin-top: 2px;
        color: rgb(var(--v-theme-text-darken-1));
        font-size: 12px;
    }

    &__controls {
        display: flex;
        align-items: center;
        justify-content: space-evenly;
        padding: 0 12px 6px;
    }

    &__volume {
        padding-top: 4px;
    }

    &__volume-unavailable {
        padding: 0 12px 8px;
        color: rgb(var(--v-theme-text-darken-1));
        font-size: 12px;
    }
}
</style>

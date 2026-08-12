<template>
    <v-menu v-if="isLoggedIn" v-model="isOpen" location="bottom end" :close-on-content-click="false"
        :persistent="isPinned"
        :offset="8" transition="fade-transition" @update:model-value="handleMenuVisibility">
        <template #activator="{ props: activatorProps }">
            <v-btn ref="activatorButton" v-bind="activatorProps" icon variant="text"
                :color="selectedDeviceId === null ? undefined : 'primary'" aria-label="テレビを選択">
                <Icon icon="material-symbols:cast-rounded" height="26px" />
                <v-tooltip activator="parent" location="bottom">{{ selectedDeviceName ?? 'テレビを選択' }}</v-tooltip>
            </v-btn>
        </template>

        <v-list class="remote-device-menu" density="compact" elevation="8" bg-color="background-lighten-1">
            <v-list-item class="remote-device-menu__header" title="テレビで再生">
                <template #append>
                    <v-btn icon size="small" variant="text" :color="isPinned ? 'primary' : undefined"
                        :aria-label="isPinned ? 'テレビ操作メニューの固定を解除' : 'テレビ操作メニューを固定'" @click="togglePinned">
                        <Icon :icon="isPinned ? 'fluent:pin-20-filled' : 'fluent:pin-20-regular'" width="20px" />
                    </v-btn>
                    <v-btn icon size="small" variant="text" aria-label="テレビ一覧を更新" :loading="isLoading" @click="refreshDevices">
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
                    <div v-if="selectedPlaybackState.artwork_url" class="remote-device-menu__artwork"
                        :class="{'remote-device-menu__artwork--logo': selectedPlaybackState.content_type === 'Live'}">
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
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import RemoteControl, { type IRemoteDevice, type RemoteCommand } from '@/services/RemoteControl';
import useSettingsStore from '@/stores/SettingsStore';
import Utils from '@/utils';

interface IRemotePlaybackState {
    content_type: 'Idle' | 'Live' | 'Recorded';
    title?: string;
    subtitle?: string;
    artwork_url?: string;
    is_playing?: boolean;
    can_seek?: boolean;
}

const settingsStore = useSettingsStore();
const activatorButton = ref<{ $el: HTMLElement } | null>(null);
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
let refreshInterval: number | null = null;
let refreshInProgress = false;
let devicesMissingSince: number | null = null;

function isActivatorVisible(): boolean {
    const element = activatorButton.value?.$el;
    return element !== undefined && element.getClientRects().length > 0;
}

function syncPinnedMenuVisibility(): void {
    // HeaderBar と SPHeaderBar は CSS で片方を隠しているだけで、どちらのコンポーネントもマウントされている。
    // 固定状態を全インスタンスへそのまま適用すると、非表示側の v-menu まで Teleport されて二重表示になる。
    if (isActivatorVisible() === false) {
        isOpen.value = false;
    } else if (isPinned.value === true) {
        isOpen.value = true;
    }
}

async function refreshDevices(): Promise<void> {
    if (refreshInProgress === true) return;
    refreshInProgress = true;
    isLoading.value = devices.value.length === 0;
    try {
        const fetchedDevices = await RemoteControl.fetchDevices();
        // 通信失敗時は直前の成功結果を維持し、一瞬だけ「オフライン」に切り替わるのを防ぐ。
        if (fetchedDevices === null) return;

        if (fetchedDevices.length > 0 || devices.value.length === 0) {
            devices.value = fetchedDevices;
            devicesMissingSince = null;
            return;
        }

        // Komorebi の WebSocket 再接続中に一覧が一時的に空になるため、3秒継続した場合だけオフラインへ切り替える。
        devicesMissingSince ??= performance.now();
        if (performance.now() - devicesMissingSince >= 3_000) {
            devices.value = [];
            devicesMissingSince = null;
        }
    } finally {
        isLoading.value = false;
        refreshInProgress = false;
    }
}

function handleMenuVisibility(visible: boolean): void {
    if (visible === false && isPinned.value === true && isActivatorVisible()) {
        isOpen.value = true;
        return;
    }
    if (refreshInterval !== null) {
        window.clearInterval(refreshInterval);
        refreshInterval = null;
    }
    if (visible) {
        refreshDevices();
        refreshInterval = window.setInterval(refreshDevices, 1_000);
    }
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
    window.removeEventListener('resize', syncPinnedMenuVisibility);
    if (refreshInterval !== null) window.clearInterval(refreshInterval);
});

onMounted(() => {
    window.addEventListener('resize', syncPinnedMenuVisibility);
    nextTick(syncPinnedMenuVisibility);
});

watch(isPinned, () => nextTick(syncPinnedMenuVisibility));
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

        &--logo img {
            padding: 6px;
            object-fit: contain;
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
}
</style>

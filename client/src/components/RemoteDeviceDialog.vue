<template>
    <v-menu v-if="isLoggedIn" v-model="isOpen" location="bottom end" :close-on-content-click="false"
        :offset="8" transition="slide-y-transition" @update:model-value="handleMenuVisibility">
        <template #activator="{ props: activatorProps }">
            <v-btn v-bind="activatorProps" icon variant="text"
                :color="selectedDeviceId === null ? undefined : 'primary'" aria-label="テレビを選択">
                <Icon icon="material-symbols:cast-rounded" height="26px" />
                <v-tooltip activator="parent" location="bottom">{{ selectedDeviceName ?? 'テレビを選択' }}</v-tooltip>
            </v-btn>
        </template>

        <v-card class="remote-device-menu" elevation="12">
            <div class="remote-device-menu__header">
                <div>
                    <div class="remote-device-menu__title">テレビで再生</div>
                    <div class="remote-device-menu__caption">再生先を選択</div>
                </div>
                <v-btn icon size="small" variant="text" aria-label="テレビ一覧を更新" :loading="isLoading" @click="refreshDevices">
                    <Icon icon="material-symbols:refresh-rounded" height="22px" />
                </v-btn>
            </div>

            <v-divider />
            <v-progress-linear v-if="isLoading" color="primary" indeterminate />
            <v-list v-else-if="devices.length > 0" class="remote-device-menu__list" bg-color="transparent" density="compact">
                <v-list-item v-for="device in devices" :key="device.device_id" :active="device.device_id === selectedDeviceId"
                    color="primary" rounded="lg" @click="selectDevice(device)">
                    <template #prepend>
                        <div class="remote-device-menu__device-icon">
                            <Icon icon="material-symbols:tv-rounded" height="24px" />
                        </div>
                    </template>
                    <v-list-item-title>{{ device.device_name }}</v-list-item-title>
                    <v-list-item-subtitle>オンライン</v-list-item-subtitle>
                    <template #append>
                        <Icon v-if="device.device_id === selectedDeviceId" icon="material-symbols:check-rounded" height="23px" />
                    </template>
                </v-list-item>
            </v-list>
            <div v-else class="remote-device-menu__empty">
                <Icon icon="material-symbols:tv-off-outline-rounded" height="32px" />
                <span>オンラインのテレビがありません</span>
                <small>Komorebi を起動して、HonomiTV とペアリングしてください。</small>
            </div>

            <template v-if="selectedDeviceId !== null">
                <v-divider />
                <button class="remote-device-menu__disconnect" type="button" @click="disconnect">
                    <Icon icon="material-symbols:link-off-rounded" height="20px" />
                    このテレビとの接続を解除
                </button>
            </template>
        </v-card>
    </v-menu>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';

import RemoteControl, { type IRemoteDevice } from '@/services/RemoteControl';
import useSettingsStore from '@/stores/SettingsStore';
import Utils from '@/utils';

const settingsStore = useSettingsStore();
const isOpen = ref(false);
const isLoading = ref(false);
const devices = ref<IRemoteDevice[]>([]);
const isLoggedIn = computed(() => Utils.getAccessToken() !== null);
const selectedDeviceId = computed(() => settingsStore.settings.selected_remote_device_id);
const selectedDevice = computed(() => devices.value.find((device) => device.device_id === selectedDeviceId.value) ?? null);
const selectedDeviceName = computed(() => selectedDevice.value?.device_name ?? null);

async function refreshDevices(): Promise<void> {
    isLoading.value = true;
    devices.value = await RemoteControl.fetchDevices() ?? [];
    isLoading.value = false;
}

function handleMenuVisibility(visible: boolean): void {
    if (visible) {
        refreshDevices();
    }
}

function selectDevice(device: IRemoteDevice): void {
    settingsStore.settings.selected_remote_device_id = device.device_id;
    isOpen.value = false;
}

function disconnect(): void {
    settingsStore.settings.selected_remote_device_id = null;
    isOpen.value = false;
}
</script>

<style scoped lang="scss">
.remote-device-menu {
    width: min(340px, calc(100vw - 24px));
    overflow: hidden;
    border: 1px solid rgb(var(--v-theme-background-lighten-2));
    border-radius: 10px;
    background: rgb(var(--v-theme-background-lighten-1));
    color: rgb(var(--v-theme-text));

    &__header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        min-height: 64px;
        padding: 10px 10px 10px 16px;
    }

    &__title {
        font-size: 16px;
        font-weight: 600;
    }

    &__caption,
    &__empty small {
        color: rgb(var(--v-theme-text-darken-2));
        font-size: 12px;
    }

    &__list {
        max-height: 300px;
        padding: 8px;
        overflow-y: auto;
    }

    &__device-icon {
        display: grid;
        place-items: center;
        width: 36px;
        height: 36px;
        margin-right: 12px;
        border-radius: 50%;
        background: rgb(var(--v-theme-background-lighten-2));
    }

    &__empty {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 7px;
        padding: 26px 22px;
        text-align: center;
    }

    &__empty small {
        line-height: 1.55;
    }

    &__disconnect {
        display: flex;
        align-items: center;
        gap: 10px;
        width: 100%;
        padding: 13px 16px;
        color: rgb(var(--v-theme-text-darken-1));
        font-size: 13px;
        text-align: left;

        &:hover {
            background: rgb(var(--v-theme-background-lighten-2));
        }
    }
}
</style>

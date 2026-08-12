<template>
    <v-btn v-if="isLoggedIn" icon variant="text" :color="selectedDeviceId === null ? undefined : 'primary'"
        aria-label="テレビを選択" @click="openDialog">
        <Icon icon="material-symbols:cast-rounded" height="26px" />
        <v-tooltip activator="parent" location="bottom">{{ selectedDeviceName ?? 'テレビを選択' }}</v-tooltip>
    </v-btn>
    <v-dialog v-model="isOpen" max-width="480px">
        <v-card class="remote-device-dialog">
            <v-card-title>テレビを選択</v-card-title>
            <v-card-text>
                <v-progress-linear v-if="isLoading" color="primary" indeterminate />
                <v-list v-else-if="devices.length > 0" bg-color="transparent">
                    <v-list-item v-for="device in devices" :key="device.device_id" :title="device.device_name"
                        subtitle="オンライン" :active="device.device_id === selectedDeviceId" color="primary"
                        rounded="lg" @click="selectDevice(device)">
                        <template #prepend>
                            <Icon icon="material-symbols:tv-rounded" height="27px" class="mr-4" />
                        </template>
                        <template #append>
                            <Icon v-if="device.device_id === selectedDeviceId" icon="material-symbols:check-rounded" height="25px" />
                        </template>
                    </v-list-item>
                </v-list>
                <div v-else class="remote-device-dialog__empty">
                    Komorebi の設定で HonomiTV とペアリングしたテレビを起動してください。
                </div>
                <div v-if="selectedDeviceId !== null && selectedDeviceIsOnline === false" class="remote-device-dialog__offline mt-4">
                    前回選択したテレビはオフラインです。選択は保持されています。
                </div>
            </v-card-text>
            <v-card-actions>
                <v-btn v-if="selectedDeviceId !== null" variant="text" @click="disconnect">選択を解除</v-btn>
                <v-spacer />
                <v-btn color="primary" variant="text" @click="isOpen = false">閉じる</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
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
const selectedDeviceIsOnline = computed(() => selectedDeviceId.value === null || selectedDevice.value !== null);

async function openDialog(): Promise<void> {
    isOpen.value = true;
    isLoading.value = true;
    devices.value = await RemoteControl.fetchDevices() ?? [];
    isLoading.value = false;
}

function selectDevice(device: IRemoteDevice): void {
    settingsStore.settings.selected_remote_device_id = device.device_id;
    isOpen.value = false;
}

function disconnect(): void {
    settingsStore.settings.selected_remote_device_id = null;
}
</script>

<style scoped lang="scss">
.remote-device-dialog {
    background: rgb(var(--v-theme-background-lighten-1));

    &__empty,
    &__offline {
        color: rgb(var(--v-theme-text-darken-1));
        line-height: 1.7;
    }
}
</style>

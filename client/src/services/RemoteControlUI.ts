import { ref, shallowRef } from 'vue';


// リモート操作メニュー本体は App.vue に1つだけ置き、各ヘッダーは現在表示中の位置だけを共有する。
export const remoteDeviceActivatorElement = shallowRef<HTMLElement | null>(null);
export const remoteDeviceMenuOpenRequest = ref(0);
export const selectedRemoteDeviceName = ref<string | null>(null);

export function requestRemoteDeviceMenuOpen(): void {
    remoteDeviceMenuOpenRequest.value += 1;
}

export function registerRemoteDeviceActivator(element: HTMLElement): void {
    if (element.getClientRects().length > 0) {
        remoteDeviceActivatorElement.value = element;
    }
}

export function unregisterRemoteDeviceActivator(element: HTMLElement): void {
    if (remoteDeviceActivatorElement.value === element) {
        remoteDeviceActivatorElement.value = null;
    }
}

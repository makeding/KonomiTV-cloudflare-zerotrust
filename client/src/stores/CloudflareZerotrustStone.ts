
import { defineStore } from 'pinia';

// import Version, { IVersionInformation } from '@/services/Version';
import Utils from '@/utils';
import CloudflareZerotrust, { ICloudflareZerotrustIdentity } from '@/services/CloudflareZerotrust';
import useSettingsStore, { getLocalStorageSettings, setLocalStorageSettings } from './SettingsStore';


/**
 * CFZTを共有するストア
 */
const useCFZTStore = defineStore('CFZT', {
    state: () => ({

        identity_info: null as ICloudflareZerotrustIdentity | boolean | null,

        // 最終更新日時 (UNIX タイムスタンプ、秒単位)
        last_updated_at: 0,
    }),
    getters: {
        // null
        is_CFZT(): boolean {
            return this.identity_info !== null
        },
        // null false
        is_login(): boolean {
            return !!this.identity_info
        }
    },
    actions: {

        /**
         * CFZT情報を取得する
         * すでに取得済みの情報がある場合は API リクエストを行わずにそれを返す
         * @param force 強制的に API リクエストを行う場合は true
         * @returns CFZT の取得に失敗した場合は null
         */
        async fetchCFZTIdentity(force: boolean = false): Promise<ICloudflareZerotrustIdentity | null> {
            const settings_store = useSettingsStore();
            // hidden setting = cloudflare_zerotrust
            if(!settings_store.settings.cloudflare_zerotrust && force === false){
                return null
            }

            const identity_info = await CloudflareZerotrust.fetchCloudflareZerotrustIdentity();

            if (identity_info === null) {
                settings_store.settings.cloudflare_zerotrust = false;
            }
            this.identity_info = identity_info;
            this.last_updated_at = Utils.time();

            return this.identity_info;
        },
    }
});

export default useCFZTStore;

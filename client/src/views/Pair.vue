<template>
    <main class="pair-page">
        <v-card class="pa-8" width="100%" max-width="520">
            <v-card-title class="text-h5 font-weight-bold">Komorebi を連携</v-card-title>
            <v-card-text class="pt-5">
                <template v-if="userStore.is_logged_in">
                    <p>テレビに表示されているコードを確認してください。</p>
                    <v-text-field class="mt-5" v-model="code" label="ペアリングコード" maxlength="8" />
                </template>
                <template v-else>
                    この操作には HonomiTV アカウントへのログインが必要です。
                </template>
                <v-alert v-if="message" class="mt-4" :type="success ? 'success' : 'error'">{{message}}</v-alert>
            </v-card-text>
            <v-card-actions>
                <v-btn v-if="!userStore.is_logged_in" color="secondary" :to="`/login/?return=${encodeURIComponent($route.fullPath)}`">ログイン</v-btn>
                <v-btn v-else color="secondary" :loading="loading" :disabled="code.length !== 8" @click="approve">このテレビを許可</v-btn>
            </v-card-actions>
        </v-card>
    </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';

import DeviceAuth from '@/services/DeviceAuth';
import useUserStore from '@/stores/UserStore';

const route = useRoute();
const userStore = useUserStore();
const code = ref(String(route.query.code ?? '').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 8));
const loading = ref(false);
const message = ref('');
const success = ref(false);

onMounted(() => userStore.fetchUser());

async function approve() {
    loading.value = true;
    success.value = await DeviceAuth.approve(code.value);
    message.value = success.value ? '連携しました。テレビに戻ってください。' : 'コードが無効か、有効期限が切れています。';
    loading.value = false;
}
</script>

<style scoped>
.pair-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 24px; }
</style>

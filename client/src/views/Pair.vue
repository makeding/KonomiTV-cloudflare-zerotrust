<template>
    <main class="pair-page">
        <v-card class="pa-8" width="100%" max-width="520">
            <v-card-title class="text-h5 font-weight-bold">Komorebi を連携</v-card-title>
            <v-card-text class="pt-5">
                <template v-if="userStore.is_logged_in">
                    <p>テレビに表示されているコードを確認してください。</p>
                    <v-text-field
                        v-model="formattedCode"
                        class="pair-code-input mt-5"
                        label="ペアリングコード"
                        placeholder="ABCD EFGH"
                        autocomplete="one-time-code"
                        autocapitalize="characters"
                        spellcheck="false"
                        autofocus
                        @keydown.enter="approve"
                    />
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
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';

import DeviceAuth from '@/services/DeviceAuth';
import useUserStore from '@/stores/UserStore';

const route = useRoute();
const userStore = useUserStore();
const code = ref(String(route.query.code ?? '').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 8));
const formattedCode = computed({
    get: () => code.value.length > 4 ? `${code.value.slice(0, 4)} ${code.value.slice(4)}` : code.value,
    set: (value: string) => {
        // TV 側と同じ 4 文字区切りで表示しつつ、内部では区切りを含まない 8 文字だけを保持する。
        // これにより、小文字入力や空白・ハイフンを含む貼り付けでも末尾の文字が欠けない。
        code.value = value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 8);
    },
});
const loading = ref(false);
const message = ref('');
const success = ref(false);

onMounted(() => userStore.fetchUser());

async function approve() {
    if (code.value.length !== 8 || loading.value) return;
    loading.value = true;
    success.value = await DeviceAuth.approve(code.value);
    message.value = success.value ? '連携しました。テレビに戻ってください。' : 'コードが無効か、有効期限が切れています。';
    loading.value = false;
}
</script>

<style scoped>
.pair-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 24px; }
.pair-code-input :deep(input) {
    font-family: monospace;
    font-size: 1.5rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-align: center;
    text-transform: uppercase;
}
</style>

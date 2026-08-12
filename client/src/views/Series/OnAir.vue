<template>
    <div class="route-container">
        <HeaderBar />
        <main>
            <Navigation />
            <div class="on-air-wrapper">
                <SPHeaderBar />
                <div class="on-air-container">
                    <Breadcrumbs :crumbs="[
                        { name: 'ホーム', path: '/' },
                        { name: 'シリーズ', path: '/series/' },
                        { name: '放送中', path: '/series/on-air', disabled: true },
                    ]" />
                    <div class="on-air-header">
                        <div>
                            <h2>放送中</h2>
                            <p>直近 3 週間の録画から通常の放送曜日・時刻を推定しています。</p>
                        </div>
                        <v-btn to="/series/" variant="tonal" prepend-icon="mdi-view-grid-outline">すべてのシリーズ</v-btn>
                    </div>

                    <div v-if="isLoading" class="on-air-loading">
                        <v-skeleton-loader v-for="index in 14" :key="index" type="image" />
                    </div>
                    <div v-else class="on-air-week">
                        <section v-for="day in weekdays" :key="day.index" class="on-air-day">
                            <header>
                                <h3>{{day.label}}</h3>
                                <span>{{seriesByWeekday[day.index].length}}件</span>
                            </header>
                            <div class="on-air-day__cards">
                                <button v-for="series in seriesByWeekday[day.index]" :key="series.id"
                                    v-ripple class="on-air-card" type="button"
                                    :aria-expanded="expandedSeriesID === series.id"
                                    @click="toggleSeries(series.id)">
                                    <div class="on-air-card__thumbnails"
                                        :class="`on-air-card__thumbnails--${series.thumbnail_recorded_program_ids.length}`">
                                        <img v-for="(programId, index) in series.thumbnail_recorded_program_ids"
                                            :key="programId" :class="`on-air-card__thumbnail--${index + 1}`"
                                            :src="`${Utils.api_base_url}/videos/${programId}/thumbnail`" alt=""
                                            loading="lazy" decoding="async">
                                    </div>
                                    <div class="on-air-card__shade"></div>
                                    <div class="on-air-card__body">
                                        <time>{{series.broadcast_time}}</time>
                                        <strong>{{series.title}}</strong>
                                        <div class="on-air-card__meta">
                                            <span>{{series.recorded_programs_count}}件</span>
                                            <div class="on-air-card__logos">
                                                <div v-for="channelId in series.channel_ids.slice(0, 2)" :key="channelId"
                                                    class="on-air-card__logo">
                                                    <div class="ch-sprite" :chid="channelId">
                                                        <img :src="`${Utils.api_base_url}/channels/${channelId}/logo`" alt="">
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    <Icon class="on-air-card__chevron"
                                        :icon="expandedSeriesID === series.id
                                            ? 'fluent:chevron-up-12-regular'
                                            : 'fluent:chevron-down-12-regular'"
                                        width="20px" />
                                </button>
                                <p v-if="seriesByWeekday[day.index].length === 0" class="on-air-day__empty">録画なし</p>
                            </div>
                        </section>
                    </div>
                </div>
            </div>
        </main>
        <v-dialog :model-value="expandedSeriesID !== null" class="on-air-dialog"
            :fullscreen="Utils.isSmartphoneVertical()" scrollable @update:model-value="closeSeries">
            <v-card class="on-air-dialog__card">
                <v-btn class="on-air-dialog__close" icon="mdi-close" variant="text"
                    aria-label="閉じる" @click="closeSeries()" />
                <div v-if="isSummaryLoading" class="on-air-dialog__loading">
                    <v-skeleton-loader type="heading, image, paragraph, paragraph" />
                </div>
                <SeriesEpisodeList v-else-if="expandedSeriesSummary"
                    :seriesId="expandedSeriesSummary.id"
                    :title="expandedSeriesSummary.title"
                    :description="expandedSeriesSummary.description"
                    :bangumiSubjectId="expandedSeriesSummary.bangumi_subject_id"
                    :bangumiSubjectName="expandedSeriesSummary.bangumi_subject_name"
                    :bangumiSubjectNameCn="expandedSeriesSummary.bangumi_subject_name_cn"
                    :bangumiSubjectSummary="expandedSeriesSummary.bangumi_subject_summary"
                    :bangumiSubjectImageUrl="expandedSeriesSummary.bangumi_subject_image_url" />
            </v-card>
        </v-dialog>
    </div>
</template>
<script lang="ts" setup>

import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import Breadcrumbs from '@/components/Breadcrumbs.vue';
import HeaderBar from '@/components/HeaderBar.vue';
import Navigation from '@/components/Navigation.vue';
import SeriesEpisodeList from '@/components/Series/SeriesEpisodeList.vue';
import SPHeaderBar from '@/components/SPHeaderBar.vue';
import Series, { IOnAirSeries, ISeriesSummary } from '@/services/Series';
import Utils from '@/utils';

const weekdays = [
    { index: 0, label: '月' }, { index: 1, label: '火' }, { index: 2, label: '水' },
    { index: 3, label: '木' }, { index: 4, label: '金' }, { index: 5, label: '土' },
    { index: 6, label: '日' },
];
const seriesList = ref<IOnAirSeries[]>([]);
const isLoading = ref(true);
const route = useRoute();
const router = useRouter();
const expandedSeriesID = ref<number | null>(null);
const expandedSeriesSummary = ref<ISeriesSummary | null>(null);
const isSummaryLoading = ref(false);
const seriesByWeekday = computed(() => weekdays.map(day =>
    seriesList.value.filter(series => series.weekday === day.index),
));

const syncExpandedSeriesFromRoute = async () => {
    const routeSeriesID = Array.isArray(route.params.series_id)
        ? route.params.series_id[0]
        : route.params.series_id;
    const parsedSeriesID = typeof routeSeriesID === 'string' ? Number.parseInt(routeSeriesID, 10) : Number.NaN;
    if (!Number.isFinite(parsedSeriesID) || parsedSeriesID <= 0) {
        expandedSeriesID.value = null;
        expandedSeriesSummary.value = null;
        isSummaryLoading.value = false;
        return;
    }
    if (!seriesList.value.some(series => series.id === parsedSeriesID)) {
        await router.replace('/series/on-air');
        return;
    }
    expandedSeriesID.value = parsedSeriesID;
    expandedSeriesSummary.value = null;
    isSummaryLoading.value = true;
    expandedSeriesSummary.value = await Series.fetchSeriesSummary(parsedSeriesID);
    isSummaryLoading.value = false;
};

const toggleSeries = async (seriesID: number) => {
    const isClosing = expandedSeriesID.value === seriesID;
    await router.push(isClosing ? '/series/on-air' : `/series/on-air/${seriesID}`);
};

const closeSeries = async (isOpen = false) => {
    if (isOpen || expandedSeriesID.value === null) return;
    await router.push('/series/on-air');
};

const loadOnAirSeries = async () => {
    isLoading.value = true;
    const result = await Series.fetchOnAirSeriesList();
    if (result) seriesList.value = result.series_list;
    isLoading.value = false;
    await syncExpandedSeriesFromRoute();
};

onMounted(async () => {
    await loadOnAirSeries();
});

watch(() => route.params.series_id, async () => {
    if (isLoading.value) return;
    await syncExpandedSeriesFromRoute();
});

</script>
<style lang="scss" scoped>

.on-air-wrapper { width: 100%; min-width: 0; }
.on-air-container { max-width: 1800px; padding: 20px; margin: 0 auto; }
.on-air-header {
    display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 20px;
    h2 { font-size: 24px; }
    p { margin-top: 4px; color: rgb(var(--v-theme-text-darken-1)); font-size: 12px; }
}
.on-air-week, .on-air-loading {
    display: grid; grid-template-columns: repeat(7, minmax(180px, 1fr)); gap: 10px;
    overflow-x: auto; padding-bottom: 8px;
}
.on-air-loading :deep(.v-skeleton-loader) { aspect-ratio: 16 / 10; min-width: 180px; }
.on-air-day {
    min-width: 180px;
    > header { display: flex; align-items: baseline; justify-content: space-between; padding: 0 4px 8px; }
    > header h3 { font-size: 18px; }
    > header span { color: rgb(var(--v-theme-text-darken-1)); font-size: 11px; }
    &__cards { display: flex; flex-direction: column; gap: 8px; }
    &__empty { padding: 24px 8px; color: rgb(var(--v-theme-text-darken-1)); text-align: center; }
}
.on-air-card {
    position: relative; display: block; aspect-ratio: 16 / 10; overflow: hidden;
    width: 100%; padding: 0; border: 0; font: inherit; text-align: left; cursor: pointer;
    color: white; text-decoration: none; background: rgb(var(--v-theme-background-lighten-2)); border-radius: 8px;
    &__thumbnails, &__shade { position: absolute; inset: 0; }
    &__thumbnails img { position: absolute; width: 94%; height: 94%; object-fit: cover; border-radius: 7px; }
    &__thumbnail--1 { right: 0; bottom: 0; z-index: 3; }
    &__thumbnail--2 { top: 3%; left: 2%; z-index: 2; }
    &__thumbnail--3 { top: 0; left: -3%; z-index: 1; }
    &__thumbnails--1 img { width: 100%; height: 100%; border-radius: 0; }
    &__shade { z-index: 4; background: linear-gradient(180deg, rgb(0 0 0 / 8%), rgb(0 0 0 / 88%)); }
    &__body { position: absolute; right: 9px; bottom: 8px; left: 9px; z-index: 5; }
    &__chevron { position: absolute; top: 7px; right: 7px; z-index: 5; filter: drop-shadow(0 1px 3px black); }
    time { font-size: 16px; font-weight: 700; }
    strong { display: -webkit-box; margin-top: 2px; overflow: hidden; font-size: 12px; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
    &__meta { display: flex; align-items: center; justify-content: space-between; margin-top: 5px; font-size: 10px; }
    &__logos { display: flex; gap: 3px; }
    &__logo { --ch-sprite-width: 34; --ch-sprite-height: 20; --ch-sprite-border-radius: 3; overflow: hidden; border-radius: 3px; }
}
.on-air-dialog {
    :deep(.v-overlay__content) { width: min(1800px, calc(100vw - 48px)); max-width: none; max-height: 92vh; }
    &__card { position: relative; overflow-y: auto; padding: 18px; background: rgb(var(--v-theme-background)); }
    &__close { position: sticky; top: 0; z-index: 20; align-self: flex-end; margin-bottom: -48px; }
    &__loading { min-height: 60vh; padding: 44px 12px 12px; }
    &__loading :deep(.v-skeleton-loader) { min-height: 52vh; }
}
@include smartphone-vertical {
    .on-air-container { padding: 8px; }
    .on-air-header { align-items: flex-start; padding: 0 8px; }
    .on-air-header p { max-width: 230px; }
    .on-air-week, .on-air-loading { grid-template-columns: repeat(7, 74vw); scroll-snap-type: x proximity; }
    .on-air-day { min-width: 74vw; scroll-snap-align: start; }
    .on-air-dialog {
        :deep(.v-overlay__content) { width: 100%; max-height: none; }
        &__card { padding: 8px; }
    }
}

</style>

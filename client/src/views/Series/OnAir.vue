<template>
    <div class="route-container">
        <HeaderBar />
        <main>
            <Navigation />
            <div ref="onAirWrapper" class="on-air-wrapper">
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
                        </div>
                        <v-btn to="/series/" variant="tonal" prepend-icon="mdi-view-grid-outline">すべてのシリーズ</v-btn>
                    </div>

                    <div v-if="isLoading" class="on-air-loading">
                        <v-skeleton-loader v-for="index in 14" :key="index" type="image" />
                    </div>
                    <div v-else class="on-air-week">
                        <section v-for="day in weekdays" :key="day.index"
                            class="on-air-day"
                            :class="[
                                `on-air-day--${day.index}`,
                                {'on-air-day--attention': hasAttentionSeries(day.index)},
                            ]">
                            <header>
                                <h3>{{day.label}}</h3>
                                <span>{{seriesByWeekday[day.index].length}}件</span>
                            </header>
                            <div class="on-air-day__cards">
                                <button v-for="series in seriesByWeekday[day.index]" :key="series.id"
                                    v-ripple class="on-air-card" type="button"
                                    :class="{'on-air-card--attention': isInAttentionWindow(series)}"
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
                                </button>
                                <p v-if="seriesByWeekday[day.index].length === 0" class="on-air-day__empty">録画なし</p>
                            </div>
                        </section>
                    </div>
                </div>
                <v-dialog :model-value="expandedSeriesID !== null" class="on-air-dialog"
                    :style="dialogOverlayStyle" scroll-strategy="none" @update:model-value="closeSeries">
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
        </main>
    </div>
</template>
<script lang="ts" setup>

import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import Breadcrumbs from '@/components/Breadcrumbs.vue';
import HeaderBar from '@/components/HeaderBar.vue';
import Navigation from '@/components/Navigation.vue';
import SeriesEpisodeList from '@/components/Series/SeriesEpisodeList.vue';
import SPHeaderBar from '@/components/SPHeaderBar.vue';
import Series, { IOnAirSeries, ISeriesSummary } from '@/services/Series';
import Utils, { dayjsOriginal } from '@/utils';

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
const onAirWrapper = ref<HTMLElement | null>(null);
const dialogOverlayBounds = ref({top: 0, left: 0, width: 0, height: 0});
let wrapperResizeObserver: ResizeObserver | null = null;
const seriesByWeekday = computed(() => weekdays.map(day =>
    seriesList.value.filter(series => series.weekday === day.index),
));
const dialogOverlayStyle = computed(() => ({
    top: `${dialogOverlayBounds.value.top}px`,
    left: `${dialogOverlayBounds.value.left}px`,
    width: `${dialogOverlayBounds.value.width}px`,
    height: `${dialogOverlayBounds.value.height}px`,
}));
const currentJST = ref(dayjsOriginal().tz('Asia/Tokyo'));
let currentTimeUpdateTimer: number | null = null;

// 番組表の曜日・時刻は日本時間なので、ブラウザのローカルタイムゾーンには依存させない。
// 現在時刻の 3 時間前から翌日 5 時までを、直近で確認したい放送枠として扱う。
const isInAttentionWindow = (series: IOnAirSeries): boolean => {
    const attentionStart = currentJST.value.subtract(3, 'hour');
    const attentionEnd = currentJST.value.add(1, 'day').startOf('day').add(5, 'hour');
    const currentWeekday = (currentJST.value.day() + 6) % 7;
    const weekStart = currentJST.value.startOf('day').subtract(currentWeekday, 'day');
    const [hour, minute] = series.broadcast_time.split(':').map(Number);
    const baseOccurrence = weekStart.add(series.weekday, 'day').hour(hour).minute(minute).second(0);

    // 日曜から月曜へ跨ぐ場合も拾えるよう、前後週の同じ放送枠も照合する。
    return [-7, 0, 7].some(dayOffset => {
        const occurrence = baseOccurrence.add(dayOffset, 'day');
        return occurrence.isBetween(attentionStart, attentionEnd, null, '[]');
    });
};

const hasAttentionSeries = (weekday: number): boolean => {
    return seriesByWeekday.value[weekday].some(isInAttentionWindow);
};

const updateDialogOverlayBounds = () => {
    if (!onAirWrapper.value) return;
    const wrapperBounds = onAirWrapper.value.getBoundingClientRect();
    const top = Math.max(0, wrapperBounds.top);
    const left = Math.max(0, wrapperBounds.left);
    dialogOverlayBounds.value = {
        top,
        left,
        width: window.innerWidth - left,
        height: window.innerHeight - top,
    };
};

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
    updateDialogOverlayBounds();
    wrapperResizeObserver = new ResizeObserver(updateDialogOverlayBounds);
    if (onAirWrapper.value) wrapperResizeObserver.observe(onAirWrapper.value);
    window.addEventListener('resize', updateDialogOverlayBounds);
    currentTimeUpdateTimer = window.setInterval(() => {
        currentJST.value = dayjsOriginal().tz('Asia/Tokyo');
    }, 60_000);
    await loadOnAirSeries();
});

onBeforeUnmount(() => {
    wrapperResizeObserver?.disconnect();
    window.removeEventListener('resize', updateDialogOverlayBounds);
    if (currentTimeUpdateTimer !== null) window.clearInterval(currentTimeUpdateTimer);
});

watch(() => route.params.series_id, async () => {
    if (isLoading.value) return;
    await syncExpandedSeriesFromRoute();
});

</script>
<style lang="scss" scoped>

.on-air-wrapper { position: relative; width: 100%; min-width: 0; }
.on-air-container { max-width: 1800px; padding: 20px; margin: 0 auto; }
.on-air-header {
    display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 20px;
    h2 { font-size: 24px; }
}
.on-air-week, .on-air-loading {
    display: grid; grid-template-columns: repeat(7, minmax(180px, 1fr)); gap: 10px;
    overflow-x: auto; padding-bottom: 8px;
}
.on-air-loading :deep(.v-skeleton-loader) { aspect-ratio: 16 / 10; min-width: 180px; }
.on-air-day {
    --on-air-day-color: #64748b;
    min-width: 180px;
    > header {
        display: flex; align-items: baseline; justify-content: space-between;
        padding: 6px 9px; margin-bottom: 8px;
        color: white; background: var(--on-air-day-color); border-radius: 6px;
    }
    > header h3 { font-size: 18px; text-shadow: 0 1px 2px rgb(0 0 0 / 28%); }
    > header span { color: rgb(255 255 255 / 88%); font-size: 11px; }
    &--0 { --on-air-day-color: #e76f51; }
    &--1 { --on-air-day-color: #e9a23b; }
    &--2 { --on-air-day-color: #84a83f; }
    &--3 { --on-air-day-color: #3aa889; }
    &--4 { --on-air-day-color: #438ac7; }
    &--5 { --on-air-day-color: #646fc1; }
    &--6 { --on-air-day-color: #ff69b4; }
    &__cards { display: flex; flex-direction: column; gap: 8px; }
    &__empty { padding: 24px 8px; color: rgb(var(--v-theme-text-darken-1)); text-align: center; }
    &--attention {
        padding: 5px;
        margin: -5px;
        background: rgb(var(--v-theme-primary) / 9%);
        border-radius: 9px;
    }
}
.on-air-card {
    position: relative; display: block; aspect-ratio: 16 / 10; overflow: hidden;
    width: 100%; padding: 0; border: 0; font: inherit; text-align: left; cursor: pointer;
    color: white; text-decoration: none; background: rgb(var(--v-theme-background-lighten-2)); border-radius: 8px;
    box-shadow: 0 2px 6px rgb(0 0 0 / 18%);
    transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
    &:hover, &:focus-visible {
        z-index: 1;
        filter: brightness(1.07);
        box-shadow: 0 6px 16px rgb(0 0 0 / 34%);
        transform: translateY(-2px) scale(1.012);
    }
    @media (hover: none) {
        &:hover { filter: none; box-shadow: 0 2px 6px rgb(0 0 0 / 18%); transform: none; }
    }
    &__thumbnails, &__shade { position: absolute; inset: 0; }
    &__thumbnails img { position: absolute; width: 94%; height: 94%; object-fit: cover; border-radius: 7px; }
    &__thumbnail--1 { right: 0; bottom: 0; z-index: 3; }
    &__thumbnail--2 { top: 3%; left: 2%; z-index: 2; }
    &__thumbnail--3 { top: 0; left: -3%; z-index: 1; }
    &__thumbnails--1 img { width: 100%; height: 100%; border-radius: 0; }
    &__shade { z-index: 4; background: linear-gradient(180deg, rgb(0 0 0 / 8%), rgb(0 0 0 / 88%)); }
    &__body { position: absolute; right: 9px; bottom: 8px; left: 9px; z-index: 5; }
    time { font-size: 16px; font-weight: 700; }
    strong { display: -webkit-box; margin-top: 2px; overflow: hidden; font-size: 12px; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
    &__meta { display: flex; align-items: center; justify-content: space-between; margin-top: 5px; font-size: 10px; }
    &__logos { display: flex; gap: 3px; }
    &__logo { --ch-sprite-width: 34; --ch-sprite-height: 20; --ch-sprite-border-radius: 3; overflow: hidden; border-radius: 3px; }
    &--attention {
        outline: 2px solid rgb(var(--v-theme-primary) / 78%);
        box-shadow: 0 0 0 4px rgb(var(--v-theme-primary) / 12%);
    }
}
.on-air-dialog {
    :deep(.v-overlay__content) {
        width: min(1480px, calc(100% - 64px));
        max-width: none;
        max-height: 84dvh;
    }
    &__card {
        position: relative; overflow-y: auto; padding: 0;
        background: transparent !important; box-shadow: none !important;
    }
    &__close {
        position: sticky; top: 8px; z-index: 20; align-self: flex-end;
        margin: 0 8px -48px 0; background: rgb(var(--v-theme-background-lighten-1));
    }
    &__loading { min-height: 60vh; padding: 44px 12px 12px; }
    &__loading :deep(.v-skeleton-loader) { min-height: 52vh; }

    // 通常の Series ページより表示面積が限られるため、外枠だけを広げず内容も一段大きくする。
    :deep(.series-episode-list) { padding: 22px 26px 24px; }
    :deep(.series-episode-list__header h3) { font-size: 24px; }
    :deep(.series-episode-list__bangumi > img) { width: 128px; height: 181px; }
    :deep(.series-episode-list__bangumi-profile p) { font-size: 13px; }
    :deep(.series-episode-list__matrix) {
        grid-template-columns: 64px 94px repeat(var(--episode-column-count), 184px);
    }
    :deep(.series-episode-list__channel-logo) {
        --ch-sprite-width: 56;
        --ch-sprite-height: 32;
    }
    :deep(.series-episode-list__channel-name span) { font-size: 13px; }
    :deep(.series-episode-list__episode-label span) { font-size: 11px; }
}
@include smartphone-vertical {
    .on-air-container { padding: 8px; }
    .on-air-header { align-items: flex-start; padding: 0 8px; }
    .on-air-week, .on-air-loading {
        grid-template-columns: repeat(7, min(36vw, 180px));
        gap: 8px;
        scroll-snap-type: x proximity;
    }
    .on-air-day {
        min-width: min(36vw, 180px);
        scroll-snap-align: start;
        > header { padding: 5px 7px; margin-bottom: 6px; }
        > header h3 { font-size: 16px; }
    }
    .on-air-card {
        &__body { right: 7px; bottom: 6px; left: 7px; }
        time { font-size: 14px; }
        strong { font-size: 11px; line-height: 1.35; }
        &__meta { margin-top: 3px; font-size: 9px; }
        &__logo { --ch-sprite-width: 30; --ch-sprite-height: 18; --ch-sprite-border-radius: 3; }
    }
    .on-air-dialog {
        :deep(.v-overlay__content) {
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
            max-height: none;
            margin: 0;
        }
        &__card {
            width: 100%;
            min-width: 0;
            height: 100%;
            padding: 0;
            background: rgb(var(--v-theme-background)) !important;
            border-radius: 0;
        }
        &__loading { min-height: 100%; }
        &__loading :deep(.v-skeleton-loader) { min-height: calc(100dvh - 64px); }
        :deep(.series-episode-list) { min-height: 100%; padding: 14px 12px 18px; border-radius: 0; }
        :deep(.series-episode-list__header h3) { font-size: 21px; }
        :deep(.series-episode-list__bangumi > img) { width: 76px; height: 108px; }
        :deep(.series-episode-list__bangumi-profile p) { font-size: 12px; }
        :deep(.series-episode-list__matrix) {
            grid-template-columns: 52px 56px repeat(var(--episode-column-count), 145px);
        }
        :deep(.series-episode-list__channel-logo) {
            --ch-sprite-width: 44;
            --ch-sprite-height: 25;
        }
        :deep(.series-episode-list__channel-name span) { font-size: 12px; }
        :deep(.series-episode-list__episode-label span) { font-size: 10px; }
    }
}

</style>

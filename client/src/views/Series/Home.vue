<template>
    <div class="route-container">
        <HeaderBar v-model:searchQuery="search_query" @search="updateSearchQuery" />
        <main>
            <Navigation />
            <div class="series-home-container-wrapper">
                <SPHeaderBar v-model:searchQuery="search_query" @search="updateSearchQuery" />
                <div class="series-home-container">
                    <Breadcrumbs :crumbs="[
                        { name: 'ホーム', path: '/' },
                        { name: 'シリーズ', path: '/series/', disabled: true },
                    ]" />
                    <div class="series-home-container__header">
                        <h2 class="series-home-container__title">
                            シリーズ
                            <span class="series-home-container__count">{{is_loading ? '取得中…' : `${total_series}件`}}</span>
                        </h2>
                        <v-select
                            v-model="sort_order"
                            :items="[
                                { title: '更新が新しい順', value: 'desc' },
                                { title: '更新が古い順', value: 'asc' },
                            ]"
                            item-title="title"
                            item-value="value"
                            class="series-home-container__sort"
                            color="primary"
                            bg-color="background-lighten-1"
                            variant="solo"
                            density="comfortable"
                            hide-details
                            @update:model-value="updateSortOrder($event as 'desc' | 'asc')" />
                    </div>

                    <div v-if="is_loading" class="series-grid">
                        <v-skeleton-loader v-for="index in 6" :key="index" type="article" class="series-card" />
                    </div>
                    <div v-else-if="series_list.length > 0" class="series-grid">
                        <router-link v-for="series in series_list" :key="series.id" v-ripple
                            class="series-card" :to="`/series/${series.id}`">
                            <div class="series-card__thumbnails"
                                :class="`series-card__thumbnails--${series.thumbnail_recorded_program_ids.length}`"
                                aria-hidden="true">
                                <img v-for="(recorded_program_id, index) in series.thumbnail_recorded_program_ids"
                                    :key="recorded_program_id"
                                    class="series-card__thumbnail"
                                    :class="`series-card__thumbnail--${index + 1}`"
                                    loading="lazy"
                                    decoding="async"
                                    :src="`${Utils.api_base_url}/videos/${recorded_program_id}/thumbnail`"
                                    alt="">
                            </div>
                            <div class="series-card__overlay"></div>
                            <div class="series-card__body">
                                <h3 class="series-card__title">{{series.title}}</h3>
                                <div class="series-card__meta">
                                    <span>{{series.recorded_programs_count}}件の録画</span>
                                    <span v-for="genre in getMajorGenres(series)" :key="genre" class="series-card__genre">{{genre}}</span>
                                </div>
                            </div>
                            <Icon class="series-card__chevron" icon="fluent:chevron-right-12-regular" width="22px" />
                        </router-link>
                    </div>
                    <div v-else class="series-empty">
                        <Icon icon="fluent:video-clip-multiple-20-regular" width="56px" />
                        <h2>{{search_query ? 'シリーズが見つかりませんでした。' : 'シリーズ情報がありません。'}}</h2>
                        <p v-if="!search_query">シリーズ情報を持つ録画番組が追加されると、ここに表示されます。</p>
                    </div>

                    <v-pagination v-if="!is_loading && total_series > 0"
                        v-model="current_page"
                        class="series-pagination"
                        active-color="primary"
                        density="comfortable"
                        :length="Math.ceil(total_series / 30)"
                        :total-visible="Utils.isSmartphoneVertical() ? 5 : 7"
                        @update:model-value="updatePage" />
                </div>
            </div>
        </main>
    </div>
</template>
<script lang="ts" setup>

import { onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import Breadcrumbs from '@/components/Breadcrumbs.vue';
import HeaderBar from '@/components/HeaderBar.vue';
import Navigation from '@/components/Navigation.vue';
import SPHeaderBar from '@/components/SPHeaderBar.vue';
import Series, { ISeriesSummary } from '@/services/Series';
import useUserStore from '@/stores/UserStore';
import Utils from '@/utils';

const route = useRoute();
const router = useRouter();

const series_list = ref<ISeriesSummary[]>([]);
const total_series = ref(0);
const current_page = ref(1);
const sort_order = ref<'desc' | 'asc'>('desc');
const search_query = ref('');
const is_loading = ref(true);
const is_mounted = ref(false);

const syncStateFromRoute = () => {
    const parsed_page = Number.parseInt(route.query.page as string ?? '1', 10);
    current_page.value = Number.isFinite(parsed_page) && parsed_page > 0 ? parsed_page : 1;
    sort_order.value = route.query.order === 'asc' ? 'asc' : 'desc';
    search_query.value = typeof route.query.query === 'string' ? route.query.query : '';
};

const fetchSeries = async () => {
    is_loading.value = true;
    const result = search_query.value
        ? await Series.searchSeries(search_query.value, sort_order.value, current_page.value)
        : await Series.fetchSeriesList(sort_order.value, current_page.value);
    if (result) {
        series_list.value = result.series_list;
        total_series.value = result.total;
    }
    is_loading.value = false;
};

const replaceQuery = async (query: string, order: 'desc' | 'asc', page: number) => {
    await router.replace({
        path: '/series/',
        query: {
            ...(query ? { query } : {}),
            order,
            page: page.toString(),
        },
    });
};

const updateSearchQuery = async (query: string) => {
    search_query.value = query.trim();
    await replaceQuery(search_query.value, sort_order.value, 1);
};

const updateSortOrder = async (order: 'desc' | 'asc') => {
    sort_order.value = order;
    await replaceQuery(search_query.value, order, 1);
};

const updatePage = async (page: number) => {
    await replaceQuery(search_query.value, sort_order.value, page);
};

const getMajorGenres = (series: ISeriesSummary): string[] => {
    return [...new Set(series.genres.map(genre => genre.major))].slice(0, 2);
};

watch(() => route.query, async () => {
    if (!is_mounted.value) return;
    syncStateFromRoute();
    await fetchSeries();
}, { deep: true });

onMounted(async () => {
    const userStore = useUserStore();
    await userStore.fetchUser();
    syncStateFromRoute();
    is_mounted.value = true;
    await fetchSeries();
});

</script>
<style lang="scss" scoped>

.series-home-container-wrapper {
    display: flex;
    flex-direction: column;
    width: 100%;
    min-width: 0;
}

.series-home-container {
    width: 100%;
    max-width: 1440px;
    padding: 20px;
    margin: 0 auto;
    @include smartphone-horizontal {
        padding: 16px 20px;
    }
    @include smartphone-vertical {
        padding: 8px;
    }

    &__header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        margin-bottom: 20px;
        @include smartphone-vertical {
            padding: 0 8px;
        }
    }

    &__title {
        min-width: 0;
        font-size: 24px;
        font-weight: 700;
    }

    &__count {
        margin-left: 10px;
        color: rgb(var(--v-theme-text-darken-1));
        font-size: 14px;
        font-weight: 400;
    }

    &__sort {
        flex: 0 0 190px;
        max-width: 190px;
    }
}

.series-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    @include tablet-vertical {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    @include smartphone-vertical {
        grid-template-columns: minmax(0, 1fr);
        gap: 8px;
    }
}

.series-card {
    position: relative;
    display: block;
    aspect-ratio: 16 / 9;
    min-width: 0;
    overflow: hidden;
    color: rgb(var(--v-theme-text));
    text-decoration: none;
    background: rgb(var(--v-theme-background-lighten-1));
    border-radius: 8px;
    box-shadow: 0 2px 6px rgb(0 0 0 / 18%);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    &:hover {
        box-shadow: 0 5px 14px rgb(0 0 0 / 28%);
        transform: translateY(-2px);
    }

    &__thumbnails,
    &__overlay {
        position: absolute;
        inset: 0;
    }

    &__thumbnails {
        background: rgb(var(--v-theme-background-lighten-2));
    }

    &__thumbnail {
        position: absolute;
        width: 92%;
        height: 92%;
        object-fit: cover;
        border: 1px solid rgb(255 255 255 / 14%);
        border-radius: 7px;
        box-shadow: 0 4px 14px rgb(0 0 0 / 42%);

        &--1 {
            top: 1%;
            left: -2%;
            transform: rotate(-2deg);
        }

        &--2 {
            top: 4%;
            left: 4%;
            transform: rotate(1deg);
        }

        &--3 {
            top: 8%;
            left: 9%;
        }
    }

    &__thumbnails--1 &__thumbnail--1 {
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        border: 0;
        border-radius: 0;
        transform: none;
    }

    &__thumbnails--2 &__thumbnail {
        width: 96%;
        height: 96%;
    }

    &__overlay {
        background: linear-gradient(180deg, rgb(0 0 0 / 4%) 20%, rgb(0 0 0 / 82%) 100%);
    }

    &__body {
        position: absolute;
        right: 16px;
        bottom: 14px;
        left: 16px;
        z-index: 1;
        min-width: 0;
    }

    &__title {
        overflow: hidden;
        color: white;
        font-size: 17px;
        font-weight: 700;
        text-shadow: 0 1px 4px rgb(0 0 0 / 75%);
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    &__meta {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-top: 6px;
        overflow: hidden;
        color: rgb(255 255 255 / 82%);
        font-size: 12px;
        text-shadow: 0 1px 3px rgb(0 0 0 / 80%);
        white-space: nowrap;
    }

    &__genre {
        padding: 2px 6px;
        background: rgb(0 0 0 / 38%);
        border-radius: 10px;
    }

    &__chevron {
        position: absolute;
        right: 12px;
        top: 12px;
        z-index: 1;
        color: white;
        filter: drop-shadow(0 1px 3px rgb(0 0 0 / 80%));
    }
}

.series-empty {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    min-height: 320px;
    color: rgb(var(--v-theme-text-darken-1));
    text-align: center;
    h2 {
        margin-top: 16px;
        color: rgb(var(--v-theme-text));
        font-size: 20px;
    }
    p {
        margin-top: 8px;
        font-size: 14px;
    }
}

.series-pagination {
    margin-top: 28px;
}

</style>

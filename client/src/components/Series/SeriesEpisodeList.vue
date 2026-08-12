<template>
    <div class="series-episode-list">
        <RecordedProgramList
            :title="title"
            :programs="programs"
            :total="total_programs"
            :page="current_page"
            :sortOrder="sort_order"
            :isLoading="is_loading"
            :showEmptyMessage="!is_loading"
            @update:page="updatePage"
            @update:sortOrder="updateSortOrder($event as SortOrder)" />
    </div>
</template>
<script lang="ts" setup>

import { onMounted, ref } from 'vue';

import RecordedProgramList from '@/components/Videos/RecordedProgramList.vue';
import { IRecordedProgram, SortOrder } from '@/services/Videos';
import Videos from '@/services/Videos';

const props = defineProps<{
    seriesId: number;
    title: string;
}>();

const programs = ref<IRecordedProgram[]>([]);
const total_programs = ref(0);
const current_page = ref(1);
const sort_order = ref<SortOrder>('desc');
const is_loading = ref(true);

const fetchPrograms = async () => {
    is_loading.value = true;
    const result = await Videos.fetchVideosBySeries(props.seriesId, null, sort_order.value, current_page.value);
    if (result) {
        programs.value = result.recorded_programs;
        total_programs.value = result.total;
    }
    is_loading.value = false;
};

const updatePage = async (page: number) => {
    current_page.value = page;
    await fetchPrograms();
};

const updateSortOrder = async (order: SortOrder) => {
    sort_order.value = order;
    current_page.value = 1;
    await fetchPrograms();
};

onMounted(fetchPrograms);

</script>
<style lang="scss" scoped>

.series-episode-list {
    padding: 16px;
    background: rgb(var(--v-theme-background-lighten-1));
    border: 1px solid rgb(var(--v-theme-background-lighten-2));
    border-radius: 8px;
    box-shadow: 0 4px 16px rgb(0 0 0 / 24%);
    @include smartphone-vertical {
        padding: 10px 8px;
    }
}

</style>

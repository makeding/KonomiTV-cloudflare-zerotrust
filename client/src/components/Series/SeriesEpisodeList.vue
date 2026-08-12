<template>
    <div class="series-episode-list">
        <div class="series-episode-list__header">
            <h3>{{title}}</h3>
            <span>{{total_programs}}話</span>
        </div>
        <div v-if="is_loading" class="series-episode-list__loading">
            <v-skeleton-loader v-for="index in 6" :key="index" type="image" />
        </div>
        <div v-else class="series-episode-list__matrix-scroll">
            <div class="series-episode-list__matrix"
                :style="{'--episode-column-count': episode_matrix.slots.length}">
                <div class="series-episode-list__corner">放送局</div>
                <div v-for="slot in episode_matrix.slots" :key="slot.key"
                    class="series-episode-list__column-header">
                    {{slot.label}}
                </div>
                <template v-for="channel_row in episode_matrix.rows" :key="channel_row.id">
                    <div class="series-episode-list__channel-header">
                        <div v-if="channel_row.channel_id" class="series-episode-list__channel-logo">
                            <div class="ch-sprite" :chid="channel_row.channel_id">
                                <img loading="lazy"
                                    decoding="async"
                                    :src="`${Utils.api_base_url}/channels/${channel_row.channel_id}/logo`"
                                    alt="">
                            </div>
                        </div>
                        <div class="series-episode-list__channel-name">
                            <span>{{channel_row.name}}</span>
                            <small>{{channel_row.program_count}}話</small>
                        </div>
                    </div>
                    <template v-for="(program, slot_index) in channel_row.programs"
                        :key="episode_matrix.slots[slot_index].key">
                        <router-link v-if="program"
                            v-ripple
                            class="series-episode-list__episode"
                            :to="`/videos/watch/${program.id}`">
                            <img loading="lazy" decoding="async"
                                :src="`${Utils.api_base_url}/videos/${program.id}/thumbnail`"
                                alt="">
                            <div class="series-episode-list__episode-label">
                                <span>{{getEpisodeCaption(program)}}</span>
                            </div>
                        </router-link>
                        <div v-else class="series-episode-list__episode-placeholder" aria-hidden="true"></div>
                    </template>
                </template>
            </div>
        </div>
    </div>
</template>
<script lang="ts" setup>

import { computed, onMounted, ref } from 'vue';

import { IRecordedProgram } from '@/services/Videos';
import Videos from '@/services/Videos';
import Utils, { dayjs } from '@/utils';

const props = defineProps<{
    seriesId: number;
    title: string;
}>();

interface IEpisodeSlot {
    key: string;
    label: string;
}

interface IChannelRow {
    id: string;
    channel_id: string | null;
    name: string;
    program_count: number;
    programs: Array<IRecordedProgram | null>;
}

const programs = ref<IRecordedProgram[]>([]);
const total_programs = ref(0);
const is_loading = ref(true);
const episode_number_collator = new Intl.Collator('ja', { numeric: true });

const getEpisodeSlots = (program: IRecordedProgram): IEpisodeSlot[] => {
    if (program.episode_number) {
        const range_match = program.episode_number.match(/^(\d+)-(\d+)$/);
        const episode_numbers = range_match
            ? Array.from(
                { length: Number(range_match[2]) - Number(range_match[1]) + 1 },
                (_, index) => String(Number(range_match[1]) + index),
            )
            : program.episode_number.split('・');
        return episode_numbers.map(episode_number => ({
            key: `episode:${episode_number}`,
            label: `第${episode_number}話`,
        }));
    }
    const date = dayjs(program.start_time).format('YYYY-MM-DD');
    return [{
        key: `date:${date}`,
        label: dayjs(program.start_time).format('M/D'),
    }];
};

const episode_matrix = computed<{ slots: IEpisodeSlot[]; rows: IChannelRow[] }>(() => {
    const slots = [...new Map(programs.value.flatMap(program =>
        getEpisodeSlots(program).map(slot => [slot.key, slot] as const),
    )).values()].sort((left, right) => episode_number_collator.compare(left.key, right.key));

    const groups = new Map<string, {
        id: string;
        channel_id: string | null;
        name: string;
        program_count: number;
        programs: Map<string, IRecordedProgram>;
    }>();
    for (const program of programs.value) {
        const id = program.channel?.id ?? 'unknown';
        const group = groups.get(id) ?? {
            id,
            channel_id: program.channel?.id ?? null,
            name: program.channel?.name ?? 'チャンネル情報なし',
            program_count: 0,
            programs: new Map<string, IRecordedProgram>(),
        };
        group.program_count++;
        for (const slot of getEpisodeSlots(program)) {
            if (!group.programs.has(slot.key)) group.programs.set(slot.key, program);
        }
        groups.set(id, group);
    }

    const rows = [...groups.values()].map(group => ({
        id: group.id,
        channel_id: group.channel_id,
        name: group.name,
        program_count: group.program_count,
        programs: slots.map(slot => group.programs.get(slot.key) ?? null),
    }));
    return { slots, rows };
});

const getEpisodeCaption = (program: IRecordedProgram): string => {
    return program.subtitle || dayjs(program.start_time).format('YYYY/M/D (dd) HH:mm');
};

const fetchPrograms = async () => {
    is_loading.value = true;
    const first_page = await Videos.fetchVideosBySeries(props.seriesId, null, 'asc', 1);
    if (first_page) {
        const all_programs = [...first_page.recorded_programs];
        const total_pages = Math.ceil(first_page.total / 30);
        const remaining_pages = await Promise.all(
            Array.from({ length: total_pages - 1 }, (_, index) =>
                Videos.fetchVideosBySeries(props.seriesId, null, 'asc', index + 2),
            ),
        );
        for (const page of remaining_pages) {
            if (page) all_programs.push(...page.recorded_programs);
        }
        programs.value = all_programs;
        total_programs.value = first_page.total;
    }
    is_loading.value = false;
};

onMounted(fetchPrograms);

</script>
<style lang="scss" scoped>

.series-episode-list {
    padding: 18px 20px 20px;
    background: rgb(var(--v-theme-background-lighten-1));
    border: 1px solid rgb(var(--v-theme-background-lighten-2));
    border-radius: 8px;
    box-shadow: 0 4px 16px rgb(0 0 0 / 24%);
    @include smartphone-vertical {
        padding: 14px 12px 16px;
    }

    &__header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 14px;
        h3 {
            min-width: 0;
            overflow: hidden;
            font-size: 21px;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        span {
            flex: 0 0 auto;
            color: rgb(var(--v-theme-text-darken-1));
            font-size: 13px;
        }
    }

    &__loading {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(145px, 1fr));
        gap: 8px;
    }

    &__matrix-scroll {
        overflow-x: auto;
        overscroll-behavior-x: contain;
        -webkit-overflow-scrolling: touch;
    }

    &__matrix {
        display: grid;
        grid-template-columns: 150px repeat(var(--episode-column-count), 170px);
        gap: 8px;
        width: max-content;
        min-width: 100%;
        @include smartphone-vertical {
            grid-template-columns: 116px repeat(var(--episode-column-count), 145px);
        }
    }

    &__corner,
    &__column-header {
        position: sticky;
        top: 0;
        z-index: 2;
        padding: 3px 8px;
        color: rgb(var(--v-theme-text-darken-1));
        font-size: 11px;
        text-align: center;
        background: rgb(var(--v-theme-background-lighten-1));
    }

    &__corner {
        left: 0;
        z-index: 3;
        text-align: left;
    }

    &__channel-header {
        position: sticky;
        left: 0;
        z-index: 2;
        display: flex;
        align-items: center;
        gap: 8px;
        min-width: 0;
        padding-right: 8px;
        background: rgb(var(--v-theme-background-lighten-1));
    }

    &__channel-logo {
        flex: 0 0 auto;
        --ch-sprite-width: 52;
        --ch-sprite-height: 30;
        --ch-sprite-border-radius: 4;
        width: calc(var(--ch-sprite-width) * 1px);
        height: calc(var(--ch-sprite-height) * 1px);
        overflow: hidden;
        background: linear-gradient(150deg, rgb(var(--v-theme-gray)), rgb(var(--v-theme-background-lighten-2)));
        border-radius: calc(var(--ch-sprite-border-radius) * 1px);
        @include smartphone-vertical {
            --ch-sprite-width: 44;
            --ch-sprite-height: 25;
        }
    }

    &__channel-name {
        min-width: 0;
        span,
        small {
            display: block;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        span {
            font-size: 12px;
            font-weight: 700;
        }
        small {
            color: rgb(var(--v-theme-text-darken-1));
            font-size: 10px;
        }
    }

    &__episode,
    &__episode-placeholder {
        aspect-ratio: 16 / 9;
        border-radius: 6px;
    }

    &__episode {
        position: relative;
        overflow: hidden;
        color: white;
        text-decoration: none;
        background: rgb(var(--v-theme-background-lighten-2));
        img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        &::after {
            position: absolute;
            inset: 0;
            content: '';
            background: linear-gradient(180deg, transparent 45%, rgb(0 0 0 / 86%) 100%);
        }
    }

    &__episode-placeholder {
        background: rgb(var(--v-theme-background-lighten-2) / 34%);
        border: 1px dashed rgb(var(--v-theme-text-darken-1) / 18%);
    }

    &__episode-label {
        position: absolute;
        right: 8px;
        bottom: 6px;
        left: 8px;
        z-index: 1;
        min-width: 0;
        text-shadow: 0 1px 3px rgb(0 0 0 / 85%);
        span {
            display: block;
            overflow: hidden;
            font-size: 10px;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
    }
}

</style>

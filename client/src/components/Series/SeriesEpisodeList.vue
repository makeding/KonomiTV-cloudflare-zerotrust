<template>
    <div class="series-episode-list">
        <div class="series-episode-list__header">
            <div class="series-episode-list__titles">
                <h3>{{title}}</h3>
                <small v-if="bangumiSubjectNameCn">{{bangumiSubjectNameCn}}</small>
            </div>
            <span>{{seriesCountLabel}}</span>
        </div>
        <div v-if="bangumiSubjectId" class="series-episode-list__bangumi">
            <img v-if="bangumiSubjectImageUrl" :src="bangumiSubjectImageUrl" alt="" loading="lazy" decoding="async">
            <div class="series-episode-list__bangumi-profile">
                <p v-if="japaneseSummary">{{japaneseSummary}}</p>
                <p v-if="chineseSummary" class="series-episode-list__chinese-summary">{{chineseSummary}}</p>
                <a :href="`https://bgm.tv/subject/${bangumiSubjectId}`"
                    target="_blank" rel="noopener noreferrer" @click.stop>
                    Bangumi で見る
                    <Icon icon="fluent:open-16-regular" width="13px" />
                </a>
            </div>
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
                    <div class="series-episode-list__channel-logo-cell">
                        <div v-if="channel_row.channel_id" class="series-episode-list__channel-logo">
                            <div class="ch-sprite" :chid="channel_row.channel_id">
                                <img loading="lazy"
                                    decoding="async"
                                    :src="`${Utils.api_base_url}/channels/${channel_row.channel_id}/logo`"
                                alt="">
                            </div>
                        </div>
                    </div>
                    <div class="series-episode-list__channel-name">
                        <span>{{channel_row.name}}</span>
                        <small>{{channel_row.episode_label}}</small>
                    </div>
                    <template v-for="(program, slot_index) in channel_row.programs"
                        :key="episode_matrix.slots[slot_index].key">
                        <div v-if="program" class="series-episode-list__episode">
                            <router-link v-ripple class="series-episode-list__episode-link"
                                :to="`/videos/watch/${program.id}`">
                                <img loading="lazy" decoding="async"
                                    :src="`${Utils.api_base_url}/videos/${program.id}/thumbnail`"
                                    alt="">
                                <div class="series-episode-list__episode-label">
                                    <span>{{getEpisodeCaption(program)}}</span>
                                </div>
                            </router-link>
                            <RecordedProgramMenu :program="program" variant="Thumbnail"
                                @deleted="onProgramDeleted" />
                        </div>
                        <div v-else class="series-episode-list__episode-placeholder"
                            :class="{'series-episode-list__episode-placeholder--missing':
                                episode_matrix.slots[slot_index].key.startsWith('episode:')}">
                            <span v-if="episode_matrix.slots[slot_index].key.startsWith('episode:')">未録画</span>
                        </div>
                    </template>
                </template>
            </div>
        </div>
    </div>
</template>
<script lang="ts" setup>

import { computed, onMounted, ref } from 'vue';

import RecordedProgramMenu from '@/components/Videos/RecordedProgramMenu.vue';
import { IRecordedProgram } from '@/services/Videos';
import Videos from '@/services/Videos';
import Utils, { dayjs } from '@/utils';

const props = defineProps<{
    seriesId: number;
    title: string;
    description: string;
    bangumiSubjectId: number | null;
    bangumiSubjectName: string | null;
    bangumiSubjectNameCn: string | null;
    bangumiSubjectSummary: string | null;
    bangumiSubjectImageUrl: string | null;
}>();

interface IEpisodeSlot {
    key: string;
    label: string;
}

interface IChannelRow {
    id: string;
    channel_id: string | null;
    name: string;
    episode_label: string;
    programs: Array<IRecordedProgram | null>;
}

const programs = ref<IRecordedProgram[]>([]);
const total_programs = ref(0);
const is_loading = ref(true);
const episode_number_collator = new Intl.Collator('ja', { numeric: true });

const programSummary = computed(() => props.description.trim());
const bangumiSummary = computed(() => props.bangumiSubjectSummary?.trim() ?? '');
const splitBangumiSummary = computed(() => {
    const summaryParts = bangumiSummary.value.split(/[【[][简簡]介原文[】\]]/, 2);
    return {
        chinese: summaryParts[0]?.trim() ?? '',
        original: summaryParts[1]?.trim() ?? '',
    };
});
const japaneseSummary = computed(() => {
    return splitBangumiSummary.value.original.length >= 12
        ? splitBangumiSummary.value.original
        : programSummary.value;
});
const chineseSummary = computed(() => splitBangumiSummary.value.chinese);

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
    const observedSlots = [...new Map(programs.value.flatMap(program =>
        getEpisodeSlots(program).map(slot => [slot.key, slot] as const),
    )).values()].sort((left, right) => episode_number_collator.compare(left.key, right.key));
    const integerEpisodeNumbers = observedSlots
        .filter(slot => /^episode:\d+$/.test(slot.key))
        .map(slot => Number(slot.key.slice('episode:'.length)));
    const continuousEpisodeSlots = integerEpisodeNumbers.length > 0
        ? Array.from(
            {
                length: Math.max(...integerEpisodeNumbers) - Math.min(...integerEpisodeNumbers) + 1,
            },
            (_, index): IEpisodeSlot => {
                const episodeNumber = Math.min(...integerEpisodeNumbers) + index;
                return {key: `episode:${episodeNumber}`, label: `第${episodeNumber}話`};
            },
        )
        : [];
    const otherSlots = observedSlots.filter(slot => !/^episode:\d+$/.test(slot.key));
    const slots = [...continuousEpisodeSlots, ...otherSlots];

    const groups = new Map<string, {
        id: string;
        channel_id: string | null;
        name: string;
        programs: Map<string, IRecordedProgram>;
    }>();
    for (const program of programs.value) {
        const id = program.channel?.id ?? 'unknown';
        const group = groups.get(id) ?? {
            id,
            channel_id: program.channel?.id ?? null,
            name: program.channel?.name ?? 'チャンネル情報なし',
            programs: new Map<string, IRecordedProgram>(),
        };
        for (const slot of getEpisodeSlots(program)) {
            if (!group.programs.has(slot.key)) group.programs.set(slot.key, program);
        }
        groups.set(id, group);
    }

    const rows = [...groups.values()].map(group => ({
        id: group.id,
        channel_id: group.channel_id,
        name: group.name,
        episode_label: formatEpisodeCoverage(slots, group.programs),
        programs: slots.map(slot => group.programs.get(slot.key) ?? null),
    }));
    return { slots, rows };
});

// 同じ話数の別局録画は数えず、視聴者が「どこまで録れているか」を一目で把握できる表記にする。
const formatEpisodeCoverage = (
    slots: IEpisodeSlot[],
    programsBySlot: Map<string, IRecordedProgram>,
): string => {
    const episodeSlots = slots.filter(slot => slot.key.startsWith('episode:'));
    if (episodeSlots.length === 0) return `${programsBySlot.size}件の録画`;
    const recordedCount = episodeSlots.filter(slot => programsBySlot.has(slot.key)).length;
    const missingCount = episodeSlots.length - recordedCount;
    return missingCount > 0
        ? `${recordedCount}話録画・${missingCount}話未録画`
        : `${recordedCount}話録画`;
};

const seriesCountLabel = computed(() => {
    const episodeSlots = episode_matrix.value.slots.filter(slot => slot.key.startsWith('episode:'));
    if (episodeSlots.length === 0) return `${total_programs.value}件の録画`;
    const latestEpisode = episodeSlots[episodeSlots.length - 1].key.slice('episode:'.length);
    return `第${latestEpisode}話まで`;
});

const getEpisodeCaption = (program: IRecordedProgram): string => {
    return program.subtitle || dayjs(program.start_time).format('YYYY/M/D (dd) HH:mm');
};

// 共通メニューから録画ファイルを削除した場合は、Series 全体を取り直さず表示中の行列だけを更新する。
const onProgramDeleted = (programID: number) => {
    programs.value = programs.value.filter(program => program.id !== programID);
    total_programs.value = Math.max(0, total_programs.value - 1);
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
        align-items: flex-start;
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

    &__titles {
        min-width: 0;
        h3 {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        small {
            display: block;
            margin-top: 2px;
            overflow: hidden;
            color: rgb(var(--v-theme-text-darken-1));
            font-family: 'PingFang SC', 'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif;
            font-size: 12px;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
    }

    &__loading {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(145px, 1fr));
        gap: 8px;
    }

    &__bangumi {
        display: flex;
        gap: 12px;
        margin-bottom: 16px;
        padding: 10px;
        background: rgb(var(--v-theme-background-lighten-2) / 45%);
        border-radius: 7px;
        > img {
            flex: 0 0 auto;
            width: 112px;
            height: 158px;
            object-fit: cover;
            border-radius: 5px;
            @include smartphone-vertical {
                width: 76px;
                height: 108px;
            }
        }
    }

    &__bangumi-profile {
        min-width: 0;
        max-width: 68ch;
        p {
            color: rgb(var(--v-theme-text-darken-1));
            display: -webkit-box;
            margin: 5px 0;
            overflow: hidden;
            font-size: 12px;
            line-height: 1.65;
            -webkit-box-orient: vertical;
            -webkit-line-clamp: 3;
        }
        .series-episode-list__chinese-summary {
            font-family: 'PingFang SC', 'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif;
            opacity: 0.82;
        }
        a {
            display: inline-flex;
            align-items: center;
            gap: 3px;
            color: rgb(var(--v-theme-primary));
            font-size: 12px;
            text-decoration: none;
        }
    }

    &__matrix-scroll {
        overflow-x: auto;
        overscroll-behavior-x: contain;
        -webkit-overflow-scrolling: touch;
    }

    &__matrix {
        display: grid;
        grid-template-columns: 60px 82px repeat(var(--episode-column-count), 170px);
        gap: 8px;
        width: max-content;
        min-width: 100%;
        @include smartphone-vertical {
            grid-template-columns: 52px 56px repeat(var(--episode-column-count), 145px);
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
        grid-column: span 2;
        text-align: left;
    }

    &__channel-logo-cell {
        position: sticky;
        left: 0;
        z-index: 3;
        display: flex;
        align-items: center;
        justify-content: center;
        pointer-events: none;
        background: transparent;
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
        box-shadow: 0 2px 7px rgb(0 0 0 / 42%);
        @include smartphone-vertical {
            --ch-sprite-width: 44;
            --ch-sprite-height: 25;
        }
    }

    &__channel-name {
        display: flex;
        flex-direction: column;
        justify-content: center;
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
        background: rgb(var(--v-theme-background-lighten-2));
    }

    &__episode-link {
        position: absolute;
        inset: 0;
        overflow: hidden;
        color: white;
        text-decoration: none;
        border-radius: inherit;
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
        &--missing {
            display: flex;
            align-items: center;
            justify-content: center;
            color: rgb(var(--v-theme-error-lighten-1));
            background: rgb(var(--v-theme-error) / 7%);
            border-color: rgb(var(--v-theme-error) / 30%);
            span {
                font-size: 11px;
                font-weight: 700;
            }
        }
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

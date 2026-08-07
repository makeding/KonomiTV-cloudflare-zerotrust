import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { createMemoryHistory, createRouter } from 'vue-router';

import RecordedProgramList from '@/components/Videos/RecordedProgramList.vue';

const router = createRouter({
    history: createMemoryHistory(),
    routes: [],
});

// 空メッセージ表示のテストに必要な最小構成で RecordedProgramList をマウントする
// 未解決の Vuetify コンポーネントはスタブへ差し替え、マウント時の警告を抑える
const mountList = (props: Record<string, unknown> = {}) => {
    return mount(RecordedProgramList, {
        props: {
            title: 'テスト',
            programs: [],
            total: 0,
            hideHeader: true,
            hideSort: true,
            showEmptyMessage: true,
            ...props,
        },
        global: {
            plugins: [router],
            // 未解決の Vuetify コンポーネントと ripple ディレクティブの警告を抑える
            directives: { ripple: {} },
            stubs: {
                Icon: true,
                'v-select': true,
                'v-btn': true,
                'v-pagination': true,
            },
        },
    });
};

describe('RecordedProgramList 空メッセージ', () => {

    it('HTML を含む空メッセージがテキストとして表示され、要素や event handler が生成されない', () => {
        const wrapper = mountList({ emptyMessage: '<img src=x onerror=alert(1)><br class=\'d-sm-none\'>INJECTED' });
        const heading = wrapper.find('.recorded-program-list__empty-content h2');
        // メッセージ文字列の中に <br> が含まれていても、要素としては一切生成されない
        expect(heading.findAll('*')).toHaveLength(0);
        expect(heading.text()).toContain('<img src=x onerror=alert(1)>');
        expect(heading.text()).toContain('INJECTED');
    });

    it('行配列のメッセージは行間へ固定の <br> のみを挿入する', () => {
        const wrapper = mountList({
            emptyMessage: ['「<img src=x onerror=alert(1)>」に一致する録画番組は', '見つかりませんでした。'],
        });
        const heading = wrapper.find('.recorded-program-list__empty-content h2');
        // 検索語が <img> などの HTML を含んでもテキスト表示され、要素は固定の <br> のみになる
        const breaks = heading.findAll('br');
        expect(breaks).toHaveLength(1);
        expect(breaks[0].attributes('class')).toBe('d-sm-none');
        expect(heading.findAll('*').every((el) => el.element.tagName === 'BR')).toBe(true);
        expect(heading.findAll('*').every((el) => Object.keys(el.attributes()).every((attr) => !attr.startsWith('on')))).toBe(true);
        expect(heading.text()).toContain('<img src=x onerror=alert(1)>');
    });

    it('補足メッセージも同様にテキスト表示される', () => {
        const wrapper = mountList({
            emptySubMessage: ['別のキーワードで', '<script>alert(1)</script>検索をお試しください。'],
        });
        const submessage = wrapper.find('.recorded-program-list__empty-submessage');
        expect(submessage.findAll('br')).toHaveLength(1);
        expect(submessage.findAll('*').every((el) => el.element.tagName === 'BR')).toBe(true);
        expect(submessage.text()).toContain('<script>alert(1)</script>');
    });
});

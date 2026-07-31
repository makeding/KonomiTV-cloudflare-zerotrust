import DPlayer, { DPlayerType } from 'dplayer';
import {
    AribReceiverHost,
    BroadcastVfsSession,
    ServiceWorkerBroadcastVfs,
} from 'libaribhtml5';

import type {
    AribMediaPlane,
    AribMediaPlaneAdapter,
    AribMediaPlaneUnmountReason,
    ProgramInfo,
    RuntimeWindow,
} from 'libaribhtml5';

import PlayerManager from '@/services/player/PlayerManager';
import usePlayerStore from '@/stores/PlayerStore';
import useSettingsStore from '@/stores/SettingsStore';
import { dayjs } from '@/utils';


type TLVApplicationResource = {
    contextId: number;
    path: string;
    contentType: string;
    data: Uint8Array;
};

type TLVApplicationState = {
    contextId: number;
    applicationType: number;
    organizationId: number;
    applicationId: number;
    controlCode: number;
    entryPath: string;
    transportUrls: string[];
    entryReady: boolean;
};

type TLVBroadcastClock = {
    mediaTimeValue: bigint;
    mediaTimeTimescale: number;
    broadcastTimeValue: bigint;
    broadcastTimeTimescale: number;
};

type TLVEventInfo = DPlayerType.TLVEventInfo;

interface RuntimeHostWindow extends Window {
    __ARIB_HTML5_INSTALL__?: (target: RuntimeWindow) => void;
}

const RECEIVER_KEY_MAP: Record<number, number> = {
    1: 38,
    2: 40,
    3: 37,
    4: 39,
    18: 13,
    19: 461,
    20: 457,
    21: 406,
    22: 403,
    23: 404,
    24: 405,
};

const LEGACY_RECEIVER_INFO_PREFIX = 'KonomiTV-BMLBrowser_nvram_prefix=receiverinfo%2F';

type ReceiverInfo = {
    zipcode: string | null;
    prefecture: number | null;
    regioncode: number | null;
};

type BrowserPseudo = {
    readPersistentArray: (namespace: string, structure: string) => unknown[] | null;
};


/**
 * DPlayer の video を元の 16:9 コンテナから動かさず、データ放送の映像枠だけへ合わせる。
 * MSE 接続済みの video を iframe へ移動すると Chromium が MediaSource を閉じるため、
 * DOM の親子関係は維持したまま位置と大きさだけを更新する。
 */
class DPlayerMediaPlaneAdapter implements AribMediaPlaneAdapter {

    public readonly renderMode = 'external' as const;

    private readonly player: DPlayer;
    private managed_video: HTMLVideoElement | null = null;

    constructor(player: DPlayer) {
        this.player = player;
    }

    public mountMediaPlane(_object: HTMLElement, plane: AribMediaPlane): void {
        this.apply(plane);
    }

    public updateMediaPlane(_object: HTMLElement, plane: AribMediaPlane): void {
        this.apply(plane);
    }

    public unmountMediaPlane(reason: AribMediaPlaneUnmountReason): void {
        // アプリ終了時と Manager 破棄時は、DPlayer 本来の CSS レイアウトへ完全に戻す。
        if (reason === 'application-exit' || reason === 'host-destroy') {
            this.restoreNormalLayout();
            return;
        }

        // ページ遷移中や映像 object が消えた間は、直前の映像が全面に残らないよう隠す。
        if (this.managed_video !== null) this.managed_video.style.visibility = 'hidden';
    }

    private apply(plane: AribMediaPlane): void {
        const video = this.player.video;
        if (this.managed_video !== null && this.managed_video !== video) this.restoreNormalLayout();
        this.managed_video = video;

        const percent = (value: number, extent: number): string => `${value / extent * 100}%`;
        Object.assign(video.style, {
            position: 'absolute',
            left: percent(plane.x, plane.screenWidth),
            top: percent(plane.y, plane.screenHeight),
            width: percent(plane.width, plane.screenWidth),
            height: percent(plane.height, plane.screenHeight),
            maxWidth: 'none',
            maxHeight: 'none',
            display: 'block',
            visibility: plane.visible ? 'visible' : 'hidden',
            objectFit: 'contain',
            background: '#000',
            pointerEvents: 'none',
            zIndex: '1',
        });
    }

    private restoreNormalLayout(): void {
        if (this.managed_video === null) return;
        for (const property of [
            'position', 'left', 'top', 'width', 'height', 'max-width', 'max-height',
            'display', 'visibility', 'object-fit', 'background', 'pointer-events', 'z-index',
        ]) {
            this.managed_video.style.removeProperty(property);
        }
        this.managed_video = null;
    }
}


/**
 * MMT/TLV 上の ARIB STD-B62 HTML5 データ放送を HonomiTV の UI へ接続する。
 * TLV の解析と再生は DPlayer、iframe/VFS/リモコンはアプリ側が所有する。
 */
class TLVDataBroadcastingManager implements PlayerManager {

    public readonly restart_required_when_quality_switched = true;

    private readonly player: DPlayer;
    private readonly playback_mode: 'Live' | 'Video';
    private readonly remocon_element: HTMLElement;
    private readonly remocon_data_broadcasting_element: HTMLElement;
    private viewport: HTMLDivElement | null = null;
    private iframe: HTMLIFrameElement | null = null;
    private host: AribReceiverHost | null = null;
    private vfs: BroadcastVfsSession | null = null;
    private vfs_backend: ServiceWorkerBroadcastVfs | null = null;
    private remocon_abort_controller: AbortController | null = null;
    private previous_installer?: (target: RuntimeWindow) => void;
    private runtime_installer?: (target: RuntimeWindow) => void;
    private readonly resource_revisions = new Map<string, number>();
    private readonly program_events = new Map<number, TLVEventInfo>();
    private session_generation = 0;
    private ready_context_id: number | null = null;
    private ready_entry: string | null = null;
    private visible = false;
    private previous_remocon_display: boolean | null = null;

    constructor(player: DPlayer, playback_mode: 'Live' | 'Video') {
        this.player = player;
        this.playback_mode = playback_mode;
        this.remocon_element = document.querySelector('.watch-panel__remocon')!;
        this.remocon_data_broadcasting_element = this.remocon_element.querySelector('.remote-control-data-broadcasting')!;
    }

    public async init(): Promise<void> {
        if (this.player.quality?.type !== 'tlv' || useSettingsStore().settings.tv_show_data_broadcasting === false) {
            this.toggleRemoconLoading(false);
            this.toggleRemoconEnabled(false);
            return;
        }

        // Worker 自身を scope 配下へ配置しているため Service-Worker-Allowed ヘッダーは不要。
        this.vfs_backend = new ServiceWorkerBroadcastVfs({
            workerUrl: '/data-broadcast/arib-vfs-sw.js',
            baseUrl: '/data-broadcast/',
        });
        this.vfs = new BroadcastVfsSession(this.vfs_backend, {
            onError: error => {
                console.error('[TLVDataBroadcastingManager] VFS operation failed.', error);
                this.player.notice('データ放送リソースの保存に失敗しました。', 3000, undefined, '#FF6F6A');
            },
        });

        this.viewport = document.createElement('div');
        this.viewport.className = 'dplayer-tlv-data-broadcast-viewport';
        Object.assign(this.viewport.style, {
            position: 'absolute',
            inset: '0',
            overflow: 'hidden',
            background: 'transparent',
            opacity: '0',
            pointerEvents: 'none',
            zIndex: '0',
        });

        this.iframe = document.createElement('iframe');
        this.iframe.className = 'dplayer-tlv-data-broadcast';
        this.iframe.setAttribute('sandbox', 'allow-scripts allow-same-origin');
        this.iframe.setAttribute('aria-hidden', 'true');
        Object.assign(this.iframe.style, {
            position: 'absolute',
            inset: '0',
            width: '100%',
            height: '100%',
            border: '0',
            display: 'none',
            transformOrigin: '0 0',
        });
        this.viewport.append(this.iframe);
        // iframe、video、字幕面を同じ 16:9 コンテナの兄弟にして、座標系を一つに固定する。
        // video 自体は DPlayer が生成した直系子要素のままなので、通常再生の寸法を失わない。
        this.player.template.videoWrapAspect.prepend(this.viewport);

        const receiver_info = this.readReceiverInfo();
        this.host = new AribReceiverHost({
            iframe: this.iframe,
            viewport: this.viewport,
            broadcastBaseUrl: '/data-broadcast/',
            allowExternalNetwork: useSettingsStore().settings.enable_internet_access_from_data_broadcasting,
            systemInformation: {
                zipcode: receiver_info.zipcode,
                prefecture: receiver_info.prefecture,
                regioncode: receiver_info.regioncode,
            },
            mediaPlaneAdapter: new DPlayerMediaPlaneAdapter(this.player),
            onLifecycle: event => {
                if (event.type === 'installed') {
                    this.visible = true;
                    this.lockPanelForApplication();
                    if (this.viewport !== null) this.viewport.style.opacity = '1';
                    this.iframe?.setAttribute('aria-hidden', 'false');
                } else if (event.type === 'exited') {
                    this.visible = false;
                    this.unlockPanelForApplication();
                    if (this.viewport !== null) this.viewport.style.opacity = '0';
                    if (this.iframe !== null) {
                        this.iframe.style.display = 'none';
                        this.iframe.setAttribute('aria-hidden', 'true');
                    }
                } else if (event.type === 'error') {
                    console.error('[TLVDataBroadcastingManager] Receiver runtime failed.', event.message);
                }
            },
        });
        const host_window = window as RuntimeHostWindow;
        this.previous_installer = host_window.__ARIB_HTML5_INSTALL__;
        this.runtime_installer = target => {
            this.host?.installRuntime(target);
            this.installReceiverInfo(target, receiver_info);
            this.installNetworkProxy(target);
        };
        host_window.__ARIB_HTML5_INSTALL__ = this.runtime_installer;

        this.player.on('tlv_application_resources_reset', this.handleResourcesReset);
        this.player.on('tlv_application_resource', this.handleApplicationResource);
        this.player.on('tlv_application_state', this.handleApplicationState);
        this.player.on('tlv_broadcast_clock', this.handleBroadcastClock);
        this.player.on('tlv_event_info', this.handleEventInfo);
        this.initRemoconButtons();
        await this.beginSession();
        console.log('[TLVDataBroadcastingManager] Initialized.');
    }

    public async destroy(): Promise<void> {
        this.player.off('tlv_application_resources_reset', this.handleResourcesReset);
        this.player.off('tlv_application_resource', this.handleApplicationResource);
        this.player.off('tlv_application_state', this.handleApplicationState);
        this.player.off('tlv_broadcast_clock', this.handleBroadcastClock);
        this.player.off('tlv_event_info', this.handleEventInfo);
        this.remocon_abort_controller?.abort();
        this.remocon_abort_controller = null;
        this.session_generation += 1;
        this.exitApplication();
        this.unlockPanelForApplication();
        this.host?.destroy();
        this.host = null;
        this.viewport?.remove();
        this.viewport = null;
        this.iframe = null;
        await this.vfs_backend?.reset().catch(error => {
            console.error('[TLVDataBroadcastingManager] VFS reset failed.', error);
        });
        this.vfs = null;
        this.vfs_backend = null;
        this.resource_revisions.clear();
        this.program_events.clear();
        this.toggleRemoconLoading(true);
        this.toggleRemoconEnabled(false);
        const host_window = window as RuntimeHostWindow;
        // 古い PlayerManager の遅延 destroy が、新しいインスタンスの installer を消さないようにする。
        if (host_window.__ARIB_HTML5_INSTALL__ === this.runtime_installer) {
            if (this.previous_installer !== undefined) host_window.__ARIB_HTML5_INSTALL__ = this.previous_installer;
            else delete host_window.__ARIB_HTML5_INSTALL__;
        }
        this.runtime_installer = undefined;
        console.log('[TLVDataBroadcastingManager] Destroyed.');
    }

    private async beginSession(): Promise<void> {
        const generation = ++this.session_generation;
        this.resource_revisions.clear();
        this.program_events.clear();
        this.ready_context_id = null;
        this.ready_entry = null;
        this.host?.clearBroadcastClock();
        this.host?.clearProgramInfo();
        this.exitApplication();
        this.toggleRemoconLoading(true);
        this.toggleRemoconEnabled(false);
        try {
            await this.vfs?.beginSession();
        } catch (error) {
            if (generation !== this.session_generation) return;
            console.error('[TLVDataBroadcastingManager] Failed to begin VFS session.', error);
            this.toggleRemoconLoading(false);
        }
    }

    private readonly handleResourcesReset = (): void => {
        void this.beginSession();
    };

    private readonly handleApplicationResource = (detail?: Event | TLVApplicationResource): void => {
        const resource = detail as TLVApplicationResource;
        if (!resource || this.vfs === null) return;
        const content_type = this.normalizeResourceContentType(resource.path, resource.contentType);
        const revision = this.vfs.enqueue({
            path: resource.path,
            // 放送側が application/xhtml+xml 等を指定しても、VFS Worker が HTML/CSS を
            // 確実に準備し runtime bootstrap と放送ルートの URL 変換を適用できるようにする。
            contentType: content_type,
            // NHK の二段階ページでも parent の階層に依存せず、放送側スクリプトより前に
            // receiverDevice を同期導入する。Worker 側の bootstrap は冪等なので併存できる。
            data: content_type.startsWith('text/html') ? this.injectRuntimeBootstrap(resource.data) : resource.data,
        });
        this.resource_revisions.set(`${resource.contextId}:${resource.path}`, revision);
    };

    private readonly handleApplicationState = (detail?: Event | TLVApplicationState): void => {
        const state = detail as TLVApplicationState;
        // d ボタンで起動すべきなのは PRESENT application (control_code=0x02)。
        // AUTOSTART application (0x01) は透明な常駐ページなので、手動起動の入口には使わない。
        if (!state?.entryReady || state.controlCode !== 0x02) return;
        const entry = this.resolveApplicationEntry(state);
        if (entry === null) return;
        this.ready_context_id = state.contextId;
        this.ready_entry = entry;
        console.log('[TLVDataBroadcastingManager] PRESENT application is ready.', {
            applicationId: state.applicationId,
            organizationId: state.organizationId,
            entry,
        });
        this.toggleRemoconLoading(false);
        this.toggleRemoconEnabled(true);
    };

    private readonly handleBroadcastClock = (detail?: Event | TLVBroadcastClock): void => {
        const clock = detail as TLVBroadcastClock;
        if (!clock || this.host === null || !(clock.broadcastTimeTimescale > 0) || !(clock.mediaTimeTimescale > 0)) return;
        const epoch_milliseconds = Number(clock.broadcastTimeValue) * 1000 / clock.broadcastTimeTimescale - 2208988800 * 1000;
        const media_time_seconds = Number(clock.mediaTimeValue) / clock.mediaTimeTimescale;
        if (!Number.isFinite(epoch_milliseconds) || !Number.isFinite(media_time_seconds)) return;
        this.host.setBroadcastClock({
            epochMilliseconds: epoch_milliseconds,
            mediaTimeSeconds: media_time_seconds,
            currentMediaTimeSeconds: () => this.player.video.currentTime,
        });
        this.updateProgramInfo();
    };

    private readonly handleEventInfo = (detail?: Event | TLVEventInfo): void => {
        const event = detail as TLVEventInfo;
        if (!event || event.tableId !== 0x8b || event.currentNext === false || ![0, 1].includes(event.sectionNumber)) return;
        this.program_events.set(event.sectionNumber, event);
        this.updateProgramInfo();
    };

    private updateProgramInfo(): void {
        const present = this.program_events.get(0);
        if (present === undefined || present.startTimeUnixMilliseconds === null || present.durationSeconds === null) return;
        const program_info: ProgramInfo = {
            original_network_id: present.originalNetworkId,
            transport_stream_id: present.tlvStreamId,
            service_id: present.serviceId,
            event_id: present.eventId,
            name: present.title,
            event_name: present.title,
            start_time: dayjs(present.startTimeUnixMilliseconds).toDate(),
            duration: present.durationSeconds * 1000,
            desc: present.description,
            event_text: present.description,
            running_status: present.runningStatus,
            free_ca_mode: present.freeCaMode,
        };
        const following = this.program_events.get(1);
        if (following !== undefined && following.startTimeUnixMilliseconds !== null && following.durationSeconds !== null) {
            Object.assign(program_info, {
                f_event_id: following.eventId,
                f_name: following.title,
                f_start_time: dayjs(following.startTimeUnixMilliseconds).toDate(),
                f_duration: following.durationSeconds * 1000,
                f_desc: following.description,
            });
        }
        this.host?.setProgramInfo(program_info);
    }

    private initRemoconButtons(): void {
        this.remocon_abort_controller = new AbortController();
        this.remocon_element.querySelectorAll<HTMLButtonElement>('button').forEach(button => {
            button.addEventListener('click', () => {
                const key_code = Number(button.dataset.aribKeyCode);
                const remocon_id = button.dataset.remoconId !== undefined ? Number(button.dataset.remoconId) : null;

                // ライブの数字キーはデータアプリ表示中だけアプリへ渡し、通常時は既存の換台 UI に任せる。
                if (remocon_id !== null && (this.playback_mode === 'Live' && this.visible === false)) return;
                if (key_code === 20 && this.visible === false) {
                    void this.enterApplication();
                    return;
                }
                const receiver_key = remocon_id !== null ? this.resolveNumberKey(remocon_id) : RECEIVER_KEY_MAP[key_code];
                if (receiver_key !== undefined) this.host?.dispatchKey(receiver_key);
            }, {signal: this.remocon_abort_controller?.signal});
        });
    }

    private async enterApplication(): Promise<void> {
        if (this.ready_context_id === null || this.ready_entry === null || this.vfs === null || this.iframe === null) return;
        const generation = this.session_generation;
        const entry = this.ready_entry;
        const revision = this.resource_revisions.get(`${this.ready_context_id}:${entry}`);
        if (revision === undefined) return;
        try {
            await this.vfs.waitFor(revision);
            await this.vfs.ensure(entry, revision);
            if (generation !== this.session_generation) return;
            const base_url = new URL('/data-broadcast/', location.origin);
            const application_url = new URL(entry.replace(/^\/+/, ''), base_url);
            if (application_url.origin !== location.origin || !application_url.pathname.startsWith(base_url.pathname)) {
                throw new Error(`Application entry escaped receiver scope: ${entry}`);
            }
            this.iframe.style.display = 'block';
            if (this.viewport !== null) this.viewport.style.opacity = '0';
            this.lockPanelForApplication();
            this.host?.loadApplication(application_url.href);
        } catch (error) {
            this.unlockPanelForApplication();
            console.error('[TLVDataBroadcastingManager] Failed to enter application.', error);
            this.player.notice('データ放送を起動できませんでした。', 3000, undefined, '#FF6F6A');
        }
    }

    private exitApplication(): void {
        if (this.visible) this.host?.exitApplication();
        this.visible = false;
        this.unlockPanelForApplication();
        if (this.viewport !== null) this.viewport.style.opacity = '0';
        if (this.iframe !== null) this.iframe.style.display = 'none';
    }

    private lockPanelForApplication(): void {
        const player_store = usePlayerStore();
        if (this.previous_remocon_display === null) this.previous_remocon_display = player_store.is_remocon_display;
        player_store.is_data_broadcasting_display = true;
        player_store.is_remocon_display = true;
    }

    private unlockPanelForApplication(): void {
        const player_store = usePlayerStore();
        player_store.is_data_broadcasting_display = false;
        if (this.previous_remocon_display !== null) player_store.is_remocon_display = this.previous_remocon_display;
        this.previous_remocon_display = null;
    }

    private resolveNumberKey(remocon_id: number): number | undefined {
        if (remocon_id >= 1 && remocon_id <= 9) return 48 + remocon_id;
        if (remocon_id === 10) return 48;
        return undefined;
    }

    private resolveApplicationEntry(state: TLVApplicationState): string | null {
        const normalizePath = (path: string): string | null => {
            const parts = path.split('/').filter(part => part !== '' && part !== '.');
            if (parts.some(part => part === '..')) return null;
            return parts.join('/');
        };
        const entry_path = normalizePath(state.entryPath);
        if (entry_path === null) return null;

        // entryPath 単体と、transport_protocol_descriptor の base URL を付けた候補を
        // tlvdemux と同じ順序で照合し、この application 自身の起動文書を選ぶ。
        const candidates = [entry_path];
        for (const transport_url of state.transportUrls) {
            if (transport_url.includes('://')) continue;
            const transport_path = normalizePath(transport_url);
            if (transport_path !== null) candidates.push([transport_path, entry_path].filter(Boolean).join('/'));
        }
        return candidates.find(candidate => this.resource_revisions.has(`${state.contextId}:${candidate}`)) ?? null;
    }

    private normalizeResourceContentType(path: string, content_type: string): string {
        const pathname = path.split(/[?#]/, 1)[0].toLowerCase();
        if (pathname.endsWith('.html') || pathname.endsWith('.htm')) return 'text/html; charset=utf-8';
        if (pathname.endsWith('.css')) return 'text/css; charset=utf-8';
        return content_type;
    }

    private injectRuntimeBootstrap(data: Uint8Array): Uint8Array {
        const source = new TextDecoder().decode(data);
        const bootstrap = '<script>top.__ARIB_HTML5_INSTALL__?.(window)</script>';
        const head = /<head(?:\s[^>]*)?>/i.exec(source);
        const prepared = head === null ? `${bootstrap}${source}` :
            `${source.slice(0, head.index + head[0].length)}${bootstrap}${source.slice(head.index + head[0].length)}`;
        return new TextEncoder().encode(prepared);
    }

    private readReceiverInfo(): ReceiverInfo {
        const decode = (name: string): string | null => {
            const value = localStorage.getItem(`${LEGACY_RECEIVER_INFO_PREFIX}${name}`);
            if (value === null) return null;
            try {
                return window.atob(value);
            } catch {
                return null;
            }
        };
        const zipcode = decode('zipcode');
        const prefecture_raw = decode('prefecture');
        const regioncode_raw = decode('regioncode');
        return {
            zipcode: zipcode?.match(/^\d{7}$/) ? zipcode : null,
            prefecture: prefecture_raw?.length === 1 ? prefecture_raw.charCodeAt(0) : null,
            regioncode: regioncode_raw?.length === 2 ?
                (regioncode_raw.charCodeAt(0) << 8) | regioncode_raw.charCodeAt(1) : null,
        };
    }

    private installReceiverInfo(target: RuntimeWindow, receiver_info: ReceiverInfo): void {
        const navigator = target.navigator as Navigator & {
            bmlCompat?: {browserPseudo?: BrowserPseudo};
        };
        const browser_pseudo = navigator.bmlCompat?.browserPseudo;
        if (browser_pseudo === undefined) return;
        const original_read = browser_pseudo.readPersistentArray.bind(browser_pseudo);
        browser_pseudo.readPersistentArray = (namespace, structure) => {
            const stored = original_read(namespace, structure);
            if (stored !== null || !namespace.toLowerCase().includes('receiverinfo')) return stored;
            return structure.split(',').map(field => {
                const key = field.trim().toLowerCase() as keyof ReceiverInfo;
                return key in receiver_info ? receiver_info[key] : null;
            });
        };
    }

    private installNetworkProxy(target: RuntimeWindow): void {
        if (useSettingsStore().settings.enable_internet_access_from_data_broadcasting === false) return;

        // 許可時も放送アプリからインターネットへ直結させず、KonomiTV の既存プロキシだけを通す。
        // /api は本番では同一 origin、Vite 開発時は vite.config.mts の proxy が 7000 番へ転送する。
        const proxyUrl = (value: string): string | null => {
            let url: URL;
            try {
                url = new URL(value, target.location.href);
            } catch {
                return null;
            }
            if (!['http:', 'https:'].includes(url.protocol) || url.origin === target.location.origin) return null;
            return new URL(`/api/data-broadcasting/request/${url.href}`, target.location.origin).href;
        };

        const original_fetch = target.fetch.bind(target);
        target.fetch = (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
            const is_request = input instanceof target.Request;
            const request_url = is_request ? (input as Request).url : String(input);
            const proxied_url = proxyUrl(request_url);
            if (proxied_url === null) return original_fetch(input, init);
            const proxied_input = is_request ? new target.Request(proxied_url, input as Request) : proxied_url;
            return original_fetch(proxied_input, init);
        };

        const original_open = target.XMLHttpRequest.prototype.open;
        target.XMLHttpRequest.prototype.open = function(this: XMLHttpRequest, method: string, url: string | URL, ...args: unknown[]): void {
            const proxied_url = proxyUrl(String(url));
            Reflect.apply(original_open, this, [method, proxied_url ?? url, ...args]);
        } as typeof target.XMLHttpRequest.prototype.open;

        if (typeof target.navigator.sendBeacon === 'function') {
            const original_send_beacon = target.navigator.sendBeacon.bind(target.navigator);
            Object.defineProperty(target.navigator, 'sendBeacon', {
                configurable: true,
                value: (url: string | URL, data?: BodyInit | null): boolean =>
                    original_send_beacon(proxyUrl(String(url)) ?? url, data),
            });
        }
    }

    private toggleRemoconLoading(loading: boolean): void {
        this.remocon_data_broadcasting_element.classList.toggle('remote-control-data-broadcasting--loading', loading);
    }

    private toggleRemoconEnabled(enabled: boolean): void {
        this.remocon_data_broadcasting_element.classList.toggle('remote-control-data-broadcasting--disabled', !enabled);
    }
}

export default TLVDataBroadcastingManager;

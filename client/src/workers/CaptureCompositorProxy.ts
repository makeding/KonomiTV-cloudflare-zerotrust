
import * as Comlink from 'comlink';

import { ICaptureCompositorConstructor } from '@/workers/CaptureCompositor';


// CaptureCompositor を Web Worker 上で動作させるためのラッパー
// Comlink を経由し、Web Worker とメインスレッド間でオブジェクトをやり取りする
// ラップ元と同じファイルに定義すると Webpack から Circler Dependency として警告されブラウザの挙動が不安定になるため、別ファイルに定義している
// vite-plugin-comlink の ComlinkWorker は Worker module 全体を自動で expose するが、CaptureCompositor.ts は
// コンストラクタ自体を Comlink.expose() している。両方を併用すると同じ RPC に二重応答し、空の module 側が
// undefined を返して `Cannot read properties of undefined (reading 'apply')` になるため、通常の Vite Worker を使う。
const worker = new Worker(new URL('./CaptureCompositor', import.meta.url), {type: 'module'});
const CaptureCompositorProxy = Comlink.wrap<ICaptureCompositorConstructor>(worker);
export default CaptureCompositorProxy;

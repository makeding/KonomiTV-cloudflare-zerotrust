// Vite の Comlink プラグインがビルド時に注入する constructor を、単体テストの import 時だけ代替する。
(globalThis as unknown as {ComlinkWorker: new (...args: unknown[]) => object}).ComlinkWorker = class {};

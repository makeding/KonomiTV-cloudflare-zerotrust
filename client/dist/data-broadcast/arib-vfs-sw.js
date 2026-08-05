(function() {
  "use strict";
  function deferRomSoundMarkup(source) {
    return source.replace(
      /\s+src\s*=\s*(?:(["'])(romsound:\/\/\d+)\1|(romsound:\/\/\d+)(?=[\s/>]))/gi,
      (_match, _quote, quoted, bare) => ` data-arib-romsound="${quoted ?? bare}"`
    );
  }
  const DEFAULT_RECEIVER_DEVICE_IDENTIFIER = "4194c4ae4730";
  function createRuntimeBootstrap(scopePath = "/data-broadcast/") {
    const basePath = normalizeBasePath(scopePath);
    return `<script>
(function installAribHtml5Runtime(attempt) {
  var install
  try {
    install = parent && parent.__ARIB_HTML5_INSTALL__
  } catch (error) {
    install = null
  }
  if (typeof install === 'function') {
    try {
      install(window)
      return
    } catch (error) {
      console.error('ARIB HTML5 runtime installation failed', error)
    }
  }
  if (!navigator.receiverDevice) {
    Object.defineProperty(navigator, 'receiverDevice', {
      configurable: true,
      enumerable: true,
      value: {
        getSystemInformation: function () {
          return {
            browsername: 'unknown',
            browserversion: 'unknown',
            makerid: 'unknown',
            modelname: 'unknown',
            baseurl: new URL(${JSON.stringify(basePath)}, location.origin).href
          }
        },
        getDeviceIdentifier: function (kind, callback) {
          queueMicrotask(function () { callback(${JSON.stringify(DEFAULT_RECEIVER_DEVICE_IDENTIFIER)}) })
        }
      }
    })
  }
  if (attempt < 100) {
    setTimeout(function () { installAribHtml5Runtime(attempt + 1) }, 50)
  }
})(0)
<\/script>`;
  }
  function normalizeBasePath(value) {
    const base = value || "/data-broadcast/";
    return `/${base.replace(/^\/+|\/+$/g, "")}/`;
  }
  function rewriteBroadcastObjectMarkup(source) {
    return source.replace(/<object\b[^>]*>/gi, (tag) => {
      const broadcast = /\btype\s*=\s*(?:["']video\/x-arib2-broadcast["']|video\/x-arib2-broadcast)(?:\s|\/?>)/i.test(tag);
      if (!broadcast) return tag;
      return tag.replace(
        /\s+type\s*=\s*(?:["']video\/x-arib2-broadcast["']|video\/x-arib2-broadcast)/i,
        ' data-arib-type="video/x-arib2-broadcast"'
      ).replace(/\s+data\s*=\s*(["'])(.*?)\1/i, " data-arib-data=$1$2$1");
    });
  }
  function receiverPath(path, base, scope) {
    if (path.startsWith(scope)) return path;
    const mount = base.startsWith(scope) ? base.slice(scope.length).replace(/^\/+|\/+$/g, "") : "";
    const requested = path.replace(/^\/+/, "");
    if (mount && (requested === mount || requested.startsWith(`${mount}/`))) {
      return `${scope}${requested}`;
    }
    return `${base}${requested}`;
  }
  function prefixBroadcastRootAttributes(source, basePath, scopePath) {
    const base = normalizeBasePath(basePath);
    const scope = normalizeBasePath(scopePath ?? basePath);
    return source.replace(
      /(\b(?:href|src|action|poster)\s*=\s*)(?:(['"])(\/[^/][^"']*)\2|(\/[^\s>]*))/gi,
      (match, name, quote, quotedPath, barePath) => {
        const path = quotedPath ?? barePath;
        if (!path || path.startsWith(base)) return match;
        const value = receiverPath(path, base, scope);
        return quote ? `${name}${quote}${value}${quote}` : `${name}${value}`;
      }
    );
  }
  function prepareBroadcastStylesheet(source, options = {}) {
    const base = normalizeBasePath(options.basePath);
    const scope = normalizeBasePath(options.scopePath ?? options.basePath);
    return source.replace(
      /url\(\s*(["']?)(\/[^/)][^)]*)\1\s*\)/gi,
      (match, quote, path) => path.startsWith(base) ? match : `url(${quote}${receiverPath(path, base, scope)}${quote})`
    ).replace(
      /(@import\s+)(["'])(\/[^/][^"']*)\2/gi,
      (match, keyword, quote, path) => path.startsWith(base) ? match : `${keyword}${quote}${receiverPath(path, base, scope)}${quote}`
    );
  }
  function prepareBroadcastHtml(source, options = {}) {
    const prepared = prefixBroadcastRootAttributes(
      deferRomSoundMarkup(rewriteBroadcastObjectMarkup(source)),
      options.basePath,
      options.scopePath
    );
    if (!options.bootstrap) return prepared;
    const head = /<head(?:\s[^>]*)?>/i.exec(prepared);
    if (!head) return `${options.bootstrap}${prepared}`;
    const offset = head.index + head[0].length;
    return `${prepared.slice(0, offset)}${options.bootstrap}${prepared.slice(offset)}`;
  }
  const scopeUrl = new URL(self.registration.scope);
  const VFS_PREFIX = scopeUrl.pathname.endsWith("/") ? scopeUrl.pathname : `${scopeUrl.pathname}/`;
  const CACHE_NAME = `libaribhtml5-arib-vfs-v1:${VFS_PREFIX}`;
  const CACHE_RESOURCE_PATH = `${VFS_PREFIX}.libaribhtml5-arib-vfs-resource`;
  const CACHE_SESSION_PATH = `${VFS_PREFIX}.libaribhtml5-arib-vfs-session`;
  const RUNTIME_BOOTSTRAP = createRuntimeBootstrap(VFS_PREFIX);
  const resources = /* @__PURE__ */ new Map();
  const waiters = /* @__PURE__ */ new Map();
  let enabled = false;
  let uniqueBasenameFallback = false;
  let restorePromise = null;
  function cacheRequest(path) {
    const url = new URL(CACHE_RESOURCE_PATH, self.location.origin);
    url.searchParams.set("path", path);
    return new Request(url.href);
  }
  function sessionRequest() {
    return new Request(new URL(CACHE_SESSION_PATH, self.location.origin).href);
  }
  async function beginPersistentSession() {
    await caches.delete(CACHE_NAME);
    const cache = await caches.open(CACHE_NAME);
    await cache.put(sessionRequest(), new Response("", {
      headers: {
        "X-Arib-VFS-Session": "active",
        "X-Arib-VFS-Unique-Basename-Fallback": uniqueBasenameFallback ? "1" : "0"
      }
    }));
    restorePromise = null;
  }
  async function persistResource(path, resource) {
    const cache = await caches.open(CACHE_NAME);
    await cache.put(cacheRequest(path), new Response(resource.data.slice(), {
      headers: {
        "Content-Type": resource.contentType || "application/octet-stream",
        "X-Arib-VFS-Path": path
      }
    }));
  }
  async function restorePersistentResources() {
    if (enabled) return true;
    if (restorePromise) return restorePromise;
    restorePromise = (async () => {
      const cache = await caches.open(CACHE_NAME);
      const session = await cache.match(sessionRequest());
      if (!session) return false;
      uniqueBasenameFallback = session.headers.get("X-Arib-VFS-Unique-Basename-Fallback") === "1";
      for (const request of await cache.keys()) {
        const response = await cache.match(request);
        const path = response?.headers.get("X-Arib-VFS-Path");
        if (!path) continue;
        resources.set(path, {
          data: new Uint8Array(await response.arrayBuffer()),
          contentType: response.headers.get("Content-Type") || ""
        });
      }
      enabled = true;
      return true;
    })();
    try {
      return await restorePromise;
    } finally {
      restorePromise = null;
    }
  }
  function normalizePath(value) {
    let pathname;
    try {
      pathname = decodeURIComponent(new URL(String(value), self.location.origin).pathname);
    } catch {
      return null;
    }
    if (pathname.startsWith(VFS_PREFIX)) pathname = pathname.slice(VFS_PREFIX.length);
    const parts = pathname.split("/").filter(Boolean);
    if (!parts.length || parts.some((part) => part === "." || part === "..")) return null;
    return parts.join("/");
  }
  function uniqueBasenameMatch(path) {
    if (!uniqueBasenameFallback) return null;
    const slash = path.lastIndexOf("/");
    const basename = slash >= 0 ? path.slice(slash + 1) : path;
    if (!basename) return null;
    let match = null;
    for (const candidate of resources.keys()) {
      if (candidate !== basename && !candidate.endsWith(`/${basename}`)) continue;
      if (match !== null) return null;
      match = candidate;
    }
    return match;
  }
  function hasBroadcastRoot(path) {
    const slash = path.indexOf("/");
    const root = slash < 0 ? path : path.slice(0, slash);
    for (const candidate of resources.keys()) {
      if (candidate === root || candidate.startsWith(`${root}/`)) return true;
    }
    return false;
  }
  function hasResourceCandidate(value) {
    const path = normalizePath(value);
    return Boolean(path && (resources.has(path) || hasBroadcastRoot(path) || uniqueBasenameMatch(path) !== null));
  }
  function contentType(path, supplied) {
    if (supplied) return supplied;
    const extension = path.slice(path.lastIndexOf(".")).toLowerCase();
    return (/* @__PURE__ */ new Map([
      [".html", "text/html; charset=utf-8"],
      [".htm", "text/html; charset=utf-8"],
      [".css", "text/css; charset=utf-8"],
      [".js", "text/javascript; charset=utf-8"],
      [".json", "application/json; charset=utf-8"],
      [".svg", "image/svg+xml"],
      [".png", "image/png"],
      [".jpg", "image/jpeg"],
      [".jpeg", "image/jpeg"],
      [".gif", "image/gif"],
      [".webp", "image/webp"],
      [".woff", "font/woff"],
      [".woff2", "font/woff2"]
    ])).get(extension) || "application/octet-stream";
  }
  function broadcastRootPath(path) {
    const separator = path.indexOf("/");
    return separator <= 0 ? VFS_PREFIX : `${VFS_PREFIX}${path.slice(0, separator)}/`;
  }
  function wake(path, resource) {
    const exact = waiters.get(path);
    if (exact) {
      waiters.delete(path);
      for (const resolve of exact) resolve({ path, resource });
    }
    if (!uniqueBasenameFallback) return;
    for (const [requestedPath, pending] of [...waiters]) {
      const fallback = uniqueBasenameMatch(requestedPath);
      if (!fallback) continue;
      const fallbackResource = resources.get(fallback);
      if (!fallbackResource) continue;
      waiters.delete(requestedPath);
      for (const resolve of pending) resolve({ path: fallback, resource: fallbackResource });
    }
  }
  function waitFor(path, timeout = 3e4) {
    const current = resources.get(path);
    if (current) return Promise.resolve({ path, resource: current });
    const fallback = uniqueBasenameMatch(path);
    if (fallback) return Promise.resolve({ path: fallback, resource: resources.get(fallback) });
    return new Promise((resolve) => {
      const pending = waiters.get(path) || /* @__PURE__ */ new Set();
      pending.add(resolve);
      waiters.set(path, pending);
      setTimeout(() => {
        pending.delete(resolve);
        if (!pending.size) waiters.delete(path);
        resolve(null);
      }, timeout);
    });
  }
  async function hasAvailableResource(value) {
    await restorePersistentResources();
    const path = normalizePath(`/${value || ""}`);
    return Boolean(enabled && path && resources.has(path));
  }

  // location.href への直接代入は Fetch / XHR の差し替えでは捕捉できないため、
  // 許可ホスト上の文書も VFS Worker の scope 内に写像して receiver runtime を維持する。
  const EXTERNAL_PROXY_PREFIX = VFS_PREFIX + ".external/";
  const EXTERNAL_PROXY_ALLOWED_HOSTS = new Set(["4kdata-p.qvc.jp","api.qvc.jp","api.nhk.or.jp","beacon.nhk.jp","img.nhk.jp","nhk.jp","qvc.jp","qvc.scene7.com","shv.nhk.jp","tv-stream.nhk.jp","www.nhk-cs.jp","www.nhk.or.jp"]);
  function externalProxyRoot(scheme, hostname) {
    return EXTERNAL_PROXY_PREFIX + scheme + "/" + hostname + "/";
  }
  function rewriteExternalProxyUrls(source) {
    for (const hostname of EXTERNAL_PROXY_ALLOWED_HOSTS) {
      const escapedHostname = hostname.replaceAll(".", "\\.");
      const pattern = new RegExp("(?:https?:)?//" + escapedHostname + "(?:/|(?=[?#\\\"'\\\\s]|$))", "gi");
      source = source.replace(pattern, value => {
        const scheme = value.toLowerCase().startsWith("http:") ? "http" : "https";
        return externalProxyRoot(scheme, hostname);
      });
    }
    return source;
  }
  function resolveExternalProxyUrl(url) {
    if (!url.pathname.startsWith(EXTERNAL_PROXY_PREFIX)) return null;
    const relativePath = url.pathname.slice(EXTERNAL_PROXY_PREFIX.length);
    const separator = relativePath.indexOf("/");
    if (separator <= 0) return null;
    const scheme = relativePath.slice(0, separator);
    const hostAndPath = relativePath.slice(separator + 1);
    const hostSeparator = hostAndPath.indexOf("/");
    if (hostSeparator <= 0 || !["https", "http"].includes(scheme)) return null;
    const hostname = hostAndPath.slice(0, hostSeparator).toLowerCase();
    if (!EXTERNAL_PROXY_ALLOWED_HOSTS.has(hostname)) return null;
    const path = hostAndPath.slice(hostSeparator + 1);
    const upstreamUrl = new URL(scheme + "://" + hostname + "/" + path);
    upstreamUrl.search = url.search;
    return { upstreamUrl, rootPath: externalProxyRoot(scheme, hostname) };
  }
  async function serveExternalProxy(request, url) {
    const resolved = resolveExternalProxyUrl(url);
    if (!resolved) return new Response("Bad external broadcast path", { status: 400 });
    const proxyUrl = new URL("/api/data-broadcasting/arib-html5/request", self.location.origin);
    proxyUrl.searchParams.set("url", resolved.upstreamUrl.href);
    const method = request.method === "HEAD" ? "GET" : request.method;
    const response = await fetch(proxyUrl, {
      method,
      headers: request.headers,
      body: method === "POST" ? await request.clone().arrayBuffer() : void 0,
      credentials: "same-origin"
    });
    const headers = new Headers(response.headers);
    const type = headers.get("Content-Type") || "application/octet-stream";
    const rewriteHtml = /^text\/html(?:;|$)/i.test(type) || /^application\/xhtml\+xml(?:;|$)/i.test(type);
    const rewriteCss = /^text\/css(?:;|$)/i.test(type);
    const rewriteJavaScript = /(?:java|ecma)script/i.test(type);
    if (!rewriteHtml && !rewriteCss && !rewriteJavaScript) {
      return new Response(request.method === "HEAD" ? null : response.body, {
        status: response.status,
        headers
      });
    }
    let source = rewriteExternalProxyUrls(await response.text());
    if (rewriteHtml) {
      source = prepareBroadcastHtml(source, {
        basePath: resolved.rootPath,
        scopePath: resolved.rootPath,
        bootstrap: RUNTIME_BOOTSTRAP
      });
    } else if (rewriteCss) {
      source = prepareBroadcastStylesheet(source, {
        basePath: resolved.rootPath,
        scopePath: resolved.rootPath
      });
    }
    headers.delete("Content-Encoding");
    headers.delete("Content-Length");
    headers.set("Cache-Control", "no-store");
    headers.set("Content-Security-Policy", "default-src 'self' data: blob:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; object-src 'none'; frame-src 'none'");
    headers.set("X-Content-Type-Options", "nosniff");
    return new Response(request.method === "HEAD" ? null : source, {
      status: response.status,
      headers
    });
  }

  async function serve(request) {
    const path = normalizePath(request.url);
    if (!path) return new Response("Bad broadcast path", { status: 400 });
    const resolved = await waitFor(path);
    if (!resolved) return new Response("Broadcast resource is not available", { status: 404 });
    if (resolved.path !== path) {
      return Response.redirect(new URL(`${VFS_PREFIX}${resolved.path}`, self.location.origin), 302);
    }
    const resource = resolved.resource;
    const type = contentType(path, resource.contentType);
    let body = resource.data.slice(0);
    if (/^text\/html(?:;|$)/i.test(type)) {
      const source = prepareBroadcastHtml(rewriteExternalProxyUrls(new TextDecoder().decode(resource.data)), {
        basePath: broadcastRootPath(resolved.path),
        scopePath: VFS_PREFIX,
        bootstrap: RUNTIME_BOOTSTRAP
      });
      body = new TextEncoder().encode(source);
    } else if (/^text\/css(?:;|$)/i.test(type)) {
      const source = prepareBroadcastStylesheet(rewriteExternalProxyUrls(new TextDecoder().decode(resource.data)), {
        basePath: broadcastRootPath(resolved.path),
        scopePath: VFS_PREFIX
      });
      body = new TextEncoder().encode(source);
    } else if (/(?:java|ecma)script/i.test(type)) {
      const source = rewriteExternalProxyUrls(new TextDecoder().decode(resource.data));
      body = new TextEncoder().encode(source);
    }
    return new Response(request.method === "HEAD" ? null : body, {
      status: 200,
      headers: {
        "Cache-Control": "no-store",
        "Content-Type": type,
        "Content-Security-Policy": "default-src 'self' data: blob:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; object-src 'none'; frame-src 'none'",
        "X-Content-Type-Options": "nosniff"
      }
    });
  }
  self.addEventListener("install", (event) => {
    event.waitUntil(self.skipWaiting());
  });
  self.addEventListener("activate", (event) => {
    event.waitUntil(self.clients.claim());
  });
  self.addEventListener("message", (event) => {
    const message = event.data || {};
    const reply = (value) => event.ports[0]?.postMessage(value);
    const handle = async () => {
      if (message.type === "arib-vfs-probe") {
        reply({ ok: true, available: await hasAvailableResource(message.path) });
        return;
      }
      if (message.type === "arib-vfs-begin") {
        enabled = true;
        uniqueBasenameFallback = Boolean(message.uniqueBasenameFallback);
        resources.clear();
        for (const pending of waiters.values()) {
          for (const resolve of pending) resolve(null);
        }
        waiters.clear();
        await beginPersistentSession();
        reply({ ok: true });
        return;
      }
      if (message.type === "arib-vfs-put") {
        const path = normalizePath(`/${message.path || ""}`);
        if (!path || !(message.data instanceof ArrayBuffer)) {
          reply({ ok: false, error: "invalid resource" });
          return;
        }
        const resource = {
          data: new Uint8Array(message.data),
          contentType: String(message.contentType || "")
        };
        enabled = true;
        resources.set(path, resource);
        await persistResource(path, resource);
        wake(path, resource);
        reply({ ok: true });
        return;
      }
      if (message.type === "arib-vfs-reset") {
        enabled = false;
        uniqueBasenameFallback = false;
        resources.clear();
        restorePromise = null;
        for (const pending of waiters.values()) {
          for (const resolve of pending) resolve(null);
        }
        waiters.clear();
        await caches.delete(CACHE_NAME);
        reply({ ok: true });
        return;
      }
      reply({ ok: false, error: "unsupported VFS message" });
    };
    event.waitUntil(handle().catch((error) => {
      reply({ ok: false, error: error?.message || String(error) });
    }));
  });
  self.addEventListener("fetch", (event) => {
    const url = new URL(event.request.url);
    if (url.origin !== self.location.origin || !url.pathname.startsWith(VFS_PREFIX)) return;
    if (url.pathname.startsWith(EXTERNAL_PROXY_PREFIX)) {
      if (event.request.method !== "GET" && event.request.method !== "HEAD" && event.request.method !== "POST") return;
      event.respondWith(serveExternalProxy(event.request, url));
      return;
    }
    if (event.request.method !== "GET" && event.request.method !== "HEAD") return;
    event.respondWith((async () => {
      await restorePersistentResources();
      if (!enabled || !hasResourceCandidate(url.pathname)) return fetch(event.request);
      return serve(event.request);
    })());
  });
})();

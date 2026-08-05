const EXTERNAL_PROXY_ALLOWED_HOSTS = [
    '4kdata-p.qvc.jp',
    'api.qvc.jp',
    'api.nhk.or.jp',
    'beacon.nhk.jp',
    'img.nhk.jp',
    'nhk.jp',
    'qvc.jp',
    'qvc.scene7.com',
    'shv.nhk.jp',
    'tv-stream.nhk.jp',
    'www.nhk-cs.jp',
    'www.nhk.or.jp',
];

const EXTERNAL_PROXY_RUNTIME = String.raw`
  // location.href への直接代入は Fetch / XHR の差し替えでは捕捉できないため、
  // 許可ホスト上の文書も VFS Worker の scope 内に写像して receiver runtime を維持する。
  const EXTERNAL_PROXY_PREFIX = VFS_PREFIX + ".external/";
  const EXTERNAL_PROXY_ALLOWED_HOSTS = new Set(${JSON.stringify(EXTERNAL_PROXY_ALLOWED_HOSTS)});
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
`;

const ORIGINAL_FETCH_HANDLER = String.raw`  self.addEventListener("fetch", (event) => {
    const url = new URL(event.request.url);
    if (url.origin !== self.location.origin || !url.pathname.startsWith(VFS_PREFIX) || event.request.method !== "GET" && event.request.method !== "HEAD") return;
    event.respondWith((async () => {
      await restorePersistentResources();
      if (!enabled || !hasResourceCandidate(url.pathname)) return fetch(event.request);
      return serve(event.request);
    })());
  });`;

const PATCHED_FETCH_HANDLER = String.raw`  self.addEventListener("fetch", (event) => {
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
  });`;

/** libaribhtml5 の生成済み VFS Worker に HonomiTV 固有の外部文書プロキシを追加する。 */
export function patchARIBVFSWorkerSource(source: string): string {
    const serveMarker = '  async function serve(request) {';
    if (!source.includes(serveMarker) || !source.includes(ORIGINAL_FETCH_HANDLER)) {
        throw new Error('Unsupported libaribhtml5 VFS Worker layout.');
    }

    // 放送波由来の HTML / CSS / JavaScript に埋め込まれた絶対 URL も、Worker scope 内へ戻す。
    source = source
        .replace(serveMarker, `${EXTERNAL_PROXY_RUNTIME}\n${serveMarker}`)
        .replace(
            'const source = prepareBroadcastHtml(new TextDecoder().decode(resource.data), {',
            'const source = prepareBroadcastHtml(rewriteExternalProxyUrls(new TextDecoder().decode(resource.data)), {',
        )
        .replace(
            'const source = prepareBroadcastStylesheet(new TextDecoder().decode(resource.data), {',
            'const source = prepareBroadcastStylesheet(rewriteExternalProxyUrls(new TextDecoder().decode(resource.data)), {',
        )
        .replace(
            '      body = new TextEncoder().encode(source);\n    }\n    return new Response(request.method === "HEAD" ? null : body, {',
            '      body = new TextEncoder().encode(source);\n' +
            '    } else if (/(?:java|ecma)script/i.test(type)) {\n' +
            '      const source = rewriteExternalProxyUrls(new TextDecoder().decode(resource.data));\n' +
            '      body = new TextEncoder().encode(source);\n' +
            '    }\n' +
            '    return new Response(request.method === "HEAD" ? null : body, {',
        )
        .replace(ORIGINAL_FETCH_HANDLER, PATCHED_FETCH_HANDLER);

    return source;
}

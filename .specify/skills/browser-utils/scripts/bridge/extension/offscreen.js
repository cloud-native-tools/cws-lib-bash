/**
 * Offscreen document — Layer 3 keepalive.
 * Periodically pings the service worker so Chrome keeps it alive.
 */
setInterval(() => {
  chrome.runtime.sendMessage({ keepAlive: true }).catch(() => {
    // Service worker may be momentarily inactive; ignore.
  });
}, 20_000);

/**
 * Console interceptor — runs in the MAIN world (see manifest) so it patches the
 * page's real console, not the content script's isolated copy. Buffers the last
 * MAX messages into window.__bridgeConsole for the `getConsole` command to read.
 */
(function () {
  if (window.__bridgeConsole) return;
  window.__bridgeConsole = [];
  var MAX = 500;
  var methods = ['log', 'warn', 'error', 'info'];
  for (var i = 0; i < methods.length; i++) {
    (function (m) {
      var orig = console[m].bind(console);
      console[m] = function () {
        var args = Array.prototype.slice.call(arguments);
        window.__bridgeConsole.push({
          level: m === 'warn' ? 'warning' : m,
          text: args.map(function (a) {
            try { return typeof a === 'object' ? JSON.stringify(a) : String(a); }
            catch (e) { return String(a); }
          }).join(' '),
          timestamp: Date.now(),
        });
        if (window.__bridgeConsole.length > MAX) window.__bridgeConsole.shift();
        return orig.apply(console, arguments);
      };
    })(methods[i]);
  }
})();

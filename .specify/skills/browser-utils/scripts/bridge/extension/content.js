/**
 * Content script (isolated world) — placeholder for page-side helpers that need
 * the extension's isolated context. Most automation goes through CDP / scripting
 * from background.js; the MAIN-world console buffer lives in console-interceptor.js.
 *
 * Kept intentionally minimal. Extend with DOM helpers if a command needs the
 * isolated world (e.g. reading extension-injected markers).
 */
// no-op by default

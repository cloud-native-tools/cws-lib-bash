#!/usr/bin/env node

// opencode session adapter — spec-kit owned platform extension (P7-b).
// Follows the provider-runner pattern (like claude.mjs / cursor.mjs).
//
// opencode storage layout (public local-JSON format, one file per object):
//   ~/.local/share/opencode/project/<projectID>/storage/session/info/<sessionID>.json
//   ~/.local/share/opencode/project/<projectID>/storage/session/message/<sessionID>/<messageID>.json
//   ~/.local/share/opencode/project/<projectID>/storage/session/part/<sessionID>/<messageID>/<partID>.json
//   (older single-dir variants keep info/message under storage/session directly; both are probed)
// Session info carries { id, projectID, directory, time: { created, updated } } with
// epoch-millisecond timestamps; message files carry { id, role, sessionID, time: { created } };
// part files carry { type: "text"|"tool"|..., messageID, sessionID, ... }.
//
// Capability gaps (declared, per FR-012 discipline):
//   - eventTimestampCoverage: "partial" — text/tool parts do not always carry
//     their own timestamps; events inherit the owning message's created time.
//   - no model-usage or permission-audit source is persisted by opencode.

import path from "node:path";
import { fileURLToPath } from "node:url";

import { SessionAnalyzer } from "../../session-analysis.mjs";
import { parseArgs } from "../cli.mjs";
import { pathExists, walkFiles } from "../fs.mjs";
import { readFile } from "node:fs/promises";
import { expandHome, normalizeWorkspace } from "../paths.mjs";
import {
  emitProviderResult,
  runProviderAnalysis,
  runProviderCommand,
} from "../provider-runner.mjs";
import { parseResultFacts } from "../result-facts.mjs";
import { mergeTimeRange, normalizeCliDate, normalizeTimestamp, timestampMillis, withinTimeRange } from "../time.mjs";

async function readJson(filePath) {
  try {
    return JSON.parse(await readFile(filePath, "utf8"));
  } catch {
    return null;
  }
}

function isWorkspaceMatch(candidate, workspace) {
  if (!candidate) return false;
  const resolved = normalizeWorkspace(String(candidate));
  return resolved === workspace || resolved.startsWith(`${workspace}${path.sep}`);
}

function infoTimestamp(info, field) {
  return normalizeTimestamp(info?.time?.[field] ?? null);
}

function partText(part) {
  if (typeof part?.text === "string") return part.text;
  if (typeof part?.content === "string") return part.content;
  return "";
}

function toolStateOutput(state) {
  if (!state || typeof state !== "object") return "";
  if (typeof state.output === "string") return state.output;
  if (typeof state.error === "string") return state.error;
  return "";
}

// spec-kit owned (P2): SQLite helpers (node:sqlite, read-only, lazily imported
// because node:sqlite is still flagged experimental on some 22.x runtimes).
let sqliteModulePromise = null;
async function loadSqlite() {
  if (!sqliteModulePromise) {
    sqliteModulePromise = import("node:sqlite").catch(() => null);
  }
  return sqliteModulePromise;
}

function parseDataColumn(row) {
  if (row && typeof row.data === "string") {
    try {
      row.data = JSON.parse(row.data);
    } catch {
      row.data = null;
    }
  }
  return row;
}

async function openOpencodeDb(dbPath) {
  const sqlite = await loadSqlite();
  if (!sqlite?.DatabaseSync) return null;
  try {
    return new sqlite.DatabaseSync(dbPath, { readOnly: true });
  } catch {
    return null;
  }
}

async function queryOpencodeSessions(dbPath) {
  const db = await openOpencodeDb(dbPath);
  if (!db) return [];
  try {
    const rows = db.prepare("SELECT * FROM session ORDER BY time_updated DESC").all();
    return rows.map(parseDataColumn);
  } catch {
    return [];
  } finally {
    db.close();
  }
}

function queryOpencodeMessages(db, sessionId) {
  try {
    return db.prepare("SELECT * FROM message WHERE session_id = ? ORDER BY rowid").all(sessionId).map(parseDataColumn);
  } catch {
    return [];
  }
}

function queryOpencodeParts(db, messageId) {
  try {
    return db.prepare("SELECT * FROM part WHERE message_id = ? ORDER BY rowid").all(messageId).map(parseDataColumn);
  } catch {
    return [];
  }
}

export class OpencodeSessionAnalyzer extends SessionAnalyzer {
  currentSessionId() {
    return process.env.OPENCODE_SESSION_ID ?? null;
  }

  async resolveScope(options = {}) {
    const since = normalizeCliDate(options.since, false);
    const until = normalizeCliDate(options.until, true);
    const workspace = normalizeWorkspace(options.workspace);
    return {
      platform: "opencode",
      workspace,
      home: path.resolve(expandHome(
        options.home ?? options.opencodeHome ?? options["opencode-home"] ?? "~/.local/share/opencode")),
      since: since.label,
      sinceTime: since.time,
      until: until.label,
      untilTime: until.time,
      sessionId: options["session-id"] ?? options.sessionId ?? options._?.[0] ?? null,
    };
  }

  async discoverSourceRoots(scope) {
    const roots = [
      {
        id: "opencode-project-storage",
        kind: "opencode-session-json",
        role: "session-transcript",
        path: path.join(scope.home, "project"),
        optional: false,
        enabled: true,
        workspaceScoped: true,
        coverage: "primary",
      },
      {
        id: "opencode-flat-storage",
        kind: "opencode-session-json-flat",
        role: "session-transcript",
        path: path.join(scope.home, "storage", "session"),
        optional: true,
        enabled: true,
        workspaceScoped: true,
        coverage: "optional",
      },
      {
        // spec-kit owned (P2): opencode also persists sessions in a SQLite DB
        // (session/message/part tables, parent_id for subsessions) — adopted
        // from export-session's storage reality. Probed in parallel; sessions
        // found in both sources are merged by sessionId.
        id: "opencode-sqlite",
        kind: "opencode-sqlite-db",
        role: "session-transcript",
        path: path.join(scope.home, "opencode.db"),
        optional: true,
        enabled: true,
        workspaceScoped: true,
        coverage: "optional",
      },
    ];
    return Promise.all(roots.map(async (root) => ({
      ...root,
      exists: await pathExists(root.path),
    })));
  }

  async discoverSessions(scope, roots) {
    const sessionsById = new Map();
    const pushSession = (session) => {
      const existing = sessionsById.get(session.sessionId);
      if (!existing) {
        sessionsById.set(session.sessionId, session);
        return;
      }
      existing.sourceKinds = [...new Set([...existing.sourceKinds, ...session.sourceKinds])];
      existing.sourceRefs.push(...session.sourceRefs);
      if (session.parentId && !existing.parentId) existing.parentId = session.parentId;
      mergeTimeRange(existing, session.firstSeen);
      mergeTimeRange(existing, session.lastSeen);
    };

    const infoDirs = [];
    for (const root of roots.filter((item) => item.exists && item.enabled && item.kind !== "opencode-sqlite-db")) {
      if (root.kind === "opencode-session-json") {
        const projectDirs = await walkFiles(root.path, {
          maxDepth: 4,
          limit: 20_000,
          match: (file) => file.includes(`${path.sep}session${path.sep}info${path.sep}`) && file.endsWith(".json"),
        });
        infoDirs.push(...projectDirs.map((file) => ({ file, kind: root.kind, role: root.role })));
      } else {
        const flatInfos = await walkFiles(path.join(root.path, "info"), {
          maxDepth: 2,
          limit: 20_000,
          match: (file) => file.endsWith(".json"),
        }).catch(() => []);
        infoDirs.push(...flatInfos.map((file) => ({ file, kind: root.kind, role: root.role })));
      }
    }
    for (const { file, kind, role } of infoDirs) {
      const info = await readJson(file);
      if (!info || typeof info !== "object") continue;
      const sessionId = info.id ?? path.basename(file, ".json");
      const directory = info.directory ?? info.cwd ?? info.worktree ?? null;
      if (!isWorkspaceMatch(directory, scope.workspace)) continue;
      const firstSeen = infoTimestamp(info, "created");
      const lastSeen = infoTimestamp(info, "updated") ?? firstSeen;
      if (!withinTimeRange(lastSeen ?? firstSeen, scope)) continue;
      const session = {
        sessionId,
        workspace: scope.workspace,
        firstSeen: null,
        lastSeen: null,
        sourceKinds: [kind],
        sourceRefs: [{
          kind,
          role,
          path: file,
          sessionRoot: path.dirname(path.dirname(file)),
          firstSeen,
          lastSeen,
        }],
        title: typeof info.title === "string" ? info.title.slice(0, 120) : null,
      };
      mergeTimeRange(session, firstSeen);
      mergeTimeRange(session, lastSeen);
      pushSession(session);
    }

    // SQLite source (opencode.db): session/message/part tables; parent_id
    // marks subagent subsessions. Rows double as their own source ref.
    const dbRoot = roots.find((item) => item.kind === "opencode-sqlite-db" && item.exists && item.enabled);
    if (dbRoot) {
      for (const row of await queryOpencodeSessions(dbRoot.path)) {
        const directory = row.directory ?? row.data?.directory ?? null;
        if (!isWorkspaceMatch(directory, scope.workspace)) continue;
        const firstSeen = normalizeTimestamp(row.time_created ?? row.data?.time?.created ?? null);
        const lastSeen = normalizeTimestamp(row.time_updated ?? row.data?.time?.updated ?? null) ?? firstSeen;
        if (!withinTimeRange(lastSeen ?? firstSeen, scope)) continue;
        const session = {
          sessionId: row.id,
          parentId: row.parent_id ?? row.data?.parentID ?? null,
          workspace: scope.workspace,
          firstSeen: null,
          lastSeen: null,
          sourceKinds: ["opencode-sqlite-db"],
          sourceRefs: [{ kind: "opencode-sqlite-db", role: dbRoot.role, path: dbRoot.path, firstSeen, lastSeen }],
          title: typeof row.title === "string" ? row.title.slice(0, 120) : null,
        };
        mergeTimeRange(session, firstSeen);
        mergeTimeRange(session, lastSeen);
        pushSession(session);
      }
    }

    return [...sessionsById.values()].sort((left, right) =>
      (timestampMillis(right.lastSeen) ?? 0) - (timestampMillis(left.lastSeen) ?? 0));
  }

  normalizeEvent(raw, sourceRef, options = {}) {
    const base = {
      sessionId: sourceRef.sessionId ?? raw?.sessionID ?? null,
      timestamp: normalizeTimestamp(raw?.time?.created ?? raw?._messageTime ?? null),
      sourceKind: sourceRef.kind,
      planningScope: "workspace",
      evidenceRef: { kind: sourceRef.kind, path: sourceRef.path, line: null, seq: raw?._seq ?? null, type: raw?._eventType ?? "record" },
    };
    if (raw?._eventType === "message") {
      const role = raw.role === "user" ? "user" : "assistant";
      const event = {
        ...base,
        type: role,
        category: role,
        summary: `${role} message`,
      };
      if (role === "user") event.userPrompt = true;
      if (role === "assistant") {
        event.userVisibleAssistantMessage = true;
        if (raw?.modelID || raw?.model) event.model = raw.modelID ?? raw.model;
      }
      if (raw?._text) {
        event.contentLength = raw._text.length;
        if (options.includeContent) event.content = raw._text;
        if (role === "user" && options.includeUserText) event.userText = raw._text;
      }
      return event;
    }
    if (raw?._eventType === "tool.call") {
      const event = {
        ...base,
        type: "tool.call",
        category: "tool",
        lifecyclePhase: "request",
        toolName: raw?.tool ?? raw?.name ?? "unknown-tool",
        toolInvocationId: raw?.callID ?? raw?.id ?? null,
        summary: `${raw?.tool ?? "unknown-tool"} request`,
      };
      const input = raw?.state?.input && typeof raw.state.input === "object" ? raw.state.input : {};
      if (options.includeCommandText && typeof input.command === "string") event.commandText = input.command;
      if (typeof input.filePath === "string" || typeof input.file_path === "string") {
        event.filePath = input.filePath ?? input.file_path;
      }
      return event;
    }
    if (raw?._eventType === "tool.result") {
      const status = raw?.state?.status ?? "completed";
      const event = {
        ...base,
        type: "tool.result",
        category: "tool",
        lifecyclePhase: "result",
        toolInvocationId: raw?.callID ?? raw?.id ?? null,
        success: status !== "error",
        hasError: status === "error",
        summary: status === "error" ? "tool result failed" : "tool result",
      };
      const facts = parseResultFacts(toolStateOutput(raw?.state).slice(-8_192));
      if (facts) event.resultFacts = facts;
      return event;
    }
    return {
      ...base,
      type: `metadata.${raw?._eventType ?? raw?.type ?? "record"}`,
      category: "metadata",
      summary: raw?._eventType ?? raw?.type ?? "record",
    };
  }

  async readSqliteSession(session, scope, ref, options, events, seq) {
    const db = await openOpencodeDb(ref.path);
    if (!db) return seq;
    try {
      for (const row of queryOpencodeMessages(db, session.sessionId)) {
        const data = row.data && typeof row.data === "object" ? row.data : {};
        const messageTime = row.time_created ?? data?.time?.created ?? null;
        const role = row.role ?? data.role;
        const model = row.model ?? data.model?.modelID ?? data.modelID ?? null;
        const messageParts = queryOpencodeParts(db, row.id);
        const text = messageParts
          .filter((part) => (part.type ?? part.data?.type) === "text")
          .map((part) => partText(part.data && typeof part.data === "object" ? { ...part.data, type: "text" } : part))
          .filter(Boolean)
          .join("\n")
          .trim();
        const messageEvent = this.normalizeEvent(
          { ...data, id: row.id, role, modelID: model, _eventType: "message", _text: text, _messageTime: messageTime, _seq: seq += 1 },
          { ...ref, sessionId: session.sessionId }, options);
        if (withinTimeRange(messageEvent.timestamp, scope)) events.push(messageEvent);
        for (const part of messageParts) {
          const pdata = part.data && typeof part.data === "object" ? part.data : {};
          const ptype = part.type ?? pdata.type;
          if (ptype !== "tool") continue;
          const state = pdata.state && typeof pdata.state === "object" ? pdata.state : part.state;
          const callEvent = this.normalizeEvent(
            { ...pdata, id: part.id, _eventType: "tool.call", _messageTime: state?.time?.start ?? messageTime, _seq: seq += 1 },
            { ...ref, sessionId: session.sessionId }, options);
          if (withinTimeRange(callEvent.timestamp, scope)) events.push(callEvent);
          if (state?.status === "completed" || state?.status === "error") {
            const resultEvent = this.normalizeEvent(
              { ...pdata, id: part.id, _eventType: "tool.result", _messageTime: state?.time?.end ?? messageTime, _seq: seq += 1 },
              { ...ref, sessionId: session.sessionId }, options);
            if (withinTimeRange(resultEvent.timestamp, scope)) events.push(resultEvent);
          }
        }
      }
    } finally {
      db.close();
    }
    return seq;
  }

  async readSession(session, scope, options = {}) {
    const events = [];
    let seq = 0;
    for (const ref of session.sourceRefs ?? []) {
      if (ref.kind === "opencode-sqlite-db") {
        seq = await this.readSqliteSession(session, scope, ref, options, events, seq);
        continue;
      }
      const sessionRoot = ref.sessionRoot;
      const messageDir = path.join(sessionRoot, "message", session.sessionId);
      const partDir = path.join(sessionRoot, "part", session.sessionId);
      const messages = new Map();
      if (await pathExists(messageDir)) {
        for (const file of await walkFiles(messageDir, { maxDepth: 1, limit: 10_000, match: (f) => f.endsWith(".json") })) {
          const message = await readJson(file);
          if (!message) continue;
          messages.set(message.id ?? path.basename(file, ".json"), message);
        }
      }
      const parts = new Map();
      if (await pathExists(partDir)) {
        for (const file of await walkFiles(partDir, { maxDepth: 2, limit: 20_000, match: (f) => f.endsWith(".json") })) {
          const part = await readJson(file);
          if (!part) continue;
          const owner = part.messageID ?? path.basename(path.dirname(file));
          const list = parts.get(owner) ?? [];
          list.push(part);
          parts.set(owner, list);
        }
      }
      const ordered = [...messages.values()].sort((left, right) =>
        (timestampMillis(normalizeTimestamp(left?.time?.created)) ?? 0)
        - (timestampMillis(normalizeTimestamp(right?.time?.created)) ?? 0));
      for (const message of ordered) {
        const messageTime = message?.time?.created ?? null;
        const messageParts = parts.get(message.id) ?? [];
        const text = messageParts.filter((part) => part.type === "text").map(partText).filter(Boolean).join("\n").trim();
        const messageEvent = this.normalizeEvent(
          { ...message, _eventType: "message", _text: text, _messageTime: messageTime, _seq: seq += 1 },
          { ...ref, sessionId: session.sessionId }, options);
        if (withinTimeRange(messageEvent.timestamp, scope)) events.push(messageEvent);
        for (const part of messageParts.filter((item) => item.type === "tool")) {
          const callEvent = this.normalizeEvent(
            { ...part, _eventType: "tool.call", _messageTime: part?.state?.time?.start ?? messageTime, _seq: seq += 1 },
            { ...ref, sessionId: session.sessionId }, options);
          if (withinTimeRange(callEvent.timestamp, scope)) events.push(callEvent);
          const status = part?.state?.status;
          if (status === "completed" || status === "error") {
            const resultEvent = this.normalizeEvent(
              { ...part, _eventType: "tool.result", _messageTime: part?.state?.time?.end ?? messageTime, _seq: seq += 1 },
              { ...ref, sessionId: session.sessionId }, options);
            if (withinTimeRange(resultEvent.timestamp, scope)) events.push(resultEvent);
          }
        }
      }
    }
    return events;
  }

  async analysisWarnings(_scope, _roots, sessions) {
    const warnings = [{
      code: "opencode-partial-event-timestamps",
      message: "opencode parts inherit their owning message's created time when they carry no own timestamp; eventTimestampCoverage: partial.",
    }];
    if (sessions.length === 0) {
      warnings.push({
        code: "opencode-no-workspace-sessions",
        message: "No opencode sessions matched this workspace directory.",
      });
    }
    return warnings;
  }

  async analyze(options = {}) {
    return runProviderAnalysis(this, options, { platform: "opencode", adapterVersion: "opencode-v1" });
  }
}

export async function main(argv = process.argv.slice(2)) {
  const { command = "sessions", options } = parseArgs(argv);
  const analyzer = new OpencodeSessionAnalyzer();
  const result = await runProviderCommand(analyzer, command, options);
  await emitProviderResult({ provider: "opencode", command, options, result });
  return result;
}

const isCli = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isCli) {
  main().catch((error) => {
    process.stderr.write(`opencode session-analysis failed: ${error.stack ?? error.message}\n`);
    process.exitCode = 1;
  });
}

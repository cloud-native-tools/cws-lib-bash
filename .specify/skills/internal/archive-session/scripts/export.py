#!/usr/bin/env python3
"""
archive-session: 把当前 AI Agent 会话相关的全部原始文件导出为目录到项目根 .session-export/<name>/

支持的工具(恰好六家,规范名): claude-code / codex-cli / qoder-cli / copilot / opencode / hermes
  - Claude Code: 主 {sid}.jsonl + {sid}/subagents/*(→subagents/) + {sid}/tool-results/*(→large-results/)
                 + request-ids.jsonl(message.id)
  - Codex CLI:   state_5.sqlite(source∈cli/exec)→ rollout {sid}.jsonl + 递归 spawn 子 agent(→subagents/)
  - Qoder CLI:   ~/.qoder/projects/<enc>/{sid}.jsonl + {sid}/ 状态目录(→state/)
                 + logs/sessions 段日志(→state/logs/) + request-ids.jsonl
  - OpenCode:    从 SQLite 还原(session+message+part,按 parent_id 递归含子会话)→ main.jsonl
  - copilot / hermes: 探测式适配器——available() 按已知候选路径探测会话存储;
                 未探测到落盘 → 声明"该平台会话存储未探测到",退出码 4;不臆造导出行为。

导出目录形态(固定布局):
  .session-export/<name>/
  ├── main.<原生扩展名>      # 主记录(宿主原生形态,逐字节拷贝;运行中会话为截至导出时点的快照)
  ├── subagents/             # 子代理日志(宿主有则导出,无则缺省,不造假目录)
  ├── state/                 # 状态目录与段日志(宿主有则导出)
  ├── large-results/         # 超大工具结果(宿主有则导出)
  ├── request-ids.jsonl      # 仅可提取 requestId 的工具
  ├── session-meta.json      # 元信息机读形态(脚本确定性提取)
  └── SESSION.md             # 会话描述文档(元信息节 + 结构化总结占位节,总结由 agent 补写)

会话定位一律以文件内真实 cwd 字段 / SQLite 的 cwd|directory 列精确匹配,
不依赖各工具有损且互不一致的目录名编码。当前客户端优先按安装位置/进程链识别
(见 _client_bias);同 cwd 出现多个候选会话/工具时,多因子锁定当前会话:
显式会话 id 环境变量(Claude CLAUDE_(CODE_)SESSION_ID / Codex CODEX_THREAD_ID) >
会话内容末条时间戳最新。

平台支持 macOS / Linux / Windows,平台差异全部收敛在少数几处(其余逻辑共用):
  - 路径比较: Windows 大小写不敏感且 '/' 与 '\\' 混用,一律走 _same_path 规范化后比较,
    不做裸字符串相等(SQLite 的 cwd 列同理: 精确查询未命中时回扫全表按 _same_path 比对);
  - 进程祖先链: Windows 无 ps,改用 CreateToolhelp32Snapshot(纯 ctypes)取 pid/ppid/exe 名;
    node/npm 安装的 CLI 进程名一律 node.exe,exe 名识别不出客户端时再查一次命令行;
  - 存储根: OpenCode 数据目录跨平台候选探测(_resolve_opencode_db),Codex 支持 CODEX_HOME;
  - 超长路径: Windows MAX_PATH 限制下给 >255 的路径加 \\\\?\\ 前缀,避免深层会话目录读取失败。

导出对宿主会话存储只读:只读、不写、不删、不改权限。

退出码: 0 成功(stdout 打印导出目录绝对路径) / 2 参数无效(含缺 --name、--name 文法越界、
--session 为空) / 3 无会话 / 4 工具未安装或会话存储未探测到 / 5 IO/SQLite 错误
"""
import argparse
import io
import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
IS_WINDOWS = os.name == "nt"

# 结构化总结预算阈值(以主记录计):行数或字节任一超限即 over_summary_budget=true,
# agent 补写总结时按骨架总结降级(见 SESSION.md 总结节契约)。
SUMMARY_LINE_LIMIT = 50000
SUMMARY_BYTE_LIMIT = 32 * 1024 * 1024

# 运行中会话快照判定:主记录文件 mtime 距导出时刻在该窗口内即视为仍活跃(snapshot=true)。
# 简化启发式——活跃会话持续被写入,mtime 必然新鲜;备份/同步造成的 mtime 扰动接受误判。
SNAPSHOT_MTIME_WINDOW_SECONDS = 300


# ---------------- 跨平台路径 ----------------

def _norm_path(p):
    """路径规范化为可比较形式:转绝对路径,消除 '.'/'..'/重复分隔符/尾部分隔符,
    再经 os.path.normcase 统一形态(Windows 折大小写与 '/'→'\\',POSIX 为恒等)。
    Windows 文件系统大小写不敏感,各工具写进 jsonl/SQLite 的 cwd 可能是 'C:/x'、
    'C:\\x'、'c:\\x' 任一形态,裸字符串相等会漏匹配。空/非字符串/异常返 None。"""
    if not isinstance(p, str) or not p:
        return None
    try:
        return os.path.normcase(os.path.abspath(os.path.normpath(p)))
    except (OSError, ValueError):
        return None


def _same_path(a, b):
    """两路径是否指向同一位置(规范化后比较);任一不可规范化即 False。"""
    na, nb = _norm_path(a), _norm_path(b)
    return na is not None and na == nb


def _os_path(p):
    """交给文件系统调用的实际路径:Windows 上给超 MAX_PATH(260)的路径加 '\\\\?\\' 前缀,
    否则未开启长路径支持的系统会 OSError。前缀要求完全限定且无 '.'/'..',故先 abspath;
    UNC 走 '\\\\?\\UNC\\'。非 Windows / 短路径 / 已带前缀原样返回。

    适用范围是**读取侧**(各 agent 的存储目录):其路径由工具生成、嵌套深且不可控
    (projects/<长编码目录名>/<uuid>/subagents/agent-<uuid>.jsonl),遍历根、stat、open、
    拷贝写入必须全程带前缀,只包其中一环无效(前面的 rglob/stat 会先失败)。
    写出侧(<项目根>/.session-export/)由用户自己控制且层级浅,不做包装;
    SQLite 库路径也不包装,它经 _sqlite_ro_uri 进 URI,前缀会被当成路径内容。"""
    if not IS_WINDOWS:
        return str(p)
    s = os.path.abspath(str(p))
    if len(s) < 256 or s.startswith("\\\\?\\"):
        return s
    return ("\\\\?\\UNC\\" + s[2:]) if s.startswith("\\\\") else ("\\\\?\\" + s)


def _sqlite_ro_uri(path):
    """本地路径 → SQLite 只读 URI(file:...?mode=ro)。
    路径须先百分号转义再进 URI:'%XX' 会被 SQLite 解码、'?' 起查询串、'#' 起片段,
    直接拼接会把 'C:\\bob#work\\a.db' 截断成 'C:\\bob'、'v1%2Ffinal' 解成 'v1/final'。
    分隔符与盘符冒号保持原样,'/a/b'、'C:\\a\\b'、UNC '\\\\srv\\share\\b' 逐字符不变
    (故不能用 Path.as_uri():它把 UNC 转成 'file://srv/...',authority 非空会被 SQLite 拒绝)。"""
    from urllib.parse import quote
    return "file:" + quote(str(path), safe="/\\:") + "?mode=ro"


# ---------------- 通用辅助 ----------------

def _safe_float(v):
    """SQLite 时间字段可能是 int/float/str(ISO)/None，统一转 float，失败返 0.0"""
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _read_cwd_from_jsonl(path, max_lines=200):
    """读 jsonl 前若干行，返回第一个出现的顶层 cwd 字段；找不到返 None。
    大会话开头可能有大量无 cwd 的 summary / queue-operation / runtime-config 行，故窗口放宽。
    只认非空字符串:畸形 jsonl 里的数字 cwd 无法参与路径比较,跳过即可。"""
    try:
        with open(_os_path(path), encoding="utf-8", errors="ignore") as f:
            for _ in range(max_lines):
                line = f.readline()
                if not line:
                    break
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict) and isinstance(obj.get("cwd"), str) and obj["cwd"]:
                    return obj["cwd"]
    except OSError:
        return None
    return None


def _list_jsonl_projects(root, cwd, rel_glob):
    """遍历 root 下每个项目子目录，用文件内真实 cwd 字段精确匹配当前 cwd。

    rel_glob 是子目录内会话文件的相对 glob：
      Claude '*.jsonl' / QoderCLI '*.jsonl'。
    一个项目目录对应一个 cwd，取该目录第一个能读出 cwd 的文件作为归属判据，
    从而彻底规避各工具目录名编码规则的差异与有损问题。
    返回 [(sessionId, path, mtime)] 按 mtime 降序。"""
    root = Path(_os_path(root))
    if not root.exists():
        return []
    out = []
    for proj in root.iterdir():
        if not proj.is_dir():
            continue
        files = sorted(proj.glob(rel_glob),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            continue
        probe_cwd = None
        for probe in files:
            probe_cwd = _read_cwd_from_jsonl(probe)
            if probe_cwd is not None:
                break
        if not _same_path(probe_cwd, cwd):
            continue
        for f in files:
            out.append((f.stem, f, f.stat().st_mtime))
    out.sort(key=lambda t: t[2], reverse=True)
    return out


def _strip_chatcmpl(v):
    """chatcmpl-<uuid> 里 <uuid> 即百炼 request-id;非该形态返 None"""
    if isinstance(v, str) and v.startswith("chatcmpl-"):
        return v[len("chatcmpl-"):]
    return None


def _assistant_request_ids(src_path, id_key):
    """通用:从 claude 风格 jsonl 的 assistant 行按 id_key 取 chatcmpl-<uuid>,
    剥前缀为 request_id;按 request_id 去重、时间升序。id_key 为 message 内字段名。"""
    out, seen = [], set()
    try:
        with open(_os_path(src_path), encoding="utf-8", errors="ignore") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not (isinstance(d, dict) and d.get("type") in ("assistant", "message")):
                    continue
                m = d.get("message") if isinstance(d.get("message"), dict) else {}
                if d.get("type") == "message" and m.get("role") != "assistant":
                    continue
                rid = _strip_chatcmpl(m.get(id_key))
                if not rid or rid in seen:
                    continue
                seen.add(rid)
                out.append({"timestamp": d.get("timestamp"),
                            "request_id": rid, "model": m.get("model")})
    except OSError:
        return out
    return sorted(out, key=lambda r: r.get("timestamp") or "")


def _write_jsonl_file(path, records):
    """把 records(dict 列表)按 JSONL 写入 path;空则不写。返回写入文件数(0/1)。"""
    if not records:
        return 0
    buf = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    Path(path).write_text(buf, encoding="utf-8")
    return 1


def _copy_dir_into(src_dir, dst_dir):
    """把 src_dir 下全部文件拷贝到 dst_dir(保持相对子路径);跳过符号链接;
    源不存在/是符号链接返 0(缺省类不造假目录)。返回拷贝文件数。
    从带前缀的根开始遍历,子路径自动继承前缀,rglob/stat/open 全程一致。"""
    src_dir = Path(src_dir)
    if not src_dir.is_dir() or src_dir.is_symlink():
        return 0
    root = Path(_os_path(src_dir))
    n = 0
    for f in sorted(root.rglob("*")):
        if f.is_symlink() or not f.is_file():
            continue
        rel = f.relative_to(root)
        dst = Path(dst_dir) / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(f), _os_path(dst))
        n += 1
    return n


def _maybe_parse_json_field(d, key):
    """SQLite 里存成字符串的 JSON 字段，尽量解析成对象，失败保持原样"""
    if isinstance(d.get(key), str):
        try:
            d[key] = json.loads(d[key])
        except (json.JSONDecodeError, TypeError):
            pass


def _ts_to_epoch(v):
    """把一条 timestamp 值转 epoch 秒:数字(秒/毫秒/微秒/纳秒)或 ISO8601 字符串;失败返 None。
    数字按量级归一:逐级 /1000 直到落入合理 epoch 秒区间(< 1e11 ≈ 公元 5138 年),
    从而兼容 s(~1.7e9)/ms(~1.7e12)/us(~1.7e15)/ns(~1.7e18) 混用;单档阈值(如只按 1e12
    判毫秒)会把 us/ns 判成远未来,让该会话冒充最新。bool 是 int 子类须先排除,非正数视为无效。"""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        f = float(v)
        if f <= 0:
            return None
        while f >= 1e11:
            f /= 1000.0
        return f
    if isinstance(v, str) and v:
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    return None


def _epoch_to_iso(ep):
    """epoch 秒 → ISO-8601 UTC 字符串(如 2026-01-02T03:04:05Z);None/非法返 None。"""
    if ep is None:
        return None
    try:
        return datetime.fromtimestamp(float(ep), tz=timezone.utc) \
                       .isoformat().replace("+00:00", "Z")
    except (OverflowError, OSError, ValueError):
        return None


def _now_iso():
    """当前时刻的 ISO-8601 UTC 字符串。"""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _content_last_activity(path, max_bytes=64 * 1024, max_scan=32 * 1024 * 1024):
    """读 jsonl 尾部，返回内容里最后(最大)的 timestamp(epoch 秒);找不到返 None。
    比文件 mtime 更能反映真实对话活动(mtime 会被备份/同步/改名等非内容操作扰动)。
    尾部窗口可能整块落在一条超大行(如超大工具结果)内、扫不到任何顶层 timestamp,
    此时逐步放大窗口(×8)直至覆盖全文,避免误返 None 后退化到不可信的 mtime。
    放大设 max_scan 上限(默认 32MB):防止病态'全文无顶层 timestamp'的超大文件被整体读入内存。"""
    try:
        size = Path(_os_path(path)).stat().st_size
    except OSError:
        return None
    window = max_bytes
    while True:
        try:
            with open(_os_path(path), "rb") as f:
                if size > window:
                    f.seek(size - window)
                data = f.read()
        except OSError:
            return None
        best = None
        for line in data.decode("utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line[0] != "{":
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                ep = _ts_to_epoch(obj.get("timestamp"))
                if ep is not None and (best is None or ep > best):
                    best = ep
        # 本窗口找到,或已读完全文,或达扫描上限→返回;否则放大窗口重试
        if best is not None or window >= size or window >= max_scan:
            return best
        window *= 8


def _state_json_updated(src_path):
    """claude 风格布局里同名 {sid}/state.json 维护的可靠 updatedAt(ISO8601)。
    该文件小、不含超大行,不受 _content_last_activity 尾部窗口局限,也免疫 mtime 扰动,
    是'最近活跃'的最稳来源(对无会话 id 环境变量的工具尤其如此)。
    返 epoch 秒;非 jsonl / 无该文件 / 无字段 → None。"""
    if not (isinstance(src_path, Path) and src_path.suffix == ".jsonl"):
        return None
    sj = Path(_os_path(src_path.parent / src_path.stem / "state.json"))
    if not sj.is_file():
        return None
    try:
        d = json.loads(sj.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, json.JSONDecodeError):
        return None
    return _ts_to_epoch(d.get("updatedAt")) if isinstance(d, dict) else None


def _session_recency(src, fallback_ts):
    """会话'最近活跃'时间(epoch 秒):综合两路更可靠信号取最大——
      1) 同名 {sid}/state.json 的 updatedAt(小文件、稳、免疫尾部超大行);
      2) 会话内容末条 timestamp(_content_last_activity,通用)。
    二者皆取不到(src 非 jsonl 如 OpenCode 的 DB / 解析失败)时退回 fallback_ts(通常为 mtime)。"""
    if isinstance(src, Path) and src.suffix == ".jsonl" and Path(_os_path(src)).is_file():
        cands = [t for t in (_state_json_updated(src), _content_last_activity(src))
                 if t is not None]
        if cands:
            return max(cands)
    return fallback_ts


def _find_model_value(obj):
    """从一条 jsonl 记录取模型名:top-level model(runtime-config)、message.model(assistant)
    或 payload.model(Codex 的 turn_context)。"""
    if isinstance(obj, dict):
        v = obj.get("model")
        if isinstance(v, str) and v:
            return v
        msg = obj.get("message")
        if isinstance(msg, dict) and isinstance(msg.get("model"), str) and msg["model"]:
            return msg["model"]
        payload = obj.get("payload")
        if isinstance(payload, dict) and isinstance(payload.get("model"), str) and payload["model"]:
            return payload["model"]
    return None


def _last_model(src_path):
    """会话最后声明的模型:扫描整个 jsonl,返回最后一个 model 值(top-level model 或 message.model);
    无则 None。会话中途切换模型时以最终使用的模型为准。"""
    last = None
    try:
        with open(_os_path(src_path), encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line[0] != "{":
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                m = _find_model_value(d)
                if m:
                    last = m
    except OSError:
        return None
    return last


# ---------------- 目录形态落点辅助 ----------------

def _bundle_main(bundle_dir, src_path):
    """主记录落点:逐字节拷贝为 main.<原生扩展名>(无扩展名则 main.jsonl)。
    只读纪律:只从宿主存储读,绝不写回。返回落点 Path。"""
    ext = Path(src_path).suffix or ".jsonl"
    dst = Path(bundle_dir) / ("main" + ext)
    shutil.copyfile(_os_path(src_path), _os_path(dst))
    return dst


def _bundle_subagents(bundle_dir, src_dir):
    """子代理日志落点 subagents/(宿主有则导出,无则缺省)。返回文件数。"""
    return _copy_dir_into(src_dir, Path(bundle_dir) / "subagents")


def _bundle_state(bundle_dir, src_dir, sub=""):
    """状态目录/段日志落点 state/(可带子目录,如 state/logs)。返回文件数。"""
    return _copy_dir_into(src_dir, Path(bundle_dir) / "state" / sub if sub
                          else Path(bundle_dir) / "state")


def _bundle_large_results(bundle_dir, src_dir):
    """超大工具结果落点 large-results/(既有分段机制迁移,不因体积静默丢弃)。返回文件数。"""
    return _copy_dir_into(src_dir, Path(bundle_dir) / "large-results")


def _bundle_request_ids(bundle_dir, records):
    """requestId 附带落点 request-ids.jsonl(仅可提取者;空则不写)。返回写入文件数(0/1)。"""
    return _write_jsonl_file(Path(bundle_dir) / "request-ids.jsonl", records)


# ---------------- Claude Code ----------------

def claudecode_available():
    return (HOME / ".claude" / "projects").exists()


def claudecode_list(cwd):
    root = HOME / ".claude" / "projects"
    items = _list_jsonl_projects(root, cwd, "*.jsonl")

    # 在 Claude Code 子进程里跑时，CLAUDE_(CODE_)SESSION_ID 精确指向当前会话。
    current_sid = _env_session_id("claude-code")
    if current_sid:
        # a) 当前会话就在本 cwd 列表里 → 置顶(确保导出当前会话而非同项目其它会话)
        for i, (sid, _, _) in enumerate(items):
            if sid == current_sid:
                items.insert(0, items.pop(i))
                return items
        # b) 本 cwd 完全无会话(如 skill 从子目录被调用)才全局按 sid 兜底;
        #    若本 cwd 已有其它会话(说明在导另一个项目)则不覆盖,保持 --project 语义。
        if not items:
            hits = sorted(Path(_os_path(root)).glob(f"*/{current_sid}.jsonl"))
            if hits:
                p = hits[0]
                items.insert(0, (p.stem, p, p.stat().st_mtime))
    return items


def _claude_request_ids(src_path, session_id):
    """从 Claude Code 会话(含 subagents)提取请求标识:request_id 取 assistant 消息体的
    message.id(msg_*)。流式下同一次调用多行重复同一 message.id,按 message.id 去重、时间升序。"""
    files = [src_path]
    subdir = src_path.parent / session_id / "subagents"
    if subdir.is_dir():
        files += sorted(Path(_os_path(subdir)).glob("*.jsonl"))
    seen = {}
    for fp in files:
        try:
            with open(_os_path(fp), encoding="utf-8", errors="ignore") as f:
                for line in f:
                    try:
                        d = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(d, dict):
                        continue
                    m = d.get("message") if isinstance(d.get("message"), dict) else {}
                    mid = m.get("id")
                    if not mid or mid in seen:
                        continue
                    seen[mid] = {
                        "timestamp": d.get("timestamp"),
                        "request_id": mid,
                        "model": m.get("model"),
                    }
        except OSError:
            continue
    return sorted(seen.values(), key=lambda r: r.get("timestamp") or "")


def claudecode_pack(src_path, session_id, bundle_dir):
    """主 jsonl(逐字节) + 同名子目录:subagents/ → subagents/,tool-results/ → large-results/
    + 最外层 request-ids.jsonl。返回导出文件/记录数。"""
    _bundle_main(bundle_dir, src_path)
    n = 1
    sibling_dir = src_path.parent / session_id
    n += _bundle_subagents(bundle_dir, sibling_dir / "subagents")
    n += _bundle_large_results(bundle_dir, sibling_dir / "tool-results")
    n += _bundle_request_ids(bundle_dir, _claude_request_ids(src_path, session_id))
    return n


# ---------------- Qoder CLI (claude 风格: 主 jsonl + 同名状态目录) ----------------
# Qoder CLI: ~/.qoder/projects/<enc>/{sid}.jsonl(顶层) + 同名 {sid}/ 状态目录。
# (~/.qoder-cli 只是 CLI 的 ai-stats 代码统计,非会话,不在此。)

def qodercli_available():
    return (HOME / ".qoder" / "projects").exists()


def qodercli_list(cwd):
    return _list_jsonl_projects(HOME / ".qoder" / "projects", cwd, "*.jsonl")


def qodercli_pack(src_path, session_id, bundle_dir):
    """主 {sid}.jsonl(子 agent 以 isSidechain 内联其中)
    + 同名运行时状态目录 {sid}/(state.json / compression-v2/...) → state/
    + 段日志 {root}/logs/sessions/<enc>/{sid}/segments/*(执行轨迹) → state/logs/
    + 最外层 request-ids.jsonl。
    <enc> 为项目编码目录名(= src_path.parent.name),projects 与 logs/sessions 同编码。"""
    _bundle_main(bundle_dir, src_path)
    n = 1
    sibling_dir = src_path.parent / session_id
    enc = src_path.parent.name
    logs_dir = HOME / ".qoder" / "logs" / "sessions" / enc / session_id
    n += _bundle_state(bundle_dir, sibling_dir)
    n += _bundle_state(bundle_dir, logs_dir, sub="logs")
    # assistant 的 message.id 形如 chatcmpl-<uuid>,<uuid> 即百炼 request-id(旧版无此字段则跳过)
    n += _bundle_request_ids(bundle_dir, _assistant_request_ids(src_path, "id"))
    return n


# ---------------- Codex CLI ----------------

def _codex_home():
    """Codex 数据根:CODEX_HOME 优先,否则 ~/.codex。
    Windows 上 home 即 %USERPROFILE%,与官方默认 %USERPROFILE%\\.codex 一致
    (Codex 在 Windows 用的是 home/.codex,不是 %APPDATA%)。"""
    env = os.environ.get("CODEX_HOME")
    return Path(env) if env else HOME / ".codex"


CODEX_DB = _codex_home() / "state_5.sqlite"

# threads.source 语义: 'cli'/'exec'=Codex CLI;
# 以 '{' 开头的 JSON 串=spawn 出来的 subagent(通过 thread_spawn_edges 递归带出,不作顶层)。
CODEX_CLI_SOURCES = ("cli", "exec")


def _codex_list(cwd, sources):
    """按 cwd + source 取该项目会话。cwd 先走 SQL 精确相等(命中即走索引、零额外开销);
    未命中再回扫同 source 全部行、用 _same_path 规范化比对——Windows 上 threads.cwd
    的盘符大小写与分隔符形态可能与本进程 os.getcwd() 不同,裸相等会整体漏匹配。"""
    if not CODEX_DB.exists():
        return []
    conn = sqlite3.connect(_sqlite_ro_uri(CODEX_DB), uri=True)
    try:
        ph = ",".join("?" * len(sources))
        rows = conn.execute(
            "SELECT id, rollout_path, updated_at FROM threads "
            f"WHERE archived = 0 AND cwd = ? AND source IN ({ph}) "
            "ORDER BY updated_at DESC",
            (cwd, *sources)
        ).fetchall()
        if not rows:
            rows = [(sid, path, upd) for sid, path, upd, c in conn.execute(
                "SELECT id, rollout_path, updated_at, cwd FROM threads "
                f"WHERE archived = 0 AND source IN ({ph}) "
                "ORDER BY updated_at DESC", tuple(sources)
            ).fetchall() if _same_path(c, cwd)]
    finally:
        conn.close()
    out = []
    for sid, path, updated_at in rows:
        p = Path(_os_path(path)) if path else None
        if p and p.exists():
            out.append((sid, p, _safe_float(updated_at)))
    return out


def codexcli_available():
    return CODEX_DB.exists()


def codexcli_list(cwd):
    return _codex_list(cwd, CODEX_CLI_SOURCES)


def codexcli_pack(src_path, session_id, bundle_dir):
    """主 rollout jsonl(逐字节) + 递归 spawn 的全部子 agent rollout(各为独立文件)→ subagents/。"""
    _bundle_main(bundle_dir, src_path)
    n = 1
    # 递归 thread_spawn_edges 收集全部后代子 agent 的 rollout
    if CODEX_DB.exists():
        conn = sqlite3.connect(_sqlite_ro_uri(CODEX_DB), uri=True)
        try:
            cur = conn.execute(
                "WITH RECURSIVE d(id) AS ("
                "  SELECT child_thread_id FROM thread_spawn_edges WHERE parent_thread_id = ?"
                "  UNION ALL"
                "  SELECT e.child_thread_id FROM thread_spawn_edges e JOIN d ON e.parent_thread_id = d.id"
                ") SELECT d.id, t.rollout_path FROM d LEFT JOIN threads t ON t.id = d.id",
                (session_id,)
            )
            for _cid, cpath in cur.fetchall():
                if cpath:
                    p = Path(cpath)
                    if Path(_os_path(p)).is_file():
                        dst = Path(bundle_dir) / "subagents" / p.name
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(_os_path(p), _os_path(dst))
                        n += 1
        except sqlite3.Error:
            # thread_spawn_edges 不存在(旧版本)等：只导主 rollout，不致命
            pass
        finally:
            conn.close()
    return n


# ---------------- OpenCode ----------------

def _opencode_db_candidates():
    """OpenCode 数据库候选位置(按优先级)。OpenCode 走 XDG 风格路径且**不分平台**,
    macOS 也用 ~/.local/share/opencode(不是 ~/Library/Application Support);
    Windows 官方 troubleshooting 指向 %USERPROFILE%\\.local\\share\\opencode,
    但部分版本/桌面端落在 %LOCALAPPDATA%\\opencode,故 Windows 两处都探。
    OPENCODE_DB 可直接指定库文件,OPENCODE_DATA_DIR / XDG_DATA_HOME 指定数据根。"""
    dirs = []
    data_dir = os.environ.get("OPENCODE_DATA_DIR")
    if data_dir:
        dirs.append(Path(data_dir))
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        dirs.append(Path(xdg) / "opencode")
    dirs.append(HOME / ".local" / "share" / "opencode")
    if IS_WINDOWS:
        local = os.environ.get("LOCALAPPDATA")
        dirs.append((Path(local) if local else HOME / "AppData" / "Local") / "opencode")
    out = []
    db = os.environ.get("OPENCODE_DB")
    if db:
        out.append(Path(db))
    out += [d / "opencode.db" for d in dirs]
    return out


def _resolve_opencode_db():
    """取首个真实存在的候选库;都不存在时返回默认位置(供 available() 判否与报错展示)。"""
    cands = _opencode_db_candidates()
    for p in cands:
        try:
            if p.is_file():
                return p
        except OSError:
            continue
    return HOME / ".local" / "share" / "opencode" / "opencode.db"


OPENCODE_DB = _resolve_opencode_db()


def opencode_available():
    return OPENCODE_DB.exists()


def _opencode_conn():
    return sqlite3.connect(_sqlite_ro_uri(OPENCODE_DB), uri=True)


def opencode_list(cwd):
    """directory 列同 Codex 的 cwd:先 SQL 精确相等,未命中再回扫按 _same_path 规范化比对
    (Windows 盘符大小写/分隔符形态差异)。"""
    if not OPENCODE_DB.exists():
        return []
    conn = _opencode_conn()
    try:
        rows = conn.execute(
            "SELECT id, time_updated FROM session "
            "WHERE time_archived IS NULL AND directory = ? "
            "ORDER BY time_updated DESC",
            (cwd,)
        ).fetchall()
        if not rows:
            rows = [(sid, ts) for sid, ts, d in conn.execute(
                "SELECT id, time_updated, directory FROM session "
                "WHERE time_archived IS NULL ORDER BY time_updated DESC"
            ).fetchall() if _same_path(d, cwd)]
    finally:
        conn.close()
    return [(sid, OPENCODE_DB, _safe_float(ts) / 1000) for sid, ts in rows]


def _opencode_last_model(conn, ids):
    """从 message.data 取最后一个模型标识:data.model.modelID(嵌套)或 data.modelID(扁平);无则 None。
    (OpenCode 会话存 SQLite,模型记在 assistant 消息的 data JSON 里,非独立列;中途切换以最终为准。)"""
    ph = ",".join("?" * len(ids))
    try:
        cur = conn.execute(
            f"SELECT data FROM message WHERE session_id IN ({ph}) ORDER BY rowid", ids)
    except sqlite3.Error:
        return None
    last = None
    for (data,) in cur.fetchall():
        if not isinstance(data, str):
            continue
        try:
            d = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(d, dict):
            continue
        m = d.get("model")
        if isinstance(m, dict) and isinstance(m.get("modelID"), str) and m["modelID"]:
            last = m["modelID"]
        elif isinstance(d.get("modelID"), str) and d["modelID"]:
            last = d["modelID"]
    return last


def opencode_pack(_db_path, session_id, bundle_dir):
    """从 session/message/part 还原 jsonl；按 parent_id 递归包含全部子会话(subagent)。
    还原结果落 main.jsonl(目录形态下重建文件即主记录)。"""
    buf = io.StringIO()
    conn = _opencode_conn()
    try:
        cur = conn.execute(
            "WITH RECURSIVE tree(id) AS ("
            "  SELECT id FROM session WHERE id = ?"
            "  UNION ALL"
            "  SELECT s.id FROM session s JOIN tree t ON s.parent_id = t.id"
            ") SELECT id FROM tree",
            (session_id,)
        )
        ids = [r[0] for r in cur.fetchall()]
        if not ids:
            ids = [session_id]
        ph = ",".join("?" * len(ids))

        # session 行
        cur = conn.execute(f"SELECT * FROM session WHERE id IN ({ph})", ids)
        cols = [d[0] for d in cur.description]
        for row in cur.fetchall():
            d = dict(zip(cols, row))
            d["_table"] = "session"
            _maybe_parse_json_field(d, "data")
            buf.write(json.dumps(d, ensure_ascii=False, default=str) + "\n")

        # message + 其 part
        cur = conn.execute(
            f"SELECT * FROM message WHERE session_id IN ({ph}) ORDER BY rowid", ids)
        cols = [d[0] for d in cur.description]
        for row in cur.fetchall():
            d = dict(zip(cols, row))
            d["_table"] = "message"
            _maybe_parse_json_field(d, "data")
            buf.write(json.dumps(d, ensure_ascii=False, default=str) + "\n")
            pcur = conn.execute(
                "SELECT * FROM part WHERE message_id = ? ORDER BY rowid",
                (d.get("id"),))
            pcols = [pd[0] for pd in pcur.description]
            for prow in pcur.fetchall():
                pd = dict(zip(pcols, prow))
                pd["_table"] = "part"
                _maybe_parse_json_field(pd, "data")
                buf.write(json.dumps(pd, ensure_ascii=False, default=str) + "\n")
    finally:
        conn.close()

    dst = Path(bundle_dir) / "main.jsonl"
    dst.write_text(buf.getvalue(), encoding="utf-8")
    return 1


# ---------------- copilot / hermes(探测式适配器) ----------------
# 会话存储形态未在本环境探测到落盘:available() 按已知候选路径探测;
# 无落盘 → main() 声明"该平台会话存储未探测到"并退出码 4;MUST NOT 臆造 list/pack 行为。
# 未来探测到真实落盘 → 升级为完整适配器(独立迭代)。

def copilot_available():
    """候选存储路径探测:任一路径存在即视为有落盘。"""
    for p in (HOME / ".copilot",
              HOME / ".config" / "github-copilot",
              HOME / ".local" / "share" / "github-copilot"):
        try:
            if p.exists():
                return True
        except OSError:
            continue
    return False


def copilot_list(cwd):
    raise NotImplementedError(
        "copilot 会话存储形态未落盘验证,导出行为未实现(no verified storage; export not implemented)")


def copilot_pack(src_path, session_id, bundle_dir):
    raise NotImplementedError(
        "copilot 会话存储形态未落盘验证,导出行为未实现(no verified storage; export not implemented)")


def hermes_available():
    """候选存储路径探测:任一路径存在即视为有落盘。"""
    for p in (HOME / ".hermes",
              HOME / ".config" / "hermes"):
        try:
            if p.exists():
                return True
        except OSError:
            continue
    return False


def hermes_list(cwd):
    raise NotImplementedError(
        "hermes 会话存储形态未落盘验证,导出行为未实现(no verified storage; export not implemented)")


def hermes_pack(src_path, session_id, bundle_dir):
    raise NotImplementedError(
        "hermes 会话存储形态未落盘验证,导出行为未实现(no verified storage; export not implemented)")


def _probe_no_source(tool_name):
    """探测式适配器无源时的诚实声明(退出码 4 用)。"""
    return (f"error: {tool_name} 会话存储未探测到"
            f"(no session storage detected for {tool_name}; export not implemented)")


# ---------------- 注册 ----------------

PARSERS = {
    "claude-code": (claudecode_available, claudecode_list, claudecode_pack),
    "codex-cli":   (codexcli_available,   codexcli_list,   codexcli_pack),
    "qoder-cli":   (qodercli_available,   qodercli_list,   qodercli_pack),
    "copilot":     (copilot_available,    copilot_list,    copilot_pack),
    "opencode":    (opencode_available,   opencode_list,   opencode_pack),
    "hermes":      (hermes_available,     hermes_list,     hermes_pack),
}
PRIORITY = ["qoder-cli", "codex-cli", "opencode", "claude-code", "copilot", "hermes"]

# 客户端专属安装根 → 该客户端会话工具。用于在多个工具共享同一 cwd 时,
# 依脚本自身安装位置(__file__)优先归属当前客户端。共享的 ~/.claude/skills
# 被多个客户端扫描、无法区分,故不在此表;此时退回 PRIORITY + cwd。
_CLIENT_ROOTS = [
    (".qoder",     ["qoder-cli"]),
    (".codex",     ["codex-cli"]),
    ("opencode",   ["opencode"]),   # ~/.config/opencode
]


# macOS 由 OS 注入的“启动 app bundle id” → 客户端。shell env 共享伪造不了(非继承链能改的普通 env)。
# 注意:在独立终端跑 CLI 时此值是终端的 bundle id(如 com.apple.Terminal),不代表 agent,
# 故优先级低于进程祖先链,且在 env 内排在“会话 id”类变量之后。
_BUNDLE_ID_CLIENTS = [
    ("com.openai.codex",               ["codex-cli"]),
    ("com.anthropic.claudefordesktop", ["claude-code"]),
]


def _client_from_env():
    """据客户端注入的运行时环境变量判定当前客户端(最后兜底信号)。
    信号取产品专属、不可能被其它产品误设的“会话 id”类变量;
    再加 macOS 的 __CFBundleIdentifier(OS 注入的启动 app id,精确且难伪造)。
    Windows 没有等价的“启动 app 标识”环境变量,识别改由更靠前的进程祖先链承担
    (见 _client_from_process,Windows 分支基于 toolhelp 快照 + 命令行)。"""
    # Codex 专属(thread/session id,仅 Codex 注入)
    if os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID"):
        return ["codex-cli"]
    # Claude Code 专属(会话 id,仅 Claude Code 注入)
    if os.environ.get("CLAUDE_CODE_SESSION_ID"):
        return ["claude-code"]
    # macOS: OS 注入的启动 app bundle id(GUI-agent-app 精确区分,不依赖 ps)
    bid = os.environ.get("__CFBundleIdentifier")
    if bid:
        for key, tools in _BUNDLE_ID_CLIENTS:
            if bid == key or bid.startswith(key + "."):
                return tools
    return []


_WIN_PROC_TABLE = None


def _win_process_table():
    """Windows 全进程表快照 {pid: (ppid, exeName)}。
    Windows 没有 ps,这是 `ps -o ppid=,comm=` 的等价替代:CreateToolhelp32Snapshot 纯 ctypes
    调用,不起子进程、无解释器启动开销,一次拿到全表。进程表在单次导出内不变,故全局缓存一次。
    非 Windows / API 失败(权限等)返 {},调用方自然降级到其它信号。"""
    global _WIN_PROC_TABLE
    if _WIN_PROC_TABLE is not None:
        return _WIN_PROC_TABLE
    _WIN_PROC_TABLE = {}
    if not IS_WINDOWS:
        return _WIN_PROC_TABLE
    try:
        import ctypes
        from ctypes import wintypes

        class _PE32(ctypes.Structure):
            _fields_ = [
                ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.c_void_p),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
                ("szExeFile", ctypes.c_char * 260),
            ]

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        # 必须显式声明 restype:HANDLE 在 64 位下是 8 字节,默认 c_int 会截断句柄
        k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
        k32.Process32First.restype = wintypes.BOOL
        k32.Process32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(_PE32)]
        k32.Process32Next.restype = wintypes.BOOL
        k32.Process32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(_PE32)]
        k32.CloseHandle.argtypes = [wintypes.HANDLE]

        snap = k32.CreateToolhelp32Snapshot(0x00000002, 0)   # TH32CS_SNAPPROCESS
        if not snap or snap == ctypes.c_void_p(-1).value:
            return _WIN_PROC_TABLE
        try:
            e = _PE32()
            e.dwSize = ctypes.sizeof(_PE32)
            ok = k32.Process32First(snap, ctypes.byref(e))
            while ok:
                _WIN_PROC_TABLE[int(e.th32ProcessID)] = (
                    int(e.th32ParentProcessID),
                    e.szExeFile.decode("mbcs", errors="ignore"),
                )
                e = _PE32()
                e.dwSize = ctypes.sizeof(_PE32)
                ok = k32.Process32Next(snap, ctypes.byref(e))
        finally:
            k32.CloseHandle(snap)
    except Exception:
        # ctypes 不可用 / 结构体布局异常 / 权限不足:视作拿不到进程信息
        _WIN_PROC_TABLE = {}
    return _WIN_PROC_TABLE


def _win_ancestor_chain():
    """Windows: 自身及各级祖先的 [(pid, exeName)](自身在前)。
    ppid 在 Windows 会被复用(父进程退出后 pid 可能指向无关新进程),故遇到已访问过的 pid
    或 pid<=0 即停止,避免成环;上溯层数与 POSIX 分支同为 20。"""
    table = _win_process_table()
    out, seen, pid = [], set(), os.getpid()
    for _ in range(20):
        ent = table.get(pid)
        if not ent:
            break
        out.append((pid, ent[1]))
        seen.add(pid)
        pid = ent[0]
        if pid <= 0 or pid in seen:
            break
    return out


def _self_path_fragments():
    """本脚本自身路径的各种书写形态(原样/resolve/posix 分隔符)+ skill 目录。
    用于从命令行文本里剔除自身路径:本脚本常安装在 ~/.claude/skills/archive-session/ 下,
    启动它的命令行里含 'claude' 字样,若不剔除会让 _CLIENT_PROC_MARKERS 误判客户端。"""
    me, skill_dir = Path(__file__), Path(__file__).parents[1]
    frags = set()
    for p in (me, me.resolve(), skill_dir, skill_dir.resolve()):
        frags.add(str(p).lower())
        frags.add(p.as_posix().lower())
    env_dir = os.environ.get("CLAUDE_SKILL_DIR")
    if env_dir:
        frags.add(env_dir.lower())
        frags.add(env_dir.replace("\\", "/").lower())
    return {f for f in frags if f}


def _win_ancestor_cmdlines():
    """Windows: 祖先链各进程的完整命令行(小写,已剔除本脚本自身路径)。
    npm/node 安装的 CLI 进程名一律是 node.exe,exe 名区分不出客户端,
    只有命令行里的入口脚本路径能区分。
    Win32_Process.CommandLine 只能经 WMI 取(toolhelp 不提供),PowerShell 启动有开销,
    故仅在 exe 名匹配失败时才调用,且只查祖先链这几个 pid。取不到返 []。"""
    if not IS_WINDOWS:
        return []
    import subprocess
    pids = [pid for pid, _ in _win_ancestor_chain()]
    if not pids:
        return []
    flt = " or ".join(f"ProcessId={p}" for p in pids)
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             f"Get-CimInstance Win32_Process -Filter '{flt}' | "
             "ForEach-Object { $_.CommandLine }"],
            capture_output=True, text=True, timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        return []
    frags = _self_path_fragments()
    out = []
    for line in (r.stdout or "").splitlines():
        low = line.strip().lower()
        if not low:
            continue
        for f in frags:
            low = low.replace(f, " ")
        out.append(low)
    return out


def _proc_ancestry():
    """上溯进程祖先链,返回每个祖先的可执行名/路径。
    skill 经软链共享安装(__file__ 落 ~/.claude 无法区分)、且客户端不注入专属环境变量时,
    进程树是唯一可靠的当前客户端信号。
    POSIX 用 ps;Windows 无 ps,走 toolhelp 快照(见 _win_process_table)。
    两者都拿不到时返 [],不影响其它信号。"""
    if IS_WINDOWS:
        return [name for _, name in _win_ancestor_chain()]
    import subprocess
    out, pid = [], os.getpid()
    for _ in range(20):
        if pid <= 1:
            break
        try:
            r = subprocess.run(["ps", "-o", "ppid=,comm=", "-p", str(pid)],
                               capture_output=True, text=True, timeout=2)
        except (OSError, subprocess.SubprocessError):
            break
        line = (r.stdout or "").strip()
        if not line:
            break
        parts = line.split(None, 1)
        if len(parts) < 2:
            break
        out.append(parts[1])
        try:
            nxt = int(parts[0])
        except ValueError:
            break
        if nxt == pid:
            break
        pid = nxt
    return out


# 进程可执行名/路径 → 客户端会话工具(有序)。与 _CLIENT_ROOTS 对齐。
_CLIENT_PROC_MARKERS = [
    (["qoder-cli"],   (".qoder-cli", "qoder")),
    (["codex-cli"],   ("codex",)),
    (["claude-code"], ("claude",)),
    (["opencode"],    ("opencode",)),
]


def _match_proc_marker(text):
    """一段进程可执行名/路径/命令行文本命中哪个客户端;不命中返 None。
    basename 同时按 '/' 和 '\\' 切(Windows 是反斜杠,且 exe 名带 .exe 后缀,
    故除精确等值外仍保留子串匹配:'claude' in 'claude.exe')。"""
    low = text.lower()
    base = low.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    for tools, markers in _CLIENT_PROC_MARKERS:
        if any(mk == base or mk in low for mk in markers):
            return list(tools)
    return None


def _client_from_process():
    """据进程祖先链的可执行名判定当前客户端 → 对应会话工具;识别不到返 []。
    claude 风格 jsonl 的各产品结构相同、无法内容区分,但进程可执行名不同。
    Windows 上 npm/node 安装的 CLI 进程名全是 node.exe,exe 名无从区分,故再退一步查
    祖先链命令行里的入口脚本路径(仅此时才付 WMI 查询开销,见 _win_ancestor_cmdlines)。"""
    for comm in _proc_ancestry():
        tools = _match_proc_marker(comm)
        if tools:
            return tools
    for cmdline in _win_ancestor_cmdlines():
        tools = _match_proc_marker(cmdline)
        if tools:
            return tools
    return []


def _client_bias():
    """识别当前客户端 → 该客户端对应的会话工具(有序);识别不到返回 []。
    信号按可靠性从高到低:
      1) 安装位置:脚本 __file__ / 客户端注入的 $CLAUDE_SKILL_DIR 落在某客户端专属根;
         未解析路径与 resolve() 结果都看,兼容 `skills link` 软链安装。这是物理事实,最稳。
      2) 客户端运行时环境特征(见 _client_from_env)。
    共享的 ~/.claude/skills 路径无法区分客户端,故此时只能靠进程祖先链与环境变量。"""
    # 按"路径段"比较:不受平台分隔符差异影响(Windows 是 '\\'),且天然精确
    seg_sets = [set(Path(__file__).parts), set(Path(__file__).resolve().parts)]
    skill_dir = os.environ.get("CLAUDE_SKILL_DIR")
    if skill_dir:
        seg_sets.append(set(Path(skill_dir).parts))
    for marker, tools in _CLIENT_ROOTS:
        if any(marker in segs for segs in seg_sets):
            return tools
    # 安装路径无法区分(skill 软链到 ~/.claude/skills 被多客户端共享)时,
    # 用进程祖先链这一运行时物理事实识别;再退回环境变量。
    proc = _client_from_process()
    if proc:
        return proc
    return _client_from_env()


def _ordered(bias):
    return bias + [t for t in PRIORITY if t not in bias]


# ---- 多因子锁定"当前会话"(仅在同 cwd 出现多个候选会话/工具时启用;单候选走快路径,零额外开销) ----
# 因子按可靠性从高到低:
#   1) 客户端注入的"当前会话 id"环境变量(精确):Claude 的 CLAUDE_CODE_SESSION_ID / CLAUDE_SESSION_ID、
#      Codex 的 CODEX_THREAD_ID / CODEX_SESSION_ID;取不到即回退到下一因子。
#   2) 会话内容末条 timestamp 最新(当前会话此刻正被写入),并以 (mtime, sid) 做确定性兜底。
_SESSION_ID_ENV = {
    "claude-code": ("CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID"),
    "codex-cli":   ("CODEX_THREAD_ID", "CODEX_SESSION_ID"),
}


def _env_session_id(tool_name):
    """客户端注入的当前会话 id(逐个候选环境变量取首个非空);无则 None。"""
    for k in _SESSION_ID_ENV.get(tool_name, ()):
        v = os.environ.get(k)
        if v and v.strip():
            return v.strip()
    return None


def _most_active_tool(matches, cwd):
    """多个工具争同一 cwd 时按精确信号择一:环境变量精确命中 > 按 PRIORITY 顺序取首个。
    matches=[(tool_name, items)],已按 PRIORITY/bias 排序。
    兜底不看时间戳:同一 cwd 下 claude-code 会话可能碰巧更新而误赢 qoder-cli。"""
    for name, items in matches:
        sid = _env_session_id(name)
        if sid and any(it[0] == sid for it in items):
            return name, items
    # 无精确信号 → 按 PRIORITY 顺序取首个(qoder-cli 永远最优先)
    return matches[0]


def detect_tool(cwd):
    """自动定位当前会话所属工具。
    - 识别到当前客户端(_client_bias 非空)→ 仅在其工具内找,不回退别家(避免误导出同目录别家旧会话);
      同源多工具争同一 cwd 时,按'当前活跃'择一而非盲目按序。
    - 识别不到 → 该 cwd 只有 1 个工具有会话则直接用;2+ 个同样按'当前活跃'择一。
    '当前活跃'见 _most_active_tool(环境变量 / 内容时间戳多因子)。"""
    def _collect(names):
        out = []
        for name in names:
            avail, list_fn, _ = PARSERS[name]
            try:
                if avail():
                    items = list_fn(cwd)
                    if items:
                        out.append((name, items))
            except (sqlite3.Error, OSError):
                # 单个工具探测出错(如 db 不可读)不能拖垮整体识别,跳过该工具
                continue
        return out

    bias = _client_bias()
    matches = _collect(_ordered(bias) if bias else PRIORITY)
    if not matches:
        return None, []
    return matches[0] if len(matches) == 1 else _most_active_tool(matches, cwd)


def _choose_session(tool_name, items, cwd):
    """同工具多会话里选当前会话(多因子;仅多候选时才计算,单候选直接返回):
    1) 客户端注入的当前会话 id 环境变量(精确,见 _SESSION_ID_ENV);
    2) 内容时间戳最新者(免疫文件 mtime 扰动),以 (mtime, sid) 做确定性兜底。
    仍选不准的极端并发场景,应由调用方用 --session 精确指定。"""
    if len(items) == 1:
        return items[0]
    env_sid = _env_session_id(tool_name)
    if env_sid:
        for it in items:
            if it[0] == env_sid:
                return it
    return max(items, key=lambda it: (_session_recency(it[1], it[2]), it[2], it[0]))


# jsonl 类工具的存储根 + 会话文件 glob(用于 --session 跨项目定位)
_SESSION_GLOBS = [
    ("qoder-cli",   HOME / ".qoder" / "projects",    "*.jsonl"),
    ("claude-code", HOME / ".claude" / "projects",   "*.jsonl"),
]


def _find_session_by_location(sid):
    """跨所有工具、所有项目,按 session id 定位文件物理位置 → 确定所属工具。
    位置即事实:文件在谁的目录结构里就是谁的产品,不依赖优先级/cwd/环境变量。
    找到返回 (tool_name, (sid, path, mtime));找不到返 (None, None)。"""
    # 1) jsonl 类: 按文件名匹配(sid 即 stem 或 stem 尾部)
    for tool, root, glob in _SESSION_GLOBS:
        if not root.is_dir():
            continue
        for f in Path(_os_path(root)).glob("*/" + glob):
            if f.stem == sid or f.stem.endswith("_" + sid):
                return tool, (sid, f, f.stat().st_mtime)
    # 2) Codex: DB 查 id → rollout_path
    if CODEX_DB.exists():
        try:
            conn = sqlite3.connect(_sqlite_ro_uri(CODEX_DB), uri=True)
            row = conn.execute(
                "SELECT rollout_path FROM threads WHERE id = ?", (sid,)
            ).fetchone()
            conn.close()
            p = Path(_os_path(row[0])) if row and row[0] else None
            if p and p.is_file():
                return "codex-cli", (sid, p, p.stat().st_mtime)
        except sqlite3.Error:
            pass
    # 3) OpenCode: DB 查 id → 确认存在
    if OPENCODE_DB.exists():
        try:
            conn = _opencode_conn()
            row = conn.execute(
                "SELECT id FROM session WHERE id = ?", (sid,)
            ).fetchone()
            conn.close()
            if row:
                return "opencode", (sid, OPENCODE_DB, 0.0)
        except sqlite3.Error:
            pass
    return None, None


def find_session_in_cwd(cwd, sid):
    """按 session id 查找会话,通过文件物理位置确定所属工具(位置即事实,不靠优先级猜)。
    1) 先在 cwd 范围内全量搜索(所有工具平等,不按 bias 排序);
    2) cwd 内未命中 → 扩大到全量项目按文件位置定位(跨 cwd)。
    命中返回 (tool_name, item);未命中返 (None, None)。"""
    # 1) cwd 内: 全量工具平等搜索
    for name in PARSERS:
        avail, list_fn, _ = PARSERS[name]
        try:
            if not avail():
                continue
            for item in list_fn(cwd):
                if item[0] == sid:
                    return name, item
        except (sqlite3.Error, OSError, NotImplementedError):
            continue
    # 2) 扩大: 按文件物理位置定位(忽略 cwd)
    return _find_session_by_location(sid)


def _session_contains_text(src_path, text, max_bytes=512 * 1024):
    """在 session 文件尾部 max_bytes 内搜索 text;命中 True。
    当前对话内容一定在文件末尾(正在被写入),尾部窗口即可。"""
    if not isinstance(src_path, Path):
        return False
    fp = Path(_os_path(src_path))
    if not fp.is_file():
        return False
    try:
        size = fp.stat().st_size
        with open(fp, "rb") as f:
            if size > max_bytes:
                f.seek(size - max_bytes)
            data = f.read()
    except OSError:
        return False
    return text in data.decode("utf-8", errors="ignore")


def _verify_or_relocate(cwd, verify_text, current_tool, current_sid):
    """内容匹配兜底:当前选择未命中 verify_text → 跨工具/跨会话搜索包含该内容的 session。
    找到返回 (tool_name, item);全部未命中返 None。"""
    candidates = []
    for name in PARSERS:
        avail, list_fn, _ = PARSERS[name]
        try:
            if not avail():
                continue
            for item in list_fn(cwd):
                if item[0] == current_sid:
                    continue
                candidates.append((name, item))
        except (sqlite3.Error, OSError, NotImplementedError):
            continue
    candidates.sort(key=lambda ni: _session_recency(ni[1][1], ni[1][2]), reverse=True)
    for name, item in candidates:
        if _session_contains_text(item[1], verify_text):
            return name, item
    return None


# ---------------- session-meta.json / SESSION.md(确定性元信息半体) ----------------

def _iter_jsonl_dicts(path):
    """逐行产出 jsonl 里的 dict 记录;坏行跳过;IO 错误即止。"""
    try:
        with open(_os_path(path), encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line[0] != "{":
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(d, dict):
                    yield d
    except OSError:
        return


def _first_last_ts(obj):
    """claude 风格记录的事件时间候选:仅 user/assistant 消息(排除 summary / 系统行),
    顶层 timestamp 优先,退回 message.timestamp。返 epoch 秒或 None。"""
    if obj.get("type") not in ("user", "assistant"):
        return None
    ep = _ts_to_epoch(obj.get("timestamp"))
    if ep is not None:
        return ep
    m = obj.get("message")
    if isinstance(m, dict):
        return _ts_to_epoch(m.get("timestamp"))
    return None


def _meta_from_jsonl(path):
    """claude 风格 jsonl 主记录的元信息提取:workspace(首个顶层 cwd)、
    started_at/ended_at(首末条 user/assistant 消息 timestamp)、
    message_count(user+assistant 消息记录数)、turn_count(同口径)。
    记录中不可得的字段返 None,MUST NOT 猜测填充。"""
    workspace = None
    first = None
    last = None
    msgs = 0
    for d in _iter_jsonl_dicts(path):
        if workspace is None and isinstance(d.get("cwd"), str) and d["cwd"]:
            workspace = d["cwd"]
        if d.get("type") in ("user", "assistant"):
            msgs += 1
            ep = _first_last_ts(d)
            if ep is not None:
                if first is None:
                    first = ep
                last = ep
    return {
        "workspace": workspace,
        "started_at": _epoch_to_iso(first),
        "ended_at": _epoch_to_iso(last),
        "message_count": msgs,
        "turn_count": msgs,
    }


def _oc_first_last_ts(d):
    """opencode 还原行的时间候选:user/assistant message 行的 time_created/time_updated
    (epoch 毫秒,经 _ts_to_epoch 量级归一)。返 epoch 秒或 None。"""
    data = d.get("data") if isinstance(d.get("data"), dict) else {}
    if data.get("role") not in ("user", "assistant"):
        return None
    for k in ("time_created", "time_updated"):
        ep = _ts_to_epoch(d.get(k))
        if ep is not None:
            return ep
    return None


def _oc_meta(path):
    """opencode 还原 main.jsonl 的元信息提取:workspace 取 session 行 directory 列,
    时间窗与计数取 user/assistant message 行。返与 _meta_from_jsonl 同形的 dict。"""
    workspace = None
    first = None
    last = None
    msgs = 0
    for d in _iter_jsonl_dicts(path):
        t = d.get("_table")
        if t == "session" and workspace is None:
            for k in ("directory", "cwd"):
                if isinstance(d.get(k), str) and d[k]:
                    workspace = d[k]
                    break
        elif t == "message":
            data = d.get("data") if isinstance(d.get("data"), dict) else {}
            if data.get("role") in ("user", "assistant"):
                msgs += 1
                ep = _oc_first_last_ts(d)
                if ep is not None:
                    if first is None:
                        first = ep
                    last = ep
    return {
        "workspace": workspace,
        "started_at": _epoch_to_iso(first),
        "ended_at": _epoch_to_iso(last),
        "message_count": msgs,
        "turn_count": msgs,
    }


def _session_snapshot(main_path):
    """运行中会话快照判定(简化启发式):主记录文件 mtime 距导出时刻 5 分钟内
    即视为仍活跃(活跃会话持续被写入)→ True。备份/同步扰动 mtime 的误判接受。"""
    try:
        mt = Path(_os_path(main_path)).stat().st_mtime
    except OSError:
        return False
    return (datetime.now(timezone.utc).timestamp() - mt) <= SNAPSHOT_MTIME_WINDOW_SECONDS


def _over_summary_budget(main_path):
    """预算判定:主记录行数 > SUMMARY_LINE_LIMIT 或字节 > SUMMARY_BYTE_LIMIT 即 True。"""
    lines = 0
    size = 0
    try:
        with open(_os_path(main_path), "rb") as f:
            for raw in f:
                lines += 1
                size += len(raw)
    except OSError:
        return False
    return lines > SUMMARY_LINE_LIMIT or size > SUMMARY_BYTE_LIMIT


def _session_meta(tool_name, session_id, main_path):
    """session-meta.json 的字段集(元信息权威,全部确定性提取自原始记录)。"""
    if tool_name == "opencode":
        extra = _oc_meta(main_path)
    else:
        extra = _meta_from_jsonl(main_path)
    meta = {
        "tool": tool_name,
        "session_id": str(session_id),
        "model": _last_model(main_path),
        "workspace": extra["workspace"],
        "started_at": extra["started_at"],
        "ended_at": extra["ended_at"],
        "snapshot": _session_snapshot(main_path),
        "message_count": extra["message_count"],
        "turn_count": extra["turn_count"],
        "exported_at": _now_iso(),
        "over_summary_budget": _over_summary_budget(main_path),
    }
    return meta


def _render_meta_value(v):
    """元信息节字段值渲染:null 字段标注"记录未含"(MUST NOT 猜测填充)。"""
    if v is None:
        return "null(记录未含)"
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def _render_session_md(meta):
    """SESSION.md:首行 heading + STR-003 标识行(session-export:<tool>/<session-id>)
    + 元信息节(与 session-meta.json 逐字段一致)+ 结构化总结占位节(agent 补写)。
    脚本只写元信息半体与固定 heading 占位;agent 补写总结时 MUST NOT 改动元信息节。"""
    lines = [
        "# Session Description",
        "",
        f"session-export:{meta['tool']}/{meta['session_id']}",
        "",
        "## 元信息",
        "",
    ]
    for k in ("tool", "session_id", "model", "workspace", "started_at", "ended_at",
              "snapshot", "message_count", "turn_count", "exported_at",
              "over_summary_budget"):
        lines.append(f"- {k}: {_render_meta_value(meta[k])}")
    lines += [
        "",
        "## 结构化总结",
        "",
        "<!-- agent 补写:任务脉络 / 关键决策 / 产物清单 -->",
        "",
    ]
    return "\n".join(lines)


def _write_description(bundle_dir, meta):
    """描述文档两形态同出:session-meta.json(机读权威)+ SESSION.md(人读)。"""
    (Path(bundle_dir) / "session-meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (Path(bundle_dir) / "SESSION.md").write_text(
        _render_session_md(meta), encoding="utf-8")


# ---------------- CLI ----------------

# --name 安全路径段文法:首字符字母/数字,其余 [A-Za-z0-9_.-],且不得为 '.'/'..'
# (与 goal 身份文法一致;天然兼容派发 label 形 <team-slug>--<run-stamp>--<member-role>)。
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def _valid_name(name):
    return bool(name) and name not in (".", "..") and _NAME_RE.match(name) is not None


def main():
    parser = argparse.ArgumentParser(
        description="Export the current AI Agent session (main record + subagents + state + "
                    "large tool results) into a directory <project>/.session-export/<name>/"
    )
    parser.add_argument("--project", default=os.getcwd())
    parser.add_argument("--output", default=".session-export")
    parser.add_argument("--name", default=None,
                        help="导出目录名(必填);安全路径段文法:首字符字母/数字,其余 [A-Za-z0-9_.-]")
    parser.add_argument("--session", default=None,
                        help="精确指定 sessionId，仅在当前项目范围内查找")
    parser.add_argument("--tool", default=None, choices=list(PARSERS.keys()),
                        help="显式指定产品，跳过自动识别(当调用方确知自身产品时用)")
    parser.add_argument("--verify", default=None,
                        help="本轮对话中的一段独特文本,用于内容匹配二次确认选中的 session 是否正确")
    args = parser.parse_args()

    # --name 必填 + 文法校验(越界退出码 2;同名冲突在会话定位后检查,报错需带出目录名)
    if args.name is None:
        print("error: --name 必填(missing required argument --name)", file=sys.stderr)
        sys.exit(2)
    if not _valid_name(args.name):
        print(f"error: --name 文法越界: {args.name!r}"
              "(安全路径段:首字符字母/数字,其余 [A-Za-z0-9_.-],不得为 '.'/'..')",
              file=sys.stderr)
        sys.exit(2)

    cwd = os.path.abspath(args.project)
    out_dir = (Path(args.output) if os.path.isabs(args.output)
               else Path(cwd) / args.output)

    if out_dir.exists() and not out_dir.is_dir():
        print(f"error: --output {out_dir} exists but is not a directory",
              file=sys.stderr)
        sys.exit(5)

    try:
        if args.session is not None:
            if not args.session.strip():
                print("error: --session 不能为空", file=sys.stderr)
                sys.exit(2)
            tool_name, item = find_session_in_cwd(cwd, args.session)
            if not tool_name:
                installed = [n for n in PRIORITY if PARSERS[n][0]()]
                if not installed:
                    print("error: no supported tool installed", file=sys.stderr)
                    sys.exit(4)
                print(f"error: session {args.session} not found in {cwd} (checked {installed})",
                      file=sys.stderr)
                sys.exit(3)
            items = [item]
        elif args.tool is not None:
            # 显式指定产品:跳过自动识别,直接在该产品内取当前(最近活跃)会话。
            avail, list_fn, _ = PARSERS[args.tool]
            if not avail():
                if args.tool in ("copilot", "hermes"):
                    # 探测式适配器无源:诚实声明,不臆造导出行为
                    print(_probe_no_source(args.tool), file=sys.stderr)
                else:
                    print(f"error: tool {args.tool} not installed", file=sys.stderr)
                sys.exit(4)
            items = list_fn(cwd)
            if not items:
                print(f"error: no {args.tool} session found for {cwd}",
                      file=sys.stderr)
                sys.exit(3)
            tool_name = args.tool
            items = [_choose_session(tool_name, items, cwd)]
        else:
            tool_name, items = detect_tool(cwd)
            if not tool_name:
                installed = [n for n in PRIORITY if PARSERS[n][0]()]
                if not installed:
                    print("error: no supported tool installed", file=sys.stderr)
                    sys.exit(4)
                print(f"error: no session found for {cwd} (checked {installed})",
                      file=sys.stderr)
                sys.exit(3)
            # 同工具多会话里选当前会话(Claude 用会话环境变量精确锁定,否则内容时间戳最新)
            items = [_choose_session(tool_name, items, cwd)]

        # 探测式适配器即使 available() 为真也未实现导出行为:诚实声明,不臆造
        if tool_name in ("copilot", "hermes"):
            print(_probe_no_source(tool_name), file=sys.stderr)
            sys.exit(4)

        # --verify 内容匹配二次确认:模型传入本轮对话独特文本,验证选中的 session 确实包含它
        if args.verify:
            sid, src, _ = items[0]
            if not _session_contains_text(src, args.verify):
                found = _verify_or_relocate(cwd, args.verify, tool_name, sid)
                if found:
                    tool_name, item = found
                    items = [item]
                    print(f"verify: relocated to [{tool_name}] {item[0][:12]}...",
                          file=sys.stderr)
                else:
                    print("verify: warning - text not found in any session, "
                          "proceeding with best match", file=sys.stderr)

        # 同名冲突:导出目录已存在 → 拒绝(无 --force 旁路;覆盖须由命令面交互确认后清空重写)
        bundle_dir = out_dir / args.name
        if bundle_dir.exists():
            print(f"error: 导出目录已存在,拒绝覆盖: {bundle_dir}"
                  f"(export directory already exists: {bundle_dir})", file=sys.stderr)
            sys.exit(2)

        out_dir.mkdir(parents=True, exist_ok=True)
        bundle_dir.mkdir()   # 不带 exist_ok:并发创建亦按冲突失败

        _, _, pack_fn = PARSERS[tool_name]
        total_entries = 0
        main_path = None
        try:
            for sid, src, _ in items:
                n = pack_fn(src, sid, bundle_dir)
                total_entries += n
                if main_path is None:
                    hits = sorted(Path(bundle_dir).glob("main.*"))
                    main_path = hits[0] if hits else None
            if main_path is None:
                raise OSError("internal error: main record not written to bundle")
            # 描述文档确定性半体:session-meta.json + SESSION.md(两形态同出)
            meta = _session_meta(tool_name, items[0][0], main_path)
            _write_description(bundle_dir, meta)
        except Exception:
            # 失败清理:不留半成品目录(否则同名冲突检查会挡住重试)
            shutil.rmtree(str(bundle_dir), ignore_errors=True)
            raise

        print(str(Path(bundle_dir).resolve()))
        budget_note = ("over summary budget" if meta["over_summary_budget"]
                       else "within summary budget")
        print(f"exported {len(items)} session(s) [{tool_name}], "
              f"{total_entries} file(s)/record(s) inside directory; {budget_note}",
              file=sys.stderr)
        sys.exit(0)

    except sqlite3.Error as e:
        print(f"error: sqlite: {e}", file=sys.stderr)
        sys.exit(5)
    except OSError as e:
        print(f"error: io: {e}", file=sys.stderr)
        sys.exit(5)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(5)


if __name__ == "__main__":
    main()

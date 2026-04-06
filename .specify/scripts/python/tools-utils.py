#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import dataclasses
import json
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

_ALLOWED_TOOL_TYPES = {
    "mcp",
    "system",
    "shell",
    "project",
    "mcp-call",
    "system-binary",
    "shell-function",
    "project-script",
}


@dataclass
class ToolArgument:
    name: str
    type: str
    required: bool
    description: str
    default: Optional[str] = None


@dataclass
class ToolRecord:
    name: str
    tool_type: str
    source_identifier: str
    description: str
    status: str = "Draft"
    aliases: List[str] = field(default_factory=list)
    arguments: List[ToolArgument] = field(default_factory=list)
    returns: List[dict] = field(default_factory=list)
    tool_id: Optional[str] = None
    last_updated: str = field(default_factory=lambda: date.today().isoformat())

    def validate(self) -> List[str]:
        errors: List[str] = []

        if not self.name or not self.name.strip():
            errors.append("name is required")
        if self.tool_type not in _ALLOWED_TOOL_TYPES:
            errors.append(
                "tool_type must be one of mcp/system/shell/project or "
                "mcp-call/system-binary/shell-function/project-script"
            )
        if not self.source_identifier or not self.source_identifier.strip():
            errors.append("source_identifier is required")
        if not self.description or not self.description.strip():
            errors.append("description is required")

        if self.status.lower() == "verified" and not self.arguments and not self.returns:
            errors.append("Verified record must include arguments or returns")

        return errors


@dataclass
class ToolInvocationSession:
    requested_name: str
    resolved_name: str
    resolved_type: str
    used_existing_record: bool
    disambiguation_required: bool
    user_confirmed_execution: bool
    result_status: str
    result_summary: str

    def validate(self) -> List[str]:
        errors: List[str] = []
        if self.resolved_type not in _ALLOWED_TOOL_TYPES:
            errors.append("resolved_type must be a supported tool type")
        if not self.user_confirmed_execution and self.result_status != "cancelled":
            errors.append(
                "result_status must be cancelled when user_confirmed_execution is false"
            )
        return errors


class ResourceIdError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _normalize_workspace_path(path: str | Path, workspace_root: str | Path) -> str:
    root = Path(workspace_root).resolve()
    target = Path(path)
    if not target.is_absolute():
        target = root / target
    target = target.resolve()
    try:
        return target.relative_to(root).as_posix()
    except ValueError as exc:
        raise ResourceIdError("out-of-workspace", "Path is outside workspace") from exc


def _generate_tool_id(artifact_path: str | Path, workspace_root: str | Path) -> str:
    canonical = _normalize_workspace_path(artifact_path, workspace_root)
    return f"<TOOL:{canonical}>"


def _record_path(tools_dir: Path, name: str) -> Path:
    return tools_dir / f"{name}.md"


def _normalize_tool_type(tool_type: str) -> str:
    mapping = {
        "mcp": "mcp-call",
        "system": "system-binary",
        "shell": "shell-function",
        "project": "project-script",
    }
    return mapping.get(tool_type, tool_type)


def save_record(tools_dir: Path, record: Any) -> Path:
    tools_dir.mkdir(parents=True, exist_ok=True)
    record.last_updated = date.today().isoformat()
    if not record.tool_id:
        record_file = _record_path(tools_dir, record.name)
        root = tools_dir
        while root.name != ".specify" and root.parent != root:
            root = root.parent
        workspace_root = root.parent if root.name == ".specify" else tools_dir.parents[2]
        record.tool_id = _generate_tool_id(record_file, workspace_root)

    record_file = _record_path(tools_dir, record.name)
    lines = [
        f"# Tool Record: {record.name}",
        "",
        f"**Tool Name**: {record.name}",
        f"**Tool Type**: `{_normalize_tool_type(record.tool_type)}`",
        f"**Source Identifier**: {record.source_identifier}",
        f"**Tool ID**: {record.tool_id}",
        f"**Aliases**: {', '.join(record.aliases) if record.aliases else ''}",
        f"**Status**: {record.status}",
        f"**Last Updated**: {record.last_updated}",
        "",
        "## Description",
        "",
        record.description,
        "",
        "## Parameters",
    ]

    if record.arguments:
        lines.extend(
            [
                "",
                "| Name | Type | Required | Description | Default |",
                "|------|------|----------|-------------|---------|",
            ]
        )
        for argument in record.arguments:
            lines.append(
                "| {name} | {type_} | {required} | {description} | {default} |".format(
                    name=argument.name,
                    type_=argument.type,
                    required="yes" if argument.required else "no",
                    description=argument.description,
                    default=argument.default or "",
                )
            )
    else:
        lines.extend(["", "- None"])

    lines.extend(["", "## Returns", "", "- None"])
    record_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return record_file


def load_record(tools_dir: Path, name: str) -> Optional[ToolRecord]:
    record_file = _record_path(tools_dir, name)
    if not record_file.exists():
        return None

    content = record_file.read_text(encoding="utf-8")
    fields = {}
    for line in content.splitlines():
        if line.startswith("**") and "**:" in line:
            key, value = line.split("**:", 1)
            normalized_key = key.replace("**", "").strip().lower().replace(" ", "_")
            fields[normalized_key] = value.strip().strip("`")

    description = ""
    if "## Description" in content:
        description_block = content.split("## Description", 1)[1]
        if "## Parameters" in description_block:
            description = description_block.split("## Parameters", 1)[0].strip()

    aliases = [a.strip() for a in fields.get("aliases", "").split(",") if a.strip()]

    record = ToolRecord(
        name=fields.get("tool_name", name),
        tool_type=fields.get("tool_type", ""),
        source_identifier=fields.get("source_identifier", ""),
        description=description,
        status=fields.get("status", "Draft"),
        aliases=aliases,
        tool_id=fields.get("tool_id") or None,
        arguments=[],
    )
    return record


def add_alias(record: Any, alias: str) -> None:
    cleaned = alias.strip()
    if cleaned and cleaned not in record.aliases and cleaned != record.name:
        record.aliases.append(cleaned)


def resolve_alias(name_or_alias: str, records: Iterable[Any]) -> Tuple[Optional[Any], Optional[str]]:
    for record in records:
        if record.name == name_or_alias:
            return record, None
        if name_or_alias in record.aliases:
            return record, name_or_alias
    return None, None


def rename_record(
    tools_dir: Path,
    record: Any,
    new_name: str,
    existing_records: Iterable[Any],
) -> Any:
    for existing in existing_records:
        if existing.name == new_name and existing.name != record.name:
            raise ValueError(f"Record name conflict: {new_name}")

    old_path = _record_path(tools_dir, record.name)
    record.name = new_name
    new_path = _record_path(tools_dir, record.name)

    if old_path.exists():
        old_path.rename(new_path)
    return record


def backfill_tool_id(record_file: Path, workspace_root: Path) -> Optional[str]:
    content = record_file.read_text(encoding="utf-8")
    if "**Tool ID**:" in content:
        return None

    tool_id = _generate_tool_id(record_file, workspace_root)
    lines = content.splitlines()
    updated = []
    inserted = False
    for line in lines:
        updated.append(line)
        if line.startswith("**Source Identifier**:") and not inserted:
            updated.append(f"**Tool ID**: {tool_id}")
            inserted = True

    record_file.write_text("\n".join(updated) + "\n", encoding="utf-8")
    return tool_id


def _group_tools_by_server() -> Dict[str, List[dict]]:
    from cws_ai.mcp import get_all_tools

    tools = get_all_tools()
    tools_by_server: Dict[str, List[dict]] = {}
    for tool in tools:
        tools_by_server.setdefault(tool.server_name, []).append(dataclasses.asdict(tool))
    return tools_by_server


def get_mcp_payload() -> dict:
    from cws_ai.mcp import get_all_mcp_servers

    servers = get_all_mcp_servers()
    tools_by_server = _group_tools_by_server()

    servers_payload = []
    for server in servers:
        server_data = dataclasses.asdict(server)
        server_tools = tools_by_server.get(server.name, [])
        server_data["tools"] = server_tools
        server_data["tools_count"] = len(server_tools)
        servers_payload.append(server_data)

    return {
        "timestamp": datetime.now().isoformat(),
        "count": len(servers_payload),
        "servers": servers_payload,
        "note": "This list represents configured MCP servers. 'tools' field populated for HTTP servers if reachable.",
    }


def find_root_dir(start: Optional[Path] = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
        if (candidate / "pyproject.toml").exists() and (candidate / "scripts").exists():
            return candidate
    return current


def detect_scripts_dir(root_dir: Path) -> Optional[Path]:
    specify_scripts = root_dir / ".specify" / "scripts"
    local_scripts = root_dir / "scripts"
    if specify_scripts.exists() and specify_scripts.is_dir():
        return specify_scripts
    if local_scripts.exists() and local_scripts.is_dir():
        return local_scripts
    return None


def extract_python_docstring(file_path: Path) -> str:
    try:
        content = file_path.read_text(encoding="utf-8")
        doc = ast.get_docstring(ast.parse(content))
        if doc:
            return doc.splitlines()[0].strip()
    except Exception:
        pass
    return "No description available"


def extract_shell_comment(file_path: Path) -> str:
    try:
        for line in file_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#!"):
                continue
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip() or "No description available"
    except Exception:
        pass
    return "No description available"


def list_project_scripts(root_dir: Path) -> List[Dict[str, str]]:
    scripts_dir = detect_scripts_dir(root_dir)
    if not scripts_dir:
        return []

    results: List[Dict[str, str]] = []
    for file_path in sorted(scripts_dir.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.suffix not in {".sh", ".py"}:
            continue

        rel_path = file_path.resolve().relative_to(root_dir.resolve()).as_posix()
        script_type = "python" if file_path.suffix == ".py" else "bash"
        if script_type == "python":
            description = extract_python_docstring(file_path)
        else:
            description = extract_shell_comment(file_path)

        results.append(
            {
                "name": file_path.name,
                "path": rel_path,
                "type": script_type,
                "description": description,
            }
        )
    return results


_SHELL_PROFILE_SOURCES = """
[ -f /etc/profile ] && source /etc/profile
[ -f ~/.bashrc ] && source ~/.bashrc
[ -f ~/.profile ] && source ~/.profile
[ -f ~/.bash_profile ] && source ~/.bash_profile
"""


def get_shell_functions() -> List[Dict[str, str]]:
    try:
        cmd = f"{_SHELL_PROFILE_SOURCES}\ncompgen -A function | sort"
        result = subprocess.run(
            ["bash", "-c", cmd],
            capture_output=True,
            text=True,
            check=False,
        )
        functions = []
        for line in result.stdout.strip().split("\n"):
            func_name = line.strip()
            if func_name and not func_name.startswith("_"):
                functions.append({"name": func_name})
        return functions
    except Exception:
        return []


def get_shell_info() -> Dict[str, Any]:
    functions = get_shell_functions()
    return {
        "functions": functions,
        "count": len(functions),
    }


def get_os_release() -> str:
    os_release_path = Path("/etc/os-release")
    if os_release_path.exists():
        try:
            return os_release_path.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    return ""


def get_kernel_info() -> str:
    try:
        result = subprocess.run(
            ["uname", "-a"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip()
    except Exception:
        return f"{platform.system()} {platform.release()}"


def get_system_binaries() -> List[Dict[str, str]]:
    binaries_to_check = [
        "git",
        "docker",
        "kubectl",
        "python3",
        "python",
        "pip",
        "pip3",
        "node",
        "npm",
        "hatch",
        "gh",
        "jq",
        "curl",
        "wget",
        "make",
        "uv",
        "uvx",
    ]

    found_binaries = []
    for binary in binaries_to_check:
        path = shutil.which(binary)
        if path:
            found_binaries.append({"name": binary, "path": path})

    return found_binaries


def get_system_info() -> Dict[str, Any]:
    return {
        "os_release": get_os_release(),
        "kernel": get_kernel_info(),
        "binaries": get_system_binaries(),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unified tools utilities")
    parser.add_argument(
        "--action",
        required=True,
        choices=["list", "model-validate-record", "record-backfill", "record-load"],
    )
    parser.add_argument("--type", choices=["mcp", "system", "shell", "project"], default=None)
    parser.add_argument("--functions-only", action="store_true")
    parser.add_argument("--root-dir", default=".")

    parser.add_argument("--name", default=None)
    parser.add_argument("--tool-type", default=None)
    parser.add_argument("--source-identifier", default=None)
    parser.add_argument("--description", default=None)

    parser.add_argument("--record-file", default=None)
    parser.add_argument("--workspace-root", default=None)
    parser.add_argument("--tools-dir", default=None)

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.action == "list":
        if args.type == "mcp":
            if not os.environ.get("MCP_AUTH"):
                print("[Error] MCP_AUTH environment variable is not set.", file=os.sys.stderr)
                return 1
            payload = get_mcp_payload()
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0

        if args.type == "system":
            print(json.dumps(get_system_info(), indent=2, ensure_ascii=False))
            return 0

        if args.type == "shell":
            payload = get_shell_info()
            if args.functions_only:
                print(json.dumps(payload.get("functions", []), ensure_ascii=False))
            else:
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0

        if args.type == "project":
            root_dir = find_root_dir(Path(args.root_dir))
            records = list_project_scripts(root_dir)
            print(json.dumps(records, ensure_ascii=False, indent=2))
            return 0

        parser.error("--action list requires --type")

    if args.action == "model-validate-record":
        if not all([args.name, args.tool_type, args.source_identifier, args.description]):
            parser.error("model-validate-record requires --name --tool-type --source-identifier --description")
        record = ToolRecord(
            name=args.name,
            tool_type=args.tool_type,
            source_identifier=args.source_identifier,
            description=args.description,
        )
        print(json.dumps({"errors": record.validate()}))
        return 0

    if args.action == "record-backfill":
        if not args.record_file or not args.workspace_root:
            parser.error("record-backfill requires --record-file --workspace-root")
        value = backfill_tool_id(Path(args.record_file), Path(args.workspace_root))
        print(value or "")
        return 0

    if args.action == "record-load":
        if not args.tools_dir or not args.name:
            parser.error("record-load requires --tools-dir --name")
        record = load_record(Path(args.tools_dir), args.name)
        if record is None:
            print("")
        else:
            print(record.name)
        return 0

    parser.error("Unknown action")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

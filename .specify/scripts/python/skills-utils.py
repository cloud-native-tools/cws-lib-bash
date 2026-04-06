#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional, Tuple


class ResourceIdError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


_TYPE_TO_TAG = {"tool": "TOOL", "skill": "SKILL"}
_TAG_TO_TYPE = {value: key for key, value in _TYPE_TO_TAG.items()}


def normalize_workspace_path(path: str | Path, workspace_root: str | Path) -> str:
    root = Path(workspace_root).resolve()
    target = Path(path)
    if not target.is_absolute():
        target = root / target
    target = target.resolve()

    try:
        relative = target.relative_to(root)
    except ValueError as exc:
        raise ResourceIdError("out-of-workspace", "Path is outside workspace") from exc

    return relative.as_posix()


def infer_resource_type_from_path(canonical_path: str) -> Optional[str]:
    if canonical_path.startswith(".specify/memory/tools/") and canonical_path.endswith(".md"):
        return "tool"
    if canonical_path.startswith(".github/skills/") and canonical_path.endswith("/SKILL.md"):
        return "skill"
    return None


def format_resource_id(resource_type: str, canonical_path: str) -> str:
    tag = _TYPE_TO_TAG.get(resource_type)
    if not tag:
        raise ResourceIdError("invalid-type", f"Unsupported resource type: {resource_type}")
    return f"<{tag}:{canonical_path}>"


def parse_resource_id(resource_id: str) -> Tuple[Optional[str], str]:
    value = resource_id.strip()
    if not value:
        raise ResourceIdError("invalid-path", "Resource id is empty")

    if value.startswith("<") and value.endswith(">"):
        inner = value[1:-1]
        if ":" not in inner:
            raise ResourceIdError("invalid-path", "Wrapped resource id must contain type prefix")
        tag, canonical_path = inner.split(":", 1)
        resource_type = _TAG_TO_TYPE.get(tag.upper())
        if not resource_type:
            raise ResourceIdError("invalid-type", f"Unsupported resource id type tag: {tag}")
        return resource_type, canonical_path

    return None, value


def infer_resource_type(resource_id_or_path: str) -> Optional[str]:
    try:
        wrapped_type, canonical_path = parse_resource_id(resource_id_or_path)
    except ResourceIdError:
        return None

    if wrapped_type:
        return wrapped_type
    return infer_resource_type_from_path(canonical_path)


def validate_resource_id(resource_id: str, expected_type: str | None = None) -> Tuple[bool, Optional[str]]:
    if not resource_id or not resource_id.strip():
        return False, "invalid-path"

    try:
        wrapped_type, canonical_path = parse_resource_id(resource_id)
    except ResourceIdError as exc:
        return False, exc.code

    if canonical_path.startswith("/"):
        return False, "invalid-path"
    if ".." in canonical_path.split("/"):
        return False, "invalid-path"

    inferred_path_type = infer_resource_type_from_path(canonical_path)
    if wrapped_type and inferred_path_type and wrapped_type != inferred_path_type:
        return False, "invalid-type"

    inferred = wrapped_type or inferred_path_type
    if expected_type and inferred and inferred != expected_type:
        return False, "invalid-type"

    return True, None


def generate_resource_id(
    resource_type: str,
    artifact_path: str | Path,
    workspace_root: str | Path,
) -> str:
    canonical = normalize_workspace_path(artifact_path, workspace_root)
    inferred = infer_resource_type_from_path(canonical)
    if inferred and inferred != resource_type:
        raise ResourceIdError(
            "invalid-type",
            f"Resource type mismatch: expected {resource_type}, got {inferred}",
        )
    return format_resource_id(resource_type, canonical)


def resolve_resource_id(resource_id: str, workspace_root: str | Path) -> Path:
    root = Path(workspace_root).resolve()
    valid, code = validate_resource_id(resource_id)
    if not valid:
        raise ResourceIdError(code or "invalid-path", "Invalid resource id")

    _, canonical_path = parse_resource_id(resource_id)
    target = (root / canonical_path).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ResourceIdError("out-of-workspace", "Resolved path outside workspace") from exc

    if not target.exists():
        raise ResourceIdError("stale-id", "Resource id points to missing artifact")

    return target


def skill_file_path(skill_root: Path) -> Path:
    return skill_root / "SKILL.md"


def generate_skill_id(skill_root: Path, workspace_root: Path) -> str:
    return generate_resource_id("skill", skill_file_path(skill_root), workspace_root)


def read_skill_id(skill_file: Path) -> Optional[str]:
    for line in skill_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("skill_id:"):
            return line.split(":", 1)[1].strip().strip('"')
    return None


def persist_skill_id(skill_file: Path, skill_id: str) -> None:
    content = skill_file.read_text(encoding="utf-8")
    lines = content.splitlines()

    if any(line.startswith("skill_id:") for line in lines):
        updated = [
            f'skill_id: "{skill_id}"' if line.startswith("skill_id:") else line
            for line in lines
        ]
        skill_file.write_text("\n".join(updated) + "\n", encoding="utf-8")
        return

    if lines and lines[0].strip() == "---":
        insert_at = 1
        while insert_at < len(lines) and lines[insert_at].strip() != "---":
            insert_at += 1
        lines.insert(insert_at, f'skill_id: "{skill_id}"')
        skill_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    skill_file.write_text(f"skill_id: \"{skill_id}\"\n" + content, encoding="utf-8")


def backfill_skill_id(skill_file: Path, workspace_root: Path) -> Optional[str]:
    existing = read_skill_id(skill_file)
    if existing:
        return None

    skill_root = skill_file.parent
    skill_id = generate_skill_id(skill_root, workspace_root)
    persist_skill_id(skill_file, skill_id)
    return skill_id


@dataclass
class ResolutionResult:
    result_type: str
    resolved_type: Optional[str]
    resolved_id: Optional[str]
    resolved_path: Optional[str]
    message: str
    fallback_used: bool = False


class ResolutionConflictError(ValueError):
    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason


def _backfill_tool_id(record_file: Path, workspace_root: Path) -> Optional[str]:
    content = record_file.read_text(encoding="utf-8")
    if "**Tool ID**:" in content:
        return None
    canonical = record_file.resolve().relative_to(workspace_root.resolve()).as_posix()
    tool_id = format_resource_id("tool", canonical)
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


def _backfill_skill_id(skill_file: Path, workspace_root: Path) -> Optional[str]:
    lines = skill_file.read_text(encoding="utf-8").splitlines()
    if any(line.startswith("skill_id:") for line in lines):
        return None
    canonical = skill_file.resolve().relative_to(workspace_root.resolve()).as_posix()
    skill_id = format_resource_id("skill", canonical)
    if lines and lines[0].strip() == "---":
        end = 1
        while end < len(lines) and lines[end].strip() != "---":
            end += 1
        lines.insert(end, f'skill_id: "{skill_id}"')
        skill_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        skill_file.write_text(f'skill_id: "{skill_id}"\n' + "\n".join(lines) + "\n", encoding="utf-8")
    return skill_id


def _discover_by_text(
    requested_text: str,
    workspace_root: Path,
    expected_type: Optional[str] = None,
) -> ResolutionResult:
    text = requested_text.lower().strip()
    matches = []

    if expected_type in (None, "tool"):
        tools_dir = workspace_root / ".specify" / "memory" / "tools"
        if tools_dir.exists():
            for file in tools_dir.glob("*.md"):
                if text in file.stem.lower():
                    rel = file.relative_to(workspace_root).as_posix()
                    matches.append(("tool", rel))

    if expected_type in (None, "skill"):
        skills_dir = workspace_root / ".github" / "skills"
        if skills_dir.exists():
            for file in skills_dir.glob("*/SKILL.md"):
                if text in file.parent.name.lower():
                    rel = file.relative_to(workspace_root).as_posix()
                    matches.append(("skill", rel))

    if not matches:
        raise ResourceIdError("not-found", "No artifact matched the provided hint")
    if len(matches) > 1:
        raise ResolutionConflictError("hint-conflict", "Multiple artifacts match the hint")

    resolved_type, canonical_path = matches[0]
    resolved_id = format_resource_id(resolved_type, canonical_path)
    return ResolutionResult(
        result_type="fallback",
        resolved_type=resolved_type,
        resolved_id=resolved_id,
        resolved_path=canonical_path,
        message="Resolved using natural-language fallback",
        fallback_used=True,
    )


def resolve_resource(
    workspace_root: str | Path,
    requested_id: Optional[str] = None,
    requested_text: Optional[str] = None,
    expected_type: Optional[str] = None,
) -> ResolutionResult:
    root = Path(workspace_root).resolve()

    if requested_id:
        resolved_path = resolve_resource_id(requested_id, root)
        resolved_type = infer_resource_type(requested_id)
        _, canonical_path = parse_resource_id(requested_id)

        if expected_type and resolved_type and resolved_type != expected_type:
            raise ResolutionConflictError("type-mismatch", "Resolved type mismatches expected type")

        if requested_text:
            hint = requested_text.lower().strip()
            basename = resolved_path.stem.lower()
            parent_name = resolved_path.parent.name.lower()
            if hint and hint not in basename and hint not in parent_name:
                raise ResolutionConflictError(
                    "hint-conflict",
                    "resource_id and natural-language hint point to different artifacts",
                )

        resolved_id = requested_id
        if resolved_type:
            resolved_id = format_resource_id(resolved_type, canonical_path)

        return ResolutionResult(
            result_type="resolved",
            resolved_type=resolved_type,
            resolved_id=resolved_id,
            resolved_path=resolved_path.relative_to(root).as_posix(),
            message="Resolved by canonical resource id",
            fallback_used=False,
        )

    if requested_text:
        return _discover_by_text(requested_text, root, expected_type)

    raise ResourceIdError("invalid-path", "Either requested_id or requested_text is required")


def backfill_resource_id(
    workspace_root: str | Path,
    resource_type: str,
    persistence_target: str | Path,
) -> str:
    root = Path(workspace_root).resolve()
    target = Path(persistence_target)
    if not target.is_absolute():
        target = (root / target).resolve()

    if resource_type == "tool":
        result = _backfill_tool_id(target, root)
    elif resource_type == "skill":
        result = _backfill_skill_id(target, root)
    else:
        raise ResourceIdError("invalid-type", f"Unsupported resource type: {resource_type}")

    if result is None:
        rel = target.relative_to(root).as_posix()
        return format_resource_id(resource_type, rel)

    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unified skills/resource-id utilities")
    parser.add_argument(
        "--action",
        required=True,
        choices=[
            "generate",
            "validate",
            "parse",
            "resolve-path",
            "resolve",
            "backfill",
            "skill-generate",
            "skill-read",
            "skill-backfill",
        ],
    )

    parser.add_argument("--resource-type", choices=["tool", "skill"], default=None)
    parser.add_argument("--artifact-path", default=None)
    parser.add_argument("--workspace-root", default=None)
    parser.add_argument("--resource-id", default=None)
    parser.add_argument("--expected-type", choices=["tool", "skill"], default=None)

    parser.add_argument("--requested-id", default=None)
    parser.add_argument("--requested-text", default=None)
    parser.add_argument("--persistence-target", default=None)
    parser.add_argument("--skill-root", default=None)
    parser.add_argument("--skill-file", default=None)

    parser.add_argument("--field", choices=["json", "id", "path", "type"], default="json")

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.action == "generate":
        if not all([args.resource_type, args.artifact_path, args.workspace_root]):
            parser.error("generate requires --resource-type --artifact-path --workspace-root")
        value = generate_resource_id(args.resource_type, args.artifact_path, args.workspace_root)
        print(value)
        return

    if args.action == "validate":
        if not args.resource_id:
            parser.error("validate requires --resource-id")
        valid, error_code = validate_resource_id(args.resource_id, args.expected_type)
        print(json.dumps({"valid": valid, "error_code": error_code}))
        return

    if args.action == "parse":
        if not args.resource_id:
            parser.error("parse requires --resource-id")
        resource_type, canonical_path = parse_resource_id(args.resource_id)
        print(json.dumps({"resource_type": resource_type, "canonical_path": canonical_path}))
        return

    if args.action == "resolve-path":
        if not args.resource_id or not args.workspace_root:
            parser.error("resolve-path requires --resource-id --workspace-root")
        path = resolve_resource_id(args.resource_id, args.workspace_root)
        print(path.as_posix())
        return

    if args.action == "resolve":
        if not args.workspace_root:
            parser.error("resolve requires --workspace-root")
        result = resolve_resource(
            workspace_root=args.workspace_root,
            requested_id=args.requested_id,
            requested_text=args.requested_text,
            expected_type=args.expected_type,
        )
        if args.field == "id":
            print(result.resolved_id or "")
        elif args.field == "path":
            print(result.resolved_path or "")
        elif args.field == "type":
            print(result.resolved_type or "")
        else:
            print(json.dumps(asdict(result), ensure_ascii=False))
        return

    if args.action == "backfill":
        if not all([args.workspace_root, args.resource_type, args.persistence_target]):
            parser.error("backfill requires --workspace-root --resource-type --persistence-target")
        value = backfill_resource_id(args.workspace_root, args.resource_type, args.persistence_target)
        print(value)
        return

    if args.action == "skill-generate":
        if not args.skill_root or not args.workspace_root:
            parser.error("skill-generate requires --skill-root --workspace-root")
        print(generate_skill_id(Path(args.skill_root), Path(args.workspace_root)))
        return

    if args.action == "skill-read":
        if not args.skill_file:
            parser.error("skill-read requires --skill-file")
        value = read_skill_id(Path(args.skill_file))
        print(value or "")
        return

    if args.action == "skill-backfill":
        if not args.skill_file or not args.workspace_root:
            parser.error("skill-backfill requires --skill-file --workspace-root")
        value = backfill_skill_id(Path(args.skill_file), Path(args.workspace_root))
        print(value or "")
        return

    parser.error("Unknown action")


if __name__ == "__main__":
    main()

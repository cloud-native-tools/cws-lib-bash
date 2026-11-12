#!/usr/bin/env python3
"""
Unified database query dispatcher.
Routes queries to MySQL or PostgreSQL handlers based on connection config.
"""

import json
import os
import stat
import sys
import argparse
import importlib.util
from pathlib import Path
from typing import Optional

# Constants
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_LOCATIONS = [
    SKILL_DIR / "connections.json",
    Path.home() / ".config" / "claude" / "db-connections.json",
]

# Default port-to-protocol mapping for inference
PORT_PROTOCOL_MAP = {
    3306: "mysql",
    9030: "mysql",   # Apache Doris / SelectDB
    5432: "postgres",
    9005: "postgres", # ClickHouse (PostgreSQL wire protocol)
}


def validate_config_permissions(path: Path) -> None:
    """Warn if config file has insecure permissions (Unix only)."""
    if os.name != 'nt':
        mode = path.stat().st_mode
        if bool(mode & stat.S_IRWXG) or bool(mode & stat.S_IRWXO):
            print(f"WARNING: {path} has insecure permissions!")
            print(f"Config contains credentials. Run: chmod 600 {path}")


def find_config() -> Optional[Path]:
    """Find config file in supported locations."""
    for path in CONFIG_LOCATIONS:
        if path.exists():
            return path
    return None


def load_config(config_path: Optional[Path] = None) -> dict:
    """Load database connections from JSON config."""
    path = config_path or find_config()
    if not path:
        print("Config not found. Searched:")
        for loc in CONFIG_LOCATIONS:
            print(f"  - {loc}")
        print("\nCreate connections.json with format:")
        print(json.dumps({
            "databases": [{
                "name": "mydb",
                "description": "Description of database contents",
                "protocol": "mysql",
                "host": "localhost",
                "port": 3306,
                "database": "mydb",
                "user": "user",
                "password": "password"
            }]
        }, indent=2))
        sys.exit(1)

    validate_config_permissions(path)

    with open(path) as f:
        return json.load(f)


def determine_protocol(db: dict) -> str:
    """Determine the database protocol from config entry.

    Priority:
    1. Explicit 'protocol' field
    2. Infer from port number
    3. Default to 'mysql'
    """
    protocol = db.get("protocol")
    if protocol:
        protocol = protocol.lower()
        if protocol in ("mysql", "postgres", "postgresql"):
            return "mysql" if protocol == "mysql" else "postgres"
        print(f"Error: Unknown protocol '{protocol}'. Supported: mysql, postgres")
        sys.exit(1)

    port = db.get("port")
    if port and port in PORT_PROTOCOL_MAP:
        return PORT_PROTOCOL_MAP[port]

    # Default fallback
    return "mysql"


def load_handler(protocol: str):
    """Dynamically load the protocol-specific query module."""
    if protocol == "mysql":
        module_path = SCRIPT_DIR / "query_mysql.py"
    elif protocol == "postgres":
        module_path = SCRIPT_DIR / "query_postgres.py"
    else:
        print(f"Error: No handler for protocol '{protocol}'")
        sys.exit(1)

    if not module_path.exists():
        print(f"Error: Handler not found: {module_path}")
        sys.exit(1)

    spec = importlib.util.spec_from_file_location(f"query_{protocol}", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def list_databases(config: dict) -> None:
    """List all configured databases with their protocol."""
    print("Configured databases:\n")
    for db in config.get("databases", []):
        protocol = determine_protocol(db)
        default_port = 3306 if protocol == "mysql" else 5432
        print(f"  [{db.get('name', 'unnamed')}]")
        print(f"    Protocol: {protocol}")
        print(f"    Host: {db.get('host', '?')}:{db.get('port', default_port)}")
        print(f"    Database: {db.get('database', '?')}")
        print(f"    Description: {db.get('description', 'No description')}")
        print()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Execute read-only database queries (MySQL/PostgreSQL)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list
  %(prog)s --db mydb --tables
  %(prog)s --db mydb --schema
  %(prog)s --db mydb --query "SELECT * FROM users" --limit 100
        """
    )
    parser.add_argument("--config", "-c", type=Path, help="Path to config JSON")
    parser.add_argument("--db", "-d", help="Database name to query")
    parser.add_argument("--query", "-q", help="SQL query to execute")
    parser.add_argument("--limit", "-l", type=int, help="Limit rows returned")
    parser.add_argument("--list", action="store_true", help="List configured databases")
    parser.add_argument("--schema", "-s", action="store_true", help="Show database schema")
    parser.add_argument("--tables", "-t", action="store_true", help="List tables")

    args = parser.parse_args()
    config = load_config(args.config)

    if args.list:
        list_databases(config)
        return

    if not args.db:
        print("Error: --db required. Use --list to see available databases.")
        sys.exit(1)

    # Find the database entry
    db_config = None
    for db in config.get("databases", []):
        if db.get("name", "").lower() == args.db.lower():
            db_config = db
            break

    if not db_config:
        available = [db.get("name", "unnamed") for db in config.get("databases", [])]
        print(f"Database '{args.db}' not found.")
        print(f"Available: {', '.join(available)}")
        sys.exit(1)

    # Determine protocol and load handler
    protocol = determine_protocol(db_config)
    handler = load_handler(protocol)

    # Validate config using handler's validator
    handler.validate_db_config(db_config)

    if args.tables:
        if protocol == "mysql":
            query = """
                SELECT table_name, table_type, engine, table_rows
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                ORDER BY table_name
            """
        else:
            query = """
                SELECT table_schema, table_name, table_type
                FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY table_schema, table_name
            """
        handler.execute_query(db_config, query, args.limit)
    elif args.schema:
        if protocol == "mysql":
            query = """
                SELECT c.table_name, c.column_name, c.data_type, c.column_type,
                       c.is_nullable, c.column_key, c.extra
                FROM information_schema.columns c
                JOIN information_schema.tables t
                    ON c.table_name = t.table_name AND c.table_schema = t.table_schema
                WHERE c.table_schema = DATABASE()
                ORDER BY c.table_name, c.ordinal_position
            """
        else:
            query = """
                SELECT c.table_schema, c.table_name, c.column_name, c.data_type, c.is_nullable
                FROM information_schema.columns c
                JOIN information_schema.tables t ON c.table_name = t.table_name AND c.table_schema = t.table_schema
                WHERE c.table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY c.table_schema, c.table_name, c.ordinal_position
            """
        handler.execute_query(db_config, query, args.limit)
    elif args.query:
        handler.execute_query(db_config, args.query, args.limit)
    else:
        print("Error: --query, --tables, or --schema required")
        sys.exit(1)


#
# Emitted by `.specify/scripts/python/sync-mirrors.py`; the authority for this block is
# `contracts/mirror-projection.contract.md` C-34 / C-36. It depends on nothing
# that exists only in the source tree: it re-derives its own version line (C-36).
_VERSION_SOURCE = "pyproject.toml"
_VERSION_QUOTES = chr(39) + chr(34)
_MAX_UPWARD_LEVELS = 12


def _bridge_version(start):
    _here = start.resolve()
    for _ in range(_MAX_UPWARD_LEVELS + 1):
        if (_here / _VERSION_SOURCE).is_file() and (_here / ".git").exists():
            try:
                _text = (_here / _VERSION_SOURCE).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                return "unknown"
            _in_project = False
            for _raw in _text.splitlines():
                _line = _raw.strip()
                if not _line or _line.startswith("#"):
                    continue
                if _line.startswith("[") and _line.endswith("]"):
                    _in_project = _line == "[project]"
                    continue
                if not _in_project:
                    continue
                _key, _sep, _value = _line.partition("=")
                if _sep and _key.strip() == "version":
                    _value = _value.strip()
                    if len(_value) >= 2 and _value[0] == _value[-1] and _value[0] in _VERSION_QUOTES:
                        _value = _value[1:-1]
                    return _value or "unknown"
            return "unknown"
        if _here.parent == _here:
            return "unknown"
        _here = _here.parent
    return "unknown"

def _bridge_main():
    import sys as _bridge_sys
    from pathlib import Path as _bridge_path

    _argv = list(_bridge_sys.argv[1:])
    if "--version" not in _argv:
        return
    if "--" in _argv and _argv.index("--version") > _argv.index("--"):
        return
    _invoked = _bridge_sys.argv[0] if _bridge_sys.argv[0] else "."
    _name = _bridge_path(_invoked).name or "script"
    print("%s %s" % (_name, _bridge_version(_bridge_path(_invoked).resolve().parent)))
    raise SystemExit(0)


_bridge_main()
del _bridge_main
# script-interface:86:begin (feature 086 -- generated; the rule is owned by
# `.specify/shared/definitions/script-interface-definitions.md`, its executable form by
# `.specify/scripts/python/script_interface_cli.py`. This block owns no rule of its own.)
import sys as _sig_sys
import pathlib as _sig_pathlib

_SIG_OWNER = _sig_pathlib.Path(__file__).resolve().parent
while not ((_SIG_OWNER / 'pyproject.toml').is_file()
           and (_SIG_OWNER / '.git').exists()) and _SIG_OWNER.parent != _SIG_OWNER:
    _SIG_OWNER = _SIG_OWNER.parent
_SIG_OWNER = str(_SIG_OWNER / 'scripts' / 'python')
if _SIG_OWNER not in _sig_sys.path:
    _sig_sys.path.insert(0, _SIG_OWNER)

_SIG_SCRIPT = '.specify/skills/database-utils/scripts/query.py'
_SIG_DECLARED = ('--config', '--db', '--limit', '--list', '--query', '--schema', '--tables', '-c', '-d', '-l', '-q', '-s', '-t')
_SIG_HELP = (
    'usage: query.py [options]\n'
    'options:\n'
    '  --config\n  --db\n  --limit\n  --list\n  --query\n  --schema\n  --tables\n  -c\n  -d\n  -l\n  -q\n  -s\n  -t\n'
    '  -h, --help    print this help and exit\n'
    '  --version     print the script name and the framework version, then exit\n'
    +
    'side-effects:' + ' ' + 'writes only through the options it documents; a flag-only invocation writes nothing' + '\n'
    +
    'exit-codes:' + ' ' + '0 success; 1 a documented check failed; 2 argument or environment error' + '\n'
)


def _sig_guard(argv):
    # Answer the flags and reject an undeclared option before any parsing or write.
    # RULES are asked of the owner (script_interface_cli.guard_argv), never restated:
    # the declared vocabulary and the flag forms are its, and C-9 (a recognized option
    # never rescues an unrecognized one) is its judgement. What stays local is the help
    # BODY, because its operand sentence is this script's own.
    try:
        import script_interface_cli as _sig  # noqa: E402 -- deferred: a copied script may lack it
    except ImportError:  # skill-local or sandbox copy: the module's own parser still runs
        return list(argv)
    line = list(argv)
    try:
        _sig.guard_argv(line, declared=_SIG_DECLARED)
    except SystemExit as answered:  # what guard_argv raises; _sig_sys.exit IS SystemExit
        if answered.code == 0:
            raise
        # The owner prints the rejection line and this script's help body is appended after
        # it, so the reader sees the vocabulary and not only the refusal.
        _sig_sys.stderr.write(_SIG_HELP)
        raise _sig_sys.exit(answered.code)
    stop = line.index('--') if '--' in line else len(line)
    if '-h' in line[:stop] or '--help' in line[:stop]:
        _sig_sys.stdout.write(_SIG_HELP)
        raise _sig_sys.exit(0)
    return line

if __name__ == "__main__":
    _sig_sys.argv = [_sig_sys.argv[0]] + _sig_guard(_sig_sys.argv[1:])
# script-interface:86:end

if __name__ == "__main__":
    main()

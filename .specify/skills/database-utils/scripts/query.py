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


if __name__ == "__main__":
    main()

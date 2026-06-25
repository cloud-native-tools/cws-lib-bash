---
name: database-utils
description: |
  Execute read-only SQL queries against MySQL and PostgreSQL protocol databases.
  Supports MySQL, PostgreSQL, ClickHouse (PostgreSQL wire protocol), and Apache Doris/SelectDB (MySQL protocol).
  Use when: querying databases, exploring schemas/tables, running SELECT queries for data analysis,
  checking database contents.
  Triggers: "MySQL", "PostgreSQL", "database", "SQL", "query", "ClickHouse", "Doris", "SelectDB",
  "数据库", "查询", "SQL查询", "数据库查询", "表结构", "数据分析"
skill_id: "<SKILL:.specify/skills/database-utils/SKILL.md>"
license: Apache-2.0
metadata:
  author: sanjay3290
  version: "2.0"
---

# Database Utilities

Execute safe, read-only queries against configured MySQL and PostgreSQL protocol databases from a single unified interface.

## Overview

This skill provides a unified command-line interface for querying databases that speak the MySQL or PostgreSQL wire protocols. A single `connections.json` config file holds all database entries with a `protocol` field that routes each query to the correct handler.

Supported databases:

| Database | Protocol | Default Port |
|----------|----------|--------------|
| MySQL | mysql | 3306 |
| MariaDB | mysql | 3306 |
| Apache Doris / SelectDB | mysql | 9030 |
| PostgreSQL | postgres | 5432 |
| ClickHouse (PG wire) | postgres | 9005 |

## Quick Reference

| Command | Description |
|---------|-------------|
| `--list` | List all configured databases with protocol |
| `--db <name> --tables` | List tables in a database |
| `--db <name> --schema` | Show full schema (columns, types, keys) |
| `--db <name> --query "SQL"` | Execute a read-only SQL query |
| `--db <name> --query "SQL" --limit N` | Limit result rows |

## Requirements

- Python 3.8+
- `mysql-connector-python` (for MySQL protocol databases)
- `psycopg2-binary` (for PostgreSQL protocol databases)

Install dependencies:
```bash
pip install -r ${SKILL_HOME}/requirements.txt
```

## Setup

1. Copy the example config:
```bash
cp ${SKILL_HOME}/connections.example.json ${SKILL_HOME}/connections.json
```

2. Edit `connections.json` and add your database entries. Each entry must include a `protocol` field (`mysql` or `postgres`) or use a standard port so the protocol can be inferred.

**Security**: The config file contains credentials. Restrict permissions:
```bash
chmod 600 ${SKILL_HOME}/connections.json
```

The dispatcher searches for the config in these locations (first match wins):
1. `${SKILL_HOME}/connections.json`
2. `~/.config/claude/db-connections.json`

## Config Fields

| Field | Required | Default | Protocol | Description |
|-------|----------|---------|----------|-------------|
| name | Yes | - | both | Database identifier (case-insensitive lookup) |
| description | Yes | - | both | What data this database contains (used for intent matching) |
| protocol | No | inferred | both | `mysql` or `postgres` — inferred from port if omitted |
| host | Yes | - | both | Database hostname |
| port | No | 3306/5432 | both | Port number (default depends on protocol) |
| database | Yes | - | both | Database/schema name |
| user | Yes | - | both | Username |
| password | Yes | - | both | Password |
| ssl_disabled | No | false | mysql | Set `true` to disable SSL |
| ssl_ca | No | - | mysql | Path to CA certificate file |
| ssl_cert | No | - | mysql | Path to client certificate file |
| ssl_key | No | - | mysql | Path to client private key file |
| sslmode | No | prefer | postgres | SSL mode: disable, allow, prefer, require, verify-ca, verify-full |

## Usage

### List all configured databases
```bash
python3 ${SKILL_HOME}/scripts/query.py --list
```

### List tables
```bash
python3 ${SKILL_HOME}/scripts/query.py --db production --tables
```

### Show schema
```bash
python3 ${SKILL_HOME}/scripts/query.py --db production --schema
```

### Execute a query
```bash
python3 ${SKILL_HOME}/scripts/query.py --db production --query "SELECT * FROM users LIMIT 10"
```

### Limit results
```bash
python3 ${SKILL_HOME}/scripts/query.py --db production --query "SELECT * FROM orders" --limit 100
```

### Use a specific config file
```bash
python3 ${SKILL_HOME}/scripts/query.py --config /path/to/connections.json --db production --tables
```

### Call protocol-specific scripts directly
```bash
python3 ${SKILL_HOME}/scripts/query_mysql.py --db mysql-prod --tables
python3 ${SKILL_HOME}/scripts/query_postgres.py --db pg-analytics --schema
```

## Supported Databases

### MySQL (protocol: mysql)
Standard MySQL and MariaDB databases. Uses `mysql-connector-python`. Safety enforced via `SET SESSION TRANSACTION READ ONLY`.

### PostgreSQL (protocol: postgres)
Standard PostgreSQL databases. Uses `psycopg2`. Safety enforced via `readonly=True` session mode.

### ClickHouse (protocol: postgres)
ClickHouse exposes a PostgreSQL-compatible wire protocol on port 9005. Set `protocol: "postgres"` in the config entry.

### Apache Doris / SelectDB (protocol: mysql)
Doris and SelectDB expose a MySQL-compatible wire protocol on port 9030. Set `protocol: "mysql"` in the config entry.

## Database Selection

When the user's intent maps to a database topic, match against the `description` field in each config entry:

| User asks about | Look for description containing |
|-----------------|--------------------------------|
| users, accounts | users, accounts, customers |
| orders, sales | orders, transactions, sales |
| analytics, metrics | analytics, metrics, reports |
| logs, events | logs, events, audit |
| warehouse, OLAP | warehouse, OLAP, data lake |

If the match is ambiguous, run `--list` and ask the user which database to query.

## Safety Features

- **Read-only sessions**: MySQL uses `SET SESSION TRANSACTION READ ONLY`; PostgreSQL uses `readonly=True` mode
- **Query validation**: Only SELECT, SHOW, DESCRIBE, EXPLAIN, WITH queries allowed (client-side check)
- **SELECT INTO blocked**: MySQL handler blocks `SELECT INTO OUTFILE/DUMPFILE`
- **Single statement**: Multiple statements per query rejected (prevents injection like `SELECT 1; DROP TABLE`)
- **Query timeout**: 30-second timeout enforced (MySQL `max_execution_time`, PostgreSQL `statement_timeout`)
- **Connection timeout**: 10-second connection timeout
- **Memory protection**: Max 10,000 rows per query to prevent OOM
- **Column width cap**: 100 characters max per column for readable output
- **Credential sanitization**: Error messages do not leak passwords or authentication details
- **Config permissions**: Warning emitted if `connections.json` is readable by group or others

## Troubleshooting

| Error | Solution |
|-------|----------|
| Config not found | Create `connections.json` in skill directory or `~/.config/claude/db-connections.json` |
| Authentication failed | Check username/password in config |
| Connection timeout | Verify host/port, check firewall/VPN |
| MySQL SSL error | Try `"ssl_disabled": true` for local databases |
| PostgreSQL SSL error | Try `"sslmode": "disable"` for local databases |
| Permission warning | Run `chmod 600 connections.json` |
| max_execution_time not supported | Upgrade to MySQL 5.7.8+ or MariaDB 10.1.1+ |
| Unknown protocol | Add explicit `"protocol": "mysql"` or `"protocol": "postgres"` |
| Handler not found | Ensure `query_mysql.py` and `query_postgres.py` exist in `scripts/` |
| mysql-connector-python not installed | Run `pip install mysql-connector-python` |
| psycopg2 not installed | Run `pip install psycopg2-binary` |

## Exit Codes

- **0**: Success
- **1**: Error (config missing, auth failed, invalid query, database error)

## Workflow

1. Run `--list` to show available databases and their protocols
2. Match user intent to a database by its description
3. Run `--tables` or `--schema` to explore the database structure
4. Execute the query with an appropriate `LIMIT`
5. Present results to the user

## Path Conventions

- `${SKILL_HOME}` — the skill root directory (where this SKILL.md lives)
- `${SKILL_WORKDIR}` — the caller's working directory at invocation time

All script paths in this skill use `${SKILL_HOME}/scripts/` to remain portable.

## Resources

- `scripts/query.py` — unified dispatcher (routes to protocol-specific handler)
- `scripts/query_mysql.py` — MySQL protocol handler
- `scripts/query_postgres.py` — PostgreSQL protocol handler
- `references/README.md` — setup and usage guide
- `connections.example.json` — example config with MySQL, PostgreSQL, ClickHouse, and Doris entries
- `requirements.txt` — Python dependencies
- `LICENSE.txt` — Apache-2.0 license

## Dependencies

- `mysql-connector-python` — MySQL protocol driver
- `psycopg2-binary` — PostgreSQL protocol driver

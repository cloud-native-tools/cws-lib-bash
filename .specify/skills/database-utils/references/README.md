# Database Utilities

Unified read-only database query skill. Query MySQL and PostgreSQL protocol databases safely with write protection.

Supports MySQL, PostgreSQL, ClickHouse (PostgreSQL wire protocol), and Apache Doris/SelectDB (MySQL wire protocol).

## Setup

1. Copy the example config:
```bash
cp connections.example.json connections.json
```

2. Add your database credentials. Use the `protocol` field to specify `mysql` or `postgres`:
```json
{
  "databases": [
    {
      "name": "mysql-prod",
      "description": "Production MySQL - users, orders, transactions",
      "protocol": "mysql",
      "host": "db.example.com",
      "port": 3306,
      "database": "app_prod",
      "user": "readonly",
      "password": "secret",
      "ssl_disabled": false
    },
    {
      "name": "postgres-analytics",
      "description": "Analytics PostgreSQL - metrics, reports",
      "protocol": "postgres",
      "host": "analytics.example.com",
      "port": 5432,
      "database": "analytics",
      "user": "readonly",
      "password": "secret",
      "sslmode": "require"
    },
    {
      "name": "clickhouse-warehouse",
      "description": "ClickHouse data warehouse (PostgreSQL protocol)",
      "protocol": "postgres",
      "host": "ch.example.com",
      "port": 9005,
      "database": "warehouse",
      "user": "readonly",
      "password": "secret",
      "sslmode": "prefer"
    },
    {
      "name": "doris-olap",
      "description": "Apache Doris OLAP database (MySQL protocol)",
      "protocol": "mysql",
      "host": "doris.example.com",
      "port": 9030,
      "database": "olap_db",
      "user": "readonly",
      "password": "secret",
      "ssl_disabled": true
    }
  ]
}
```

3. Secure the config:
```bash
chmod 600 connections.json
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

This installs `mysql-connector-python` and `psycopg2-binary`.

## Usage

```bash
# List all configured databases (shows protocol for each)
python3 scripts/query.py --list

# List tables in a database
python3 scripts/query.py --db mysql-prod --tables

# Show schema
python3 scripts/query.py --db postgres-analytics --schema

# Run a query
python3 scripts/query.py --db mysql-prod --query "SELECT * FROM users" --limit 100

# You can also call protocol-specific scripts directly
python3 scripts/query_mysql.py --db mysql-prod --tables
python3 scripts/query_postgres.py --db postgres-analytics --tables
```

## Config Fields

### Common Fields (all protocols)

| Field | Required | Description |
|-------|----------|-------------|
| name | Yes | Database identifier (case-insensitive) |
| description | Yes | What data it contains (for auto-selection) |
| protocol | No | `mysql` or `postgres` (inferred from port if omitted) |
| host | Yes | Hostname |
| port | No | Port (default: 3306 for mysql, 5432 for postgres) |
| database | Yes | Database name |
| user | Yes | Username |
| password | Yes | Password |

### MySQL-specific Fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| ssl_disabled | No | false | Disable SSL connections |
| ssl_ca | No | - | Path to CA certificate |
| ssl_cert | No | - | Path to client certificate |
| ssl_key | No | - | Path to client private key |

### PostgreSQL-specific Fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| sslmode | No | prefer | disable, allow, prefer, require, verify-ca, verify-full |

## Protocol Detection

If the `protocol` field is omitted, the dispatcher infers it from the port:

| Port | Inferred Protocol | Typical Database |
|------|-------------------|------------------|
| 3306 | mysql | MySQL, MariaDB |
| 9030 | mysql | Apache Doris, SelectDB |
| 5432 | postgres | PostgreSQL |
| 9005 | postgres | ClickHouse |

If neither `protocol` nor a recognized port is provided, defaults to `mysql`.

## Safety Features

### MySQL
- Read-only sessions: `SET SESSION TRANSACTION READ ONLY` blocks writes at session level
- Query validation: Only SELECT, SHOW, DESCRIBE, EXPLAIN, WITH allowed
- SELECT INTO OUTFILE/DUMPFILE blocked
- 30s query timeout via `max_execution_time` (MySQL 5.7.8+)

### PostgreSQL
- Read-only sessions: `readonly=True` mode blocks writes at database level
- Query validation: Only SELECT, SHOW, EXPLAIN, WITH allowed
- 30s statement timeout

### Shared
- Single statement only: No multi-statement queries
- Memory cap: Max 10,000 rows per query
- Column width cap: 100 chars max per column
- Credential protection: Passwords sanitized from error messages
- Config permission warning: Alerts if connections.json is world-readable

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
| Unknown protocol | Add explicit `"protocol": "mysql"` or `"protocol": "postgres"` to config entry |

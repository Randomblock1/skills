# Postgres Tool Catalog

Full catalog of Postgres extensions and Postgres-based tools, organized by the specialized system they replace. Sourced from postgresisenough.dev (github.com/agoodway/postgresisenough). "Extension" = installs into Postgres itself; "software" = runs alongside/on top of Postgres.

## Message queues & background jobs
Replaces: Redis queues, SQS, RabbitMQ, Sidekiq, Celery, Bull, Temporal (partially)

Why Postgres wins here: `FOR UPDATE SKIP LOCKED` makes competing consumers cheap; jobs enqueue in the same transaction as your data changes, so a rolled-back insert never leaves an orphaned job. Most apps run thousands of jobs/sec on modest hardware — far below where a dedicated broker pays off.

| Tool | Type | What it is | URL |
|---|---|---|---|
| PGMQ | extension | Lightweight message queue, at-least-once delivery, visibility timeout (SQS-like semantics) | github.com/pgmq/pgmq |
| Graphile Worker | software | High-performance Node.js job queue on SKIP LOCKED | github.com/graphile/worker |
| pg-boss | software | Node.js job queue with exponential backoff and scheduling | github.com/timgit/pg-boss |
| River | software | Fast background jobs for Go | github.com/riverqueue/river |
| Oban | software | Robust job processing for Elixir | github.com/sorentwo/oban |
| pgflow-elixir | software | Multi-step workflow orchestration for Elixir on pgmq (Temporal/Inngest-style) | github.com/agoodway/pgflow |
| pg_cron | extension | Periodic jobs inside Postgres, cron syntax | github.com/citusdata/pg_cron |
| pg_timetable | software | Advanced scheduler: chaining, conditions, remote execution | github.com/cybertec-postgresql/pg_timetable |

## Full-text search
Replaces: Elasticsearch, Solr

Why Postgres wins here: no sync pipeline between the source of truth and the search index (the #1 operational pain of Elasticsearch deployments); search joins directly against permissions/business tables. Built-in tsvector + GIN covers most app search; the extensions below add modern BM25 ranking.

| Tool | Type | What it is | URL |
|---|---|---|---|
| ParadeDB | software | Postgres-native search + analytics with BM25 scoring | github.com/paradedb/paradedb |
| pg_search | extension | BM25 full-text search extension (from ParadeDB) | github.com/paradedb/paradedb/tree/dev/pg_search |
| PGroonga | extension | All-language full-text search (strong CJK), fast index updates | github.com/pgroonga/pgroonga |
| ZomboDB | extension | Bridge to query an existing Elasticsearch from SQL (hybrid/transition path) | github.com/zombodb/zombodb |

## Vectors / AI search
Replaces: Pinecone, Milvus, Qdrant, Weaviate

Why Postgres wins here: RAG queries almost always combine vector similarity with metadata filters — one indexed SQL query instead of a filtered ANN workaround; embeddings stay transactionally consistent with source rows.

| Tool | Type | What it is | URL |
|---|---|---|---|
| pgvector | extension | The default: vector column type, HNSW/IVFFlat indexes, distance operators | github.com/pgvector/pgvector |
| pgvectorscale | extension | StreamingDiskANN index for higher scale/performance (Timescale) | github.com/timescale/pgvectorscale |
| Lantern | extension | HNSW-indexed vector search | github.com/lanterndata/lantern |
| pgai | extension | Embedding pipelines, LLM calls, RAG in-database | github.com/timescale/pgai |
| PostgresML | extension | Run ML models in-database with GPU acceleration | github.com/postgresml/postgresml |

## Time-series
Replaces: InfluxDB, Prometheus (as long-term storage), QuestDB

| Tool | Type | What it is | URL |
|---|---|---|---|
| TimescaleDB | extension | Hypertables: automatic partitioning, compression, continuous aggregates | github.com/timescale/timescaledb |
| pg_partman | extension | Automatic time-based partition management (no new query model needed) | github.com/pgpartman/pg_partman |

## Caching
Replaces: Redis, Memcached

Ask first whether an index or materialized view removes the need for a cache entirely — cache invalidation is a bug class you can often just not have.

| Tool | Type | What it is | URL |
|---|---|---|---|
| ReadySet | software | Wire-compatible SQL caching proxy between app and Postgres — no code changes | github.com/readysettech/readyset |
| pg_ivm | extension | Incrementally maintained materialized views (auto-update on base-table change) | github.com/sraoss/pg_ivm |

Also: `UNLOGGED` tables (no WAL overhead) work as an in-Postgres ephemeral cache.

## Documents / NoSQL
Replaces: MongoDB, RavenDB

JSONB columns with GIN indexes are the answer most of the time — flexible schema where you want it, joins and constraints where you don't. The tools below are for when you need a Mongo-style API.

| Tool | Type | What it is | URL |
|---|---|---|---|
| FerretDB | software | MongoDB wire-protocol layer on Postgres | github.com/FerretDB/FerretDB |
| DocumentDB | software | MongoDB-compatible document DB on Postgres | github.com/documentdb/documentdb |
| Pongo | software | MongoDB-like API using JSONB | github.com/event-driven-io/Pongo |
| Marten | software | .NET document DB + event store on Postgres | github.com/JasperFx/marten |
| Dox | software | Simple document-database API | github.com/robconery/dox |

## Graph
Replaces: Neo4j, Neptune

Try `WITH RECURSIVE` CTEs first — they cover hierarchies, reachability, and friend-of-friend queries without any new component.

| Tool | Type | What it is | URL |
|---|---|---|---|
| Apache AGE | extension | Graph extension with openCypher query support | github.com/apache/age |
| Gel (ex-EdgeDB) | software | Graph-relational DB on Postgres with declarative schema + EdgeQL | github.com/geldata/gel |

## Geospatial
Replaces: MongoDB geospatial, Elasticsearch geo — PostGIS is the industry standard here, not a compromise.

| Tool | Type | What it is | URL |
|---|---|---|---|
| PostGIS | extension | Geographic objects and spatial queries | github.com/postgis/postgis |
| pgRouting | extension | Routing / shortest-path / graph analysis on PostGIS | github.com/pgRouting/pgrouting |
| h3-pg | extension | H3 hexagonal hierarchical spatial indexing | github.com/zachasme/h3-pg |

## Analytics / OLAP
Replaces: ClickHouse, Snowflake (up to a scale ceiling — be honest about it)

| Tool | Type | What it is | URL |
|---|---|---|---|
| pg_analytics | extension | Columnar storage + vectorized execution (ParadeDB) | github.com/paradedb/pg_analytics |
| Hydra | software | Column-oriented Postgres for OLAP | github.com/hydradatabase/hydra |
| Citus | extension | Distributed Postgres: sharding, multi-tenant, real-time analytics | github.com/citusdata/citus |
| duckdb_fdw | extension | Query DuckDB (Parquet etc.) from Postgres via FDW | github.com/alitrack/duckdb_fdw |
| pg_lake | extension | Query Iceberg tables / data lakes from Postgres | github.com/Snowflake-Labs/pg_lake |
| Evidence | software | Reports/dashboards from SQL + markdown | github.com/evidence-dev/evidence |
| Metabase | software | Open-source self-service BI | github.com/metabase/metabase |

## Change data capture / streaming
Replaces: custom CDC, some Kafka use cases (not a distributed log — see skill limits)

| Tool | Type | What it is | URL |
|---|---|---|---|
| Debezium | software | Stream DB changes to Kafka and other systems | github.com/debezium/debezium |
| PeerDB | software | Fast replication to Snowflake/BigQuery/warehouses | github.com/PeerDB-io/peerdb |
| pglogical | extension | Logical replication for selective table sync | github.com/2ndQuadrant/pglogical |
| wal2json | extension | Logical decoding output as JSON | github.com/eulerto/wal2json |
| ElectricSQL | software | Local-first sync with real-time replication | github.com/electric-sql/electric |
| WalEx | software | Elixir WAL change listener via logical replication | github.com/cpursley/walex |

Also built-in: `LISTEN/NOTIFY` for lightweight pub-sub (no persistence, at-most-once — fine for cache-bust signals and live UI updates).

## API generation & app platform
Replaces: hand-written CRUD backends, Firebase

| Tool | Type | What it is | URL |
|---|---|---|---|
| PostgREST | software | Instant REST API from schema | github.com/PostgREST/postgrest |
| Hasura | software | Instant GraphQL + REST | github.com/hasura/graphql-engine |
| PostGraphile | software | Customizable GraphQL from schema | github.com/graphile/postgraphile |
| pg_graphql | extension | GraphQL inside Postgres (Supabase) | github.com/supabase/pg_graphql |
| Supabase | software | Firebase alternative: Postgres + auth + APIs + realtime | github.com/supabase/supabase |
| GraphJin | software | Auto GraphQL/REST APIs | github.com/dosco/graphjin |
| Omnigres | extension | Postgres as full app platform incl. web server | github.com/omnigres/omnigres |
| pgsql-http | extension | HTTP requests from Postgres functions (webhooks from triggers) | github.com/pramsey/pgsql-http |
| pg_net | extension | Async non-blocking HTTP from Postgres | github.com/supabase/pg_net |
| Supabase Wrappers | extension | FDWs for Stripe, Firebase, Airtable, 20+ services as tables | github.com/supabase/wrappers |

## UI / no-code
Replaces: Airtable

| Tool | Type | What it is | URL |
|---|---|---|---|
| NocoDB | software | Airtable alternative on Postgres | github.com/nocodb/nocodb |
| Baserow | software | No-code collaborative database platform | github.com/bram2w/baserow |
| SQLPage | software | Web apps written entirely in SQL | github.com/lovasoa/SQLpage |

## Auth & security

| Tool | Type | What it is | URL |
|---|---|---|---|
| pgcrypto | extension | Cryptographic functions (hashing, encryption) — ships with Postgres | postgresql.org/docs/current/pgcrypto.html |
| pgjwt | extension | JWT generation/verification in-database | github.com/michelp/pgjwt |
| Supabase Vault | extension | Secrets management | github.com/supabase/vault |

## Audit logging & history
Replaces: custom audit code, external audit services

| Tool | Type | What it is | URL |
|---|---|---|---|
| pgAudit | extension | Session/object audit logging for SOC2/HIPAA compliance | github.com/pgaudit/pgaudit |
| supa_audit | extension | Generic table-change audit logging | github.com/supabase/supa_audit |
| pgMemento | extension | Full audit trail with versioning + time-travel queries | github.com/pgMemento/pgMemento |
| Bemi | software | Automatic audit logging via CDC/WAL | github.com/BemiHQ/bemi |
| Temporal Tables | extension | SQL:2011 system-versioned tables with history | github.com/arkhipov/temporal_tables |

## Schema migrations

| Tool | Type | What it is | URL |
|---|---|---|---|
| pgroll | software | Zero-downtime migrations with automatic rollback (Xata) | github.com/xataio/pgroll |
| Atlas | software | Schema-as-code, declarative migrations | github.com/ariga/atlas |
| pg-schema-diff | software | Schema diff → safe migration SQL (Stripe) | github.com/stripe/pg-schema-diff |
| Sqitch | software | Change management with dependency tracking | github.com/sqitchers/sqitch |
| Bytebase | software | Database DevOps: CI/CD + access control | github.com/bytebase/bytebase |

## Scaling & connection management

| Tool | Type | What it is | URL |
|---|---|---|---|
| PgBouncer | software | The standard lightweight connection pooler | github.com/pgbouncer/pgbouncer |
| PgCat | software | Pooler with load balancing + sharding | github.com/postgresml/pgcat |
| PgDog | software | Pooler, load balancer, sharder | github.com/pgdogdev/pgdog |
| Supavisor | software | Cloud-native multi-tenant pooler (Elixir) | github.com/supabase/supavisor |
| Spock | extension | Multi-master (active-active) replication with conflict resolution | github.com/pgEdge/spock |

## Performance tuning

| Tool | Type | What it is | URL |
|---|---|---|---|
| PGHero | software | Performance dashboard with index suggestions | github.com/ankane/pghero |
| HypoPG | extension | Hypothetical indexes — test impact before creating | github.com/HypoPG/hypopg |
| Dexter | software | Automatic index recommendations | github.com/ankane/dexter |
| index_advisor | extension | Index recommendations (Supabase) | github.com/supabase/index_advisor |
| pg_hint_plan | extension | Planner hints in SQL | github.com/ossc-db/pg_hint_plan |
| PGAssistant | software | AI-assisted schema/performance analysis | github.com/beh74/pgassistant-community |

## Testing

| Tool | Type | What it is | URL |
|---|---|---|---|
| pgTAP | extension | Unit tests for functions/schemas with TAP output | github.com/theory/pgtap |

## Embedded / browser

| Tool | Type | What it is | URL |
|---|---|---|---|
| PGLite | software | Postgres in the browser / embedded via WASM | github.com/electric-sql/pglite |

## Package management & ops

| Tool | Type | What it is | URL |
|---|---|---|---|
| pgxman | software | npm-style package manager for extensions | github.com/pgxman/pgxman |
| dbdev | software | Package manager for trusted language extensions | github.com/supabase/dbdev |
| CloudNativePG | software | Kubernetes operator for Postgres clusters | github.com/cloudnative-pg/cloudnative-pg |
| Databasus | software | Scheduled backups with notifications + web UI | github.com/databasus/databasus |
| Portabase | software | Self-hosted backup/restore management UI | github.com/Portabase/portabase |
| postgres-mcp | software | MCP server: index tuning, explain plans, health checks for AI agents | github.com/crystaldba/postgres-mcp |

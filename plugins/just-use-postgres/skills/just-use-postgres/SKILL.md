---
name: just-use-postgres
description: Architecture guidance for choosing data infrastructure. Use this skill whenever the user is deciding what database, queue, cache, search engine, vector store, or other data-layer component to add to a system — or asks for help designing a backend/stack that involves Redis, Kafka, Elasticsearch, MongoDB, Pinecone, InfluxDB, RabbitMQ, Sidekiq/Celery-style job queues, cron systems, audit logging, or similar. Also use it when reviewing an architecture that already includes several of these, or when the user asks "do I really need X?" about any specialized datastore. The skill recommends Postgres-based alternatives where they fit, and honestly identifies the cases where Postgres is the wrong choice (including small local apps where SQLite is better).
---

# Just Use Postgres

## The core idea

Every additional datastore in a stack is a second thing to provision, secure, back up, monitor, upgrade, and learn — and a consistency boundary your application code must now manage (what happens when the DB commit succeeds but the Redis write fails?). Postgres, through its extension ecosystem and tools built on top of it, can credibly cover queues, search, vectors, time-series, caching, documents, graphs, geospatial, analytics, CDC, and more.

So when helping design a system, the default recommendation should be: **use Postgres for as much as it can reasonably handle, and add specialized infrastructure only when there's a concrete, articulated reason** — a scale number, a latency budget, a feature gap — not just habit ("everyone uses Redis for that").

The advantages compounding in Postgres's favor:

- **One operational surface.** One backup/restore story, one HA setup, one monitoring stack, one security review, one thing on-call needs to understand.
- **Transactional consistency across features.** Enqueue a job, update a row, and write an audit record in a single ACID transaction. This is impossible across separate systems without distributed-transaction pain, and it eliminates entire classes of bugs (job enqueued for a record whose insert rolled back, cache serving deleted data, search index out of sync).
- **Your data is already there.** Search, vectors, and analytics over data that lives in Postgres avoid a sync pipeline — sync pipelines are where staleness bugs and 2am pages live.
- **SQL and joins everywhere.** Vector similarity filtered by a WHERE clause on your real tables; full-text search joined with permissions; time-series aggregated alongside business data.
- **Boring, proven core.** Decades of production hardening, and every ORM, tool, and hosting provider supports it.

## How to apply this skill

1. Identify each data-infrastructure need in the user's problem (queue, cache, search, ...).
2. For each, check the category sections below (and `references/tool-catalog.md` for the full list) for the Postgres-based option.
3. Check the "When NOT to use Postgres" section — if the user's case matches, say so plainly and recommend the specialized tool. Credibility comes from being honest about the limits.
4. Recommend concretely: name the tool, why it beats the specialized alternative *for this user's situation*, and starter guidance for adopting it.
5. If the user has real scale/latency numbers, reason from those numbers rather than from vibes in either direction.

Present recommendations with reasoning, not dogma. "Postgres can do this via pgmq, and at your volume (~10k jobs/day) that's well within its comfort zone — Redis would be a second system for no benefit" is the register to aim for.

## Category guide: top picks

The full catalog (~80 tools) with all alternatives is in `references/tool-catalog.md` — read it when the user's need is specialized (CDC, migrations, pooling, audit, APIs, ops tooling) or when the top pick below doesn't fit their language/stack. Highlights:

### Queues & background jobs (instead of Redis/Sidekiq/SQS/RabbitMQ)
- **pgmq** — Postgres extension; message queue with at-least-once delivery and visibility timeouts. Starter: `CREATE EXTENSION pgmq;` then `pgmq.send()`/`pgmq.read()`.
- Language-native job runners on Postgres SKIP LOCKED: **River** (Go), **Oban** (Elixir), **Graphile Worker** / **pg-boss** (Node). These give you retries, scheduling, and exponential backoff — the things people install Sidekiq/Celery for — with jobs enqueued transactionally with your data.
- **pg_cron** for scheduled/periodic jobs (cron syntax, runs inside Postgres).

Why it works: SKIP LOCKED (Postgres 9.5+) makes competing consumers efficient; most apps never approach the throughput where a dedicated broker matters (thousands of jobs/sec is fine on modest hardware).

### Full-text search (instead of Elasticsearch/Solr)
- Built-in `tsvector`/`tsquery` with a GIN index covers a huge share of "add search to my app" needs — try this first, it's zero new dependencies.
- **ParadeDB / pg_search** — BM25 relevance ranking (the algorithm Elasticsearch uses) as an extension, when built-in ranking isn't good enough.
- **PGroonga** — strong multilingual support (CJK languages especially).

Why it works: no index-sync pipeline; search results can join directly against permissions and business tables.

### Vectors / AI & RAG (instead of Pinecone/Milvus/Qdrant/Weaviate)
- **pgvector** — the default. `CREATE EXTENSION vector;`, a `vector` column, an HNSW index, `<=>` for cosine distance. Starter: filter with normal WHERE clauses in the same query — the thing dedicated vector DBs struggle to do well.
- **pgvectorscale** (StreamingDiskANN) or **Lantern** when you need more performance at large scale; **pgai** for embedding pipelines in-database.

Why it works: RAG almost always needs metadata filtering + vector similarity together; one system does that in one indexed query, and embeddings stay transactionally consistent with source rows.

### Time-series (instead of InfluxDB/Prometheus-as-storage)
- **TimescaleDB** — hypertables give automatic partitioning, compression, and continuous aggregates on plain SQL. **pg_partman** if you just need managed partitioning.

### Caching (instead of Redis/Memcached)
- First question: do you need a cache at all, or an index? Many "add Redis" impulses are fixable with an index or a materialized view.
- **pg_ivm** — incrementally-maintained materialized views (the view updates as base tables change). **ReadySet** — wire-compatible caching proxy, no code changes.
- `UNLOGGED` tables are a decent in-Postgres cache for ephemeral data (no WAL overhead).

### Documents / JSON (instead of MongoDB)
- **JSONB columns** — this is the answer 95% of the time. Indexed with GIN, queried with SQL. Schema flexibility where you want it, relations where you don't.
- **FerretDB** or **DocumentDB** if you need actual MongoDB wire-protocol compatibility; **Marten** for .NET document/event-store patterns.

### Graph (instead of Neo4j)
- Recursive CTEs (`WITH RECURSIVE`) handle most "graph-ish" needs (hierarchies, friend-of-friend, reachability). **Apache AGE** adds openCypher when you truly need graph query semantics.

### Geospatial (instead of anything else, honestly)
- **PostGIS** — the industry standard, full stop. **pgRouting** for shortest-path, **h3-pg** for hex indexing.

### Analytics / OLAP (instead of ClickHouse/Snowflake — up to a point)
- **pg_analytics** / **Hydra** for columnar storage and vectorized execution; **Citus** for horizontal scale-out; **duckdb_fdw** / **pg_lake** to query Parquet/Iceberg from SQL.
- BI on top: **Metabase**, **Evidence**.
- This is the category where Postgres's ceiling is most real — see below.

### Realtime / CDC / pub-sub (instead of Kafka — sometimes)
- `LISTEN/NOTIFY` for lightweight in-app pub-sub; logical replication + **wal2json** for change feeds; **ElectricSQL** for local-first sync; **Debezium/PeerDB** to stream changes out when you do need a warehouse or Kafka downstream.

### Also in the catalog
Instant APIs (PostgREST, Hasura, pg_graphql), auth/crypto (pgcrypto, pgjwt), audit/compliance (pgAudit, supa_audit, temporal tables), zero-downtime migrations (pgroll, Atlas), connection pooling (PgBouncer, PgCat), tuning (PGHero, HypoPG, index_advisor), testing (pgTAP), and Postgres-in-the-browser (PGLite). See `references/tool-catalog.md`.

## When NOT to use Postgres

Recommending Postgres for everything regardless of context destroys the credibility of the recommendation. Steer away from Postgres when:

- **Small, local, single-user, or embedded: use SQLite.** A CLI tool, a desktop app, a personal project, a prototype, an on-device store, most single-server apps with modest write concurrency — SQLite is a file, needs no server process, and is extremely fast. Running a Postgres server for a todo app is the same over-engineering this skill exists to prevent, in the other direction. (If they want SQLite-now-Postgres-later, note the migration is well-trodden; or **PGLite** for embedded-but-Postgres semantics.)
- **In-browser or local-first without a server** — SQLite-WASM or PGLite, not a hosted Postgres. IndexedDB is a browser-native alternative.
- **Extreme ingest/analytics scale.** Sustained very high ingest (say, millions of events/sec) or interactive analytics over tens-of-TB+: ClickHouse/BigQuery/Snowflake earn their place. Postgres columnar extensions raise the ceiling but don't remove it.
- **Kafka-scale streaming with replay and many independent consumers.** LISTEN/NOTIFY and pgmq are not a distributed log. If you need durable multi-consumer replayable streams at high volume, use Kafka/Redpanda.
- **Sub-millisecond hot-path caching at very high QPS** (e.g., session tokens checked on every request at massive scale) — Redis is legitimately better here.
- **Genuinely graph-native workloads** — deep variable-length traversals over billions of edges as the *core* workload, not a feature.
- **Ephemeral coordination primitives** (distributed locks, rate limiters, leaderboards at scale) — Redis's data structures are the right tool.
- **The team already runs the specialized system well.** Migrating a healthy Elasticsearch cluster to pg_search has costs too; this skill is mainly about not *adding* complexity, not about ripping out what works.

The honest framing: Postgres's sweet spot is roughly "one machine's worth of hot data or less, and moderate throughput" — which describes the overwhelming majority of applications, including successful ones. Recommend the boring default until the user's actual numbers say otherwise.

## Output format for architecture recommendations

When the user asks for a stack/architecture recommendation, cover for each data need: the recommended tool, what specialized system it replaces, why (tied to the user's stated scale and constraints), and 1-3 lines of starter guidance. Flag any need where Postgres is *not* the recommendation and say why. Keep it decision-oriented — the user should finish reading knowing exactly what to install.

# ARIA — Query Pipeline Flow

> **Version:** 1.0 | **Date:** 2026-06-07

Bu doküman ARIA'nın end-to-end query pipeline'ını, komponentlerin nasıl etkileştiğini ve veri akışını açıklar.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER QUERY                                      │
│                    "Show me monthly revenue by region"                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (Next.js)                                 │
│  • Chat UI receives query                                                    │
│  • Opens SSE connection to /api/v1/query/stream                             │
│  • Sends: {question, workspace_id, user_id}                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND (FastAPI)                                  │
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │   Memory     │    │    Vault     │    │     SQL      │                   │
│  │   Lookup     │    │   Matching   │    │  Generation  │                   │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                   │
│         │                   │                   │                            │
│         ▼                   ▼                   ▼                            │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │   Query      │    │    Chart     │    │   Insight    │                   │
│  │  Execution   │    │  Generation  │    │  Generation  │                   │
│  └──────────────┘    └──────────────┘    └──────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                          SSE Events to Frontend
```

## Detailed Pipeline Stages

### Stage 1: Memory Lookup (Mem0 + Qdrant)

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────┐
│              MemoryService.lookup()                  │
│                                                      │
│  1. Query'yi embedding'e çevir (Gemini via LiteLLM) │
│  2. Qdrant'ta semantic search yap                   │
│  3. Üç tür memory ara:                              │
│     • User preferences (chart tercihleri, vs.)      │
│     • Team knowledge (ortak terminoloji)            │
│     • Query cache (benzer sorgular + SQL)           │
│                                                      │
│  Config:                                             │
│  • Embedding: gemini-embedding-001 (3072 dims)      │
│  • Collection: aria_memory                          │
│  • Similarity threshold: 0.7                        │
└─────────────────────────────────────────────────────┘
    │
    ▼
MemoryContext {
  has_context: bool,
  user_preferences: list,
  team_knowledge: list,
  similar_queries: list  // Cached NL→SQL mappings
}
```

**Mem0 Nasıl Çalışır:**
1. `Memory.add()` → LLM ile fact extraction → Embedding → Qdrant'a upsert
2. `Memory.search()` → Query embedding → Qdrant similarity search → Results
3. Graph-based deduplication: Aynı bilgiyi tekrar eklemez, günceller

### Stage 2: Vault Matching (Obsidian Semantic Vault)

```
User Query + Memory Context
    │
    ▼
┌─────────────────────────────────────────────────────┐
│           SemanticMatcher.find_tables()             │
│                                                      │
│  Vault Location:                                     │
│  docs/vaults/{workspace_id}/tables/*.md             │
│                                                      │
│  Her .md dosyası:                                    │
│  ---                                                 │
│  table: SALES_FACT                                   │
│  schema: STC                                         │
│  keywords: [revenue, sales, income, gelir]           │
│  columns:                                            │
│    - name: AMOUNT                                    │
│      type: NUMBER                                    │
│      keywords: [revenue, total, toplam]              │
│  relationships:                                      │
│    - target: DIM_CUSTOMER                            │
│      join: CUSTOMER_ID = CUSTOMER_ID                 │
│  ---                                                 │
│                                                      │
│  Matching Algorithm:                                 │
│  1. Keyword matching (exact + fuzzy)                 │
│  2. Semantic similarity (embedding-based)            │
│  3. Weighted scoring: table 40% + column 60%         │
│  4. Return top-N tables with confidence scores       │
└─────────────────────────────────────────────────────┘
    │
    ▼
MatchedTables [
  {table: "SALES_FACT", confidence: 0.92, columns: [...], joins: [...]},
  {table: "DIM_TIME", confidence: 0.85, columns: [...], joins: [...]}
]
```

**Vault Dosya Yapısı:**
```
docs/vaults/
└── stc-kuwait/
    └── tables/
        ├── SALES_FACT.md
        ├── DIM_CUSTOMER.md
        ├── DIM_TIME.md
        ├── DIM_REGION.md
        └── _relationships.md  (cross-table joins)
```

### Stage 3: SQL Generation (Rule-Based + LLM Fallback)

```
Matched Tables + Memory Context
    │
    ▼
┌─────────────────────────────────────────────────────┐
│              is_complex_query() Router               │
│                                                      │
│  Simple Query Indicators:                            │
│  • Single table                                      │
│  • Basic aggregation (SUM, COUNT, AVG)              │
│  • Standard time filters (this month, last year)    │
│  • No subqueries needed                             │
│                                                      │
│  Complex Query Indicators:                           │
│  • Multi-table joins                                │
│  • Window functions                                 │
│  • Conditional logic (CASE WHEN)                    │
│  • Correlated subqueries                            │
│  • Ambiguous intent                                 │
└─────────────────────────────────────────────────────┘
    │
    ├── Simple ──▶ RuleBasedGenerator
    │              • Template-based SQL
    │              • Fast, deterministic
    │              • No LLM cost
    │
    └── Complex ─▶ LLMSQLGenerator
                   • DeepSeek Chat via LiteLLM
                   • Schema-aware prompt
                   • Includes memory context
                   • Validates syntax before return
```

**LLM SQL Generation Prompt Structure:**
```
You are an expert SQL analyst for {database_type}.

SCHEMA:
{matched_tables_with_columns_and_relationships}

USER CONTEXT:
{memory_context.user_preferences}
{memory_context.similar_queries}

QUESTION: {user_question}

Generate SQL that:
1. Uses only the provided tables and columns
2. Includes appropriate JOINs
3. Handles NULL values
4. Uses aliases for readability
```

### Stage 4: Query Execution

```
Generated SQL
    │
    ▼
┌─────────────────────────────────────────────────────┐
│              DatabaseExecutor.execute()              │
│                                                      │
│  Multi-DB Support:                                   │
│  • PostgreSQL (psycopg2-binary)                     │
│  • Oracle (oracledb, thin mode)                     │
│  • MySQL (pymysql)                                  │
│  • MSSQL (pymssql)                                  │
│                                                      │
│  Safety Checks:                                      │
│  1. EXPLAIN PLAN (dry-run)                          │
│  2. Row count estimation                            │
│  3. Timeout enforcement                             │
│  4. Read-only validation (no INSERT/UPDATE/DELETE)  │
│                                                      │
│  Row Governance:                                     │
│  • < 10K rows → direct return                       │
│  • > 10K rows + admin/team_lead → Prefect job       │
│  • > 10K rows + analyst/viewer → blocked            │
└─────────────────────────────────────────────────────┘
    │
    ▼
QueryResult {
  data: DataFrame,
  row_count: int,
  execution_time_ms: int,
  sql: str
}
```


### Stage 4.1: Semantic Self-Correction (Error Handling)
If the query execution fails with a database schema error (e.g., Oracle ORA-00904 Invalid Identifier due to LLM hallucination):
1. The error is caught by the pipeline.
2. The invalid column is extracted from the error message.
3. A Semantic Matcher (`_get_relevant_columns`) performs fuzzy string matching and checks a hardcoded semantic dictionary (e.g. mapping "region" to "nationality") against the *actual* table schema.
4. The LLM is re-prompted with the exact error and a precise hint: `"The column 'REGION' does not exist. Did you mean 'NATIONALITY'?"`.
5. The corrected SQL is executed again.

### Stage 5: Chart Generation

```
Query Result
    │
    ▼
┌─────────────────────────────────────────────────────┐
│             ChartGenerator.generate()                │
│                                                      │
│  Chart Type Selection:                               │
│  • Time series → Line chart                         │
│  • Categories → Bar chart                           │
│  • Proportions → Pie chart                          │
│  • Distribution → Histogram                         │
│  • User preference override (from memory)           │
│                                                      │
│  Output:                                             │
│  • Plotly JSON spec                                 │
│  • HTML artifact (MinIO'ya kaydedilir)              │
└─────────────────────────────────────────────────────┘
    │
    ▼
ChartSpec {
  type: "bar",
  data: {...},
  layout: {...},
  artifact_url: "minio://artifacts/chart_xxx.html"
}
```

### Stage 6: Insight Generation

```
Query Result + Chart
    │
    ▼
┌─────────────────────────────────────────────────────┐
│           InsightGenerator.generate()                │
│                                                      │
│  LLM-based analysis:                                 │
│  • Trend detection                                  │
│  • Anomaly highlighting                             │
│  • Comparison with historical data                  │
│  • Business recommendations                         │
│                                                      │
│  Memory-aware:                                       │
│  • References past queries if relevant              │
│  • Considers user's domain context                  │
└─────────────────────────────────────────────────────┘
    │
    ▼
Insight {
  summary: "Revenue increased 15% MoM...",
  highlights: [...],
  suggestions: ["Try breaking down by product category"]
}
```

### Stage 7: Memory Store (Post-Query)

```
Successful Query
    │
    ▼
┌─────────────────────────────────────────────────────┐
│            MemoryService.store_query()               │
│                                                      │
│  Stores:                                             │
│  • Original question                                │
│  • Generated SQL                                    │
│  • Primary table used                               │
│  • User/workspace context                           │
│                                                      │
│  Purpose:                                            │
│  • Future similar queries → cache hit               │
│  • Learn user patterns                              │
│  • Improve suggestions                              │
└─────────────────────────────────────────────────────┘
```

## SSE Event Stream

Frontend'e gönderilen event'ler:

```
event: status
data: {"message": "Analyzing query..."}

event: status
data: {"message": "Found relevant tables: SALES_FACT, DIM_TIME"}

event: sql
data: {"sql": "SELECT ..."}

event: data
data: {"rows": [...], "columns": [...]}

event: chart
data: {"type": "bar", "spec": {...}}

event: insight
data: {"summary": "Revenue increased...", "suggestions": [...]}

event: done
data: {"query_id": "uuid", "duration_ms": 1234}
```

## Component Dependencies

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   LiteLLM   │◄────│   Backend   │────►│   Qdrant    │
│   :4000     │     │   :8000     │     │   :6333     │
└─────────────┘     └──────┬──────┘     └─────────────┘
      │                    │
      │                    │
      ▼                    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  DeepSeek   │     │  Customer   │     │   MinIO     │
│  Gemini     │     │  Databases  │     │   :9000     │
│  Claude     │     │  (Oracle,   │     │  (artifacts)│
└─────────────┘     │   PG, etc.) │     └─────────────┘
                    └─────────────┘
```

## Error Handling

| Stage | Error | Response |
|-------|-------|----------|
| Memory Lookup | Qdrant down | Continue without memory context |
| Vault Matching | No tables found | SSE error: "No relevant tables found" |
| SQL Generation | LLM timeout | Fallback to rule-based if possible |
| Query Execution | DB error | SSE error with sanitized message |
| Chart Generation | Invalid data | Skip chart, return data only |

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Memory lookup | < 100ms | Qdrant local, pre-warmed |
| Vault matching | < 200ms | In-memory keyword index |
| SQL generation (simple) | < 50ms | Rule-based, no LLM |
| SQL generation (complex) | < 3s | LLM with streaming |
| Query execution | < 10s | Customer DB dependent |
| Total E2E (simple) | < 2s | Excluding DB execution |
| Total E2E (complex) | < 5s | Excluding DB execution |

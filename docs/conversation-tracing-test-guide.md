# Guide: Testing Conversation Flow & Audit Tracing in ARIA

This document details how you can manually test the newly added traceability of conversations (from Mem0 lookup to business rules and LLM token tracking) through the Audit Logs, as well as view the seeded sample data for Token Usage and Team Memory.

## 1. Trace a Conversation (Query) Flow

The system has been updated to insert a highly detailed `mem_trace` into the `data_audit_logs` database table whenever a natural language query is processed via the `/api/query` endpoint.

### How to trigger a trace manually:

1. **Login to the ARIA UI:**
   Navigate to [http://aria.localhost/login](http://aria.localhost/login)
   - **Email:** `asdasd@asfd.com` (The fully set-up test user we just created)
   - **Password:** `123456`

2. **Run a Query:**
   Go to the Dashboard or Chat interface and ask a query, for example:
   > *"How many users do we have?"*
   Wait for the query to finish processing and display the table/chart.

3. **Verify the Audit Log in the Backend:**
   The backend stores all the trace metadata (including whether team business rules were applied from Mem0) directly into the `DataAuditLog` table. You can inspect the latest audit log entry by running the following command in your terminal:

   ```bash
   docker exec -e DATABASE_URL="postgresql+asyncpg://aria:aria_dev@postgres:5432/aria" aria-backend sh -c 'python -c "
   import asyncio, json
   from backend.app.db.session import get_sessionmaker
   from sqlalchemy import select
   from backend.app.models.governance import DataAuditLog

   async def run():
       sessionmaker = get_sessionmaker()
       async with sessionmaker() as session:
           logs = await session.execute(select(DataAuditLog).order_by(DataAuditLog.created_at.desc()).limit(1))
           log = logs.scalars().first()
           if log:
               print(json.dumps(log.details, indent=2))

   asyncio.run(run())
   "'
   ```

   **Expected Output Example:**
   ```json
   {
     "sql": "SELECT COUNT(DISTINCT SUBNO) AS total_users\nFROM fct_prep_master...",
     "success": true,
     "question": "How many users do we have?",
     "mem_trace": {
       "raw": [
         "User asked for count of products by type..."
       ],
       "similar_queries_count": 5,
       "team_conventions_count": 0,
       "user_preferences_count": 0
     },
     "row_count": 1,
     "explanation": "LLM-generated query based on: How many users do we have?"
   }
   ```
   *Note: If team conventions are populated for your exact team and the Vector search matches them against your question, `team_conventions_count` will be > 0.*

---

## 2. Verify Seeded Token Metrics (`/admin/tokens` / Dashboard)

I have written a seeder script that populated the system with a "Data Science Team" and allocated large token quotas across the customer, team, and user levels. It also recorded `1500` prompt tokens and `400` completion tokens (total `1900`) for the day.

### How to verify:
1. Ensure you are logged into the UI as an admin or check the Dashboard (`http://aria.localhost`).
2. Look at the **"Tokens Used Today"** quick stat card on the main Dashboard. It should now reflect `1900` tokens (or more if you just ran fresh LLM queries).
3. If you navigate to **Settings > Tokens**, you will also see the assigned quotas for the test user and the "Data Science Team".

---

## 3. Verify Seeded Team Memory (`/admin/team-memory`)

The seeder script also interacted with the **Mem0** memory service to insert mock "business rules" (conventions) tied to the test team's ID.

### How to verify:
1. Navigate to **[http://aria.localhost/admin/team-memory](http://aria.localhost/admin/team-memory)** in the UI.
2. Select the `Data Science Team` (or the default team if UI drops down).
3. You should see the following rules listed as active memory vectors:
   * *"Always exclude rows where is_active=false when querying users"*
   * *"Revenue calculations should only include completed transactions"*

These entries represent the "business rules" that the query pipeline will now cross-reference when generating SQL for any member of that team.
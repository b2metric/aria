# ARIA Competitor Battlecards

> **Target Audience:** Sales, Pre-sales, Product Management  
> **Purpose:** How to position ARIA against major market alternatives during pitches.

---

## 1. ARIA vs. Microsoft Fabric + Copilot

**Competitor Profile:** Microsoft's all-in-one analytics solution. It forces users to move data into OneLake and use PowerBI's semantic models to ask questions via Copilot.

### Where They Fail (Their Weaknesses):
- **Vendor Lock-in:** To use Fabric Copilot, the customer MUST migrate their data to Microsoft OneLake (Azure).
- **Setup Time:** Requires building complex semantic models and DAX measures before Copilot can answer accurately.
- **Cost:** Requires extremely expensive Fabric F64+ capacities just to enable Copilot features.

### How to Pitch ARIA (Our Strengths):
- **Zero Data Movement:** ARIA connects directly to the customer's *existing* Oracle, PostgreSQL, or MySQL databases. No ETL, no migrating to a new cloud.
- **On-Premise Ready:** We can deploy ARIA in air-gapped or on-premise environments (crucial for banks and telcos). Fabric is Cloud-only.
- **Team Memory (Mem0):** ARIA learns business logic dynamically via chat (e.g., "Revenue means X"). Fabric requires IT to hardcode logic into the PowerBI semantic model.

---

## 2. ARIA vs. General LLMs (ChatGPT Enterprise / Claude for Work)

**Competitor Profile:** Employees uploading CSVs or pasting database schemas into standard ChatGPT or Claude to get SQL queries.

### Where They Fail (Their Weaknesses):
- **Data Privacy & Security:** Pasting schemas or data into public LLMs risks data leaks.
- **Hallucinations:** General LLMs don't know the exact structure, foreign keys, or "dirty data" rules of the company's database, leading to syntactically correct but logically wrong SQL.
- **No Execution:** ChatGPT just gives you the SQL. The user still has to copy it, paste it into DBeaver/DataGrip, and run it.

### How to Pitch ARIA (Our Strengths):
- **Automated Execution & Safeguards:** ARIA writes the SQL, runs `EXPLAIN` to prevent database crashes, executes it securely, and draws the chart automatically.
- **Data Dictionary (Vault):** ARIA uses heavily curated Markdown vaults (schemas), so it always knows the exact column types and relations.
- **Enterprise RBAC:** ARIA obeys Row-Level Security and Role-Based Access Control. Viewers can't see raw SQL; Admins can.

---

## 3. ARIA vs. Traditional BI (Tableau, Qlik, Classic PowerBI)

**Competitor Profile:** The old way of doing analytics with drag-and-drop dashboards.

### Where They Fail (Their Weaknesses):
- **IT Bottleneck:** Business users have to wait weeks for the Data Team to build a new dashboard just to answer one new question.
- **Dashboard Rot:** Companies end up with 500+ dashboards, most of which are never looked at, because they were built for one specific ad-hoc question.

### How to Pitch ARIA (Our Strengths):
- **Conversational Speed:** Ask a question in plain English, get a chart in 5 seconds. No waiting for the data team.
- **Dynamic Visuals:** If you want to change a Bar chart to a Line chart, just type "Make it a line chart". No drag-and-drop training required.
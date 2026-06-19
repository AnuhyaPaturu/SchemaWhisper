# ⚡ SchemaWhisper: Autonomous Relational Context Mapper & Analytics Engine

> **SchemaWhisper** is an enterprise-grade AI data console that translates natural language into secure, relational SQLite syntax and automated background database triggers. Featuring an asymmetric glassmorphic dashboard with live metrics, a persistent session history panel, and an educational sandbox, it bridges the gap between raw relational databases and actionable business intelligence.

---

## 🚀 Key Architectural Highlights

* **Dynamic Metadata Ingestion:** Automatically inspects system table catalogs (`sqlite_master`) on the fly, instantly adapting to structural additions or modifications without requiring hardcoded updates.
* **Dual-Pipeline Pydantic Routing Engine:** Intelligently maps conversational user intent to either an analytical retrieval path (`DATA_QUERY`) or an administrative script compiler (`STORED_PROCEDURE`) using strict Pydantic structured output models.
* **Abstract Syntax Tree (AST) Safety Layer:** Implements an advanced security gate using `sqlglot` to evaluate and sanitize the structural validity of generated SQL dialects before execution.
* **Stateful Execution History:** Leverages Streamlit session memory states (`st.session_state`) to maintain a real-time, interactive chronological log of your executed questions and compiled queries directly inside the workspace UI.
* **Live Telemetry & KPIs:** Displays real-time organizational KPIs (Total ARR volume, average order values, and top regions) paired with descriptive hover-state tooltips.
* **Academic Sandbox Module:** Features an integrated training drawer outlining 3NF database normalization mechanics and prompt testing blueprints for entry-level developers or students.

---

## 📊 Relational Database Architecture (3NF)

The system boots up by automatically seeding a fully normalized, 6-table enterprise dataset following strict Third Normal Form (3NF) structural guidelines:

* `departments` — Organizational units and structural budget allocations.
* `regions` — Geographic operational location profiles.
* `employees` — Corporate personnel attributes, linked to departments and regions via Foreign Keys.
* `products` — Inventories SaaS, Support, and Hardware commodity pricing models.
* `customers` — Enterprise and individual client buying profiles.
* `sales` — Central high-velocity ledger table linking transactions, quantities, and timelines together.
* `audit_logs` — Dedicated security ledger built explicitly to capture automated triggers and background tasks.

---

## 🛠️ Quick Installation & Setup

### 1. Clone the Workspace Environment
```bash
git clone [https://github.com/AnuhyaPaturu/SchemaWhisper.git](https://github.com/AnuhyaPaturu/SchemaWhisper.git)
cd SchemaWhisper

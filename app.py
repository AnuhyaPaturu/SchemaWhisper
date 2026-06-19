
import streamlit as st
import sqlite3
import sqlglot
from openai import OpenAI
import pandas as pd
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import random
from datetime import datetime, timedelta
from enum import Enum

# Load local environment configuration keys
load_dotenv()
client = OpenAI()

# --- STEP 1: DATABASE SEED ENGINE ---
def init_db():
    conn = sqlite3.connect("company.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    cursor.execute("DROP TRIGGER IF EXISTS log_large_sales;")
    cursor.execute("DROP TABLE IF EXISTS sales;")
    cursor.execute("DROP TABLE IF EXISTS employees;")
    cursor.execute("DROP TABLE IF EXISTS departments;")
    cursor.execute("DROP TABLE IF EXISTS regions;")
    cursor.execute("DROP TABLE IF EXISTS products;")
    cursor.execute("DROP TABLE IF EXISTS customers;")
    cursor.execute("DROP TABLE IF EXISTS audit_logs;")

    cursor.execute("CREATE TABLE departments (dept_id INTEGER PRIMARY KEY, dept_name TEXT, budget REAL)")
    cursor.execute("CREATE TABLE regions (region_id INTEGER PRIMARY KEY, city TEXT, country TEXT)")
    cursor.execute("""CREATE TABLE employees (
        emp_id INTEGER PRIMARY KEY, name TEXT, dept_id INTEGER, region_id INTEGER, salary REAL, hire_date DATE,
        FOREIGN KEY(dept_id) REFERENCES departments(dept_id), FOREIGN KEY(region_id) REFERENCES regions(region_id)
    )""")
    cursor.execute("CREATE TABLE products (product_id INTEGER PRIMARY KEY, product_name TEXT, category TEXT, unit_price REAL)")
    cursor.execute("CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, customer_name TEXT, segment TEXT)")
    cursor.execute("""CREATE TABLE sales (
        sale_id INTEGER PRIMARY KEY, emp_id INTEGER, product_id INTEGER, customer_id INTEGER, quantity INTEGER, total_amount REAL, sale_date DATE,
        FOREIGN KEY(emp_id) REFERENCES employees(emp_id), FOREIGN KEY(product_id) REFERENCES products(product_id), FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
    )""")
    cursor.execute("CREATE TABLE audit_logs (log_id INTEGER PRIMARY KEY AUTOINCREMENT, action_details TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")

    depts = [(1, "Engineering", 500000.0), (2, "Sales", 350000.0), (3, "Marketing", 200000.0), (4, "HR", 100000.0)]
    cursor.executemany("INSERT INTO departments VALUES (?, ?, ?)", depts)
    locs = [(1, "San Francisco", "USA"), (2, "London", "UK"), (3, "Tokyo", "Japan")]
    cursor.executemany("INSERT INTO regions VALUES (?, ?, ?)", locs)
    prods = [(1, "Valkyrie Cloud License", "SaaS", 1200.0), (2, "Quantum Database Node", "Hardware", 8500.0), (3, "AI Analytics Terminal", "SaaS", 450.0), (4, "Developer Support Suite", "Support", 250.0)]
    cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", prods)
    custs = [(1, "Cyberdyne Systems", "Enterprise"), (2, "Weyland-Yutani Corp", "Enterprise"), (3, "Stark Industries", "Corporate"), (4, "Acme Corporation", "Individual")]
    cursor.executemany("INSERT INTO customers VALUES (?, ?, ?)", custs)

    first_names = ["Sarah", "John", "Ellen", "James", "David", "Emma", "Michael", "Olivia", "Robert", "Sophia"]
    last_names = ["Connor", "Doe", "Ripley", "Bond", "Smith", "Johnson", "Miller", "Davis", "Wayne", "Kent"]
    employees_data = []
    base_date = datetime(2023, 1, 1)
    for emp_id in range(1, 26):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        d_id = random.randint(1, 4)
        r_id = random.randint(1, 3)
        salary = round(random.uniform(110000, 165000), 2) if d_id == 1 else round(random.uniform(60000, 105000), 2)
        hire_date = (base_date + timedelta(days=random.randint(0, 1000))).strftime("%Y-%m-%d")
        employees_data.append((emp_id, name, d_id, r_id, salary, hire_date))
    cursor.executemany("INSERT INTO employees VALUES (?, ?, ?, ?, ?, ?)", employees_data)
    
    sales_data = []
    cursor.execute("SELECT emp_id FROM employees WHERE dept_id = 2")
    sales_reps = [row[0] for row in cursor.fetchall()]
    if not sales_reps:
        sales_reps = [2, 5]
        for r_id in sales_reps:
            cursor.execute("UPDATE employees SET dept_id = 2 WHERE emp_id = ?", (r_id,))

    sale_start_date = datetime(2025, 1, 1)
    for s_id in range(101, 181):
        emp_id = random.choice(sales_reps)
        prod_id = random.randint(1, 4)
        cust_id = random.randint(1, 4)
        qty = random.randint(1, 5)
        cursor.execute("SELECT unit_price FROM products WHERE product_id = ?", (prod_id,))
        total = round(qty * cursor.fetchone()[0], 2)
        s_date = (sale_start_date + timedelta(days=random.randint(0, 500))).strftime("%Y-%m-%d")
        sales_data.append((s_id, emp_id, prod_id, cust_id, qty, total, s_date))
        
    cursor.executemany("INSERT INTO sales VALUES (?, ?, ?, ?, ?, ?, ?)", sales_data)
    conn.commit()
    conn.close()

init_db()

def get_catalog_dataframe():
    conn = sqlite3.connect("company.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [t[0] for t in cursor.fetchall()]
    
    catalog_records = []
    for t in tables:
        cursor.execute(f"PRAGMA table_info({t});")
        cols = [f"{col[1]} ({col[2]})" for col in cursor.fetchall()]
        catalog_records.append({"Table Asset": f"🔹 {t.upper()}", "Structural Schema Map": " │ ".join(cols)})
    
    cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='trigger';")
    triggers = cursor.fetchall()
    for trig in triggers:
        catalog_records.append({"Table Asset": f"⚙️ TRIGGER: {trig[0]}", "Structural Schema Map": f"Automated Background Routine monitoring changes on table: '{trig[1]}'"})
        
    conn.close()
    return pd.DataFrame(catalog_records)

class QueryType(str, Enum):
    DATA_QUERY = "DATA_QUERY"
    STORED_PROCEDURE = "STORED_PROCEDURE"

class AdvancedSQLResponse(BaseModel):
    thought_process: str = Field(description="Step-by-step logic detailing table relationships or automation routine compilation strategy.")
    query_type: QueryType = Field(description="Is this a reading query (DATA_QUERY) or an automated background database trigger script (STORED_PROCEDURE)?")
    sql_query: str = Field(description="The executable SQLite query string or clean CREATE TRIGGER syntax.")

def generate_sql(user_prompt: str, schema_context: str) -> AdvancedSQLResponse:
    prompt = f"Convert prompt into valid SQLite database syntax.\nDatabase Context:\n{schema_context}\nUser Prompt: {user_prompt}"
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], response_format=AdvancedSQLResponse
    )
    return completion.choices[0].message.parsed

def execute_database_routine(sql: str, query_type: QueryType):
    conn = sqlite3.connect("company.db")
    cursor = conn.cursor()
    try:
        if query_type == QueryType.STORED_PROCEDURE:
            cursor.executescript(sql)
            conn.commit()
            return pd.DataFrame([{"System Status": "✅ SUCCESS: Procedural Automation Routine Compiled and Saved successfully."}]), None
        else:
            df = pd.read_sql_query(sql, conn)
            return df, None
    except Exception as e:
        return None, str(e)
    finally:
        conn.close()

# --- STEP 2: STATE TRACKING & OPERATIONAL ANALYTICS ---
if "submitted_query" not in st.session_state:
    st.session_state.submitted_query = None

# Initialize persistent tracking states
if "query_history_log" not in st.session_state:
    st.session_state.query_history_log = []
if "show_history" not in st.session_state:
    st.session_state.show_history = False

def clear_input_callback():
    st.session_state.submitted_query = st.session_state.query_input_widget
    st.session_state.query_input_widget = ""

def toggle_history_state():
    st.session_state.show_history = not st.session_state.show_history

conn = sqlite3.connect("company.db")

# Compute structural telemetry statistics
tbl_count = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';").fetchone()[0]
emp_count = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
sales_count = conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0]

# Compute live operational dashboard KPIs
total_revenue = conn.execute("SELECT SUM(total_amount) FROM sales;").fetchone()[0] or 0.0
avg_order_value = conn.execute("SELECT AVG(total_amount) FROM sales;").fetchone()[0] or 0.0

top_city_query = """
    SELECT r.city FROM regions r
    JOIN employees e ON r.region_id = e.region_id
    JOIN sales s ON e.emp_id = s.emp_id
    GROUP BY r.city ORDER BY SUM(s.total_amount) DESC LIMIT 1;
"""
top_city_result = conn.execute(top_city_query).fetchone()
top_city = top_city_result[0] if top_city_result else "N/A"

conn.close()

# Dynamic contextual snapshot string generator for LLM comprehension
conn_temp = sqlite3.connect("company.db")
cur_temp = conn_temp.cursor()
cur_temp.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
schema_context_str = ""
for t_name in [t[0] for t in cur_temp.fetchall()]:
    cur_temp.execute(f"PRAGMA table_info({t_name});")
    schema_context_str += f"Table {t_name}: " + ", ".join([c[1] for c in cur_temp.fetchall()]) + "\n"
conn_temp.close()

# --- STEP 3: HIGH-END CUSTOM GLOBAL STYLING ---
st.set_page_config(page_title="SchemaWhisper Intelligence Engine", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #090d16 0%, #030508 100%); color: #e2e8f0; font-family: 'Inter', system-ui, sans-serif; }
    
    .console-header { background: linear-gradient(90deg, rgba(0, 255, 213, 0.1) 0%, rgba(15, 23, 42, 0.6) 100%); padding: 20px; border-radius: 12px; border: 1px solid rgba(0, 255, 213, 0.2); margin-bottom: 25px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4); }
    .console-title { font-family: 'SF Pro Display', -apple-system, sans-serif; font-size: 32px; font-weight: 800; color: #00ffd5; letter-spacing: -0.5px; }
    .console-subtitle { font-size: 13px; color: #64748b; font-weight: 500; display: block; margin-top: 4px; font-family: monospace; }
    
    .glass-card { background: rgba(15, 23, 42, 0.45); border: 1px solid #1e293b; border-radius: 12px; padding: 22px; backdrop-filter: blur(10px); box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3); margin-bottom: 18px; }
    .panel-label { color: #94a3b8; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 15px; display: flex; align-items: center; gap: 8px; font-family: monospace; }
    
    /* Interactive Hover Tooltip Anchors */
    .metric-row { display: flex; gap: 15px; width: 100%; margin-bottom: 15px; }
    .metric-block { background: rgba(7, 10, 17, 0.75); border-top: 2px solid #00ffd5; padding: 14px; border-radius: 8px; flex: 1; text-align: center; border: 1px solid #1e293b; position: relative; cursor: help; }
    .metric-val { font-size: 24px; font-weight: 800; color: #ffffff; font-family: 'Courier New', monospace; letter-spacing: -0.5px; }
    .metric-lbl { font-size: 10px; color: #64748b; font-weight: 700; text-transform: uppercase; margin-top: 4px; letter-spacing: 0.5px; }
    
    /* Tooltip Popups CSS Design */
    .metric-block .tooltip-popup { visibility: hidden; width: 220px; background: rgba(11, 17, 30, 0.95); border: 1px solid #00ffd5; color: #cbd5e1; text-align: left; padding: 12px; border-radius: 8px; position: absolute; z-index: 99; bottom: 115%; left: 50%; transform: translateX(-50%); box-shadow: 0 10px 25px rgba(0,0,0,0.8); opacity: 0; transition: opacity 0.2s ease, transform 0.2s ease; font-size: 12px; line-height: 1.5; font-family: sans-serif; pointer-events: none; }
    .metric-block:hover .tooltip-popup { visibility: visible; opacity: 1; transform: translateX(-50%) translateY(-5px); }
    .tooltip-popup b { color: #00ffd5; font-family: monospace; }
    
    /* History Timeline Card Component Styles */
    .history-card-item { background: rgba(7, 10, 17, 0.6); padding: 14px; border-radius: 8px; border: 1px solid #1e293b; border-left: 4px solid #38bdf8; margin-bottom: 12px; }
    .history-card-prompt { font-size: 14px; font-weight: 700; color: #ffffff; margin-bottom: 6px; }
    .history-card-meta { font-size: 11px; font-family: monospace; color: #64748b; margin-bottom: 8px; }
    
    .stDataFrame { background: rgba(7, 10, 17, 0.4); border-radius: 8px; border: 1px solid #1e293b; padding: 4px; }
    .stTextInput>div>div>input { background-color: #070a11 !important; border: 1px solid #334155 !important; color: #00ffd5 !important; font-family: 'Courier New', monospace !important; font-size: 15px !important; height: 48px; border-radius: 8px !important; }
    .stTextInput>div>div>input:focus { border-color: #00ffd5 !important; }
    
    /* Custom Stylings for the main history button state control */
    div.stButton > button:first-child { background-color: rgba(30, 41, 59, 0.6) !important; color: #00ffd5 !important; border: 1px solid rgba(0, 255, 213, 0.4) !important; font-family: monospace !important; font-size: 12px !important; font-weight: 700 !important; width: 100% !important; border-radius: 8px !important; height: 38px; }
    div.stButton > button:first-child:hover { background-color: rgba(0, 255, 213, 0.1) !important; border-color: #00ffd5 !important; }
    
    .pipeline-badge { display: inline-block; padding: 4px 10px; font-family: monospace; font-size: 11px; font-weight: 700; background: rgba(0, 255, 213, 0.15); color: #00ffd5; border-radius: 4px; border: 1px solid rgba(0, 255, 213, 0.3); margin-left: auto; }
    .query-mirror-banner { background: rgba(30, 41, 59, 0.5); border-left: 4px solid #38bdf8; padding: 12px 16px; border-radius: 0 8px 8px 0; font-family: 'Courier New', monospace; color: #cbd5e1; font-size: 14px; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="console-header">
    <span class="console-title">⚡ SCHEMAWHISPER</span>
    <span class="console-subtitle">[SYSTEM ENGINE RUNTIME STATUS: ONLINE] Autonomous Relational Context Mapper Matrix</span>
</div>
""", unsafe_allow_html=True)

# --- STEP 4: TWO-COLUMN ASYMMETRIC GRID SYSTEM ---
col_left, col_right = st.columns([1.6, 1], gap="medium")

with col_left:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label">📂 LIVE CATALOG MATRIX VIEW</div>', unsafe_allow_html=True)
    catalog_df = get_catalog_dataframe()
    st.dataframe(
        catalog_df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Table Asset": st.column_config.TextColumn("Database Model Asset Name", width="medium"),
            "Structural Schema Map": st.column_config.TextColumn("System Column Structural Blueprint", width="large")
        }
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col_right:
    # Telemetry Blocks Container combining Structural and Financial Indicators
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label">📊 REAL-TIME MATRIX SYSTEM TELEMETRY & KPIs</div>', unsafe_allow_html=True)
    
    # Row A: System Structural Metrics
    st.markdown(f"""
    <div class="metric-row">
        <div class="metric-block">
            <div class="metric-val">{tbl_count}</div>
            <div class="metric-lbl">Active Catalogs</div>
            <div class="tooltip-popup">
                📦 <b>Database Assets:</b><br>
                • DEPARTMENTS<br>• REGIONS<br>• EMPLOYEES<br>• PRODUCTS<br>• CUSTOMERS<br>• SALES<br>• AUDIT_LOGS
            </div>
        </div>
        <div class="metric-block">
            <div class="metric-val">{emp_count}</div>
            <div class="metric-lbl">Sync Records</div>
            <div class="tooltip-popup">
                👥 <b>Employee Matrix:</b><br>
                Contains 25 randomly generated corporate personnel partitioned across 4 corporate structural departments and 3 geographic global regions.
            </div>
        </div>
        <div class="metric-block">
            <div class="metric-val">{sales_count}</div>
            <div class="metric-lbl">Total Orders</div>
            <div class="tooltip-popup">
                📈 <b>Sales Ledger:</b><br>
                80 active transaction invoices records tracking items sold, item quantities, total calculation amounts, and buying customer fields.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Row B: Dynamic Financial Metrics
    st.markdown(f"""
    <div class="metric-row" style="margin-bottom:0px;">
        <div class="metric-block">
            <div class="metric-val">${total_revenue:,.2f}</div>
            <div class="metric-lbl">Total ARR Volume</div>
            <div class="tooltip-popup">
                💰 <b>Gross Revenue Cumulative:</b><br>
                The absolute mathematical sum of all contract execution totals across the core transactions database ledger.
            </div>
        </div>
        <div class="metric-block">
            <div class="metric-val">${avg_order_value:,.2f}</div>
            <div class="metric-lbl">Avg Order Value</div>
            <div class="tooltip-popup">
                📈 <b>Average Order Value (AOV):</b><br>
                Calculated transaction baseline indicating the average ticket billing size per isolated purchase order ($Total \div Count$).
            </div>
        </div>
        <div class="metric-block">
            <div class="metric-val">{top_city}</div>
            <div class="metric-lbl">Top Region</div>
            <div class="tooltip-popup">
                🌍 <b>Top Performing Region:</b><br>
                The isolated geographic corporate region routing and processing the highest global financial volume metrics.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Input Hub Console Modules
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label">💬 AI COGNITIVE PROMPT HUBS</div>', unsafe_allow_html=True)
    st.text_input(
        label="",
        placeholder="Enter search phrase or background trigger prompt sequence...",
        key="query_input_widget",
        on_change=clear_input_callback
    )
    st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
    
    # Interactive Stateful History Trigger Button Component
    btn_label = "❌ Close Runtime History Log" if st.session_state.show_history else "📜 Open Runtime History Log"
    st.button(label=btn_label, on_click=toggle_history_state)
    st.markdown('</div>', unsafe_allow_html=True)

# --- TRACKED HISTORY VISUALIZATION SLIDEOUT LAYER ---
if st.session_state.show_history:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="panel-label">📜 PERSISTENT RUNTIME PROMPT HISTORY</div>', unsafe_allow_html=True)
    
    if not st.session_state.query_history_log:
        st.markdown('<div style="color: #64748b; font-size: 12px; font-family: monospace;">[HISTORY RETRIEVAL EMPTY: No prompt entries compiled in current runtime session]</div>', unsafe_allow_html=True)
    else:
        # Render historical log stacks backwards to maintain the freshest entries at top
        for idx, entry in enumerate(reversed(st.session_state.query_history_log)):
            st.markdown(f"""
            <div class="history-card-item">
                <div class="history-card-prompt">🔍 Question: {entry['prompt']}</div>
                <div class="history-card-meta">⚡ TIME RECORDED: {entry['timestamp']} │ PIPELINE MODE: {entry['type']}</div>
            </div>
            """, unsafe_allow_html=True)
            st.code(entry['sql'], language="sql")
            
    st.markdown('</div>', unsafe_allow_html=True)

# --- STEP 5: BOTTOM FULL-WIDTH RESULTS ARCHITECTURE DRAWERS ---
active_query = st.session_state.submitted_query

if active_query:
    st.markdown("<br>", unsafe_allow_html=True)
    with st.spinner("Processing architectural vector translation blocks..."):
        try:
            ai_response = generate_sql(active_query, schema_context_str)
            generated_sql = ai_response.sql_query
            
            if ai_response.query_type == QueryType.DATA_QUERY:
                sqlglot.parse_one(generated_sql, read="sqlite")
            
            # Record execution metrics to application session state array cache
            st.session_state.query_history_log.append({
                "prompt": active_query,
                "sql": generated_sql,
                "type": ai_response.query_type.value,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            st.markdown(f"""
            <div class="query-mirror-banner">
                <span style="color: #64748b; font-size: 11px; font-weight:700; display:block; text-transform:uppercase; margin-bottom:4px; font-family:sans-serif;">Active Pipeline Intent Sequence</span>
                🔍 "{active_query}"
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="panel-label">📊 PIPELINE OUTPUT MATRIX <span class="pipeline-badge">{ai_response.query_type.value}</span></div>', unsafe_allow_html=True)
            df, error = execute_database_routine(generated_sql, ai_response.query_type)
            if error:
                st.error(error)
            elif df.empty:
                st.warning("Execution Alert: Empty matrix return block generated.")
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            if ai_response.query_type == QueryType.DATA_QUERY and not df.empty:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown('<div class="panel-label">📝 CORE DATA RETRIEVAL RESULTS OVERVIEW</div>', unsafe_allow_html=True)
                st.write(f"The matrix query statement safely returned **{len(df)} rows** matching your prompt conditions.")
                st.markdown('</div>', unsafe_allow_html=True)
            
            sub_left, sub_right = st.columns(2, gap="medium")
            with sub_left:
                st.markdown('<div class="glass-card" style="height:100%;">', unsafe_allow_html=True)
                st.markdown('<div class="panel-label">🧠 COGNITIVE LABS LOGIC ANALYSIS</div>', unsafe_allow_html=True)
                st.info(ai_response.thought_process)
                st.markdown('</div>', unsafe_allow_html=True)
                
            with sub_right:
                st.markdown('<div class="glass-card" style="height:100%;">', unsafe_allow_html=True)
                st.markdown('<div class="panel-label">💻 COMPILED RUNTIME SYNTAX CODES</div>', unsafe_allow_html=True)
                st.code(generated_sql, language="sql")
                st.markdown('</div>', unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"Execution Intercept Failure Sequence: {e}")
else:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="glass-card" style="text-align: center; padding: 45px; color: #475569; font-family: monospace; font-size: 12px; letter-spacing:0.5px;">[CONSOLE PROCESS STATUS: STANDBY] Ready for structural query context routing.</div>', unsafe_allow_html=True)

# --- STEP 6: ACADEMIC SANDBOX MODULE (STUDENT LEARNING HUB) ---
st.markdown("---")
st.markdown("### 🎓 Academic Sandbox & Learning Hub")
expander = st.expander("ℹ️ Click here to understand how this system works under the hood", expanded=False)
with expander:
    st.markdown("""
    #### 🧠 Core Architectural Flow
    This platform maps natural conversational language into relational database commands. Here is what happens when you press enter:
    1. **Context Collection:** The engine queries database engine metadata internals to track active tables, schemas, and triggers.
    2. **Structured LLM Parsing:** The schema context string alongside your prompt is submitted to OpenAI's structured compilation engine, which responds using a strict JSON outline mapped to a **Pydantic Model**.
    3. **Syntax Guard Intercept:** If it's a data read query, the pipeline processes the token stream through `sqlglot` to verify structural validity before running it against `company.db`.
    
    #### 🧬 3NF Database Normalization Principles
    This data pool follows standard **Third Normal Form (3NF)** principles:
    - **`employees`** does not store text departments. It links to **`departments`** via `dept_id` and **`regions`** via `region_id` using **Foreign Keys**.
    - **`sales`** acts as a central transaction bridge table linking `emp_id`, `product_id`, and `customer_id` together.
    
    #### 🧪 Test Blueprint Prompts for Students
    Copy and paste these sequences into the prompt engine above to observe how the semantic layers execute:
    - **Data Query Test:** `Show the total amount of sales grouped by product category names.`
    - **Stored Procedure Test:** `Write an automated background procedure called audit_sales that triggers after every single insert on sales to record details to audit_logs.`
    """)

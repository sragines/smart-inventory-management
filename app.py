import sqlite3
import pandas as pd
import streamlit as st

# 1. Initialize databases & SQLite triggers on launch
with sqlite3.connect("inventory.db") as conn:
    pd.read_csv("components.csv").to_sql("components", conn, if_exists="replace", index=False)
    pd.read_csv("inventory_movements.csv").to_sql("inventory_movements", conn, if_exists="replace", index=False)
    
    cursor = conn.cursor()
    # Deduct stock on USAGE / OUT
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS update_stock_after_usage
        AFTER INSERT ON inventory_movements
        WHEN NEW.movement_type IN ('USAGE', 'OUT')
        BEGIN
            UPDATE components
            SET stock_quantity = stock_quantity - NEW.quantity
            WHERE component_id = NEW.component_id;
        END;
    """)
    # Increase stock on RESTOCK / IN
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS update_stock_after_restock
        AFTER INSERT ON inventory_movements
        WHEN NEW.movement_type IN ('RESTOCK', 'IN')
        BEGIN
            UPDATE components
            SET stock_quantity = stock_quantity + NEW.quantity
            WHERE component_id = NEW.component_id;
        END;
    """)
    conn.commit()

with sqlite3.connect("suppliers.db") as conn:
    pd.read_csv("suppliers.csv").to_sql("suppliers", conn, if_exists="replace", index=False)

with sqlite3.connect("procurement.db") as conn:
    pd.read_csv("purchase_orders.csv").to_sql("purchase_orders", conn, if_exists="replace", index=False)


# 2. Streamlit Application
st.set_page_config(page_title="Enterprise Inventory Operations", layout="wide")

DATABASES = {
    "Inventory Management (inventory.db)": {
        "db": "inventory.db",
        "tables": ["components", "inventory_movements"]
    },
    "Supplier Management (suppliers.db)": {
        "db": "suppliers.db",
        "tables": ["suppliers"]
    },
    "Procurement Operations (procurement.db)": {
        "db": "procurement.db",
        "tables": ["purchase_orders"]
    }
}

def fetch_data(db_file, query):
    with sqlite3.connect(db_file) as conn:
        return pd.read_sql_query(query, conn)

def execute_query(db_file, query, params=()):
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()

# Navigation
st.sidebar.title("Operational Control")
selected_db_label = st.sidebar.selectbox("Select Target Database", list(DATABASES.keys()))
db_config = DATABASES[selected_db_label]
selected_table = st.sidebar.selectbox("Select Target Table", db_config["tables"])

st.sidebar.markdown("---")
st.sidebar.caption(f"Active Connection: `{db_config['db']}`")

# Dashboard UI
st.title("Automotive Parts Inventory & Procurement Console")

tab1, tab2, tab3, tab4 = st.tabs([
    "Data Administration (CRUD)", 
    "Stock Level Thresholds", 
    "Purchase Order Tracking", 
    "Vendor Performance Metrics"
])

# Tab 1: CRUD
with tab1:
    st.subheader(f"Table View: {selected_table}")
    
    df = fetch_data(db_config["db"], f"SELECT * FROM {selected_table}")
    st.dataframe(df)
    st.caption(f"Total Records: {len(df)}")

    col1, col2 = st.columns(2)

    with col1:
        st.write("### Record Entry")
        with st.form(key="insert_record_form"):
            form_data = {}
            
            # Haetaan viiteavaimet muista tauluista valikoita varten
            comp_ids = fetch_data("inventory.db", "SELECT component_id FROM components")["component_id"].unique() if selected_table != "components" else []
            supp_ids = fetch_data("suppliers.db", "SELECT supplier_id FROM suppliers")["supplier_id"].unique() if selected_table != "suppliers" else []

            for col in df.columns:
                col_lower = col.lower()
                
                # Dynamic Dropdowns for FKs & Fixed Enums
                if col_lower == "component_id" and len(comp_ids) > 0:
                    form_data[col] = st.selectbox(col, comp_ids)
                elif col_lower == "supplier_id" and len(supp_ids) > 0:
                    form_data[col] = st.selectbox(col, supp_ids)
                elif col_lower == "movement_type":
                    form_data[col] = st.selectbox(col, ["USAGE", "RESTOCK", "IN", "OUT"])
                elif col_lower == "order_status":
                    form_data[col] = st.selectbox(col, ["OPEN", "IN_TRANSIT", "OVERDUE", "DELIVERED", "CANCELLED"])
                
                # Dates -> Date Input
                elif "date" in col_lower:
                    form_data[col] = st.date_input(col).strftime("%Y-%m-%d")
                
                # Quantities & Numbers -> Number Input
                elif any(num_word in col_lower for num_word in ["quantity", "stock", "point", "cost", "score", "lead_time"]):
                    form_data[col] = st.number_input(col, min_value=0, step=1)
                
                # Standard Text Inputs for everything else (IDs, Names, Categories)
                else:
                    form_data[col] = st.text_input(col)
            
            if st.form_submit_button("Commit Record"):
                columns = ", ".join(form_data.keys())
                placeholders = ", ".join(["?"] * len(form_data))
                sql = f"INSERT INTO {selected_table} ({columns}) VALUES ({placeholders})"
                
                try:
                    execute_query(db_config["db"], sql, tuple(form_data.values()))
                    st.success("Record committed successfully.")
                    st.rerun()
                except Exception as err:
                    st.error(f"Execution Error: {err}")

    with col2:
        st.write("### Record Removal")
        pk_column = df.columns[0]
        selected_id = st.selectbox("Select Identifier to Delete", df[pk_column].unique())
        
        if st.button("Delete Record"):
            sql = f"DELETE FROM {selected_table} WHERE {pk_column} = ?"
            execute_query(db_config["db"], sql, (selected_id,))
            st.warning(f"Record {selected_id} deleted.")
            st.rerun()

# Tab 2: Low Stock Analysis
with tab2:
    st.subheader("Critical Stock Levels")
    query_low_stock = """
        SELECT component_id, component_name, category, stock_quantity, reorder_point, safety_stock, unit_cost
        FROM components
        WHERE stock_quantity <= reorder_point
        ORDER BY stock_quantity ASC
    """
    st.dataframe(fetch_data("inventory.db", query_low_stock))

# Tab 3: Order Tracking
with tab3:
    st.subheader("Open Purchase Orders")
    query_orders = """
        SELECT order_id, component_id, supplier_id, order_date, expected_delivery_date, quantity_ordered, order_status
        FROM purchase_orders
        WHERE order_status IN ('OVERDUE', 'OPEN', 'IN_TRANSIT')
        ORDER BY expected_delivery_date ASC
    """
    st.dataframe(fetch_data("procurement.db", query_orders))

# Tab 4: Vendor Metrics
with tab4:
    st.subheader("Supplier Reliability & Lead Times")
    st.dataframe(fetch_data("suppliers.db", "SELECT * FROM suppliers ORDER BY reliability_score ASC"))

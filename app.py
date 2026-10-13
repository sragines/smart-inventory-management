import sqlite3
import pandas as pd
import streamlit as st

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

# Sidebar
st.sidebar.title("Operational Control")
selected_db_label = st.sidebar.selectbox("Select Target Database", list(DATABASES.keys()))
db_config = DATABASES[selected_db_label]
selected_table = st.sidebar.selectbox("Select Target Table", db_config["tables"])

st.sidebar.markdown("---")
st.sidebar.caption(f"Active Connection: `{db_config['db']}`")

# Main Interface
st.title("Automotive Parts Inventory & Procurement Console")

tab1, tab2, tab3, tab4 = st.tabs([
    "Data Administration (CRUD)", 
    "Stock Level Thresholds", 
    "Purchase Order Tracking", 
    "Vendor Performance Metrics"
])

# Tab 1: CRUD Operations
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
            for col in df.columns:
                form_data[col] = st.text_input(label=col)
            
            if st.form_submit_button("Commit Record"):
                columns = ", ".join(form_data.keys())
                placeholders = ", ".join(["?"] * len(form_data))
                sql = f"INSERT INTO {selected_table} ({columns}) VALUES ({placeholders})"
                
                try:
                    execute_query(db_config["db"], sql, tuple(form_data.values()))
                    st.success("Record committed successfully.")
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

# Tab 2: Reorder Threshold Analysis
with tab2:
    st.subheader("Critical Stock Levels")
    query_low_stock = """
        SELECT component_id, component_name, category, stock_quantity, reorder_point, safety_stock, unit_cost
        FROM components
        WHERE stock_quantity <= reorder_point
        ORDER BY stock_quantity ASC
    """
    st.dataframe(fetch_data("inventory.db", query_low_stock))

# Tab 3: Pending & Overdue Orders
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

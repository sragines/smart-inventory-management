import os
import sqlite3
import pandas as pd
import streamlit as st

# 1. Initialize databases & SQLite triggers on launch (only if missing)
def init_databases():
    # Inventory DB
    db_exists = os.path.exists("inventory.db")
    with sqlite3.connect("inventory.db") as conn:
        if not db_exists:
            pd.read_csv("components.csv").to_sql("components", conn, if_exists="replace", index=False)
            pd.read_csv("inventory_movements.csv").to_sql("inventory_movements", conn, if_exists="replace", index=False)
        
        cursor = conn.cursor()
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

    # Suppliers DB
    if not os.path.exists("suppliers.db"):
        with sqlite3.connect("suppliers.db") as conn:
            pd.read_csv("suppliers.csv").to_sql("suppliers", conn, if_exists="replace", index=False)

    # Procurement DB
    if not os.path.exists("procurement.db"):
        with sqlite3.connect("procurement.db") as conn:
            pd.read_csv("purchase_orders.csv").to_sql("purchase_orders", conn, if_exists="replace", index=False)

init_databases()

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

def safe_rerun():
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

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
            
            # Haetaan viitetiedot muista tauluista
            comp_df = fetch_data("inventory.db", "SELECT component_id, component_name, category FROM components") if selected_table != "components" else pd.DataFrame()
            supp_df = fetch_data("suppliers.db", "SELECT supplier_id, supplier_name FROM suppliers") if selected_table != "suppliers" else pd.DataFrame()

            for col in df.columns:
                col_lower = col.lower()
                
                # Viiteavaimet (FK) dropdown-valikkoina muissa tauluissa
                if col_lower == "component_id" and not comp_df.empty:
                    selected_comp = st.selectbox("Select Component", comp_df["component_id"].unique())
                    form_data[col] = selected_comp
                    
                    comp_info = comp_df[comp_df["component_id"] == selected_comp].iloc[0]
                    st.caption(f"ℹ️ **Selected Part:** {comp_info['component_name']} ({comp_info['category']})")

                elif col_lower == "supplier_id" and not supp_df.empty:
                    selected_supp = st.selectbox("Select Supplier", supp_df["supplier_id"].unique())
                    form_data[col] = selected_supp
                    
                    supp_info = supp_df[supp_df["supplier_id"] == selected_supp].iloc[0]
                    st.caption(f"ℹ️ **Selected Vendor:** {supp_info['supplier_name']}")

                elif col_lower == "movement_type":
                    form_data[col] = st.selectbox(col, ["USAGE", "RESTOCK", "IN", "OUT"])

                elif col_lower == "order_status":
                    form_data[col] = st.selectbox(col, ["OPEN", "IN_TRANSIT", "OVERDUE", "DELIVERED", "CANCELLED"])
                
                # Päivämäärät -> Kalenterivalitsin
                elif "date" in col_lower:
                    form_data[col] = st.date_input(col).strftime("%Y-%m-%d")
                
                # Numerot ja määrät -> Numerosyöte
                elif any(num_word in col_lower for num_word in ["quantity", "stock", "point", "cost", "score", "lead_time"]):
                    form_data[col] = st.number_input(col, min_value=0, step=1)
                
                # Pääavaimet ja tekstit (esim. uuden osan luominen 'components'-tauluun)
                else:
                    form_data[col] = st.text_input(col)
            
            if st.form_submit_button("Commit Record"):
                columns = ", ".join(form_data.keys())
                placeholders = ", ".join(["?"] * len(form_data))
                sql = f"INSERT INTO {selected_table} ({columns}) VALUES ({placeholders})"
                
                try:
                    execute_query(db_config["db"], sql, tuple(form_data.values()))
                    st.success("Record committed successfully.")
                    safe_rerun()
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
            safe_rerun()

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

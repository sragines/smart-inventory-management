# Smart Inventory & Procurement System

A Streamlit application for automotive inventory and procurement management. Built for the Data-Intensive Systems course.

## Features

- **3 SQLite Databases:** Separate databases for Inventory (`inventory.db`), Suppliers (`suppliers.db`), and Procurement (`procurement.db`).
- **Data Administration:** Full CRUD (Create, Read, Delete) capabilities with smart dynamic inputs (dropdowns for foreign keys with live component descriptions, calendar pickers for dates, and numeric inputs for quantities).
- **Automated Stock Triggers:** Uses native SQLite database triggers to automatically update component stock levels in real time during stock usage or restock events.
- **Dashboards:** Low-stock alerts, overdue purchase order tracking, and supplier reliability metrics.
- **AI-Generated Scenario Data:** Populated with synthetic datasets (fictional suppliers, component catalogs, order histories) stored in CSV files, allowing users to customize or expand the data as needed.

## Tech Stack

- Python, Streamlit, SQLite, Pandas

## Quickstart

1. Install dependencies:
   ```bash
   pip install streamlit pandas

2. Launch the application:

  ```bash
streamlit run app.py


## Future Development & Production Readiness
If scaled for a real-world enterprise solution, key production enhancements would include:

Centralized Relational Database: Migrating local SQLite files to a cloud-hosted database (e.g., PostgreSQL or MySQL) for multi-user concurrency and data security.

Authentication & RBAC: Implementing Role-Based Access Control to restrict write/delete permissions based on user roles (e.g., Warehouse Operator vs. Procurement Manager).

ERP & API Integration: Integrating external supplier APIs and automated email alert notifications when stock drops below safety thresholds.

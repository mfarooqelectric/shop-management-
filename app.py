import sqlite3
import pandas as pd
import streamlit as st

# Database Connection
conn = sqlite3.connect("shop_inventory.db", check_same_thread=False)
cursor = conn.cursor()

# Create Tables
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    company TEXT NOT NULL,
    price REAL NOT NULL,
    stock INTEGER NOT NULL
)
"""
)
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT,
    company TEXT,
    quantity INTEGER,
    total_price REAL,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""
)
conn.commit()

# App Layout
st.set_page_config(page_title="Shop Management System", layout="wide")
st.title("🛍️ Shop Management & Billing System")

menu = ["Billing (POS)", "Stock Management", "Company-wise Stock", "Sales History"]
choice = st.sidebar.selectbox("Navigation", menu)

# 1. BILLING SYSTEM
if choice == "Billing (POS)":
    st.header("🛒 Billing System")

    df_products = pd.read_sql_query("SELECT * FROM products", conn)

    if df_products.empty:
        st.warning(
            "Stock mein koi product nahi hai. Pehle Stock Management mein ja kar products add karein."
        )
    else:
        col1, col2 = st.columns([2, 1])

        with col1:
            selected_prod = st.selectbox(
                "Select Item", df_products["name"].tolist()
            )
            prod_details = df_products[
                df_products["name"] == selected_prod
            ].iloc[0]

            st.info(
                f"*Company:* {prod_details['company']} | *Price:* Rs. {prod_details['price']} | *Available Stock:* {prod_details['stock']}"
            )

            quantity = st.number_input("Quantity", min_value=1, step=1)
            total_price = quantity * prod_details["price"]

            st.subheader(f"Total Amount: Rs. {total_price}")

            if st.button("Generate Bill & Deduct Stock"):
                if quantity > prod_details["stock"]:
                    st.error("Stock mein itni quantity mojood nahi hai!")
                else:
                    # Deduct Stock
                    new_stock = prod_details["stock"] - quantity
                    cursor.execute(
                        "UPDATE products SET stock = ? WHERE id = ?",
                        (new_stock, prod_details["id"]),
                    )

                    # Record Sale
                    cursor.execute(
                        "INSERT INTO sales (product_name, company, quantity, total_price) VALUES (?, ?, ?, ?)",
                        (
                            selected_prod,
                            prod_details["company"],
                            quantity,
                            total_price,
                        ),
                    )

                    conn.commit()
                    st.success(
                        f"Bill Success! Customer Total: Rs. {total_price}"
                    )
                    st.rerun()

# 2. STOCK MANAGEMENT
elif choice == "Stock Management":
    st.header("📦 Add / Update Stock")

    with st.form("add_product"):
        p_name = st.text_input("Product Name")
        p_company = st.text_input("Company Name")
        p_price = st.number_input("Sale Price (per unit)", min_value=0.0)
        p_stock = st.number_input("Quantity", min_value=1, step=1)

        submit = st.form_submit_button("Add Product")

        if submit:
            if p_name and p_company:
                cursor.execute(
                    "INSERT INTO products (name, company, price, stock) VALUES (?, ?, ?, ?)",
                    (p_name, p_company, p_price, p_stock),
                )
                conn.commit()
                st.success(f"{p_name} Stock mein add ho gaya hai!")
                st.rerun()
            else:
                st.error("Tamam fields bharna zaroori hain.")

    st.subheader("Current All Stock")
    df_all = pd.read_sql_query("SELECT * FROM products", conn)
    st.dataframe(df_all, use_container_width=True)

# 3. COMPANY-WISE STOCK
elif choice == "Company-wise Stock":
    st.header("🏢 Filter Stock by Company")

    df_comp = pd.read_sql_query("SELECT DISTINCT company FROM products", conn)
    companies = df_comp["company"].tolist()

    if companies:
        selected_comp = st.selectbox("Select Company", companies)
        filtered_df = pd.read_sql_query(
            "SELECT name, price, stock FROM products WHERE company = ?",
            conn,
            params=(selected_comp,),
        )
        st.subheader(f"Stock list for: {selected_comp}")
        st.dataframe(filtered_df, use_container_width=True)
    else:
        st.info("Filhal koi company ka stock available nahi hai.")

# 4. SALES HISTORY
elif choice == "Sales History":
    st.header("📊 Sales History")
    df_sales = pd.read_sql_query("SELECT * FROM sales", conn)

    if not df_sales.empty:
        st.dataframe(df_sales, use_container_width=True)
        st.metric(
            label="Total Revenue", value=f"Rs. {df_sales['total_price'].sum()}"
        )
    else:
        st.info("Abhi tak koi sale nahi hui.")

st.set_page_config(page_title="My Electric Shop", layout="wide")
st.title("⚡ M. FAROOQ ELECTRIC STORE")	

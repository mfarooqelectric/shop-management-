import streamlit as st
import sqlite3
from datetime import datetime

# ---------------------------------------------------------
# DATABASE SETUP & INITIALIZATION
# ---------------------------------------------------------
DB_FILE = "shop_inventory.db"

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Products Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL UNIQUE,
            category TEXT,
            quantity INTEGER NOT NULL DEFAULT 0,
            unit_price REAL NOT NULL DEFAULT 0.0
        )
    ''')

    # 2. Sales Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT,
            customer_name TEXT,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_amount REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 3. Purchases Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_name TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            purchase_price REAL NOT NULL,
            total_amount REAL NOT NULL,
            paid_amount REAL NOT NULL,
            payment_status TEXT NOT NULL,
            purchase_date TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# Helper Functions
def fetch_all(query, params=()):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

def execute_query(query, params=()):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()

def record_purchase(supplier, product_name, category, qty, buy_price, paid_amt, status):
    total_cost = qty * buy_price
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO purchases 
        (supplier_name, product_name, quantity, purchase_price, total_amount, paid_amount, payment_status, purchase_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (supplier, product_name, qty, buy_price, total_cost, paid_amt, status, today_str))

    cursor.execute("SELECT quantity FROM products WHERE product_name = ?", (product_name,))
    row = cursor.fetchone()

    if row:
        new_qty = row[0] + qty
        cursor.execute("UPDATE products SET quantity = ?, unit_price = ? WHERE product_name = ?", (new_qty, buy_price, product_name))
    else:
        cursor.execute("INSERT INTO products (product_name, category, quantity, unit_price) VALUES (?, ?, ?, ?)",
                       (product_name, category, qty, buy_price))

    conn.commit()
    conn.close()


# ---------------------------------------------------------
# STREAMLIT UI LAYOUT
# ---------------------------------------------------------
st.set_page_config(page_title="Shop Inventory & Billing System", layout="wide")

# =========================================================
# TOP HEADER - SHOP NAME
# =========================================================
st.markdown("<h1 style='text-align: center; color: #1E88E5;'>⚡ M.FAROOQ ELECTRIC STORE .</h1>", unsafe_allow_html=True)
st.markdown("<h5 style='text-align: center; color: gray;'>Karachi, Pakistan | Contact: 0300-9294129</h5>", unsafe_allow_html=True)
st.divider()

tabs = st.tabs(["📄 Generate Bill / Invoice", "🛒 Main Stock (Products)", "📥 Purchase (Kharid Khata)", "💰 Sales History"])

# =========================================================
# TAB 1: BILL / INVOICE GENERATOR (NEW FEATURE)
# =========================================================
with tabs[0]:
    st.subheader("🧾 Create Customer Bill")
    
    col_cust1, col_cust2 = st.columns(2)
    with col_cust1:
        cust_name = st.text_input("Customer Name:", value="Cash Customer")
    with col_cust2:
        inv_no = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        st.text_input("Invoice No:", value=inv_no, disabled=True)

    prods = fetch_all("SELECT product_name, quantity, unit_price FROM products WHERE quantity > 0")
    
    if prods:
        prod_options = {f"{p[0]} (Available: {p[1]})": p for p in prods}
        selected_option = st.selectbox("Select Item to Add:", list(prod_options.keys()))
        selected_prod = prod_options[selected_option]

        with st.form("bill_form", clear_on_submit=False):
            c1, c2 = st.columns(2)
            with c1:
                sale_qty = st.number_input("Quantity:", min_value=1, max_value=selected_prod[1], step=1)
            with c2:
                sale_price = st.number_input("Selling Price per Unit (PKR):", min_value=0.0, value=selected_prod[2], step=10.0)
            
            total_bill = sale_qty * sale_price
            st.markdown(f"### *Total Amount:* Rs. {total_bill:,.2f}")
            
            generate_bill = st.form_submit_button("Generate & Save Bill")

        if generate_bill:
            # Stock Deduct
            new_q = selected_prod[1] - sale_qty
            execute_query("UPDATE products SET quantity = ? WHERE product_name = ?", (new_q, selected_prod[0]))
            
            # Record Sale
            execute_query(
                "INSERT INTO sales (invoice_no, customer_name, product_name, quantity, unit_price, total_amount) VALUES (?, ?, ?, ?, ?, ?)",
                (inv_no, cust_name, selected_prod[0], sale_qty, sale_price, total_bill)
            )
            
            st.success("Bill successfully generated!")
            
            # PRINTABLE INVOICE DISPLAY
            st.markdown("---")
            st.markdown(f"""
            <div style="border:2px solid #333; padding:20px; border-radius:10px; background-color:#f9f9f9; color:#000;">
                <h2 style="text-align:center; margin-bottom:0;">SHAH-RUKH ELECTRIC & TRADING CO.</h2>
                <p style="text-align:center; margin-top:0;">Karachi, Pakistan | Ph: 0347-3395101</p>
                <hr>
                <p><b>Invoice No:</b> {inv_no} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                <p><b>Customer Name:</b> {cust_name}</p>
                <table style="width:100%; border-collapse: collapse; margin-top:10px;">
                    <thead>
                        <tr style="background-color:#eee; border-bottom:1px solid #333;">
                            <th style="text-align:left; padding:8px;">Item Description</th>
                            <th style="text-align:center; padding:8px;">Qty</th>
                            <th style="text-align:right; padding:8px;">Unit Price</th>
                            <th style="text-align:right; padding:8px;">Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="padding:8px;">{selected_prod[0]}</td>
                            <td style="text-align:center; padding:8px;">{sale_qty}</td>
                            <td style="text-align:right; padding:8px;">Rs. {sale_price:,.2f}</td>
                            <td style="text-align:right; padding:8px;">Rs. {total_bill:,.2f}</td>
                        </tr>
                    </tbody>
                </table>
                <hr>
                <h3 style="text-align:right;">Grand Total: Rs. {total_bill:,.2f}</h3>
                <p style="text-align:center; font-size:12px;">Thank you for your business!</p>
            </div>
            """, unsafe_allow_html=True)
            st.info("💡 Bill ka print nikalne ke liye keyboard par *Ctrl + P* press karein.")
    else:
        st.warning("Stock mein filhal koi item available nahi hai. Pehle Purchase tab se stock add karein.")


# =========================================================
# TAB 2: MAIN STOCK VIEW
# =========================================================
with tabs[1]:
    st.subheader("Current Available Stock")
    products = fetch_all("SELECT id, product_name, category, quantity, unit_price FROM products")
    if products:
        stock_data = [{"ID": p[0], "Product Name": p[1], "Category": p[2] if p[2] else "-", "Stock Qty": p[3], "Unit Price": f"Rs. {p[4]:,.2f}", "Total Value": f"Rs. {(p[3]*p[4]):,.2f}"} for p in products]
        st.dataframe(stock_data, use_container_width=True)
    else:
        st.info("Stock empty hai.")


# =========================================================
# TAB 3: PURCHASE KHATA
# =========================================================
with tabs[2]:
    st.subheader("📥 New Stock Purchase Entry (Kharid)")
    with st.form("purchase_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            supplier = st.text_input("Supplier / Dealer Name:")
            prod_name = st.text_input("Product Name:")
            category = st.text_input("Category:")
            qty = st.number_input("Quantity Purchased:", min_value=1, step=1)
        with col2:
            buy_price = st.number_input("Purchase Price Per Unit (PKR):", min_value=0.0, step=10.0)
            total_cost = qty * buy_price
            paid_amt = st.number_input("Paid Amount (PKR):", min_value=0.0, value=total_cost, step=10.0)
            status = "Paid" if paid_amt >= total_cost else ("Partial" if paid_amt > 0 else "Pending")

        submit_purchase = st.form_submit_button("Save Purchase & Update Stock")

    if submit_purchase and supplier and prod_name:
        record_purchase(supplier, prod_name, category, qty, buy_price, paid_amt, status)
        st.success("Purchase entry saved!")
        st.rerun()

    st.divider()
    purchases = fetch_all("SELECT id, supplier_name, product_name, quantity, purchase_price, total_amount, paid_amount, payment_status, purchase_date FROM purchases ORDER BY id DESC")
    if purchases:
        p_list = [{"ID": r[0], "Date": r[8], "Supplier": r[1], "Item": r[2], "Qty": r[3], "Total Cost": f"Rs. {r[5]:,.2f}", "Paid": f"Rs. {r[6]:,.2f}", "Status": r[7]} for r in purchases]
        st.dataframe(p_list, use_container_width=True)


# =========================================================
# TAB 4: SALES HISTORY
# =========================================================
with tabs[3]:
    st.subheader("📊 All Generated Bills & Sales")
    sales = fetch_all("SELECT id, invoice_no, customer_name, product_name, quantity, total_amount, timestamp FROM sales ORDER BY id DESC")
    if sales:
        s_list = [{"ID": s[0], "Invoice No": s[1], "Date": s[6], "Customer": s[2], "Item": s[3], "Qty": s[4], "Total": f"Rs. {s[5]:,.2f}"} for s in sales]
        st.dataframe(s_list, use_container_width=True)

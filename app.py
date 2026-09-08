import streamlit as st
import pandas as pd
import urllib.parse
from streamlit_gsheets import GSheetsConnection

# ----------------------------------------------------
# 1. PAGE CONFIGURATION
# ----------------------------------------------------
st.set_page_config(page_title="M. Farooq Electric Store", layout="wide")
st.title("⚡ M. Farooq Electric Store - Management System")

# ----------------------------------------------------
# 2. GOOGLE SHEETS CONNECTION SETUP
# ----------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def get_sheet_data(worksheet_name, default_cols):
    """Google Sheet se data load karne ke liye helper function"""
    try:
        df = conn.read(worksheet=worksheet_name, ttl="0m")
        if df.empty:
            return pd.DataFrame(columns=default_cols)
        # Ensure column names are stripped and lowercased
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame(columns=default_cols)

def save_sheet_data(worksheet_name, df):
    """Google Sheet me crash-free data save karne ke liye helper function"""
    cleaned_df = df.reset_index(drop=True).fillna("")
    data_matrix = [cleaned_df.columns.tolist()] + cleaned_df.values.tolist()
    try:
        # Direct underlying gspread update (Bypasses streamlit-gsheets bug)
        ws = conn._instance.worksheet(worksheet_name)
        ws.clear()
        ws.update(data_matrix)
    except Exception:
        # Standard fallback update
        conn.update(worksheet=worksheet_name, data=cleaned_df)

# ----------------------------------------------------
# 3. DEFAULT COLUMNS DEFINITION
# ----------------------------------------------------
PRODUCTS_COLS = ["id", "product_name", "category", "quantity", "unit_price", "cost_price"]
SALES_COLS = ["id", "invoice_no", "customer_name", "product_name", "quantity", "unit_price", "cost_price", "total_amount", "paid_amount", "payment_status", "timestamp"]
PURCHASES_COLS = ["id", "supplier_name", "product_name", "quantity", "purchase_price", "total_amount", "paid_amount", "payment_status", "purchase_date"]
CUST_LEDGER_COLS = ["id", "customer_name", "invoice_no", "total_amount", "paid_amount", "balance", "date"]
SUPP_LEDGER_COLS = ["id", "supplier_name", "bill_no", "total_amount", "paid_amount", "balance", "date"]

# ----------------------------------------------------
# 4. DATA LOADING
# ----------------------------------------------------
products_df = get_sheet_data("products", PRODUCTS_COLS)
sales_df = get_sheet_data("sales", SALES_COLS)
purchases_df = get_sheet_data("purchases", PURCHASES_COLS)
cust_ledger_df = get_sheet_data("customer_ledger", CUST_LEDGER_COLS)
supp_ledger_df = get_sheet_data("supplier_ledger", SUPP_LEDGER_COLS)

# ----------------------------------------------------
# 5. NAVIGATION / TABS
# ----------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📦 Inventory / Stock", "🛒 Sales & Invoicing", "🛍️ Purchases"])

# --- TAB 1: INVENTORY ---
with tab1:
    st.subheader("📦 Main Stock (Products)")
    st.dataframe(products_df, use_container_width=True)

# --- TAB 2: SALES & INVOICING ---
with tab2:
    st.subheader("🛒 Record Sale & Generate Invoice")
    
    col1, col2 = st.columns(2)
    with col1:
        cust_name = st.text_input("Customer Name")
        cust_phone = st.text_input("Customer WhatsApp (e.g. 3001234567)")
    with col2:
        inv_no = st.text_input("Invoice No", value="INV-001")
    
    st.divider()
    
    if not products_df.empty and "product_name" in products_df.columns:
        p_name = st.selectbox("Select Product", products_df["product_name"].tolist())
        qty = st.number_input("Quantity", min_value=1, value=1)
        
        # Get item price
        item_row = products_df[products_df["product_name"] == p_name]
        u_price = float(item_row["unit_price"].values[0]) if not item_row.empty else 0.0
        c_price = float(item_row["cost_price"].values[0]) if not item_row.empty else 0.0
        
        tot_amt = qty * u_price
        st.write(f"*Total Amount:* Rs. {tot_amt}")
        
        paid_amt = st.number_input("Paid Amount", min_value=0.0, value=tot_amt)
        
        if st.button("Save Sale & Generate Bill"):
            new_sale = pd.DataFrame([{
                "id": len(sales_df) + 1,
                "invoice_no": inv_no,
                "customer_name": cust_name,
                "product_name": p_name,
                "quantity": qty,
                "unit_price": u_price,
                "cost_price": c_price,
                "total_amount": tot_amt,
                "paid_amount": paid_amt,
                "payment_status": "Paid" if paid_amt >= tot_amt else "Pending",
                "timestamp": str(pd.Timestamp.now())
            }])
            
            sales_df = pd.concat([sales_df, new_sale], ignore_index=True)
            save_sheet_data("sales", sales_df)
            st.success("Sale Recorded Successfully!")
            
            # WHATSAPP INTEGRATION
            if cust_phone:
                clean_phone = cust_phone.lstrip("0")
                msg = f"Dear {cust_name}, Thank you for shopping at M. Farooq Electric! Invoice #{inv_no} Total: Rs. {tot_amt}. Paid: Rs. {paid_amt}."
                encoded_msg = urllib.parse.quote(msg)
                wa_url = f"https://wa.me/92{clean_phone}?text={encoded_msg}"
                st.markdown(f'<a href="{wa_url}" target="_blank"><button style="background-color:#25D366;color:white;border:none;padding:10px 20px;border-radius:5px;cursor:pointer;font-weight:bold;">📲 Send Bill Summary on WhatsApp</button></a>', unsafe_allow_html=True)
    else:
        st.info("No products found. Please add products in Google Sheets first.")

# --- TAB 3: PURCHASES ---
with tab3:
    st.subheader("🛍️ Record Purchase")
    st.dataframe(purchases_df, use_container_width=True)

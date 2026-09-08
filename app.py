import io
from datetime import datetime

import pandas as pd
import streamlit as st
import gspread
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from streamlit_gsheets import GSheetsConnection

# ----------------------------------------------------
# 0. CONFIG
# ----------------------------------------------------
SHEET_NAME = "M.Farooq Electric Store"

# ----------------------------------------------------
# 1. GOOGLE SHEETS CONNECTION SETUP
# ----------------------------------------------------
# conn -> read ke liye (streamlit_gsheets)
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_resource
def get_gspread_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    # Handle both escaped double-slashes and single-escaped newlines
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    return gspread.service_account_from_dict(creds_dict)

def get_sheet_data(worksheet_name, default_cols):
    try:
        df = conn.read(worksheet=worksheet_name, ttl="0m")
        df = df.dropna(how="all")
        if df.empty:
            return pd.DataFrame(columns=default_cols)
        return df
    except Exception:
        return pd.DataFrame(columns=default_cols)

def save_sheet_data(worksheet_name, df):
    gc = get_gspread_client()
    sh = gc.open(SHEET_NAME)

    try:
        worksheet = sh.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=worksheet_name, rows=1000, cols=max(len(df.columns), 1))
    df_clean = df.fillna("")
    worksheet.clear()
    worksheet.update([df_clean.columns.values.tolist()] + df_clean.values.tolist())

def clean_products_df(df):
    df = df.copy()
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce").fillna(0.0)
    df["cost_price"] = pd.to_numeric(df["cost_price"], errors="coerce").fillna(0.0)
    return df

# Default Columns Setup
PRODUCTS_COLS = ["id", "product_name", "category", "quantity", "unit_price", "cost_price"]
SALES_COLS = ["id", "invoice_no", "customer_name", "product_name", "quantity", "unit_price", "cost_price", "total_amount", "paid_amount", "payment_status", "timestamp"]
PURCHASES_COLS = ["id", "supplier_name", "product_name", "quantity", "purchase_price", "total_amount", "paid_amount", "payment_status", "purchase_date"]
CUST_LEDGER_COLS = ["id", "customer_name", "invoice_no", "total_amount", "paid_amount", "balance", "date"]
SUPP_LEDGER_COLS = ["id", "supplier_name", "bill_no", "total_amount", "paid_amount", "balance", "date"]

# ----------------------------------------------------
# 2. PDF GENERATOR FUNCTION
# ----------------------------------------------------
def generate_pdf(invoice_no, customer_name, items_df, grand_total, paid_amount):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)

    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, 750, "M. FAROOQ ELECTRIC STORE")
    p.setFont("Helvetica", 10)
    p.drawString(220, 735, "Karachi, Pakistan | Contact: 0300-9294129")

    p.line(50, 720, 550, 720)

    p.drawString(50, 700, f"Invoice No: {invoice_no}")
    p.drawString(50, 685, f"Customer Name: {customer_name}")
    p.drawString(50, 670, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    y = 630
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, "Item Name")
    p.drawString(250, y, "Qty")
    p.drawString(350, y, "Unit Price")
    p.drawString(450, y, "Total")
    p.line(50, y - 5, 550, y - 5)

    y -= 20
    p.setFont("Helvetica", 10)
    for idx, row in items_df.iterrows():
        p.drawString(50, y, str(row['product_name']))
        p.drawString(250, y, str(row['quantity']))
        p.drawString(350, y, f"Rs. {row['unit_price']}")
        p.drawString(450, y, f"Rs. {row['total_amount']}")
        y -= 15

    p.line(50, y, 550, y)
    y -= 20
    p.setFont("Helvetica-Bold", 10)
    p.drawString(350, y, f"Grand Total: Rs. {grand_total}")
    p.drawString(350, y - 15, f"Paid Amount: Rs. {paid_amount}")
    p.drawString(350, y - 30, f"Balance: Rs. {grand_total - paid_amount}")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# ----------------------------------------------------
# 3. STREAMLIT UI & NAVIGATION
# ----------------------------------------------------
st.title("⚡ M. Farooq Electric Store System")

menu = ["Sales & Invoice", "Customer Khata", "Supplier Management", "Profit & Loss Dashboard", "Inventory", "Purchase Return", "Sales Return"]
choice = st.sidebar.selectbox("Navigation Menu", menu)

# --- SALES & INVOICE ---
if choice == "Sales & Invoice":
    st.subheader("🧾 Create Sales Invoice")
    cust_name = st.text_input("Customer Name")
    inv_no = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    st.text(f"Invoice No: {inv_no}")

    products_df = get_sheet_data("products", PRODUCTS_COLS)
    if not products_df.empty:
        products_df = clean_products_df(products_df)
        prod_select = st.selectbox("Select Product", products_df['product_name'].tolist())
        selected_prod = products_df[products_df['product_name'] == prod_select].iloc[0]
        max_qty = int(selected_prod['quantity']) if int(selected_prod['quantity']) > 0 else 1
        qty = st.number_input("Quantity", min_value=1, max_value=max_qty, value=1)
        unit_price = float(selected_prod['unit_price'])
        cost_price = float(selected_prod['cost_price'])
        total_price = qty * unit_price
        st.write(f"Unit Price: Rs. {unit_price} | Total: Rs. {total_price}")
        paid = st.number_input("Paid Amount", min_value=0.0, value=float(total_price))
        if st.button("Generate Invoice & Save"):
            if not cust_name.strip():
                st.error("Customer Name zaroori hai.")
            else:
                status = "Paid" if paid >= total_price else "Partial/Unpaid"
                now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                # Record Sale
                sales_df = get_sheet_data("sales", SALES_COLS)
                new_sale = pd.DataFrame([{
                    "id": len(sales_df) + 1, "invoice_no": inv_no, "customer_name": cust_name,
                    "product_name": prod_select, "quantity": qty, "unit_price": unit_price,
                    "cost_price": cost_price, "total_amount": total_price, "paid_amount": paid,
                    "payment_status": status, "timestamp": now_str
                }])
                sales_df = pd.concat([sales_df, new_sale], ignore_index=True)
                save_sheet_data("sales", sales_df)
                # Deduct stock
                products_df.loc[products_df['product_name'] == prod_select, 'quantity'] = int(selected_prod['quantity']) - qty
                save_sheet_data("products", products_df)
                # Update Customer Ledger
                balance = total_price - paid
                cust_ledger_df = get_sheet_data("customer_ledger", CUST_LEDGER_COLS)
                new_cust_entry = pd.DataFrame([{
                    "id": len(cust_ledger_df) + 1, "customer_name": cust_name, "invoice_no": inv_no,
                    "total_amount": total_price, "paid_amount": paid, "balance": balance,
                    "date": datetime.now().strftime('%Y-%m-%d')
                }])
                cust_ledger_df = pd.concat([cust_ledger_df, new_cust_entry], ignore_index=True)
                save_sheet_data("customer_ledger", cust_ledger_df)
                st.success("Sale Recorded Successfully to Google Sheets!")

                # Generate PDF
                items_data = pd.DataFrame([{
                    "product_name": prod_select,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "total_amount": total_price
                }])
                pdf_out = generate_pdf(inv_no, cust_name, items_data, total_price, paid)
                st.download_button(label="📄 Download Printable PDF Invoice", data=pdf_out, file_name=f"{inv_no}.pdf", mime="application/pdf")
    else:
        st.warning("Pehle Purchase/Stock Tab se products add karein.")

# --- CUSTOMER KHATA ---
elif choice == "Customer Khata":
    st.subheader("📓 Customer Khata / Ledger")
    cust_df = get_sheet_data("customer_ledger", CUST_LEDGER_COLS)
    if not cust_df.empty:
        cust_df['total_amount'] = pd.to_numeric(cust_df['total_amount'], errors='coerce').fillna(0.0)
        cust_df['paid_amount'] = pd.to_numeric(cust_df['paid_amount'], errors='coerce').fillna(0.0)
        cust_df['balance'] = pd.to_numeric(cust_df['balance'], errors='coerce').fillna(0.0)
        st.dataframe(cust_df, use_container_width=True)
        summary = cust_df.groupby('customer_name').agg({'total_amount': 'sum', 'paid_amount': 'sum', 'balance': 'sum'}).reset_index()
        st.subheader("Customer Total Udhaar Summary")
        st.table(summary)
    else:
        st.info("Koi Khata Record Available nahi hai.")

# --- SUPPLIER MANAGEMENT ---
elif choice == "Supplier Management":
    st.subheader("🚛 Supplier Management & Purchases")
    with st.form("supplier_form"):
        sup_name = st.text_input("Supplier Name")
        prod_name = st.text_input("Product Name")
        qty = st.number_input("Quantity Received", min_value=1, value=1)
        cost_price = st.number_input("Cost Price Per Item", min_value=0.0, value=100.0)
        sell_price = st.number_input("Selling Price Per Item", min_value=0.0, value=120.0)
        paid_amt = st.number_input("Amount Paid to Supplier", min_value=0.0, value=0.0)
        submit = st.form_submit_button("Record Purchase")
        if submit:
            if not sup_name.strip() or not prod_name.strip():
                st.error("Supplier Name aur Product Name zaroori hain.")
            else:
                tot_amt = qty * cost_price
                status = "Paid" if paid_amt >= tot_amt else "Pending"
                today_date = datetime.now().strftime('%Y-%m-%d')
                # Save Purchase
                purchases_df = get_sheet_data("purchases", PURCHASES_COLS)
                new_pur = pd.DataFrame([{
                    "id": len(purchases_df) + 1, "supplier_name": sup_name, "product_name": prod_name,
                    "quantity": qty, "purchase_price": cost_price, "total_amount": tot_amt,
                    "paid_amount": paid_amt, "payment_status": status, "purchase_date": today_date
                }])
                purchases_df = pd.concat([purchases_df, new_pur], ignore_index=True)
                save_sheet_data("purchases", purchases_df)
                # Update/Insert Product Stock
                products_df = get_sheet_data("products", PRODUCTS_COLS)
                if not products_df.empty:
                    products_df = clean_products_df(products_df)
                if not products_df.empty and prod_name in products_df['product_name'].values:
                    idx = products_df[products_df['product_name'] == prod_name].index[0]
                    products_df.at[idx, 'quantity'] = int(products_df.at[idx, 'quantity']) + qty
                    products_df.at[idx, 'unit_price'] = sell_price
                    products_df.at[idx, 'cost_price'] = cost_price
                else:
                    new_prod = pd.DataFrame([{
                        "id": len(products_df) + 1, "product_name": prod_name, "category": "General",
                        "quantity": qty, "unit_price": sell_price, "cost_price": cost_price
                    }])
                    products_df = pd.concat([products_df, new_prod], ignore_index=True)
                save_sheet_data("products", products_df)
                # Save Supplier Ledger
                supp_ledger_df = get_sheet_data("supplier_ledger", SUPP_LEDGER_COLS)
                new_supp_entry = pd.DataFrame([{
                    "id": len(supp_ledger_df) + 1, "supplier_name": sup_name, "bill_no": "PUR-NEW",
                    "total_amount": tot_amt, "paid_amount": paid_amt, "balance": tot_amt - paid_amt,
                    "date": today_date
                }])
                supp_ledger_df = pd.concat([supp_ledger_df, new_supp_entry], ignore_index=True)
                save_sheet_data("supplier_ledger", supp_ledger_df)
                st.success("Stock & Supplier Record Updated to Google Sheets!")

# --- PROFIT & LOSS DASHBOARD ---
elif choice == "Profit & Loss Dashboard":
    st.subheader("📊 Profit & Loss Dashboard")
    sales_df = get_sheet_data("sales", SALES_COLS)
    if not sales_df.empty:
        sales_df['unit_price'] = pd.to_numeric(sales_df['unit_price'], errors='coerce').fillna(0.0)
        sales_df['cost_price'] = pd.to_numeric(sales_df['cost_price'], errors='coerce').fillna(0.0)
        sales_df['quantity'] = pd.to_numeric(sales_df['quantity'], errors='coerce').fillna(0).astype(int)
        sales_df['total_amount'] = pd.to_numeric(sales_df['total_amount'], errors='coerce').fillna(0.0)
        sales_df['profit'] = (sales_df['unit_price'] - sales_df['cost_price']) * sales_df['quantity']
        total_revenue = sales_df['total_amount'].sum()
        total_profit = sales_df['profit'].sum()
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Sales Revenue", f"Rs. {total_revenue}")
        col2.metric("Net Profit", f"Rs. {total_profit}")
        col3.metric("Total Orders", len(sales_df))
        st.subheader("Detailed Sales History")
        st.dataframe(sales_df[['timestamp', 'invoice_no', 'customer_name', 'product_name', 'quantity', 'total_amount', 'profit']], use_container_width=True)
    else:
        st.info("Abhi tak koi sales nahi hui hain.")

# --- INVENTORY ---
elif choice == "Inventory":
    st.subheader("📦 Main Stock (Products)")
    stock_df = get_sheet_data("products", PRODUCTS_COLS)
    if not stock_df.empty:
        stock_df = clean_products_df(stock_df)
    st.dataframe(stock_df, use_container_width=True)

# --- PURCHASE RETURN ---
elif choice == "Purchase Return":
    st.subheader("🔄 Purchase Return")
    # Load existing purchase data
    purchases_df = get_sheet_data("purchases", PURCHASES_COLS)
    if not purchases_df.empty:
        purchase_id = st.number_input("Enter Purchase ID to Return", min_value=1)
        purchase_record = purchases_df[purchases_df['id'] == purchase_id]
        if not purchase_record.empty:
            record = purchase_record.iloc[0]
            st.write(f"Returning Purchase ID: {record['id']} from {record['supplier_name']} for {record['product_name']} (Qty: {record['quantity']})")
            return_qty = st.number_input("Quantity to Return", min_value=1, max_value=int(record['quantity']))
            reason = st.text_area("Reason for Return")
            if st.button("Process Purchase Return"):
                # Deduct stock
                products_df = get_sheet_data("products", PRODUCTS_COLS)
                if not products_df.empty:
                    products_df = clean_products_df(products_df)
                    idx = products_df[products_df['product_name'] == record['product_name']].index
                    if not idx.empty:
                        idx = idx[0]
                        new_qty = int(products_df.at[idx, 'quantity']) - return_qty
                        products_df.at[idx, 'quantity'] = max(new_qty, 0)
                        save_sheet_data("products", products_df)
                # Save return in "purchase_returns"
                gc = get_gspread_client()
                try:
                    sh = gc.open(SHEET_NAME)
                except Exception as e:
                    st.error("Error opening Google Sheet.")
                    raise e
                try:
                    sheet_returns = sh.worksheet("purchase_returns")
                except gspread.exceptions.WorksheetNotFound:
                    sheet_returns = sh.add_worksheet(title="purchase_returns", rows=1000, cols=10)
                return_df = get_sheet_data("purchase_returns", ["id", "original_purchase_id", "supplier_name", "product_name", "quantity_returned", "reason", "return_date"])
                new_return_id = len(return_df) + 1
                return_record = pd.DataFrame([{
                    "id": new_return_id,
                    "original_purchase_id": purchase_id,
                    "supplier_name": record['supplier_name'],
                    "product_name": record['product_name'],
                    "quantity_returned": return_qty,
                    "reason": reason,
                    "return_date": datetime.now().strftime('%Y-%m-%d')
                }])
                sheet_returns.append_rows(return_record.values.tolist(), value_input_option='RAW')
                st.success("Purchase Return processed successfully!")
        else:
            st.info("Purchase ID not found.")
    else:
        st.info("No purchase records available.")

# --- SALES RETURN ---
elif choice == "Sales Return":
    st.subheader("🔄 Sales Return")
    # Load sales data
    sales_df = get_sheet_data("sales", SALES_COLS)
    if not sales_df.empty:
        sale_id = st.number_input("Enter Sale ID to Return", min_value=1)
        sale_record = sales_df[sales_df['id'] == sale_id]
        if not sale_record.empty:
            record = sale_record.iloc[0]
            st.write(f"Returning Sale ID: {record['id']} for {record['product_name']} (Qty: {record['quantity']})")
            return_qty = st.number_input("Quantity to Return", min_value=1, max_value=int(record['quantity']))
            reason = st.text_area("Reason for Return")
            if st.button("Process Sales Return"):
                # Update stock: add back returned quantity
                products_df = get_sheet_data("products", PRODUCTS_COLS)
                if not products_df.empty:
                    products_df = clean_products_df(products_df)
                    idx = products_df[products_df['product_name'] == record['product_name']].index
                    if not idx.empty:
                        idx = idx[0]
                        new_qty = int(products_df.at[idx, 'quantity']) + return_qty
                        products_df.at[idx, 'quantity'] = new_qty
                        save_sheet_data("products", products_df)
                # Save return in "sales_returns"
                gc = get_gspread_client()
                try:
                    sh = gc.open(SHEET_NAME)
                except Exception as e:
                    st.error("Error opening Google Sheet.")
                    raise e
                try:
                    sheet_returns = sh.worksheet("sales_returns")
                except gspread.exceptions.WorksheetNotFound:
                    sheet_returns = sh.add_worksheet(title="sales_returns", rows=1000, cols=10)
                return_df = get_sheet_data("sales_returns", ["id", "original_sale_id", "product_name", "quantity_returned", "reason", "return_date"])
                new_return_id = len(return_df) + 1
                return_record = pd.DataFrame([{
                    "id": new_return_id,
                    "original_sale_id": sale_id,
                    "product_name": record['product_name'],
                    "quantity_returned": return_qty,
                    "reason": reason,
                    "return_date": datetime.now().strftime('%Y-%m-%d')
                }])
                sheet_returns.append_rows(return_record.values.tolist(), value_input_option='RAW')
                st.success("Sales Return processed successfully!")
        else:
            st.info("Sale ID not found.")
    else:
        st.info("No sales records available.")

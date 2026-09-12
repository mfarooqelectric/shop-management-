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
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_resource
def get_gspread_client():
    """Gspread client"""
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    return gspread.service_account_from_dict(creds_dict)


def get_sheet_data(worksheet_name, default_cols):
    """Direct gspread se data read karo - cache nahi"""
    try:
        gc = get_gspread_client()
        sh = gc.open(SHEET_NAME)
        worksheet = sh.worksheet(worksheet_name)
        all_values = worksheet.get_all_values()
        if len(all_values) <= 1:
            return pd.DataFrame(columns=default_cols)
        df = pd.DataFrame(all_values[1:], columns=all_values[0])
        df = df.dropna(how="all")
        if df.empty:
            return pd.DataFrame(columns=default_cols)
        return df
    except Exception as e:
        print(f"Error reading {worksheet_name}: {e}")
        return pd.DataFrame(columns=default_cols)


def save_sheet_data(worksheet_name, df):
    """Google Sheet me data save/append karne ke liye"""
    gc = get_gspread_client()
    sh = gc.open(SHEET_NAME)
    try:
        worksheet = sh.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.add_worksheet(title=worksheet_name, rows=5000, cols=max(len(df.columns), 1))

    df_clean = df.fillna("")
    all_data = worksheet.get_all_values()
    if len(all_data) == 0:
        worksheet.update([df_clean.columns.values.tolist()] + df_clean.values.tolist())
    else:
        if len(df_clean) > 0:
            worksheet.append_rows(df_clean.values.tolist())


def clean_products_df(df):
    df = df.copy()
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce").fillna(0.0)
    df["cost_price"] = pd.to_numeric(df["cost_price"], errors="coerce").fillna(0.0)
    return df


PRODUCTS_COLS = ["id", "product_name", "category", "company", "godown", "quantity", "unit_price", "cost_price"]
SALES_COLS = ["id", "invoice_no", "customer_name", "product_name", "quantity", "unit_price", "cost_price", "total_amount", "paid_amount", "payment_status", "timestamp"]
PURCHASES_COLS = ["id", "supplier_name", "product_name", "quantity", "purchase_price", "total_amount", "paid_amount", "payment_status", "purchase_date"]
CUST_LEDGER_COLS = ["id", "customer_name", "invoice_no", "total_amount", "paid_amount", "balance", "date"]
SUPP_LEDGER_COLS = ["id", "supplier_name", "bill_no", "total_amount", "paid_amount", "balance", "date",]
RETURN_COLS = ["id", "original_purchase_id", "supplier_name", "product_name", "quantity", "reason", "return_date"]

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
st.title("⚡M. Farooq Electric Store⚡")
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
        all_companies = ["All"] + sorted(products_df['company'].dropna().unique().tolist())
        selected_company = st.selectbox("Select Company", all_companies)
        if selected_company != "All":
            products_df = products_df[products_df['company'] == selected_company]
        all_godowns = ["All"] + sorted(products_df['godown'].dropna().unique().tolist())
        selected_godown = st.selectbox("Select Godown to Buy From", all_godowns)
        if selected_godown != "All":
            products_df = products_df[products_df['godown'] == selected_godown]
        if products_df.empty:
            st.warning("Selected filter me koi product nahi hai.")
        else:
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
                    sales_df = get_sheet_data("sales", SALES_COLS)
                    new_sale = pd.DataFrame([{
                        "id": len(sales_df) + 1, "invoice_no": inv_no, "customer_name": cust_name,
                        "product_name": prod_select, "quantity": qty, "unit_price": unit_price,
                        "cost_price": cost_price, "total_amount": total_price, "paid_amount": paid,
                        "payment_status": status, "timestamp": now_str
                    }])
                    save_sheet_data("sales", new_sale)
                    # Deduct stock
                    gc = get_gspread_client()
                    sh = gc.open(SHEET_NAME)
                    try:
                        worksheet_prod = sh.worksheet("products")
                        # Find actual row to update
                        all_prod_data = get_sheet_data("products", PRODUCTS_COLS)
                        real_idx = all_prod_data[all_prod_data['product_name'] == prod_select].index[0]
                        new_qty = int(selected_prod['quantity']) - qty
                        # Update quantity in sheet - get row values, update
                        prod_row = all_prod_data.iloc[real_idx].copy()
                        prod_row['quantity'] = new_qty
                        # Update using gspread - row = index+2 (header)
                        worksheet_prod.update(f"A{real_idx+2}:H{real_idx+2}", [prod_row.tolist()])
                    except Exception as e:
                        st.warning(f"Stock deduction me error: {e}")
                    # Customer Ledger
                    balance = total_price - paid
                    new_cust_entry = pd.DataFrame([{
                        "id": 1, "customer_name": cust_name, "invoice_no": inv_no,
                        "total_amount": total_price, "paid_amount": paid, "balance": balance,
                        "date": datetime.now().strftime('%Y-%m-%d')
                    }])
                    save_sheet_data("customer_ledger", new_cust_entry)
                    st.success("Sale Recorded Successfully to Google Sheets!")
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
        company_options = ["HERO", "ECM", "EDILUX", "HEMIL", "SCHNEIDER", "Other"]
        selected_company = st.selectbox("Select Company/Brand", company_options)
        custom_company = st.text_input("Or Enter Custom Company Name (Optional)")
        final_company = custom_company if custom_company.strip() else selected_company
        prod_name = st.text_input("Product Name")
        godown_options = ["Godown 1", "Godown 2", "Godown 3", "Godown 4", "Godown 5"]
        selected_godown = st.selectbox("Select Godown", godown_options)
        qty = st.number_input("Quantity Received", min_value=1, value=1)
        cost_price = st.number_input("Cost Price Per Item", min_value=0.0, value=100.0)
        sell_price = st.number_input("Selling Price Per Item", min_value=0.0, value=120.0)
        paid_amt = st.number_input("Amount Paid to Supplier", min_value=0.0, value=0.0)
        submit = st.form_submit_button("Record Purchase")
        if submit:
            if not sup_name.strip() or not prod_name.strip() or not final_company.strip():
                st.error("Supplier Name, Product Name, aur Company zaroori hain.")
            else:
                tot_amt = qty * cost_price
                status = "Paid" if paid_amt >= tot_amt else "Pending"
                today_date = datetime.now().strftime('%Y-%m-%d')
                purchases_df = get_sheet_data("purchases", PURCHASES_COLS)
                new_pur = pd.DataFrame([{
                    "id": len(purchases_df) + 1, "supplier_name": sup_name, "product_name": prod_name,
                    "quantity": qty, "purchase_price": cost_price, "total_amount": tot_amt,
                    "paid_amount": paid_amt, "payment_status": status, "purchase_date": today_date
                }])
                gc = get_gspread_client()
                sh = gc.open(SHEET_NAME)
                try:
                    worksheet = sh.worksheet("purchases")
                except gspread.exceptions.WorksheetNotFound:
                    worksheet = sh.add_worksheet(title="purchases", rows=5000, cols=9)
                if len(purchases_df) == 0:
                    worksheet.update([new_pur.columns.tolist()] + new_pur.values.tolist())
                else:
                    worksheet.append_rows(new_pur.values.tolist())
                products_df = get_sheet_data("products", PRODUCTS_COLS)
                if not products_df.empty:
                    products_df = clean_products_df(products_df)
                existing = products_df[(products_df['product_name'] == prod_name) & (products_df['company'] == final_company) & (products_df['godown'] == selected_godown)]
                if not existing.empty:
                    idx = existing.index[0]
                    # update existing product quantity
                    try:
                        worksheet_prod = sh.worksheet("products")
                        prod_row = products_df.iloc[idx].copy()
                        prod_row['quantity'] = int(prod_row['quantity']) + qty
                        prod_row['unit_price'] = sell_price
                        prod_row['cost_price'] = cost_price
                        worksheet_prod.update(f"A{idx+2}:H{idx+2}", [prod_row.tolist()])
                    except Exception as e:
                        st.warning(f"Product update error: {e}")
                else:
                    new_prod = pd.DataFrame([{
                        "id": len(products_df) + 1, "product_name": prod_name, "category": "General",
                        "company": final_company, "godown": selected_godown, "quantity": qty,
                        "unit_price": sell_price, "cost_price": cost_price
                    }])
                    try:
                        worksheet_prod = sh.worksheet("products")
                    except gspread.exceptions.WorksheetNotFound:
                        worksheet_prod = sh.add_worksheet(title="products", rows=5000, cols=8)
                    if len(products_df) == 0:
                        worksheet_prod.update([new_prod.columns.tolist()] + new_prod.values.tolist())
                    else:
                        worksheet_prod.append_rows(new_prod.values.tolist())
                # Supplier Ledger
                new_supp_entry = pd.DataFrame([{
                    "id": 1, "supplier_name": sup_name, "bill_no": f"PUR-{len(purchases_df)+1}",
                    "total_amount": tot_amt, "paid_amount": paid_amt, "balance": tot_amt - paid_amt,
                    "date": today_date
                }])
                save_sheet_data("supplier_ledger", new_supp_entry)
                st.success(f"Stock Added - Company: {final_company}, Godown: {selected_godown}!")
                # 3. Supplier Ledger - Running Balance
supp_ledger_df = get_sheet_data("supplier_ledger", SUPP_LEDGER_COLS)

# Same supplier ke previous balance dekho
supplier_previous = supp_ledger_df[supp_ledger_df['supplier_name'] == sup_name]

if not supplier_previous.empty:
    prev_balance = pd.to_numeric(supplier_previous.iloc[-1]['balance'], errors='coerce')
else:
    prev_balance = 0

# Running balance = previous + current
current_balance = tot_amt - paid_amt
running_balance = prev_balance + current_balance

new_supp_entry = pd.DataFrame([{
    "id": len(supp_ledger_df) + 1, 
    "supplier_name": sup_name, 
    "bill_no": "PUR-NEW",
    "total_amount": tot_amt, 
    "paid_amount": paid_amt, 
    "balance": running_balance,  # ← RUNNING BALANCE
    "date": today_date
}])

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
    st.subheader("📦 Main Stock (Products) - Godown Wise")
    stock_df = get_sheet_data("products", PRODUCTS_COLS)
    if not stock_df.empty:
        stock_df = clean_products_df(stock_df)
        all_godowns = ["All"] + sorted(stock_df['godown'].dropna().unique().tolist())
        selected_godown_filter = st.selectbox("Filter by Godown", all_godowns)
        if selected_godown_filter != "All":
            stock_df = stock_df[stock_df['godown'] == selected_godown_filter]
        st.dataframe(stock_df, use_container_width=True)
        st.subheader("📊 Godown Summary")
        summary = stock_df.groupby('godown').agg({'quantity': 'sum', 'product_name': 'count'}).reset_index()
        summary.columns = ['Godown', 'Total Quantity', 'No. of Items']
        st.table(summary)
    else:
        st.info("Koi Inventory Available nahi hai.")

# --- PURCHASE RETURN --- FIXED FULLY
elif choice == "Purchase Return":
    st.subheader("🔄 Purchase Return")
    purchases_df = get_sheet_data("purchases", PURCHASES_COLS)

    if purchases_df.empty:
        st.warning("Pehle Supplier Management se purchases add karein.")
    else:
        # ID ko numeric convert karo
        purchases_df['id'] = pd.to_numeric(purchases_df['id'], errors='coerce')
        purchases_df = purchases_df.dropna(subset=['id'])
        purchases_df['id'] = purchases_df['id'].astype(int)

        st.dataframe(purchases_df, use_container_width=True)

        purchase_id = st.number_input("Enter Purchase ID to Return", min_value=1, step=1)
        purchase_record = purchases_df[purchases_df['id'] == purchase_id]

        if not purchase_record.empty:
            record = purchase_record.iloc[0]
            st.info(f"Selected -> ID: {record['id']} | Supplier: {record['supplier_name']} | Product: {record['product_name']} | Qty: {record['quantity']}")

            max_return = int(float(str(record['quantity']).strip() or 0))
            if max_return < 1:
                max_return = 1

            return_qty = st.number_input("Quantity to Return", min_value=1, max_value=max_return, value=1)
            reason = st.text_area("Reason for Return", placeholder="Defective / Wrong item etc.")

            if st.button("Process Purchase Return"):
                try:
                    # 1. Deduct from products stock
                    products_df = get_sheet_data("products", PRODUCTS_COLS)
                    if not products_df.empty:
                        products_df = clean_products_df(products_df)
                        # Match by product name
                        prod_idx = products_df[products_df['product_name'] == record['product_name']].index
                        if not prod_idx.empty:
                            prod_idx = prod_idx[0]
                            gc = get_gspread_client()
                            sh = gc.open(SHEET_NAME)
                            worksheet_prod = sh.worksheet("products")
                            prod_row = products_df.iloc[prod_idx].copy()
                            new_stock = int(prod_row['quantity']) - return_qty
                            prod_row['quantity'] = max(new_stock, 0)
                            worksheet_prod.update(f"A{prod_idx+2}:H{prod_idx+2}", [prod_row.tolist()])

                    # 2. Save return in "purchase_returns"
                    gc = get_gspread_client()
                    sh = gc.open(SHEET_NAME)
                    try:
                        sheet_returns = sh.worksheet("purchase_returns")
                    except gspread.exceptions.WorksheetNotFound:
                        sheet_returns = sh.add_worksheet(title="purchase_returns", rows=1000, cols=20)

                    return_df = get_sheet_data("purchase_returns", RETURN_COLS)
                    new_return_id = len(return_df) + 1

                    new_return = pd.DataFrame([{
                        "id": new_return_id,
                        "original_purchase_id": purchase_id,
                        "supplier_name": record['supplier_name'],
                        "product_name": record['product_name'],
                        "quantity": return_qty,
                        "reason": reason,
                        "return_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }])

                    if len(return_df) == 0:
                        sheet_returns.update([new_return.columns.tolist()] + new_return.values.tolist())
                    else:
                        sheet_returns.append_rows(new_return.values.tolist())

                    st.success(f"Returned {return_qty} units of {record['product_name']}. Stock updated and return saved!")

                    # 3. Optional: Update original purchase quantity
                    try:
                        # Update purchase sheet to reduce quantity
                        purchase_sheet = sh.worksheet("purchases")
                        real_pur_idx = purchases_df[purchases_df['id'] == purchase_id].index[0]
                        # Get row values and update quantity
                        pur_row_values = purchase_sheet.row_values(real_pur_idx + 2)
                        # quantity is at index 3 (0:id,1:supplier,2:product,3:quantity)
                        if pur_row_values:
                            current_qty = int(float(pur_row_values[3]))
                            pur_row_values[3] = str(max(current_qty - return_qty, 0))
                            # recalc total_amount if possible: total = qty * purchase_price
                            try:
                                price = float(pur_row_values[4])
                                pur_row_values[5] = str((max(current_qty - return_qty, 0)) * price)
                            except:
                                pass
                            purchase_sheet.update(f"A{real_pur_idx+2}:I{real_pur_idx+2}", [pur_row_values])
                    except Exception as e:
                        st.warning(f"Return saved but purchase qty update failed: {e}")

                except Exception as e:
                    st.error(f"Error processing return: {e}")
        else:
            if purchase_id > 0:
                st.info("Purchase ID not found. Upar table me available IDs dekhein.")

elif choice == "Sales Return":
    st.subheader("↩️ Sales Return - Coming Soon")
    st.info("Ye feature next update me add hoga.")

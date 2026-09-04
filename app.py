import streamlit as st
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
from st_gsheets_connection import GSheetsConnection)

# Google Sheets Connection
conn = st.connection("gsheets", type=GSheetsConnection)
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

# ----------------------------------------------------
# 1. GOOGLE SHEETS CONNECTION SETUP
# ----------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

def get_sheet_data(worksheet_name, default_cols):
    """Google Sheet se data load karne ke liye helper function"""
    try:
        df = conn.read(worksheet=worksheet_name, ttl="0m")
        if df.empty:
            return pd.DataFrame(columns=default_cols)
        return df
    except Exception:
        return pd.DataFrame(columns=default_cols)

def save_sheet_data(worksheet_name, df):
    """Google Sheet me data save karne ke liye helper function"""
    conn.update(worksheet=worksheet_name, data=df)

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
    p.line(50, y-5, 550, y-5)
    
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
    p.drawString(350, y-15, f"Paid Amount: Rs. {paid_amount}")
    p.drawString(350, y-30, f"Balance: Rs. {grand_total - paid_amount}")
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer


# ----------------------------------------------------
# 3. STREAMLIT UI & NAVIGATION
# ----------------------------------------------------
st.title("⚡ M. Farooq Electric Store System")

menu = ["Sales & Invoice", "Customer Khata", "Supplier Management", "Profit & Loss Dashboard", "Inventory"]
choice = st.sidebar.selectbox("Navigation Menu", menu)

# --- SALES & INVOICE ---
if choice == "Sales & Invoice":
    st.subheader("🧾 Create Sales Invoice")
    
    cust_name = st.text_input("Customer Name")
    inv_no = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    st.text(f"Invoice No: {inv_no}")
    
    products_df = get_sheet_data("products", PRODUCTS_COLS)
    
    if not products_df.empty:
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
            status = "Paid" if paid >= total_price else "Partial/Unpaid"
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 1. Record Sale
            sales_df = get_sheet_data("sales", SALES_COLS)
            new_sale = pd.DataFrame([{
                "id": len(sales_df) + 1, "invoice_no": inv_no, "customer_name": cust_name,
                "product_name": prod_select, "quantity": qty, "unit_price": unit_price,
                "cost_price": cost_price, "total_amount": total_price, "paid_amount": paid,
                "payment_status": status, "timestamp": now_str
            }])
            sales_df = pd.concat([sales_df, new_sale], ignore_index=True)
            save_sheet_data("sales", sales_df)
            
            # 2. Deduct Stock
            products_df.loc[products_df['product_name'] == prod_select, 'quantity'] = int(selected_prod['quantity']) - qty
            save_sheet_data("products", products_df)
            
            # 3. Update Customer Khata
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
            items_data = pd.DataFrame([{"product_name": prod_select, "quantity": qty, "unit_price": unit_price, "total_amount": total_price}])
            pdf_out = generate_pdf(inv_no, cust_name, items_data, total_price, paid)
            st.download_button(label="📄 Download Printable PDF Invoice", data=pdf_out, file_name=f"{inv_no}.pdf", mime="application/pdf")
    else:
        st.warning("Pehle Purchase/Stock Tab se products add karein.")


# --- CUSTOMER KHATA ---
elif choice == "Customer Khata":
    st.subheader("📓 Customer Khata / Ledger")
    cust_df = get_sheet_data("customer_ledger", CUST_LEDGER_COLS)
    
    if not cust_df.empty:
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
            tot_amt = qty * cost_price
            status = "Paid" if paid_amt >= tot_amt else "Pending"
            today_date = datetime.now().strftime('%Y-%m-%d')
            
            # 1. Save Purchase
            purchases_df = get_sheet_data("purchases", PURCHASES_COLS)
            new_pur = pd.DataFrame([{
                "id": len(purchases_df) + 1, "supplier_name": sup_name, "product_name": prod_name,
                "quantity": qty, "purchase_price": cost_price, "total_amount": tot_amt,
                "paid_amount": paid_amt, "payment_status": status, "purchase_date": today_date
            }])
            purchases_df = pd.concat([purchases_df, new_pur], ignore_index=True)
            save_sheet_data("purchases", purchases_df)
            
            # 2. Update/Insert Product Stock
            products_df = get_sheet_data("products", PRODUCTS_COLS)
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
            
            # 3. Save Supplier Ledger
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
        sales_df['unit_price'] = sales_df['unit_price'].astype(float)
        sales_df['cost_price'] = sales_df['cost_price'].astype(float)
        sales_df['quantity'] = sales_df['quantity'].astype(int)
        sales_df['total_amount'] = sales_df['total_amount'].astype(float)
        
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
    st.dataframe(stock_df, use_container_width=True)

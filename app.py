import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

DB_FILE = "shop_inventory.db"

def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

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
            unit_price REAL NOT NULL DEFAULT 0.0,
            cost_price REAL NOT NULL DEFAULT 0.0
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
            cost_price REAL NOT NULL DEFAULT 0.0,
            total_amount REAL NOT NULL,
            paid_amount REAL DEFAULT 0.0,
            payment_status TEXT DEFAULT 'Paid',
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

    # 4. Customer Khata Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customer_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            invoice_no TEXT,
            total_amount REAL,
            paid_amount REAL,
            balance REAL,
            date TEXT
        )
    ''')

    # 5. Supplier Ledger Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS supplier_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_name TEXT NOT NULL,
            bill_no TEXT,
            total_amount REAL,
            paid_amount REAL,
            balance REAL,
            date TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# App load hote hi DB initialize karein
init_db()

# PDF Generator Function
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

# Streamlit UI Navigation
st.title("⚡ M. Farooq Electric Store System")
menu = ["Sales & Invoice", "Customer Khata", "Supplier Management", "Profit & Loss Dashboard", "Inventory"]
choice = st.sidebar.selectbox("Navigation Menu", menu)

conn = get_connection()

if choice == "Sales & Invoice":
    st.subheader("🧾 Create Sales Invoice")
    
    cust_name = st.text_input("Customer Name")
    inv_no = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    st.text(f"Invoice No: {inv_no}")
    
    # Fetch Products
    products = pd.read_sql("SELECT product_name, unit_price, cost_price, quantity FROM products", conn)
    
    if not products.empty:
        prod_select = st.selectbox("Select Product", products['product_name'].tolist())
        selected_prod = products[products['product_name'] == prod_select].iloc[0]
        
        qty = st.number_input("Quantity", min_value=1, max_value=int(selected_prod['quantity']), value=1)
        total_price = qty * selected_prod['unit_price']
        
        st.write(f"Unit Price: Rs. {selected_prod['unit_price']} | Total: Rs. {total_price}")
        
        paid = st.number_input("Paid Amount", min_value=0.0, value=float(total_price))
        
        if st.button("Generate Invoice & Save"):
            status = "Paid" if paid >= total_price else "Partial/Unpaid"
            cursor = conn.cursor()
            
            # Record Sale
            cursor.execute('''
                INSERT INTO sales (invoice_no, customer_name, product_name, quantity, unit_price, cost_price, total_amount, paid_amount, payment_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (inv_no, cust_name, prod_select, qty, selected_prod['unit_price'], selected_prod['cost_price'], total_price, paid, status))
            
            # Deduct Stock
            cursor.execute("UPDATE products SET quantity = quantity - ? WHERE product_name = ?", (qty, prod_select))
            
            # Update Customer Khata
            balance = total_price - paid
            cursor.execute('''
                INSERT INTO customer_ledger (customer_name, invoice_no, total_amount, paid_amount, balance, date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (cust_name, inv_no, total_price, paid, balance, datetime.now().strftime('%Y-%m-%d')))
            
            conn.commit()
            st.success("Sale Recorded Successfully!")
            
            # Generate PDF Download
            items_data = pd.DataFrame([{"product_name": prod_select, "quantity": qty, "unit_price": selected_prod['unit_price'], "total_amount": total_price}])
            pdf_out = generate_pdf(inv_no, cust_name, items_data, total_price, paid)
            
            st.download_button(label="📄 Download Printable PDF Invoice", data=pdf_out, file_name=f"{inv_no}.pdf", mime="application/pdf")
    else:
        st.warning("Pehle Purchase/Stock Tab se products add karein.")

elif choice == "Customer Khata":
    st.subheader("📓 Customer Khata / Ledger")
    cust_df = pd.read_sql("SELECT * FROM customer_ledger", conn)
    
    if not cust_df.empty:
        st.dataframe(cust_df)
        
        # Summary by Customer
        summary = cust_df.groupby('customer_name').agg({'total_amount': 'sum', 'paid_amount': 'sum', 'balance': 'sum'}).reset_index()
        st.subheader("Customer Total Udhaar Summary")
        st.table(summary)
    else:
        st.info("Koi Khata Record Available nahi hai.")

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
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO purchases (supplier_name, product_name, quantity, purchase_price, total_amount, paid_amount, payment_status, purchase_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (sup_name, prod_name, qty, cost_price, tot_amt, paid_amt, status, datetime.now().strftime('%Y-%m-%d')))
            
            # Stock Update/Insert
            cursor.execute("SELECT id FROM products WHERE product_name = ?", (prod_name,))
            exists = cursor.fetchone()
            
            if exists:
                cursor.execute("UPDATE products SET quantity = quantity + ?, unit_price = ?, cost_price = ? WHERE product_name = ?", (qty, sell_price, cost_price, prod_name))
            else:
                cursor.execute("INSERT INTO products (product_name, category, quantity, unit_price, cost_price) VALUES (?, 'General', ?, ?, ?)", (prod_name, qty, sell_price, cost_price))
            
            # Supplier Ledger
            cursor.execute("INSERT INTO supplier_ledger (supplier_name, bill_no, total_amount, paid_amount, balance, date) VALUES (?, ?, ?, ?, ?, ?)",
                           (sup_name, "PUR-NEW", tot_amt, paid_amt, tot_amt - paid_amt, datetime.now().strftime('%Y-%m-%d')))
            
            conn.commit()
            st.success("Stock & Supplier Record Updated!")

elif choice == "Profit & Loss Dashboard":
    st.subheader("📊 Profit & Loss Dashboard")
    
    sales_df = pd.read_sql("SELECT * FROM sales", conn)
    
    if not sales_df.empty:
        # Profit Calculation: (Selling Price - Cost Price) * Quantity
        sales_df['profit'] = (sales_df['unit_price'] - sales_df['cost_price']) * sales_df['quantity']
        
        total_revenue = sales_df['total_amount'].sum()
        total_profit = sales_df['profit'].sum()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Sales Revenue", f"Rs. {total_revenue}")
        col2.metric("Net Net Profit", f"Rs. {total_profit}")
        col3.metric("Total Orders", len(sales_df))
        
        st.subheader("Detailed Sales History")
        st.dataframe(sales_df[['timestamp', 'invoice_no', 'customer_name', 'product_name', 'quantity', 'total_amount', 'profit']])
    else:
        st.info("Abhi tak koi sales nahi hui hain.")

elif choice == "Inventory":
    st.subheader("📦 Main Stock (Products)")
    stock_df = pd.read_sql("SELECT id, product_name, category, quantity, unit_price, cost_price FROM products", conn)
    st.dataframe(stock_df)
    use_container_width=True)        
git add requirements.txt
git commit -m "Add reportlab to requirements.txt"
git push

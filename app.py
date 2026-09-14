import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

st.set_page_config(page_title="نظام إدارة المنتجات والمبيعات والخزينة", layout="wide")

DB_FILE = "store_data.db"

def get_connection():
    return sqlite3.connect(DB_FILE, timeout=20)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT UNIQUE,
            total_qty INTEGER,
            sold_qty INTEGER,
            stock_qty INTEGER,
            buy_price REAL,
            sell_price REAL,
            unit_profit REAL,
            sales_val REAL,
            extra_profit REAL,
            new_sales_profit REAL DEFAULT 0.0,
            new_sales_cash REAL DEFAULT 0.0
        )
    ''')
    try:
        c.execute("ALTER TABLE products ADD COLUMN new_sales_profit REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass
        
    try:
        c.execute("ALTER TABLE products ADD COLUMN new_sales_cash REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass

    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL,
            note TEXT,
            created_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value REAL
        )
    ''')
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('initial_cash', 1889000.0)")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('buying_costs', 0.0)")
    conn.commit()
    conn.close()

init_db()

def load_products():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()
    return df

def save_products(df):
    conn = get_connection()
    c = conn.cursor()
    for _, row in df.iterrows():
        c.execute('''
            INSERT OR REPLACE INTO products 
            (id, product_name, total_qty, sold_qty, stock_qty, buy_price, sell_price, unit_profit, sales_val, extra_profit, new_sales_profit, new_sales_cash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row.get('id', None),
            row['product_name'],
            row['total_qty'],
            row['sold_qty'],
            row['stock_qty'],
            row['buy_price'],
            row['sell_price'],
            row['unit_profit'],
            row['sales_val'],
            row['extra_profit'],
            row.get('new_sales_profit', 0.0),
            row.get('new_sales_cash', 0.0)
        ))
    conn.commit()
    conn.close()

def get_setting(key):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0.0

def update_setting(key, val):
    conn = get_connection()
    c = conn.cursor()
    c.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, val))
    conn.commit()
    conn.close()

def get_expenses():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM expenses", conn)
    conn.close()
    return df

def add_expense(amount, note):
    conn = get_connection()
    c = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO expenses (amount, note, created_at) VALUES (?, ?, ?)", (amount, note, now_str))
    conn.commit()
    conn.close()

def delete_expense(exp_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE id=?", (exp_id,))
    conn.commit()
    conn.close()

def reset_all_expenses():
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM expenses")
    conn.commit()
    conn.close()

def import_excel_to_db(file):
    df_raw = pd.read_excel(file)
    df_raw.columns = df_raw.columns.astype(str).str.strip()

    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM products")

    grouped = {}

    for _, row in df_raw.iterrows():
        p_name = str(row.get('اسم المنتج', '')).strip()
        if not p_name or p_name == 'nan':
            continue
            
        total_q = int(row.get('العدد', 0)) if pd.notnull(row.get('العدد')) else 0
        s_qty = int(row.get('الكميه المباعه', 0)) if pd.notnull(row.get('الكميه المباعه')) else 0
        rem_stock = int(row.get('باقي مخزن', total_q - s_qty)) if pd.notnull(row.get('باقي مخزن')) else max(0, total_q - s_qty)
        b_price = float(row.get('سعر الشراء الفردي', 0)) if pd.notnull(row.get('سعر الشراء الفردي')) else 0.0
        s_price = float(row.get('سعر البيع', 0)) if pd.notnull(row.get('سعر البيع')) else 0.0
        
        u_profit = float(row.get('ربح القطعه', 0)) if pd.notnull(row.get('ربح القطعه')) else (s_price - b_price)

        s_val = float(row.get('إجمالي البيع', row.get('اجمالي البيع', s_qty * s_price))) if pd.notnull(row.get('إجمالي البيع', row.get('اجمالي البيع', None))) else (s_qty * s_price)
        ex_profit = float(row.get('ارباح إضافيه', row.get('أرباح إضافية', 0))) if pd.notnull(row.get('ارباح إضافيه', row.get('أرباح إضافية', None))) else 0.0

        if p_name in grouped:
            grouped[p_name]['total_qty'] += total_q
            grouped[p_name]['sold_qty'] += s_qty
            grouped[p_name]['stock_qty'] += rem_stock
            grouped[p_name]['sales_val'] += s_val
            grouped[p_name]['extra_profit'] += ex_profit
            grouped[p_name]['unit_profit'] = u_profit or grouped[p_name]['unit_profit']
            grouped[p_name]['buy_price'] = b_price or grouped[p_name]['buy_price']
            grouped[p_name]['sell_price'] = s_price or grouped[p_name]['sell_price']
        else:
            grouped[p_name] = {
                'total_qty': total_q,
                'sold_qty': s_qty,
                'stock_qty': rem_stock,
                'buy_price': b_price,
                'sell_price': s_price,
                'unit_profit': u_profit,
                'sales_val': s_val,
                'extra_profit': ex_profit
            }

    for p_name, data in grouped.items():
        c.execute('''
            INSERT OR REPLACE INTO products (product_name, total_qty, sold_qty, stock_qty, buy_price, sell_price, unit_profit, sales_val, extra_profit, new_sales_profit, new_sales_cash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, 0.0)
        ''', (p_name, data['total_qty'], data['sold_qty'], data['stock_qty'], data['buy_price'], data['sell_price'], data['unit_profit'], data['sales_val'], data['extra_profit']))

    conn.commit()
    conn.close()

st.title("📊 نظام إدارة المنتجات والمبيعات والخزينة")

df_prod = load_products()

with st.expander("📥 استيراد بيانات من إكسل جديد (استخدمه للضبط)"):
    uploaded_file = st.file_uploader("اختر ملف الإكسل (.xlsx)", type=["xlsx"])
    if uploaded_file is not None:
        if st.button("🚀 اعتماد واستيراد ملف الإكسل"):
            import_excel_to_db(uploaded_file)
            st.success("تم استيراد وحفظ البيانات بنجاح!")
            st.rerun()

initial_cash = get_setting('initial_cash')
buying_costs = get_setting('buying_costs')

df_exp = get_expenses()
total_expenses = df_exp['amount'].sum() if not df_exp.empty else 0.0

BASE_FIXED_PROFIT = 264250.0

if not df_prod.empty:
    actual_sales = df_prod['sales_val'].sum()
    
    # حساب الأرباح الجديدة والمبالغ النقدية الجديدة للمبيعات المضافة فقط
    new_sales_profit = df_prod['new_sales_profit'].sum() if 'new_sales_profit' in df_prod.columns else 0.0
    new_sales_cash = df_prod['new_sales_cash'].sum() if 'new_sales_cash' in df_prod.columns else 0.0
    
    profit_sum = BASE_FIXED_PROFIT + new_sales_profit
    sold_qty = df_prod['sold_qty'].sum()
    stock_val = (df_prod['stock_qty'] * df_prod['buy_price']).sum()
else:
    actual_sales = 0.0
    new_sales_cash = 0.0
    profit_sum = BASE_FIXED_PROFIT
    sold_qty = 0
    stock_val = 0.0

# النقد بالصندوق يعتمد على: النقد الابتدائي + المبيعات الجديدة فقط - المصاريف - تكاليف الشراء
cash_in_hand = initial_cash + new_sales_cash - total_expenses - buying_costs

# ==================== الشريط الجانبي ====================
st.sidebar.header("💵 رأس المال / النقد الابتدائي")
new_init_cash = st.sidebar.number_input(
    "النقد الكلي في الصندوق (د.ع)", 
    min_value=0.0, 
    value=float(initial_cash), 
    step=10000.0
)
if new_init_cash != initial_cash:
    update_setting('initial_cash', new_init_cash)
    st.rerun()

if not df_prod.empty:
    st.sidebar.markdown("---")
    st.sidebar.header("🛒 تسجيل عملية بيع")
    product_list = df_prod['product_name'].dropna().unique().tolist()
    selected_product = st.sidebar.selectbox("اختر المنتج للبيع", product_list, key="sell_box")

    curr_row = df_prod[df_prod['product_name'] == selected_product].iloc[0]
    st.sidebar.caption(f"📦 المتبقي في المخزن: **{int(curr_row['stock_qty'])}** قطعة")
    default_sell_p = float(curr_row['sell_price']) if pd.notnull(curr_row['sell_price']) else 0.0

    sell_qty = st.sidebar.number_input("عدد القطع المباعة", min_value=1, value=1, step=1, key="sell_q")
    custom_sell_price = st.sidebar.number_input("سعر البيع الفردي للقطعة", min_value=0.0, value=default_sell_p, step=500.0, key="sell_p")
    extra_profit = st.sidebar.number_input("ربح إضافي (إن وجد)", min_value=0.0, value=0.0, step=250.0, key="extra_p")

    if st.sidebar.button("✅ تسجيل البيع"):
        idx = df_prod[df_prod['product_name'] == selected_product].index[0]
        
        buy_p = df_prod.loc[idx, 'buy_price']
        unit_p = custom_sell_price - buy_p
        sale_p = (sell_qty * unit_p) + extra_profit
        total_sale_amount = sell_qty * custom_sell_price

        df_prod.loc[idx, 'sold_qty'] += sell_qty
        df_prod.loc[idx, 'stock_qty'] = max(0, df_prod.loc[idx, 'stock_qty'] - sell_qty)
        df_prod.loc[idx, 'sales_val'] += total_sale_amount
        df_prod.loc[idx, 'extra_profit'] += extra_profit
        df_prod.loc[idx, 'new_sales_profit'] = df_prod.loc[idx].get('new_sales_profit', 0.0) + sale_p
        df_prod.loc[idx, 'new_sales_cash'] = df_prod.loc[idx].get('new_sales_cash', 0.0) + total_sale_amount

        save_products(df_prod)
        st.sidebar.success("تم تسجيل عملية البيع بنجاح!")
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.header("🔄 استرجاع بضاعة (مرتجع)")
    return_product = st.sidebar.selectbox("اختر المنتج المرتجع", product_list, key="return_box")
    return_qty = st.sidebar.number_input("عدد القطع المسترجعة", min_value=1, value=1, step=1, key="return_q")
    return_price_refund = st.sidebar.number_input("مبلغ الإرجاع للزبون (سعر القطعة)", min_value=0.0, value=default_sell_p, step=500.0, key="return_p")

    if st.sidebar.button("↩️ تأكيد الاسترجاع"):
        idx = df_prod[df_prod['product_name'] == return_product].index[0]
        current_sold = df_prod.loc[idx, 'sold_qty']
        
        if return_qty > current_sold:
            st.sidebar.error("عدد القطع المسترجعة أكبر من الكمية المباعة أصلاً!")
        else:
            buy_p = df_prod.loc[idx, 'buy_price']
            unit_p = return_price_refund - buy_p
            refund_total_amount = return_qty * return_price_refund
            refund_profit_deduct = (return_qty * unit_p)

            df_prod.loc[idx, 'sold_qty'] -= return_qty
            df_prod.loc[idx, 'stock_qty'] += return_qty
            df_prod.loc[idx, 'sales_val'] = max(0.0, df_prod.loc[idx, 'sales_val'] - refund_total_amount)
            df_prod.loc[idx, 'new_sales_profit'] = max(0.0, df_prod.loc[idx].get('new_sales_profit', 0.0) - refund_profit_deduct)
            df_prod.loc[idx, 'new_sales_cash'] = max(0.0, df_prod.loc[idx].get('new_sales_cash', 0.0) - refund_total_amount)

            save_products(df_prod)
            st.sidebar.success("تم استرجاع القطعة وتحديث الصندوق والأرباح بنجاح!")
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("💸 إضافة مصروف جديد")
exp_amount = st.sidebar.number_input("مبلغ المصروف", min_value=0.0, value=0.0, step=500.0)
exp_note = st.sidebar.text_input("سبب المصروف (مثلاً: إيجار، نقل)")

if st.sidebar.button("➕ تسجيل المصروف"):
    if exp_amount > 0:
        add_expense(exp_amount, exp_note if exp_note else "غير محدد")
        st.sidebar.success("تم إضافة المصروف بنجاح!")
        st.rerun()
    else:
        st.sidebar.warning("يرجى إدخال مبلغ أكبر من 0")

st.sidebar.markdown("---")
st.sidebar.header("📦 شراء بضاعة جديدة")
new_name = st.sidebar.text_input("اسم المنتج الجديد")
new_stock = st.sidebar.number_input("عدد القطع المشتراة", min_value=1, value=10)
new_buy_price = st.sidebar.number_input("سعر الشراء الفردي", min_value=0.0, value=1000.0)
new_sell_price = st.sidebar.number_input("سعر البيع الفردي", min_value=0.0, value=1500.0)

if st.sidebar.button("➕ إضافة للبضاعة والمخزون"):
    if new_name:
        total_buy_cost = new_stock * new_buy_price
        update_setting('buying_costs', buying_costs + total_buy_cost)

        unit_p = max(0.0, new_sell_price - new_buy_price)
        new_row = {
            'product_name': new_name,
            'total_qty': new_stock,
            'sold_qty': 0,
            'stock_qty': new_stock,
            'buy_price': new_buy_price,
            'sell_price': new_sell_price,
            'unit_profit': unit_p,
            'sales_val': 0.0,
            'extra_profit': 0.0,
            'new_sales_profit': 0.0,
            'new_sales_cash': 0.0
        }
        df_prod = pd.concat([df_prod, pd.DataFrame([new_row])], ignore_index=True)
        save_products(df_prod)
        st.sidebar.success(f"تم إضافة {new_name} وحفظه بنجاح!")
        st.rerun()
    else:
        st.sidebar.warning("يرجى كتابة اسم المنتج!")

# ==================== عرض الملخص المالي ====================
st.subheader("💵 حركة الصندوق والمالية")
m1, m2, m3, m4 = st.columns(4)

m1.metric("💰 النقد الصافي بالصندوق", f"{cash_in_hand:,.0f}")
m2.metric("إجمالي المبيعات", f"{actual_sales:,.0f}")
m3.metric("📈 إجمالي الأرباح", f"{profit_sum:,.0f}")
m4.metric("إجمالي المصاريف المسجلة", f"{total_expenses:,.0f}")

st.markdown("---")

# ==================== سجل المصاريف ====================
st.subheader("🧾 سجل المصاريف المحفوظ")
if not df_exp.empty:
    col_exp_list, col_exp_del = st.columns([3, 1])
    with col_exp_list:
        display_exp = df_exp.rename(columns={'id': 'ت', 'amount': 'المبلغ', 'note': 'السبب', 'created_at': 'التاريخ'})
        st.dataframe(display_exp, use_container_width=True, hide_index=True)
    with col_exp_del:
        st.markdown("**حذف مصروف:**")
        exp_options = {row['id']: f"#{row['id']} - {row['note']} ({row['amount']:,.0f} د.ع)" for _, row in df_exp.iterrows()}
        selected_exp_id = st.selectbox("اختر المصروف للحذف", options=list(exp_options.keys()), format_func=lambda x: exp_options[x])
        if st.button("🗑️ حذف المصروف المحدد"):
            delete_expense(selected_exp_id)
            st.success("تم حذف المصروف!")
            st.rerun()
        if st.button("🧹 مسح جميع المصاريف"):
            reset_all_expenses()
            st.success("تم مسح المصاريف!")
            st.rerun()
else:
    st.info("لا توجد مصاريف مسجلة حتى الآن.")

st.markdown("---")

st.subheader("📊 ملخص المخزون والقطع")
c1, c2 = st.columns(2)
c1.metric("عدد القطع المباعة الكلي", f"{int(sold_qty)}")
c2.metric("قيمة المخزون المتبقي", f"{stock_val:,.0f}")

st.markdown("---")

# ==================== المنتجات الأكثر مبيعاً ====================
st.subheader("🏆 المنتجات الأكثر مبيعاً")
if not df_prod.empty:
    top_selling = df_prod[df_prod['sold_qty'] > 0].sort_values(by='sold_qty', ascending=False)
    if not top_selling.empty:
        st.dataframe(
            top_selling[['product_name', 'sold_qty', 'sales_val', 'stock_qty']].rename(
                columns={
                    'product_name': 'اسم المنتج',
                    'sold_qty': 'الكمية المباعة',
                    'sales_val': 'إجمالي المبيعات (د.ع)',
                    'stock_qty': 'المتبقي بالمخزن'
                }
            ),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("لا توجد مبيعات مسجلة حتى الآن.")

st.markdown("---")

# ==================== عرض الجدول الكامل مع شريط البحث ====================
st.subheader("📋 سجل المبيعات والمنتجات الكامل")
search_query = st.text_input("🔍 ابحث عن اسم المنتج في الجدول...", "")

if not df_prod.empty:
    df_display_source = df_prod.copy()
    if search_query:
        df_display_source = df_display_source[df_display_source['product_name'].str.contains(search_query, na=False)]
        
    display_df = df_display_source.drop(columns=['id', 'new_sales_profit', 'new_sales_cash'], errors='ignore').rename(
        columns={
            'product_name': 'اسم المنتج',
            'total_qty': 'العدد الكلي',
            'sold_qty': 'الكمية المباعة',
            'stock_qty': 'باقي المخزن',
            'buy_price': 'سعر الشراء الفردي',
            'sell_price': 'سعر البيع',
            'unit_profit': 'ربح القطعة',
            'sales_val': 'إجمالي البيع',
            'extra_profit': 'أرباح إضافية'
        }
    )
    st.dataframe(display_df, use_container_width=True, hide_index=True)
import streamlit as st
import pandas as pd
import sqlite3
import io
from datetime import datetime
import plotly.express as px

# Database functions
def get_conn():
    return sqlite3.connect('expense_tracker.db')

def init_db():
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                category TEXT,
                description TEXT,
                amount REAL,
                date TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS income (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                source TEXT,
                amount REAL,
                date TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS budget (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                category TEXT,
                amount REAL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

init_db()

def register_user(username, password):
    with get_conn() as conn:
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))

def login_user(username, password):
    with get_conn() as conn:
        user = conn.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, password)).fetchone()
    return user[0] if user else None

def log_expense(user_id, category, description, amount, date):
    with get_conn() as conn:
        conn.execute("INSERT INTO expenses (user_id, category, description, amount, date) VALUES (?, ?, ?, ?, ?)", 
                     (user_id, category, description, amount, date))

def log_income(user_id, source, amount, date):
    with get_conn() as conn:
        conn.execute("INSERT INTO income (user_id, source, amount, date) VALUES (?, ?, ?, ?)", 
                     (user_id, source, amount, date))

def set_budget(user_id, category, amount):
    with get_conn() as conn:
        conn.execute("INSERT OR REPLACE INTO budget (user_id, category, amount) VALUES (?, ?, ?)", 
                     (user_id, category, amount))

def get_budget_df(user_id):
    with get_conn() as conn:
        return pd.read_sql_query("SELECT category, amount FROM budget WHERE user_id = ?", conn, params=(user_id,))

def get_expenses_df(user_id):
    with get_conn() as conn:
        return pd.read_sql_query("SELECT category, amount, date FROM expenses WHERE user_id = ?", conn, params=(user_id,))

# Utility functions for report generation
def get_budget_report(user_id):
    budget_df = get_budget_df(user_id)
    expenses_df = get_expenses_df(user_id)
    
    if not budget_df.empty and not expenses_df.empty:
        merged_df = pd.merge(budget_df, expenses_df.groupby('category')['amount'].sum().reset_index(), on='category', how='left')
        merged_df.columns = ['Category', 'Budgeted Amount', 'Total Expenses']
        merged_df['Total Expenses'].fillna(0, inplace=True)
        merged_df['Remaining Budget'] = merged_df['Budgeted Amount'] - merged_df['Total Expenses']
        return merged_df
    elif not budget_df.empty:
        budget_df['Total Expenses'] = 0
        budget_df['Remaining Budget'] = budget_df['amount']
        return budget_df
    else:
        return pd.DataFrame(columns=['Category', 'Budgeted Amount', 'Total Expenses', 'Remaining Budget'])

def download_csv(df):
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    return buffer.getvalue()

def download_excel(df):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Budget Report')
    buffer.seek(0)
    return buffer.getvalue()

def display_chart(df, chart_type):
    if 'date' not in df.columns:
        df['date'] = pd.to_datetime(datetime.now().date())

    if chart_type == "Pie Chart":
        fig = px.pie(df, values='amount', names='category', title='Spending by Category')
    elif chart_type == "Bar Chart":
        fig = px.bar(df, x='date', y='amount', color='category', title='Spending Over Time')
    elif chart_type == "Line Chart":
        fig = px.line(df, x='date', y='amount', color='category', title='Spending Trend')
    elif chart_type == "Stacked Bar Chart":
        fig = px.bar(df, x='date', y='amount', color='category', title='Spending Over Time', text='amount', barmode='stack')
    elif chart_type == "Area Chart":
        fig = px.area(df, x='date', y='amount', color='category', title='Spending Area Chart')
    elif chart_type == "Histogram":
        fig = px.histogram(df, x='amount', color='category', title='Expense Distribution')
    elif chart_type == "Donut Chart":
        fig = px.pie(df, values='amount', names='category', title='Spending by Category', hole=0.3)
    elif chart_type == "Bubble Chart":
        fig = px.scatter(df, x='date', y='amount', color='category', size='amount', title='Spending Bubble Chart')
    else:
        st.error("Chart type not recognized.")
        return
    st.plotly_chart(fig)

# Main Streamlit app
def main():
    st.set_page_config(page_title="Expense Tracker", page_icon="💸", layout="wide", initial_sidebar_state="expanded")
    
    st.markdown("""
        <style>
        .header-title {
            font-size: 3em;
            color: #007bff;
            text-align: center;
            font-family: 'Arial Black', sans-serif;
        }
        .sidebar-content {
            font-family: 'Segoe UI', sans-serif;
            font-size: 1.1em;
        }
        .stButton button {
            background-color: #007bff;
            color: white;
            border-radius: 5px;
            font-size: 1.1em;
            padding: 10px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<h1 class='header-title'>Expense Tracker Dashboard</h1>", unsafe_allow_html=True)
    
    st.sidebar.title("Expense Tracker")
    st.sidebar.image("1.jpg", width=150)  # Add an image or logo to sidebar
    st.sidebar.markdown("<div class='sidebar-content'>Manage your expenses and budget efficiently.</div>", unsafe_allow_html=True)
    
    auth_mode = st.sidebar.radio("Select Mode", ["Login", "Register"], index=0)

    if auth_mode == "Register":
        st.sidebar.subheader("Register")
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Register"):
            try:
                register_user(username, password)
                st.sidebar.success("Registered successfully!")
            except sqlite3.IntegrityError:
                st.sidebar.error("Username already exists. Please choose another.")
    elif auth_mode == "Login":
        st.sidebar.subheader("Login")
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Login"):
            user_id = login_user(username, password)
            if user_id:
                st.sidebar.success("Logged in successfully!")
                st.session_state['user_id'] = user_id
                st.session_state['expense_type'] = None  # Reset expense type
            else:
                st.sidebar.error("Invalid credentials. Please try again.")

    if 'user_id' in st.session_state:
        st.title("Welcome to Your Expense Tracker")
        
        # Select Expense Type
        expense_type = st.selectbox("Select Expense Type", ["Fixed Expenses", "Variable Expenses", "Discretionary Expenses", "Essential Expenses", "Non-Essential Expenses", "Periodic Expenses", "One-Time Expenses", "Operating Expenses", "Capital Expenses"])
        st.session_state['expense_type'] = expense_type

        # Filter categories based on expense type
        expense_categories = {
            "Fixed Expenses": ["Rent", "Utilities", "Insurance"],
            "Variable Expenses": ["Groceries", "Transportation", "Entertainment"],
            "Discretionary Expenses": ["Dining Out", "Subscriptions"],
            "Essential Expenses": ["Healthcare", "Education"],
            "Non-Essential Expenses": ["Luxury Items"],
            "Periodic Expenses": ["Vacation", "Annual Memberships"],
            "One-Time Expenses": ["Car Purchase", "Home Renovation"],
            "Operating Expenses": ["Salaries", "Supplies"],
            "Capital Expenses": ["Equipment", "Property"]
        }

        selected_categories = expense_categories.get(expense_type, [])

        if st.button("Log Out"):
            st.session_state.pop('user_id', None)
            st.experimental_rerun()
        
        st.header("Log Expenses")
        with st.form("log_expense_form"):
            category = st.selectbox("Category", selected_categories)
            description = st.text_input("Description")
            amount = st.number_input("Amount", min_value=0.0, step=0.01)
            date = st.date_input("Date", value=datetime.now().date())
            submit_button = st.form_submit_button("Add Expense")

        if submit_button and category:
            log_expense(st.session_state['user_id'], category, description, amount, date)
            st.success(f"Expense logged: {description} - {amount} {category}")

        st.header("Log Income")
        with st.form("log_income_form"):
            source = st.text_input("Source")
            income_amount = st.number_input("Amount", min_value=0.0, step=0.01, key="income_amount")
            income_date = st.date_input("Date", value=datetime.now().date(), key="income_date")
            income_submit_button = st.form_submit_button("Add Income")

        if income_submit_button and source:
            log_income(st.session_state['user_id'], source, income_amount, income_date)
            st.success(f"Income logged: {source} - {income_amount}")

        st.header("Set Budget")
        with st.form("set_budget_form"):
            budget_category = st.selectbox("Category", selected_categories, key="budget_category")
            budget_amount = st.number_input("Budget Amount", min_value=0.0, step=0.01, key="budget_amount")
            budget_submit_button = st.form_submit_button("Set Budget")

        if budget_submit_button:
            set_budget(st.session_state['user_id'], budget_category, budget_amount)
            st.success(f"Budget set: {budget_category} - {budget_amount}")

        st.header("Budget Report")
        budget_report_df = get_budget_report(st.session_state['user_id'])
        st.dataframe(budget_report_df)

        if st.button("Download Report as CSV"):
            csv = download_csv(budget_report_df)
            st.download_button(label="Download CSV", data=csv, file_name="budget_report.csv", mime="text/csv")

        if st.button("Download Report as Excel"):
            excel = download_excel(budget_report_df)
            st.download_button(label="Download Excel", data=excel, file_name="budget_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        st.header("Visualize Your Expenses")
        chart_type = st.selectbox("Choose Chart Type", ["Pie Chart", "Bar Chart", "Line Chart", "Stacked Bar Chart", "Area Chart", "Histogram", "Donut Chart", "Bubble Chart"])
        expense_df = get_expenses_df(st.session_state['user_id'])
        display_chart(expense_df, chart_type)

if __name__ == "__main__":
    main()

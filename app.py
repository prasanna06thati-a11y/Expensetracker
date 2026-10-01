
import json
import os
from datetime import date

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Expense Tracker",
    page_icon="💰",
    layout="wide"
)

DATA_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "expenses.json"
)

REQUIRED_FIELDS = [
    "id",
    "date",
    "category",
    "amount",
    "description"
]

PAGES = [
    "Add Expense",
    "View Expenses",
    "Edit Expense",
    "Delete Expense",
    "Dashboard"
]

CATEGORIES = [
    "Food",
    "Transport",
    "Education",
    "Shopping",
    "Entertainment",
    "Bills",
    "Health",
    "Other"
]

def is_valid_record(record):
    if not isinstance(record, dict):
        return False

    return all(
        field in record
        for field in REQUIRED_FIELDS
    )

def validate_expense_input(
    expense_date,
    category,
    amount,
    description
):
    errors = []

    if not isinstance(expense_date, date):
        errors.append("Please select a valid date.")

    if category not in CATEGORIES:
        errors.append("Please select a valid category.")

    if amount is None or amount <= 0:
        errors.append("Amount must be greater than 0.")

    if not description.strip():
        errors.append("Description cannot be empty.")

    return errors

def save_expenses(expenses):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(expenses, file, indent=4)

def backup_bad_file():
    backup_file = DATA_FILE + ".bak"

    if os.path.exists(backup_file):
        os.remove(backup_file)

    os.replace(DATA_FILE, backup_file)

def load_expenses():
    if not os.path.exists(DATA_FILE):
        save_expenses([])
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

    except json.JSONDecodeError:
        backup_bad_file()
        save_expenses([])
        return []

    except OSError:
        return []

    if not isinstance(data, list):
        return []

    return [
        record
        for record in data
        if is_valid_record(record)
    ]

def get_next_id(expenses):
    if not expenses:
        return 1

    ids = []

    for expense in expenses:
        try:
            ids.append(int(expense["id"]))
        except (KeyError, TypeError, ValueError):
            continue

    if not ids:
        return 1

    return max(ids) + 1

if "expenses" not in st.session_state:
    st.session_state.expenses = load_expenses()

if "success_message" not in st.session_state:
    st.session_state.success_message = None

if "error_message" not in st.session_state:
    st.session_state.error_message = None

if "form_counter" not in st.session_state:
    st.session_state.form_counter = 0

if st.session_state.success_message:
    st.success(st.session_state.success_message)
    st.session_state.success_message = None

if st.session_state.error_message:
    st.error(st.session_state.error_message)
    st.session_state.error_message = None

def show_add_expense():
    st.title("➕ Add Expense")
    st.write("Enter the details of your new expense.")

    form_id = st.session_state.form_counter

    with st.form(f"add_expense_form_{form_id}"):

        expense_date = st.date_input(
            "Date",
            value=date.today()
        )

        category = st.selectbox(
            "Category",
            CATEGORIES
        )

        amount = st.number_input(
            "Amount",
            min_value=0.0,
            value=0.0,
            step=1.0
        )

        description = st.text_input(
            "Description",
            placeholder="Example: Lunch at college"
        )

        submitted = st.form_submit_button(
            "Add Expense",
            use_container_width=True
        )

    if submitted:
        description = " ".join(description.split())

        errors = validate_expense_input(
            expense_date,
            category,
            amount,
            description
        )

        if errors:
            for error in errors:
                st.error(error)
            return

        new_expense = {
            "id": get_next_id(st.session_state.expenses),
            "date": expense_date.isoformat(),
            "category": category,
            "amount": round(float(amount), 2),
            "description": description
        }

        old_expenses = list(st.session_state.expenses)

        st.session_state.expenses.append(new_expense)

        try:
            save_expenses(st.session_state.expenses)

        except OSError as error:
            st.session_state.expenses = old_expenses
            st.error(f"Could not save expense: {error}")
            return

        st.session_state.success_message = (
            f"Expense added successfully! "
            f"Expense ID: {new_expense['id']}"
        )

        st.session_state.form_counter += 1
        st.rerun()

def show_view_expenses():
    st.title("📋 View Expenses")

    expenses = st.session_state.expenses

    if not expenses:
        st.info(
            "No expenses yet. Add your first expense "
            "from the Add Expense page."
        )
        return

    df = pd.DataFrame(expenses)

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    df["amount"] = pd.to_numeric(
        df["amount"],
        errors="coerce"
    )

    df = df.sort_values(
        by="date",
        ascending=False
    )

    st.subheader("🔎 Filters")

    col1, col2, col3 = st.columns(3)

    with col1:
        categories = ["All"] + sorted(
            df["category"].dropna().unique().tolist()
        )

        selected_category = st.selectbox(
            "Category",
            categories
        )

    with col2:
        min_date = df["date"].min().date()
        max_date = df["date"].max().date()

        selected_dates = st.date_input(
            "Date Range",
            value=(min_date, max_date)
        )

    with col3:
        search_text = st.text_input(
            "Search Description"
        )

    filtered_df = df.copy()

    if selected_category != "All":
        filtered_df = filtered_df[
            filtered_df["category"] == selected_category
        ]

    if isinstance(selected_dates, tuple):
        if len(selected_dates) == 2:
            start_date, end_date = selected_dates

            filtered_df = filtered_df[
                (filtered_df["date"].dt.date >= start_date)
                & (filtered_df["date"].dt.date <= end_date)
            ]

    if search_text.strip():
        filtered_df = filtered_df[
            filtered_df["description"].str.contains(
                search_text.strip(),
                case=False,
                na=False
            )
        ]

    st.subheader("📊 Summary")

    metric1, metric2 = st.columns(2)

    with metric1:
        st.metric(
            "Number of Expenses",
            len(filtered_df)
        )

    with metric2:
        total_amount = filtered_df["amount"].sum()

        st.metric(
            "Total Amount",
            f"₹{total_amount:,.2f}"
        )

    st.subheader("💰 Expense Records")

    display_df = filtered_df.copy()

    display_df["date"] = display_df["date"].dt.strftime(
        "%Y-%m-%d"
    )

    display_df = display_df[
        [
            "id",
            "date",
            "category",
            "amount",
            "description"
        ]
    ]

    display_df.columns = [
        "ID",
        "Date",
        "Category",
        "Amount",
        "Description"
    ]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

def show_edit_expense():
    st.title("✏️ Edit Expense")

    expenses = st.session_state.expenses

    if not expenses:
        st.info(
            "No expenses available to edit. "
            "Please add an expense first."
        )
        return

    expense_ids = [
        int(expense["id"])
        for expense in expenses
    ]

    selected_id = st.selectbox(
        "Select Expense ID",
        expense_ids
    )

    selected_expense = next(
        (
            expense
            for expense in expenses
            if int(expense["id"]) == selected_id
        ),
        None
    )

    if selected_expense is None:
        st.error("Selected expense could not be found.")
        return

    try:
        current_date = date.fromisoformat(
            selected_expense["date"]
        )
    except (ValueError, TypeError):
        current_date = date.today()

    current_category = selected_expense["category"]

    if current_category not in CATEGORIES:
        current_category = "Other"

    current_amount = float(
        selected_expense["amount"]
    )

    current_description = selected_expense["description"]

    with st.form("edit_expense_form"):

        new_date = st.date_input(
            "Date",
            value=current_date
        )

        new_category = st.selectbox(
            "Category",
            CATEGORIES,
            index=CATEGORIES.index(current_category)
        )

        new_amount = st.number_input(
            "Amount",
            min_value=0.0,
            value=current_amount,
            step=1.0
        )

        new_description = st.text_input(
            "Description",
            value=current_description
        )

        update_button = st.form_submit_button(
            "Update Expense",
            use_container_width=True
        )

    if update_button:
        new_description = " ".join(
            new_description.split()
        )

        errors = validate_expense_input(
            new_date,
            new_category,
            new_amount,
            new_description
        )

        if errors:
            for error in errors:
                st.error(error)
            return

        updated_expenses = []
        expense_found = False

        for expense in expenses:

            if int(expense["id"]) == selected_id:

                updated_expenses.append(
                    {
                        "id": expense["id"],
                        "date": new_date.isoformat(),
                        "category": new_category,
                        "amount": round(
                            float(new_amount),
                            2
                        ),
                        "description": new_description
                    }
                )

                expense_found = True

            else:
                updated_expenses.append(expense)

        if not expense_found:
            st.error("The selected expense was not found.")
            return

        old_expenses = st.session_state.expenses

        st.session_state.expenses = updated_expenses

        try:
            save_expenses(
                st.session_state.expenses
            )

        except OSError as error:
            st.session_state.expenses = old_expenses
            st.error(
                f"Could not save updated expense: {error}"
            )
            return

        st.session_state.success_message = (
            f"Expense ID {selected_id} "
            "updated successfully!"
        )

        st.rerun()

def show_delete_expense():
    st.title("🗑️ Delete Expense")

    expenses = st.session_state.expenses

    if not expenses:
        st.info(
            "No expenses available to delete."
        )
        return

    st.warning(
        "⚠️ Deleting an expense is permanent."
    )

    expense_ids = [
        int(expense["id"])
        for expense in expenses
    ]

    selected_id = st.selectbox(
        "Select Expense ID to Delete",
        expense_ids
    )

    selected_expense = next(
        (
            expense
            for expense in expenses
            if int(expense["id"]) == selected_id
        ),
        None
    )

    if selected_expense is None:
        st.error("Selected expense could not be found.")
        return

    st.subheader("Expense Details")

    col1, col2 = st.columns(2)

    with col1:
        st.write(
            f"**ID:** {selected_expense['id']}"
        )
        st.write(
            f"**Date:** {selected_expense['date']}"
        )
        st.write(
            f"**Category:** {selected_expense['category']}"
        )

    with col2:
        st.write(
            f"**Amount:** ₹{float(selected_expense['amount']):,.2f}"
        )
        st.write(
            f"**Description:** "
            f"{selected_expense['description']}"
        )

    st.divider()

    confirm = st.checkbox(
        "I confirm that I want to delete this expense."
    )

    if st.button(
        "🗑️ Delete Expense",
        type="primary",
        disabled=not confirm,
        use_container_width=True
    ):

        old_expenses = list(
            st.session_state.expenses
        )

        updated_expenses = [
            expense
            for expense in expenses
            if int(expense["id"]) != selected_id
        ]

        if len(updated_expenses) == len(expenses):
            st.error(
                "The selected expense was not found."
            )
            return

        st.session_state.expenses = updated_expenses

        try:
            save_expenses(
                st.session_state.expenses
            )

        except OSError as error:
            st.session_state.expenses = old_expenses
            st.error(
                f"Could not delete expense: {error}"
            )
            return

        st.session_state.success_message = (
            f"Expense ID {selected_id} "
            "deleted successfully!"
        )

        st.rerun()

def show_dashboard():
    st.title("📊 Expense Dashboard")

    expenses = st.session_state.expenses

    if not expenses:
        st.info(
            "No expense data available for the dashboard."
        )
        return

    df = pd.DataFrame(expenses)

    df["amount"] = pd.to_numeric(
        df["amount"],
        errors="coerce"
    )

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["amount", "date"]
    )

    st.subheader("🔎 Dashboard Filters")

    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:
        dashboard_categories = ["All"] + sorted(
            df["category"].unique().tolist()
        )

        dashboard_category = st.selectbox(
            "Category",
            dashboard_categories,
            key="dashboard_category"
        )

    with filter_col2:
        dashboard_min_date = df["date"].min().date()
        dashboard_max_date = df["date"].max().date()

        dashboard_dates = st.date_input(
            "Date Range",
            value=(
                dashboard_min_date,
                dashboard_max_date
            ),
            key="dashboard_dates"
        )

    dashboard_df = df.copy()

    if dashboard_category != "All":
        dashboard_df = dashboard_df[
            dashboard_df["category"] == dashboard_category
        ]

    if isinstance(dashboard_dates, tuple):
        if len(dashboard_dates) == 2:
            start_date, end_date = dashboard_dates

            dashboard_df = dashboard_df[
                (dashboard_df["date"].dt.date >= start_date)
                & (dashboard_df["date"].dt.date <= end_date)
            ]

    if dashboard_df.empty:
        st.warning(
            "No expenses found for the selected filters."
        )
        return

    total_expenses = len(dashboard_df)
    total_amount = dashboard_df["amount"].sum()
    average_expense = dashboard_df["amount"].mean()

    highest_expense = dashboard_df["amount"].max()

    highest_expense_row = dashboard_df.loc[
        dashboard_df["amount"].idxmax()
    ]

    highest_category_data = (
        dashboard_df.groupby("category")["amount"]
        .sum()
        .sort_values(ascending=False)
    )

    highest_category = (
        highest_category_data.index[0]
    )

    highest_category_amount = (
        highest_category_data.iloc[0]
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Expenses",
            total_expenses
        )

    with col2:
        st.metric(
            "Total Amount",
            f"₹{total_amount:,.2f}"
        )

    with col3:
        st.metric(
            "Average Expense",
            f"₹{average_expense:,.2f}"
        )

    with col4:
        st.metric(
            "Highest Expense",
            f"₹{highest_expense:,.2f}"
        )

    st.divider()

    info_col1, info_col2 = st.columns(2)

    with info_col1:
        st.subheader("🏆 Highest Spending Category")
        st.write(
            f"**{highest_category}**"
        )
        st.write(
            f"Total: ₹{highest_category_amount:,.2f}"
        )

    with info_col2:
        st.subheader("💸 Highest Single Expense")
        st.write(
            f"**{highest_expense_row['description']}**"
        )
        st.write(
            f"Amount: ₹{highest_expense:,.2f}"
        )

    st.divider()

    st.subheader("💰 Spending by Category")

    category_data = (
        dashboard_df.groupby("category")["amount"]
        .sum()
        .sort_values(ascending=False)
    )

    st.bar_chart(category_data)

    st.subheader("📅 Monthly Spending")

    dashboard_df["month"] = dashboard_df[
        "date"
    ].dt.strftime("%Y-%m")

    monthly_data = (
        dashboard_df.groupby("month")["amount"]
        .sum()
        .sort_index()
    )

    st.line_chart(monthly_data)

    st.subheader("📈 Expense Trend")

    trend_data = (
        dashboard_df.groupby("date")["amount"]
        .sum()
        .sort_index()
    )

    st.line_chart(trend_data)

    st.subheader("📋 Dashboard Expense Details")

    details_df = dashboard_df.copy()

    details_df["date"] = details_df[
        "date"
    ].dt.strftime("%Y-%m-%d")

    details_df = details_df[
        [
            "id",
            "date",
            "category",
            "amount",
            "description"
        ]
    ]

    details_df.columns = [
        "ID",
        "Date",
        "Category",
        "Amount",
        "Description"
    ]

    st.dataframe(
        details_df,
        use_container_width=True,
        hide_index=True
    )

st.sidebar.title("💰 Expense Tracker")

selected_page = st.sidebar.radio(
    "Navigation",
    PAGES
)

if selected_page == "Add Expense":
    show_add_expense()

elif selected_page == "View Expenses":
    show_view_expenses()

elif selected_page == "Edit Expense":
    show_edit_expense()

elif selected_page == "Delete Expense":
    show_delete_expense()

elif selected_page == "Dashboard":
    show_dashboard()
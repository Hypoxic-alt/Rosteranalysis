import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# =============================================================================
#            HELPER FUNCTION TO PROCESS THE UPLOADED FILE
# =============================================================================
def process_file(uploaded_file):
    """
    Process the uploaded Excel file (exported from Coreschedule grid view) and
    returns a melted DataFrame with columns: 'Name', 'Date', and 'Shift'.
    """
    # Read the Excel file and use the first sheet
    df = pd.ExcelFile(uploaded_file)
    sheet_name = df.sheet_names[0]
    df = pd.read_excel(df, sheet_name=sheet_name, header=None)

    # ----------------- DATA CLEANING & PREPARATION ---------------------------
    # Assume that the work schedule data starts from row 3 (0-indexed row 3)
    df_cleaned = df.iloc[3:].reset_index(drop=True)
    # Row 1 (index 1) contains column headers (names and dates)
    df_cleaned.columns = df.iloc[1]
    # Rename the first column to "Name" to identify employees
    df_cleaned.rename(columns={df_cleaned.columns[0]: "Name"}, inplace=True)
    # Drop any columns that are completely empty
    df_cleaned = df_cleaned.dropna(axis=1, how='all')

    # ----------------- DATE EXTRACTION & CORRECTION --------------------------
    # Extract date strings from row 3 (index 2), ignoring NaNs, and append a default year (2024)
    date_strings = df.iloc[2, 1:].dropna().astype(str) + "-2024"

    corrected_dates = []
    current_year = 2024  # Starting year

    # Adjust for transitions from December to January (2024 -> 2025)
    for date in date_strings:
        parsed_date = pd.to_datetime(date[:-5], format='%a %d-%b', errors='coerce')
        if corrected_dates and parsed_date.month == 1 and corrected_dates[-1].month == 12:
            current_year = 2025
        corrected_date_str = f"{parsed_date.strftime('%a %d-%b')}-{current_year}"
        corrected_date = pd.to_datetime(corrected_date_str, format='%a %d-%b-%Y', errors='coerce')
        corrected_dates.append(corrected_date)

    date_series = pd.Series(corrected_dates)
    # Update DataFrame columns: first column remains "Name", others become corrected dates
    df_cleaned.columns = ["Name"] + list(date_series)

    # ----------------- RESHAPE DATA TO LONG FORMAT ---------------------------
    # Convert from wide to long format (columns: 'Name', 'Date', 'Shift')
    df_melted = df_cleaned.melt(id_vars=["Name"], var_name="Date", value_name="Shift")
    # Convert the Date column to datetime objects
    df_melted["Date"] = pd.to_datetime(df_melted["Date"], errors='coerce')
    # Drop rows with missing shift data
    df_melted = df_melted.dropna(subset=["Shift"])

    # ----------------- FILTER OUT UNWANTED SHIFT TYPES -----------------------
    # Exclude unwanted shift codes (e.g., off days or specific shift types)
    excluded_shifts = ["OFF", "Off", "RL SMO", "FL SMO", "SL", "PDL SMO"]
    df_melted = df_melted[~df_melted["Shift"].isin(excluded_shifts)]

    return df_melted

# =============================================================================
#                          PAGE 1: UPLOAD FILE
# =============================================================================
def upload_page():
    st.title("Upload File")
    st.write("**Instructions:** Please upload an Excel file exported from the Coreschedule grid view.")
    
    # File uploader widget (only Excel files are allowed)
    uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx"])
    
    if uploaded_file is not None:
        # Process the uploaded file and store the processed DataFrame in session_state
        df_melted = process_file(uploaded_file)
        st.session_state["df_melted"] = df_melted
        st.success("File uploaded and processed successfully!")
        st.write("You can now navigate to the 'Main Data' page from the sidebar.")

# =============================================================================
#                          PAGE 2: MAIN DATA & PLOTS
# =============================================================================
def main_data_page():
    st.title("Main Data")
    
    # Check if the file has been uploaded; if not, display an error message.
    if "df_melted" not in st.session_state or st.session_state["df_melted"] is None:
        st.error("No file uploaded yet. Please navigate to the 'Upload File' page and upload a file.")
        return
    
    # Retrieve the processed data from session_state
    df_melted = st.session_state["df_melted"]

    # ------------------- SIDEBAR FILTERS -----------------------
    st.sidebar.header("Main Data Filters")
    
    # Date Range Selection
    min_date = df_melted["Date"].min()
    max_date = df_melted["Date"].max()
    start_date, end_date = st.sidebar.date_input("Select Date Range", [min_date, max_date])
    
    # Display options: percentages and median comparison
    show_percentage = st.sidebar.checkbox("Show Percentages", value=True)
    show_median = st.sidebar.checkbox("Show Median Comparison", value=True)
    
    # Apply the date filter to the data
    df_filtered = df_melted[
        (df_melted["Date"] >= pd.Timestamp(start_date)) &
        (df_melted["Date"] <= pd.Timestamp(end_date))
    ]
    
    # Filter by Name
    st.sidebar.header("Filter Options")
    names = df_filtered["Name"].unique()
    selected_name = st.sidebar.selectbox("Select a Name:", names)
    df_person = df_filtered[df_filtered["Name"] == selected_name]
    
    # Select which shifts to display using checkboxes
    st.sidebar.header("Select Shifts to Display")
    shift_options = sorted(df_person["Shift"].unique())
    selected_shifts = {shift: st.sidebar.checkbox(shift, value=True) for shift in shift_options}
    active_shifts = [shift for shift, selected in selected_shifts.items() if selected]
    df_person = df_person[df_person["Shift"].isin(active_shifts)]
    
    # ------------------- PLOT 1: SHIFT DISTRIBUTION -----------------------
    st.subheader(f"Shift Distribution for {selected_name}")
    
    # Calculate counts for each shift type for the selected person
    shift_counts = df_person["Shift"].value_counts()
    if show_percentage:
        shift_counts = (shift_counts / shift_counts.sum()) * 100  # Convert counts to percentages

    # Calculate median shift distribution across all staff for the selected shifts
    all_shifts_data = df_filtered[df_filtered["Shift"].isin(active_shifts)]
    median_shift_counts = all_shifts_data.groupby("Name")["Shift"].value_counts().unstack(fill_value=0).median(axis=0)
    if show_percentage:
        median_shift_counts = (median_shift_counts / median_shift_counts.sum()) * 100

    # Ensure both series include the same set of shifts
    all_shifts = set(shift_counts.index).union(set(median_shift_counts.index))
    shift_counts = shift_counts.reindex(all_shifts, fill_value=0)
    median_shift_counts = median_shift_counts.reindex(all_shifts, fill_value=0)
    
    # Create the bar chart for shift distribution
    fig, ax = plt.subplots(figsize=(10, 5))
    bar_width = 0.4
    x = range(len(shift_counts))
    ax.bar(x, shift_counts, width=bar_width, label=selected_name, color="skyblue", align='center')
    if show_median:
        ax.bar([i + bar_width for i in x], median_shift_counts, width=bar_width,
               label="Median (All Staff)", color="orange", align='center')
    
    ax.set_xticks([i + bar_width / 2 for i in x])
    ax.set_xticklabels(shift_counts.index, rotation=45, ha="right")
    ax.set_ylabel("Percentage" if show_percentage else "Count")
    ax.set_xlabel("Shift Type")
    ax.legend()
    st.pyplot(fig)
    
    # ------------------- PLOT 2: WEEKDAY VS. WEEKEND -----------------------
    st.subheader(f"Weekday vs. Weekend Shifts for {selected_name}")
    
    # Create a new column indicating the day name for each shift
    df_person["Day"] = df_person["Date"].dt.day_name()
    total_shifts = len(df_person)
    weekend_shifts = len(df_person[df_person["Day"].isin(["Saturday", "Sunday"])])
    weekday_shifts = total_shifts - weekend_shifts
    
    if show_percentage and total_shifts > 0:
        weekend_shifts = (weekend_shifts / total_shifts) * 100
        weekday_shifts = (weekday_shifts / total_shifts) * 100
    
    # Calculate median weekday/weekend counts across all staff if enabled
    if show_median:
        all_weekend_counts = df_filtered.groupby("Name").apply(
            lambda x: (x["Date"].dt.day_name().isin(["Saturday", "Sunday"])).sum()
        )
        all_weekday_counts = df_filtered.groupby("Name").apply(
            lambda x: (~x["Date"].dt.day_name().isin(["Saturday", "Sunday"])).sum()
        )
        median_weekend = all_weekend_counts.median()
        median_weekday = all_weekday_counts.median()
        if show_percentage:
            median_total = median_weekend + median_weekday
            if median_total > 0:
                median_weekend = (median_weekend / median_total) * 100
                median_weekday = (median_weekday / median_total) * 100
    
    # Create the bar chart comparing weekday and weekend shifts
    fig, ax = plt.subplots(figsize=(6, 4))
    labels = ["Weekdays", "Weekends"]
    selected_values = [weekday_shifts, weekend_shifts]
    median_values = [median_weekday, median_weekend] if show_median else None
    
    x = np.arange(len(labels))
    bar_width = 0.4
    ax.bar(x, selected_values, width=bar_width, label=selected_name, color="skyblue", align='center')
    if show_median:
        ax.bar(x + bar_width, median_values, width=bar_width, label="Median (All Staff)", color="orange", align='center')
    
    ax.set_xticks(x + (bar_width / 2 if show_median else 0))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Percentage" if show_percentage else "Count")
    ax.set_title(f"Weekday vs. Weekend Shifts for {selected_name}")
    ax.legend()
    st.pyplot(fig)

# =============================================================================
#                            PAGE NAVIGATION
# =============================================================================
# Use a sidebar radio button for multipage navigation.
page = st.sidebar.radio("Navigation", ["Upload File", "Main Data"])

if page == "Upload File":
    upload_page()
elif page == "Main Data":
    main_data_page()

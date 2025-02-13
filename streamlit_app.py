import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# =============================================================================
#            HELPER FUNCTION TO PROCESS THE UPLOADED FILE
# =============================================================================
def process_file(uploaded_file):
    """
    Process the uploaded Excel file (exported from the Coreschedule grid view)
    and return a melted DataFrame with columns: 'Name', 'Date', and 'Shift'.
    """
    # Read the Excel file and select the first sheet
    df = pd.ExcelFile(uploaded_file)
    sheet_name = df.sheet_names[0]
    df = pd.read_excel(df, sheet_name=sheet_name, header=None)

    # ----------------- DATA CLEANING & PREPARATION ---------------------------
    # Assume data starts at row 3 (0-indexed row 3)
    df_cleaned = df.iloc[3:].reset_index(drop=True)
    # Row 1 (index 1) contains headers (names and dates)
    df_cleaned.columns = df.iloc[1]
    # Rename first column to "Name"
    df_cleaned.rename(columns={df_cleaned.columns[0]: "Name"}, inplace=True)
    # Drop any columns that are completely empty
    df_cleaned = df_cleaned.dropna(axis=1, how='all')

    # ----------------- DATE EXTRACTION & CORRECTION --------------------------
    # Extract date strings from row 3 (index 2) and append a default year (2024)
    date_strings = df.iloc[2, 1:].dropna().astype(str) + "-2024"
    corrected_dates = []
    current_year = 2024
    for date in date_strings:
        # Parse the date (ignoring the appended year)
        parsed_date = pd.to_datetime(date[:-5], format='%a %d-%b', errors='coerce')
        # If transitioning from December to January, update to 2025
        if corrected_dates and parsed_date.month == 1 and corrected_dates[-1].month == 12:
            current_year = 2025
        corrected_date_str = f"{parsed_date.strftime('%a %d-%b')}-{current_year}"
        corrected_date = pd.to_datetime(corrected_date_str, format='%a %d-%b-%Y', errors='coerce')
        corrected_dates.append(corrected_date)
    date_series = pd.Series(corrected_dates)
    # Set DataFrame column headers: first column remains "Name", others become corrected dates
    df_cleaned.columns = ["Name"] + list(date_series)

    # ----------------- RESHAPE DATA TO LONG FORMAT ---------------------------
    df_melted = df_cleaned.melt(id_vars=["Name"], var_name="Date", value_name="Shift")
    df_melted["Date"] = pd.to_datetime(df_melted["Date"], errors='coerce')
    df_melted = df_melted.dropna(subset=["Shift"])

    # ----------------- FILTER OUT UNWANTED SHIFT TYPES -----------------------
    excluded_shifts = ["OFF", "Off", "RL SMO", "FL SMO", "SL", "PDL SMO"]
    df_melted = df_melted[~df_melted["Shift"].isin(excluded_shifts)]
    
    return df_melted

# =============================================================================
#                          PAGE 1: UPLOAD FILE
# =============================================================================
def upload_page():
    st.title("Upload File")
    st.write("**Instructions:** Please upload an Excel file exported from the Coreschedule grid view.")
    
    # File uploader (only .xlsx files are allowed)
    uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx"])
    
    if uploaded_file is not None:
        # Process the uploaded file and save the DataFrame in session_state for later pages
        df_melted = process_file(uploaded_file)
        st.session_state["df_melted"] = df_melted
        st.success("File uploaded and processed successfully!")
        st.write("You can now navigate to the 'Main Data' or 'Administrative Time' pages from the sidebar.")

# =============================================================================
#                          PAGE 2: MAIN DATA & PLOTS
# =============================================================================
def main_data_page():
    st.title("Main Data")
    
    if "df_melted" not in st.session_state or st.session_state["df_melted"] is None:
        st.error("No file uploaded yet. Please navigate to the 'Upload File' page and upload a file.")
        return
    
    df_melted = st.session_state["df_melted"]

    # ------------------- SIDEBAR FILTERS -----------------------
    st.sidebar.header("Main Data Filters")
    min_date = df_melted["Date"].min()
    max_date = df_melted["Date"].max()
    start_date, end_date = st.sidebar.date_input("Select Date Range", [min_date, max_date])
    show_percentage = st.sidebar.checkbox("Show Percentages", value=True)
    show_median = st.sidebar.checkbox("Show Median Comparison", value=True)
    
    # Apply date filter
    df_filtered = df_melted[
        (df_melted["Date"] >= pd.Timestamp(start_date)) &
        (df_melted["Date"] <= pd.Timestamp(end_date))
    ]
    
    # ------------------- FILTER BY NAME & SHIFT -----------------------
    st.sidebar.header("Filter Options")
    names = df_filtered["Name"].unique()
    selected_name = st.sidebar.selectbox("Select a Name:", names)
    df_person = df_filtered[df_filtered["Name"] == selected_name]
    
    st.sidebar.header("Select Shifts to Display")
    shift_options = sorted(df_person["Shift"].unique())
    selected_shifts = {shift: st.sidebar.checkbox(shift, value=True) for shift in shift_options}
    active_shifts = [shift for shift, selected in selected_shifts.items() if selected]
    df_person = df_person[df_person["Shift"].isin(active_shifts)]
    
    # ------------------- PLOT 1: SHIFT DISTRIBUTION -----------------------
    st.subheader(f"Shift Distribution for {selected_name}")
    shift_counts = df_person["Shift"].value_counts()
    if show_percentage:
        shift_counts = (shift_counts / shift_counts.sum()) * 100
    all_shifts_data = df_filtered[df_filtered["Shift"].isin(active_shifts)]
    median_shift_counts = all_shifts_data.groupby("Name")["Shift"].value_counts().unstack(fill_value=0).median(axis=0)
    if show_percentage:
        median_shift_counts = (median_shift_counts / median_shift_counts.sum()) * 100
    
    all_shifts = set(shift_counts.index).union(set(median_shift_counts.index))
    shift_counts = shift_counts.reindex(all_shifts, fill_value=0)
    median_shift_counts = median_shift_counts.reindex(all_shifts, fill_value=0)
    
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
    df_person["Day"] = df_person["Date"].dt.day_name()
    total_shifts = len(df_person)
    weekend_shifts = len(df_person[df_person["Day"].isin(["Saturday", "Sunday"])])
    weekday_shifts = total_shifts - weekend_shifts
    
    if show_percentage and total_shifts > 0:
        weekend_shifts = (weekend_shifts / total_shifts) * 100
        weekday_shifts = (weekday_shifts / total_shifts) * 100
    
    if show_median:
        all_weekend_counts = df_filtered.groupby("Name").apply(lambda x: (x["Date"].dt.day_name().isin(["Saturday", "Sunday"])).sum())
        all_weekday_counts = df_filtered.groupby("Name").apply(lambda x: (~x["Date"].dt.day_name().isin(["Saturday", "Sunday"])).sum())
        median_weekend = all_weekend_counts.median()
        median_weekday = all_weekday_counts.median()
        if show_percentage:
            median_total = median_weekend + median_weekday
            if median_total > 0:
                median_weekend = (median_weekend / median_total) * 100
                median_weekday = (median_weekday / median_total) * 100
    
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
#                    PAGE 3: ADMINISTRATIVE TIME ANALYSIS
# =============================================================================
def admin_time_page():
    st.title("Administrative Time Analysis")
    
    if "df_melted" not in st.session_state or st.session_state["df_melted"] is None:
        st.error("No file uploaded yet. Please navigate to the 'Upload File' page and upload a file.")
        return
    
    df_melted = st.session_state["df_melted"]
    
    # ------------------- SIDEBAR FILTERS -----------------------
    st.sidebar.header("Administrative Time Filters")
    min_date = df_melted["Date"].min()
    max_date = df_melted["Date"].max()
    start_date, end_date = st.sidebar.date_input("Select Date Range", [min_date, max_date])
    
    # Filter the data based on the selected date range
    df_filtered = df_melted[(df_melted["Date"] >= pd.Timestamp(start_date)) &
                            (df_melted["Date"] <= pd.Timestamp(end_date))].copy()
    
    # ------------------- CALCULATE ADMINISTRATIVE HOURS -----------------------
    def get_admin_hours(row):
        """
        Return the number of administrative hours (out of 10) based on the shift type.
        - CST: 10 hours
        - HB IC PM, HB 21C PM: 3 hours
        - MIC: 5 hours
        - HB AM EDSTTA, HB IC AM: 5 hours (only count on weekdays)
        - Otherwise: 0 hours
        """
        shift = row["Shift"]
        if shift == "CST":
            return 10
        elif shift in ["HB IC PM", "HB 21C PM"]:
            return 3
        elif shift == "MIC":
            return 5
        elif shift in ["HB AM EDSTTA", "HB IC AM"]:
            # Only count if the shift occurs on a weekday (Monday=0 to Friday=4)
            return 5 if row["Date"].weekday() < 5 else 0
        else:
            return 0

    # Compute the admin hours for each record
    df_filtered["AdminHours"] = df_filtered.apply(get_admin_hours, axis=1)
    
    # ------------------- COMPUTE ADMINISTRATIVE TIME PERCENTAGES -----------------------
    # Overall administrative percentage for all staff
    total_admin_hours_all = df_filtered["AdminHours"].sum()
    total_shifts_all = len(df_filtered)
    overall_admin_percentage = (total_admin_hours_all / (total_shifts_all * 10)) * 100 if total_shifts_all > 0 else 0
    
    # ------------------- SELECTED STAFF MEMBER ADMINISTRATIVE TIME -----------------------
    st.sidebar.header("Filter by Staff Member")
    names = df_filtered["Name"].unique()
    selected_name = st.sidebar.selectbox("Select a Name:", names)
    df_staff = df_filtered[df_filtered["Name"] == selected_name]
    total_admin_hours_staff = df_staff["AdminHours"].sum()
    total_shifts_staff = len(df_staff)
    staff_admin_percentage = (total_admin_hours_staff / (total_shifts_staff * 10)) * 100 if total_shifts_staff > 0 else 0
    
    # ------------------- PLOT ADMINISTRATIVE TIME -----------------------
    st.subheader("Administrative Time Percentage")
    fig, ax = plt.subplots(figsize=(6, 4))
    categories = ["All Staff", selected_name]
    values = [overall_admin_percentage, staff_admin_percentage]
    bars = ax.bar(categories, values, color=["orange", "skyblue"])
    ax.set_ylabel("Administrative Time (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Total Administrative Time as Percentage")
    # Annotate each bar with its percentage value
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.1f}%', xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom')
    st.pyplot(fig)

# =============================================================================
#                            PAGE NAVIGATION
# =============================================================================
page = st.sidebar.radio("Navigation", ["Upload File", "Main Data", "Administrative Time"])
if page == "Upload File":
    upload_page()
elif page == "Main Data":
    main_data_page()
elif page == "Administrative Time":
    admin_time_page()

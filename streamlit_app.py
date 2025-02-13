import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Streamlit Dashboard
st.title("Work Schedule Dashboard")

# Sidebar for File Upload
st.sidebar.header("Upload Data")
uploaded_file = st.sidebar.file_uploader("Upload an Excel file", type=["xlsx"])

if uploaded_file:
    # Read Excel File
    df = pd.ExcelFile(uploaded_file)
    sheet_name = df.sheet_names[0]  # Assuming first sheet
    df = pd.read_excel(df, sheet_name=sheet_name, header=None)

    # Extract Column Headers (Row 3 is the date row)
    df_cleaned = df.iloc[3:].reset_index(drop=True)  # Data starts from row 3
    df_cleaned.columns = df.iloc[1]  # Row 1 has actual column headers (names, dates)

    # Rename first column to "Name"
    df_cleaned.rename(columns={df_cleaned.columns[0]: "Name"}, inplace=True)

    # Drop any fully empty columns
    df_cleaned = df_cleaned.dropna(axis=1, how='all')

    # Extract date row (Row 3, ignoring NaNs)
    date_strings = df.iloc[2, 1:].dropna().astype(str) + "-2024"  # Start assuming 2024

    # Correct year transition from 2024 to 2025
    corrected_dates = []
    current_year = 2024  # Start with 2024

    for date in date_strings:
        parsed_date = pd.to_datetime(date[:-5], format='%a %d-%b', errors='coerce')

        # If the month switches from Dec -> Jan, update to 2025
        if corrected_dates and parsed_date.month == 1 and corrected_dates[-1].month == 12:
            current_year = 2025

        corrected_date_str = f"{parsed_date.strftime('%a %d-%b')}-{current_year}"
        corrected_date = pd.to_datetime(corrected_date_str, format='%a %d-%b-%Y', errors='coerce')
        corrected_dates.append(corrected_date)

    # Convert to pandas Series
    date_series = pd.Series(corrected_dates)

    # Update column names with corrected dates
    df_cleaned.columns = ["Name"] + list(date_series)

    # Reshape data to long format
    df_melted = df_cleaned.melt(id_vars=["Name"], var_name="Date", value_name="Shift")

    # Convert Date column to proper datetime format
    df_melted["Date"] = pd.to_datetime(df_melted["Date"], errors='coerce')

    # Drop rows where shift data is missing
    df_melted = df_melted.dropna(subset=["Shift"])

    # **Filter out unwanted shifts** (INCLUDING "PDL SMO" and previous ones)
    excluded_shifts = ["OFF", "Off", "RL SMO", "FL SMO", "SL", "PDL SMO"]
    df_melted = df_melted[~df_melted["Shift"].isin(excluded_shifts)]

    # **Sidebar for Date Range Selection**
    st.sidebar.header("Select Date Range")
    min_date = df_melted["Date"].min()
    max_date = df_melted["Date"].max()
    start_date, end_date = st.sidebar.date_input("Select Date Range", [min_date, max_date])

    # **Checkbox to show percentages (Default: Checked)**
    show_percentage = st.sidebar.checkbox("Show Percentages", value=True)

    # **Checkbox to show median comparison (Default: Checked)**
    show_median = st.sidebar.checkbox("Show Median Comparison", value=True)

    # Apply date filter
    df_melted = df_melted[(df_melted["Date"] >= pd.Timestamp(start_date)) & (df_melted["Date"] <= pd.Timestamp(end_date))]

    # Sidebar for Filtering
    st.sidebar.header("Filter Options")
    selected_name = st.sidebar.selectbox("Select a Name:", df_melted["Name"].unique())

    # Filter Data for Selected Person
    filtered_df = df_melted[df_melted["Name"] == selected_name]

    # Sidebar Checkboxes for Shift Selection
    st.sidebar.header("Select Shifts to Display")
    shift_options = sorted(filtered_df["Shift"].unique())
    selected_shifts = {shift: st.sidebar.checkbox(shift, value=True) for shift in shift_options}

    # **Filter Data Based on Selected Shifts**
    active_shifts = [shift for shift, selected in selected_shifts.items() if selected]
    filtered_df = filtered_df[filtered_df["Shift"].isin(active_shifts)]

    # **Calculate total shifts and weekend/weekday ratio**
    filtered_df["Day"] = filtered_df["Date"].dt.day_name()
    total_shifts = len(filtered_df)
    weekend_shifts = len(filtered_df[filtered_df["Day"].isin(["Saturday", "Sunday"])])
    weekday_shifts = total_shifts - weekend_shifts

    if show_percentage and total_shifts > 0:
        weekend_shifts = (weekend_shifts / total_shifts) * 100
        weekday_shifts = (weekday_shifts / total_shifts) * 100

    # **Calculate median weekend/weekday percentage across all staff**
    if show_median:
        all_weekend_counts = df_melted.groupby("Name").apply(lambda x: (x["Date"].dt.day_name().isin(["Saturday", "Sunday"])).sum())
        all_weekday_counts = df_melted.groupby("Name").apply(lambda x: (~x["Date"].dt.day_name().isin(["Saturday", "Sunday"])).sum())

        median_weekend = all_weekend_counts.median()
        median_weekday = all_weekday_counts.median()

        if show_percentage:
            median_total = median_weekend + median_weekday
            if median_total > 0:
                median_weekend = (median_weekend / median_total) * 100
                median_weekday = (median_weekday / median_total) * 100

    # **Plot Weekend vs. Weekday Shifts**
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

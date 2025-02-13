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

    # Sidebar for Filtering
    st.sidebar.header("Filter Options")
    selected_name = st.sidebar.selectbox("Select a Name:", df_melted["Name"].unique())

    # Filter Data for Selected Person
    filtered_df = df_melted[df_melted["Name"] == selected_name]

    # Sidebar Checkboxes for Shift Selection
    st.sidebar.header("Select Shifts to Display")
    shift_options = filtered_df["Shift"].unique()
    selected_shifts = {shift: st.sidebar.checkbox(shift, value=True) for shift in shift_options}

    # Filter Data Based on Selected Shifts
    active_shifts = [shift for shift, selected in selected_shifts.items() if selected]
    filtered_df = filtered_df[filtered_df["Shift"].isin(active_shifts)]

    # **Toggle for showing percentages instead of counts**
    show_percentage = st.sidebar.checkbox("Show Percentages", value=False)

    # **Display Date Range Above Chart**
    if not filtered_df.empty and filtered_df["Date"].notna().any():
        min_date = filtered_df["Date"].min().strftime("%d-%b-%Y")
        max_date = filtered_df["Date"].max().strftime("%d-%b-%Y")
        st.subheader(f"Date Range: {min_date} to {max_date}")
    else:
        st.subheader("No data available for selected shifts.")

    # **Calculate shift distribution for selected staff**
    shift_counts = filtered_df["Shift"].value_counts()
    if show_percentage:
        shift_counts = (shift_counts / shift_counts.sum()) * 100  # Convert to percentage

    # **Calculate median shift distribution for all staff**
    all_shift_counts = df_melted.groupby("Name")["Shift"].value_counts().unstack(fill_value=0)
    median_shift_counts = all_shift_counts.median(axis=0)  # Median for each shift type

    if show_percentage:
        median_shift_counts = (median_shift_counts / median_shift_counts.sum()) * 100  # Convert to percentage

    # **Ensure shifts are aligned in the chart**
    all_shifts = set(shift_counts.index).union(set(median_shift_counts.index))
    shift_counts = shift_counts.reindex(all_shifts, fill_value=0)
    median_shift_counts = median_shift_counts.reindex(all_shifts, fill_value=0)

    # **Create Bar Chart**
    fig, ax = plt.subplots(figsize=(10, 5))
    bar_width = 0.4
    x = range(len(shift_counts))

    ax.bar(x, shift_counts, width=bar_width, label=selected_name, color="skyblue", align='center')
    ax.bar([i + bar_width for i in x], median_shift_counts, width=bar_width, label="Median (All Staff)", color="orange", align='center')

    ax.set_xticks([i + bar_width / 2 for i in x])
    ax.set_xticklabels(shift_counts.index, rotation=45, ha="right")
    ax.set_ylabel("Percentage" if show_percentage else "Count")
    ax.set_xlabel("Shift Type")
    ax.set_title(f"Shift Distribution for {selected_name}")
    ax.legend()

    st.pyplot(fig)

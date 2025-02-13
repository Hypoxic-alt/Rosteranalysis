import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# -----------------------------------------------------------------------------
#                           STREAMLIT DASHBOARD SETUP
# -----------------------------------------------------------------------------

# Set the title of the dashboard
st.title("Work Schedule Dashboard")

# -----------------------------------------------------------------------------
#                         SIDEBAR: FILE UPLOAD SECTION
# -----------------------------------------------------------------------------

# Create a sidebar header for file upload
st.sidebar.header("Upload Data")
# File uploader widget to allow users to upload an Excel file (.xlsx)
uploaded_file = st.sidebar.file_uploader("Upload an Excel file", type=["xlsx"])

# Proceed only if a file has been uploaded
if uploaded_file:
    # -----------------------------------------------------------------------------
    #                        DATA READING AND INITIAL CLEANING
    # -----------------------------------------------------------------------------

    # Read the Excel file using pandas ExcelFile to access sheet names
    df = pd.ExcelFile(uploaded_file)
    # Assume that the relevant data is in the first sheet
    sheet_name = df.sheet_names[0]
    # Read the sheet into a DataFrame with no header (headers will be set manually)
    df = pd.read_excel(df, sheet_name=sheet_name, header=None)

    # -----------------------------------------------------------------------------
    #                        DATAFRAME CLEANING AND PREPARATION
    # -----------------------------------------------------------------------------

    # The actual work schedule data starts from row 3 (using zero-indexing: row index 3)
    df_cleaned = df.iloc[3:].reset_index(drop=True)  # Reset index for cleaner DataFrame
    # Set the DataFrame's column headers using row 1 (index 1), which holds the names and dates
    df_cleaned.columns = df.iloc[1]
    # Rename the first column to "Name" to clearly identify employee names
    df_cleaned.rename(columns={df_cleaned.columns[0]: "Name"}, inplace=True)
    # Drop any columns that are completely empty to avoid processing irrelevant data
    df_cleaned = df_cleaned.dropna(axis=1, how='all')

    # -----------------------------------------------------------------------------
    #                   DATE EXTRACTION AND CORRECTION
    # -----------------------------------------------------------------------------

    # Extract the date strings from row 3 (index 2) for all columns except the first column,
    # and append a default year (2024) to each date string.
    date_strings = df.iloc[2, 1:].dropna().astype(str) + "-2024"

    # Initialize a list to store the corrected datetime objects.
    corrected_dates = []
    # Start with the year 2024
    current_year = 2024

    # Iterate over each date string and adjust for year transitions (e.g., December to January)
    for date in date_strings:
        # Parse the date string, ignoring the appended year for now (use only the day and month info)
        parsed_date = pd.to_datetime(date[:-5], format='%a %d-%b', errors='coerce')

        # If there is a previous date and the month transitions from December to January,
        # update the year to 2025.
        if corrected_dates and parsed_date.month == 1 and corrected_dates[-1].month == 12:
            current_year = 2025

        # Reconstruct the date string with the correct year
        corrected_date_str = f"{parsed_date.strftime('%a %d-%b')}-{current_year}"
        # Parse the corrected date string into a datetime object
        corrected_date = pd.to_datetime(corrected_date_str, format='%a %d-%b-%Y', errors='coerce')
        # Append the corrected datetime object to the list
        corrected_dates.append(corrected_date)

    # Convert the list of corrected dates into a pandas Series for further manipulation
    date_series = pd.Series(corrected_dates)
    # Update the DataFrame's column headers: the first column remains "Name" and the rest are the corrected dates
    df_cleaned.columns = ["Name"] + list(date_series)

    # -----------------------------------------------------------------------------
    #                        RESHAPE DATA TO LONG FORMAT
    # -----------------------------------------------------------------------------

    # Use pandas melt function to reshape the DataFrame from wide to long format.
    # This creates three columns: "Name", "Date", and "Shift"
    df_melted = df_cleaned.melt(id_vars=["Name"], var_name="Date", value_name="Shift")

    # Convert the "Date" column into datetime objects to enable date-based filtering and grouping.
    df_melted["Date"] = pd.to_datetime(df_melted["Date"], errors='coerce')
    # Remove any rows where the shift data is missing (NaN)
    df_melted = df_melted.dropna(subset=["Shift"])

    # -----------------------------------------------------------------------------
    #                     FILTER OUT UNWANTED SHIFT TYPES
    # -----------------------------------------------------------------------------

    # Define a list of shift codes that should be excluded from the analysis (e.g., off days)
    excluded_shifts = ["OFF", "Off", "RL SMO", "FL SMO", "SL", "PDL SMO"]
    # Filter the DataFrame to exclude these unwanted shift types
    df_melted = df_melted[~df_melted["Shift"].isin(excluded_shifts)]

    # -----------------------------------------------------------------------------
    #                        SIDEBAR: DATE RANGE SELECTION
    # -----------------------------------------------------------------------------

    # Provide a header and date selection widget in the sidebar for filtering the data by date range
    st.sidebar.header("Select Date Range")
    # Determine the minimum and maximum dates present in the data
    min_date = df_melted["Date"].min()
    max_date = df_melted["Date"].max()
    # Use a date_input widget to allow users to select a date range, with defaults set to the full range
    start_date, end_date = st.sidebar.date_input("Select Date Range", [min_date, max_date])

    # -----------------------------------------------------------------------------
    #                 SIDEBAR: DISPLAY PREFERENCES OPTIONS
    # -----------------------------------------------------------------------------

    # Checkbox to toggle between viewing counts and percentages (default is to show percentages)
    show_percentage = st.sidebar.checkbox("Show Percentages", value=True)
    # Checkbox to toggle whether to display a median comparison across all staff (default is checked)
    show_median = st.sidebar.checkbox("Show Median Comparison", value=True)

    # -----------------------------------------------------------------------------
    #                             APPLY DATE FILTER
    # -----------------------------------------------------------------------------

    # Filter the DataFrame to include only the records that fall within the selected date range
    df_melted = df_melted[
        (df_melted["Date"] >= pd.Timestamp(start_date)) &
        (df_melted["Date"] <= pd.Timestamp(end_date))
    ]

    # -----------------------------------------------------------------------------
    #                    SIDEBAR: FILTER BY NAME & SHIFT TYPE
    # -----------------------------------------------------------------------------

    # Header for additional filter options in the sidebar
    st.sidebar.header("Filter Options")
    # Create a selectbox for choosing a specific staff member by name
    selected_name = st.sidebar.selectbox("Select a Name:", df_melted["Name"].unique())

    # Filter the DataFrame to include only data for the selected staff member
    filtered_df = df_melted[df_melted["Name"] == selected_name]

    # Provide checkboxes for selecting which shift types to display for the selected staff member
    st.sidebar.header("Select Shifts to Display")
    # Get a sorted list of unique shift types available for the selected person
    shift_options = sorted(filtered_df["Shift"].unique())
    # Create a dictionary of checkboxes for each shift type (defaulting to True for all)
    selected_shifts = {shift: st.sidebar.checkbox(shift, value=True) for shift in shift_options}

    # Build a list of active shifts based on which checkboxes are selected
    active_shifts = [shift for shift, selected in selected_shifts.items() if selected]
    # Filter the DataFrame further based on the selected shift types
    filtered_df = filtered_df[filtered_df["Shift"].isin(active_shifts)]

    # -----------------------------------------------------------------------------
    #                       SHIFT DISTRIBUTION CHART SECTION
    # -----------------------------------------------------------------------------

    st.subheader(f"Shift Distribution for {selected_name}")

    # Calculate the count of each shift type for the selected staff member
    shift_counts = filtered_df["Shift"].value_counts()
    # Convert counts to percentages if the option is enabled
    if show_percentage:
        shift_counts = (shift_counts / shift_counts.sum()) * 100

    # Calculate overall shift counts for the selected shift types across all staff
    all_shift_counts = df_melted[df_melted["Shift"].isin(active_shifts)]
    # Compute the median shift distribution across all staff by grouping by "Name" and then taking the median
    median_shift_counts = all_shift_counts.groupby("Name")["Shift"].value_counts().unstack(fill_value=0).median(axis=0)
    # Convert median values to percentages if required
    if show_percentage:
        median_shift_counts = (median_shift_counts / median_shift_counts.sum()) * 100

    # Ensure both the individual and median counts cover the same set of shifts
    all_shifts = set(shift_counts.index).union(set(median_shift_counts.index))
    shift_counts = shift_counts.reindex(all_shifts, fill_value=0)
    median_shift_counts = median_shift_counts.reindex(all_shifts, fill_value=0)

    # Create a bar chart to display the shift distribution
    fig, ax = plt.subplots(figsize=(10, 5))
    bar_width = 0.4  # Set the width for the bars
    x = range(len(shift_counts))  # Positions for each bar on the x-axis

    # Plot the selected staff member's shift distribution
    ax.bar(x, shift_counts, width=bar_width, label=selected_name, color="skyblue", align='center')
    # If median comparison is enabled, plot the median shift distribution side-by-side
    if show_median:
        ax.bar([i + bar_width for i in x], median_shift_counts, width=bar_width, label="Median (All Staff)", color="orange", align='center')

    # Configure the x-axis ticks and labels, rotating labels for readability
    ax.set_xticks([i + bar_width / 2 for i in x])
    ax.set_xticklabels(shift_counts.index, rotation=45, ha="right")
    # Set the y-axis label depending on whether counts or percentages are shown
    ax.set_ylabel("Percentage" if show_percentage else "Count")
    ax.set_xlabel("Shift Type")
    ax.legend()
    # Render the chart within the Streamlit app
    st.pyplot(fig)

    # -----------------------------------------------------------------------------
    #                     WEEKEND VS. WEEKDAY ANALYSIS SECTION
    # -----------------------------------------------------------------------------

    st.subheader(f"Weekday vs. Weekend Shifts for {selected_name}")

    # Create a new column "Day" in the filtered DataFrame to indicate the day name (e.g., Monday, Tuesday)
    filtered_df["Day"] = filtered_df["Date"].dt.day_name()
    # Calculate the total number of shifts for the selected staff member
    total_shifts = len(filtered_df)
    # Count the number of shifts that occur on weekends (Saturday and Sunday)
    weekend_shifts = len(filtered_df[filtered_df["Day"].isin(["Saturday", "Sunday"])])
    # The number of weekday shifts is the total shifts minus weekend shifts
    weekday_shifts = total_shifts - weekend_shifts

    # If percentage view is enabled and there is shift data, convert the counts to percentages
    if show_percentage and total_shifts > 0:
        weekend_shifts = (weekend_shifts / total_shifts) * 100
        weekday_shifts = (weekday_shifts / total_shifts) * 100

    # Calculate median values for weekend and weekday shifts across all staff if median view is enabled
    if show_median:
        # Calculate weekend shift counts for each staff member by checking day names
        all_weekend_counts = df_melted.groupby("Name").apply(
            lambda x: (x["Date"].dt.day_name().isin(["Saturday", "Sunday"])).sum()
        )
        # Calculate weekday shift counts for each staff member
        all_weekday_counts = df_melted.groupby("Name").apply(
            lambda x: (~x["Date"].dt.day_name().isin(["Saturday", "Sunday"])).sum()
        )

        # Compute the median for weekend and weekday shift counts across all staff
        median_weekend = all_weekend_counts.median()
        median_weekday = all_weekday_counts.median()

        # Convert median counts to percentages if required
        if show_percentage:
            median_total = median_weekend + median_weekday
            if median_total > 0:
                median_weekend = (median_weekend / median_total) * 100
                median_weekday = (median_weekday / median_total) * 100

    # -----------------------------------------------------------------------------
    #                    PLOTTING WEEKDAY VS. WEEKEND SHIFTS
    # -----------------------------------------------------------------------------

    # Create a new figure for the weekday vs. weekend analysis
    fig, ax = plt.subplots(figsize=(6, 4))
    labels = ["Weekdays", "Weekends"]  # Labels for the two bars
    # Prepare the values for the selected staff member
    selected_values = [weekday_shifts, weekend_shifts]
    # Prepare the median values if median comparison is enabled
    median_values = [median_weekday, median_weekend] if show_median else None

    x = np.arange(len(labels))  # X-axis positions for the labels
    bar_width = 0.4  # Width of the bars

    # Plot the bar for the selected staff member's weekday and weekend shifts
    ax.bar(x, selected_values, width=bar_width, label=selected_name, color="skyblue", align='center')
    # If enabled, plot the median values alongside the individual's data
    if show_median:
        ax.bar(x + bar_width, median_values, width=bar_width, label="Median (All Staff)", color="orange", align='center')

    # Adjust the x-axis tick positions and set the labels
    ax.set_xticks(x + (bar_width / 2 if show_median else 0))
    ax.set_xticklabels(labels)
    # Set the y-axis label based on whether percentages or counts are displayed
    ax.set_ylabel("Percentage" if show_percentage else "Count")
    ax.set_title(f"Weekday vs. Weekend Shifts for {selected_name}")
    ax.legend()
    # Render the weekend vs. weekday chart in the Streamlit app
    st.pyplot(fig)

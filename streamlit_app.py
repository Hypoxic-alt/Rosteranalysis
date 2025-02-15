import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import json

# =============================================================================
#            HELPER FUNCTION TO PROCESS THE UPLOADED FILE
# =============================================================================
def process_file(source):
    """
    Process the Excel file from the given source (a file-like object or a URL)
    and return a melted DataFrame with columns: 'Name', 'Date', 'Shift'.
    """
    df = pd.ExcelFile(source)
    sheet_name = df.sheet_names[0]
    df = pd.read_excel(df, sheet_name=sheet_name, header=None)

    # ----------------- DATA CLEANING & PREPARATION ---------------------------
    df_cleaned = df.iloc[3:].reset_index(drop=True)
    df_cleaned.columns = df.iloc[1]
    df_cleaned.rename(columns={df_cleaned.columns[0]: "Name"}, inplace=True)
    df_cleaned = df_cleaned.dropna(axis=1, how='all')

    # ----------------- DATE EXTRACTION & CORRECTION --------------------------
    date_strings = df.iloc[2, 1:].dropna().astype(str) + "-2024"
    corrected_dates = []
    current_year = 2024
    for date in date_strings:
        parsed_date = pd.to_datetime(date[:-5], format='%a %d-%b', errors='coerce')
        if corrected_dates and parsed_date.month == 1 and corrected_dates[-1].month == 12:
            current_year = 2025
        corrected_date_str = f"{parsed_date.strftime('%a %d-%b')}-{current_year}"
        corrected_date = pd.to_datetime(corrected_date_str, format='%a %d-%b-%Y', errors='coerce')
        corrected_dates.append(corrected_date)
    date_series = pd.Series(corrected_dates)
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
#         HELPER FUNCTION TO CONVERT GOOGLE DRIVE SHAREABLE URL
# =============================================================================
def convert_to_direct_url(shareable_url):
    """
    Convert a Google Drive shareable URL to a direct download URL.
    Example:
      Shareable URL: https://drive.google.com/file/d/FILE_ID/view?usp=sharing
      Direct download URL: https://drive.google.com/uc?export=download&id=FILE_ID
    """
    try:
        file_id = shareable_url.split('/d/')[1].split('/')[0]
    except IndexError:
        st.error("The provided URL does not appear to be valid. Please check the format.")
        return None
    return f"https://drive.google.com/uc?export=download&id={file_id}"

# =============================================================================
#                          PAGE 1: UPLOAD FILE & CONFIG IMPORT
# =============================================================================
def upload_page():
    st.title("Upload File")
    st.write("**Instructions:** Upload an Excel file exported from the Coreschedule grid view, or load one automatically from Google Drive.")
    
    # --- Option to import a saved admin configuration ---
    st.subheader("Import Admin Configuration")
    config_file = st.file_uploader("Upload a configuration JSON file", type=["json"], key="config_import")
    if config_file is not None:
        try:
            config = json.load(config_file)
            st.session_state["admin_config"] = config
            st.success("Configuration imported successfully!")
        except Exception as e:
            st.error(f"Error loading configuration: {e}")
    
    # --- Option 1: Manual file upload ---
    uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx"], key="file_upload")
    if uploaded_file is not None:
        df_melted = process_file(uploaded_file)
        st.session_state["df_melted"] = df_melted
        st.success("File uploaded and processed successfully!")
    
    st.markdown("---")
    st.write("**Or load the file automatically from Google Drive:**")
    gdrive_link = st.text_input("Enter the Google Drive shareable URL:", key="gdrive_link")
    if st.button("Load File from Google Drive"):
        if gdrive_link:
            download_url = convert_to_direct_url(gdrive_link)
            if download_url:
                try:
                    df_melted = process_file(download_url)
                    st.session_state["df_melted"] = df_melted
                    st.success("File loaded successfully from Google Drive!")
                except Exception as e:
                    st.error(f"Error processing file: {e}")
        else:
            st.error("Please enter a valid Google Drive URL.")
    
    if "df_melted" in st.session_state:
        st.write("Preview of loaded data:")
        st.dataframe(st.session_state["df_melted"].head())

# =============================================================================
#                          PAGE 2: MAIN DATA & PLOTS
# =============================================================================
def main_data_page():
    st.title("Main Data")
    
    if "df_melted" not in st.session_state:
        st.error("No file uploaded yet. Please navigate to the 'Upload File' page and upload a file.")
        return
    
    df_melted = st.session_state["df_melted"]
    st.sidebar.header("Main Data Filters")
    min_date = df_melted["Date"].min()
    max_date = df_melted["Date"].max()
    start_date, end_date = st.sidebar.date_input("Select Date Range", [min_date, max_date], key="main_date")
    show_percentage = st.sidebar.checkbox("Show Percentages", value=True, key="main_pct")
    show_median = st.sidebar.checkbox("Show Median Comparison", value=True, key="main_median")
    
    df_filtered = df_melted[
        (df_melted["Date"] >= pd.Timestamp(start_date)) &
        (df_melted["Date"] <= pd.Timestamp(end_date))
    ]
    
    st.sidebar.header("Filter Options")
    names = df_filtered["Name"].unique()
    selected_name = st.sidebar.selectbox("Select a Name:", names, key="main_name")
    df_person = df_filtered[df_filtered["Name"] == selected_name]
    
    st.sidebar.header("Select Shifts to Display")
    shift_options = sorted(df_person["Shift"].unique())
    selected_shifts = {shift: st.sidebar.checkbox(shift, value=True, key=f"main_shift_{shift}") for shift in shift_options}
    active_shifts = [shift for shift, selected in selected_shifts.items() if selected]
    df_person = df_person[df_person["Shift"].isin(active_shifts)]
    
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
#                   PAGE 3: ADMIN CONFIGURATION
# =============================================================================
def admin_config_page():
    st.title("Admin Configuration")
    st.write("Set the administration hour values for each shift and toggle shifts on or off. "
             "These settings will be used in all admin calculations.")
    
    if "df_melted" not in st.session_state:
        st.error("No file uploaded yet. Please navigate to the 'Upload File' page and upload a file.")
        return

    df_melted = st.session_state["df_melted"]
    unique_shifts = sorted(df_melted["Shift"].unique())
    
    st.write("For each shift, set the number of admin hours (out of 10). Uncheck the box to disable that shift from admin calculations.")
    # Default values for known shifts; default to 0 for others.
    default_values = {
        "CST": 10,
        "HB IC PM": 3,
        "HB 21C PM": 3,
        "MIC": 5,
        "HB AM EDSTTA": 5,
        "HB IC AM": 5
    }
    
    admin_config = {}
    for shift in unique_shifts:
        col1, col2 = st.columns([1,1])
        with col1:
            include = st.checkbox(f"Include {shift}", value=st.session_state.get(f"include_{shift}", True), key=f"include_{shift}")
        with col2:
            default_val = default_values.get(shift, 0)
            hours = st.number_input(f"{shift} admin hours (out of 10):", value=st.session_state.get(f"value_{shift}", default_val), min_value=0, max_value=10, step=1, key=f"value_{shift}")
        # Only include the shift if enabled; otherwise, set to 0.
        admin_config[shift] = hours if include else 0

    # Store the configuration in session_state so other pages can use it.
    st.session_state["admin_config"] = admin_config
    st.success("Admin configuration updated!")
    st.write("Current configuration:")
    st.json(admin_config)
    
    # Provide a download button to export configuration as a JSON file.
    config_json = json.dumps(admin_config, indent=4)
    st.download_button("Export Configuration", data=config_json, file_name="admin_config.json", mime="application/json")

# =============================================================================
#                    PAGE 4: ADMINISTRATIVE TIME ANALYSIS
# =============================================================================
def admin_time_page():
    st.title("Administrative Time Analysis")
    
    if "df_melted" not in st.session_state:
        st.error("No file uploaded yet. Please navigate to the 'Upload File' page and upload a file.")
        return
    
    # Use admin configuration from session_state; if not set, use an empty dict.
    admin_config = st.session_state.get("admin_config", {})
    
    df_melted = st.session_state["df_melted"]
    st.sidebar.header("Administrative Time Filters")
    min_date = df_melted["Date"].min()
    max_date = df_melted["Date"].max()
    start_date, end_date = st.sidebar.date_input("Select Date Range", [min_date, max_date], key="admin_time_date")
    
    df_filtered = df_melted[(df_melted["Date"] >= pd.Timestamp(start_date)) &
                            (df_melted["Date"] <= pd.Timestamp(end_date))].copy()
    
    # Calculate admin hours per record using the configuration.
    def get_admin_hours(row):
        shift = row["Shift"]
        # For HB AM EDSTTA and HB IC AM, count only on weekdays.
        if shift in ["HB AM EDSTTA", "HB IC AM"]:
            return admin_config.get(shift, 0) if row["Date"].weekday() < 5 else 0
        else:
            return admin_config.get(shift, 0)
    
    df_filtered["AdminHours"] = df_filtered.apply(get_admin_hours, axis=1)
    
    total_admin_hours_all = df_filtered["AdminHours"].sum()
    total_shifts_all = len(df_filtered)
    overall_admin_percentage = (total_admin_hours_all / (total_shifts_all * 10)) * 100 if total_shifts_all > 0 else 0
    
    st.sidebar.header("Filter by Staff Member")
    names = df_filtered["Name"].unique()
    selected_name = st.sidebar.selectbox("Select a Name:", names, key="admin_time_name")
    df_staff = df_filtered[df_filtered["Name"] == selected_name]
    total_admin_hours_staff = df_staff["AdminHours"].sum()
    total_shifts_staff = len(df_staff)
    staff_admin_percentage = (total_admin_hours_staff / (total_shifts_staff * 10)) * 100 if total_shifts_staff > 0 else 0
    
    st.subheader("Administrative Time Percentage")
    fig, ax = plt.subplots(figsize=(6, 4))
    categories = ["All Staff", selected_name]
    values = [overall_admin_percentage, staff_admin_percentage]
    bars = ax.bar(categories, values, color=["orange", "skyblue"])
    ax.set_ylabel("Administrative Time (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Total Administrative Time as Percentage")
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.1f}%', xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom')
    st.pyplot(fig)

# =============================================================================
#                    PAGE 5: ADMIN COMPARISON GRAPH
# =============================================================================
def admin_comparison_page():
    st.title("Administrative Time Comparison (All Staff)")
    
    if "df_melted" not in st.session_state:
        st.error("No file uploaded yet. Please navigate to the 'Upload File' page and upload a file.")
        return
    
    # Use admin configuration from session_state.
    admin_config = st.session_state.get("admin_config", {})
    
    df_melted = st.session_state["df_melted"]
    st.sidebar.header("Admin Comparison Filters")
    min_date = df_melted["Date"].min()
    max_date = df_melted["Date"].max()
    start_date, end_date = st.sidebar.date_input("Select Date Range", [min_date, max_date], key="admin_cmp_date")
    
    df_filtered = df_melted[(df_melted["Date"] >= pd.Timestamp(start_date)) &
                            (df_melted["Date"] <= pd.Timestamp(end_date))].copy()
    
    def get_admin_hours(row):
        shift = row["Shift"]
        if shift in ["HB AM EDSTTA", "HB IC AM"]:
            return admin_config.get(shift, 0) if row["Date"].weekday() < 5 else 0
        else:
            return admin_config.get(shift, 0)
    
    df_filtered["AdminHours"] = df_filtered.apply(get_admin_hours, axis=1)
    
    admin_percentages = {}
    for name, group in df_filtered.groupby("Name"):
        total_admin = group["AdminHours"].sum()
        total_shifts = len(group)
        percentage = (total_admin / (total_shifts * 10)) * 100 if total_shifts > 0 else 0
        admin_percentages[name] = percentage
    admin_df = pd.DataFrame(list(admin_percentages.items()), columns=["Name", "AdminPercentage"])
    
    st.sidebar.header("Select Users to Display")
    all_names = admin_df["Name"].tolist()
    selected_users = []
    for name in all_names:
        default_val = st.session_state.get(f"cmp_{name}", True)
        if st.sidebar.checkbox(name, value=default_val, key=f"cmp_{name}"):
            selected_users.append(name)
    admin_df = admin_df[admin_df["Name"].isin(selected_users)]
    
    st.subheader("Administrative Time Percentage by User")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(admin_df["Name"], admin_df["AdminPercentage"], color="purple")
    ax.set_ylabel("Administrative Time (%)")
    ax.set_xlabel("Staff Member")
    ax.set_title("Admin Time Comparison Across Staff")
    ax.set_ylim(0, 100)
    plt.xticks(rotation=45, ha="right")
    st.pyplot(fig)

# =============================================================================
#                            PAGE NAVIGATION
# =============================================================================
page = st.sidebar.radio("Navigation", [
    "Upload File",
    "Main Data",
    "Admin Configuration",
    "Administrative Time",
    "Admin Comparison"
])
if page == "Upload File":
    upload_page()
elif page == "Main Data":
    main_data_page()
elif page == "Admin Configuration":
    admin_config_page()
elif page == "Administrative Time":
    admin_time_page()
elif page == "Admin Comparison":
    admin_comparison_page()

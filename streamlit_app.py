import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# =============================================================================
#            HELPER FUNCTION TO PROCESS THE UPLOADED FILE
# =============================================================================
def process_file(source):
    """
    Process the Excel file (uploaded or URL), infer multi-year dates,
    and return a tidy DataFrame with ['Name','Date','Shift'].
    """
    # 1) Read raw
    xls = pd.ExcelFile(source)
    sheet = xls.sheet_names[0]
    raw = pd.read_excel(xls, sheet_name=sheet, header=None)

    # 2) Chop off the first 3 rows of meta, set up headers
    df = raw.iloc[3:].reset_index(drop=True)
    df.columns = raw.iloc[1]
    df.rename(columns={df.columns[0]:"Name"}, inplace=True)
    df = df.dropna(axis=1, how='all')

    # 3) Pull the date‐row strings, append placeholder year
    date_strs = raw.iloc[2,1:].dropna().astype(str) + "-XXXX"  # we’ll replace XXXX
    # Parse them once to get month/day
    mds = [pd.to_datetime(s[:-5], format='%a %d-%b', errors='coerce') for s in date_strs]

    # 4) Decide start year based on today's date vs first month
    now = datetime.now()
    start_year = now.year - 1 if mds[0].month > now.month else now.year

    # 5) Build corrected_dates by rolling forward whenever month decreases
    corrected_dates = []
    year = start_year
    prev_month = None
    for md in mds:
        if prev_month is not None and md.month < prev_month:
            year += 1
        corrected_dates.append(
            pd.to_datetime(f"{md.strftime('%a %d-%b')}-{year}", format='%a %d-%b-%Y')
        )
        prev_month = md.month

    # 6) Assign real datetime columns
    df.columns = ["Name"] + corrected_dates

    # 7) Melt to long form and clean
    df_long = df.melt(id_vars="Name", var_name="Date", value_name="Shift")
    df_long["Date"] = pd.to_datetime(df_long["Date"], errors='coerce')
    df_long = df_long.dropna(subset=["Shift"])

    # 8) Drop unwanted shifts
    exclude = ["OFF","Off","RL SMO","FL SMO","SL","PDL SMO"]
    df_long = df_long[~df_long["Shift"].isin(exclude)]

    return df_long

# =============================================================================
#         HELPER FUNCTION TO CONVERT GOOGLE DRIVE SHAREABLE URL
# =============================================================================
def convert_to_direct_url(shareable_url):
    """
    Convert a Google Drive shareable URL to a direct download URL.
    For example:
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
#                          PAGE 1: UPLOAD FILE
# =============================================================================
def upload_page():
    st.title("Upload File")
    st.write("**Instructions:** Upload an Excel file exported from the Coreschedule grid view, or load one automatically from Google Drive.")

    # --- Option 1: Manual file upload ---
    uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx"])
    if uploaded_file is not None:
        df_melted = process_file(uploaded_file)
        st.session_state["df_melted"] = df_melted
        st.success("File uploaded and processed successfully!")

    st.markdown("---")
    st.write("**Or load the file automatically from Google Drive:**")

    # --- Option 2: Load from Google Drive via copy-paste link ---
    gdrive_link = st.text_input("Enter the Google Drive shareable URL:")
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

    # Optionally display a preview if data has been loaded
    if "df_melted" in st.session_state:
        st.write("Preview of loaded data:")
        st.dataframe(st.session_state["df_melted"].head())

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
    
    # Filter data based on the selected date range
    df_filtered = df_melted[
        (df_melted["Date"] >= pd.Timestamp(start_date)) &
        (df_melted["Date"] <= pd.Timestamp(end_date))
    ].copy()
    
    # ------------------- CALCULATE ADMINISTRATIVE HOURS -----------------------
    def get_admin_hours(row):
        shift = row["Shift"]
        if shift == "CST":
            return 10
        elif shift in ["HB IC PM", "HB 21C PM"]:
            return 3
        elif shift == "MIC":
            return 5
        elif shift in ["HB AM EDSTTA", "HB IC AM"]:
            return 5 if row["Date"].weekday() < 5 else 0
        else:
            return 0

    df_filtered["AdminHours"] = df_filtered.apply(get_admin_hours, axis=1)
    
    grouped = df_filtered.groupby("Name").agg(
        TotalAdminHours=pd.NamedAgg(column="AdminHours", aggfunc="sum"),
        TotalShifts=pd.NamedAgg(column="Shift", aggfunc="count")
    )
    grouped["AdminPercentage"] = (grouped["TotalAdminHours"] / (grouped["TotalShifts"] * 10)) * 100
    
    # ------------------- NEW TOGGLES ABOVE USER SELECT -----------------------
    include_only_CST = st.sidebar.checkbox("Include only users with at least one CST shift", value=False)
    show_annotations = st.sidebar.checkbox("Show Percentage Annotations", value=True)
    
    # ------------------- SELECT USERS TO DISPLAY -----------------------
    # Exclude users with "JNR" in their name.
    if include_only_CST:
        # Identify users with at least one "CST" shift.
        cst_users = df_filtered.groupby("Name")["Shift"].apply(lambda x: (x == "CST").any())
        cst_users = cst_users[cst_users].index.tolist()
        all_users = [user for user in grouped.index if "JNR" not in user and user in cst_users]
    else:
        all_users = [user for user in grouped.index if "JNR" not in user]
    
    selected_users = st.sidebar.multiselect("Select Staff Members:", all_users, default=all_users)
    
    display_df = grouped.loc[selected_users]
    
    # ------------------- PLOT ADMINISTRATIVE TIME PERCENTAGE -----------------------
    st.subheader("Administrative Time Percentage by Staff Member")
    fig, ax = plt.subplots(figsize=(8, 5))
    
    bars = ax.bar(display_df.index, display_df["AdminPercentage"], color="skyblue")
    ax.set_ylabel("Administrative Time (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Administrative Time Percentage for Selected Staff Members")
    
    # Rotate x-axis labels to 45° for better readability.
    ax.set_xticks(range(len(display_df.index)))
    ax.set_xticklabels(display_df.index, rotation=45, ha="right")
    
    if show_annotations:
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.1f}%', 
                        xy=(bar.get_x() + bar.get_width()/2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom')
    
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

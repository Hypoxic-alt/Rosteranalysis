import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# =============================================================================
#            HELPER FUNCTION TO PROCESS THE UPLOADED FILE
# =============================================================================
def process_file(source):
    """
    Process the Excel file from the given source (file-like or URL)
    and return a melted DataFrame with columns: 'Name', 'Date', 'Shift'.
    """
    df = pd.ExcelFile(source)
    sheet_name = df.sheet_names[0]
    df = pd.read_excel(df, sheet_name=sheet_name, header=None)

    # Data starts at row 3 (index 3)
    df_cleaned = df.iloc[3:].reset_index(drop=True)
    # Row 1 (index 1) has the headers
    df_cleaned.columns = df.iloc[1]
    df_cleaned.rename(columns={df_cleaned.columns[0]: "Name"}, inplace=True)
    df_cleaned = df_cleaned.dropna(axis=1, how='all')

    # Extract and correct dates (row 2, index 2)
    date_strings = df.iloc[2, 1:].dropna().astype(str) + "-2024"
    corrected_dates = []
    current_year = 2024
    for date in date_strings:
        parsed = pd.to_datetime(date[:-5], format='%a %d-%b', errors='coerce')
        if corrected_dates and parsed.month == 1 and corrected_dates[-1].month == 12:
            current_year = 2025
        full = f"{parsed.strftime('%a %d-%b')}-{current_year}"
        corrected_dates.append(pd.to_datetime(full, format='%a %d-%b-%Y', errors='coerce'))
    df_cleaned.columns = ["Name"] + corrected_dates

    # Melt to long format
    df_melted = df_cleaned.melt(id_vars=["Name"], var_name="Date", value_name="Shift")
    df_melted["Date"] = pd.to_datetime(df_melted["Date"], errors='coerce')
    df_melted = df_melted.dropna(subset=["Shift"])

    # Exclude unwanted shifts
    excluded = ["OFF", "Off", "RL SMO", "FL SMO", "SL", "PDL SMO"]
    df_melted = df_melted[~df_melted["Shift"].isin(excluded)]
    return df_melted

# =============================================================================
#         HELPER FUNCTION TO CONVERT GOOGLE DRIVE SHAREABLE URL
# =============================================================================
def convert_to_direct_url(shareable_url):
    try:
        file_id = shareable_url.split('/d/')[1].split('/')[0]
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    except Exception:
        st.error("Invalid Google Drive URL.")
        return None

# =============================================================================
#                          PAGE 1: UPLOAD FILE
# =============================================================================
def upload_page():
    st.title("Upload File")
    st.write("Upload an Excel file or load from Google Drive:")

    uploaded = st.file_uploader("Excel file", type=["xlsx"])
    if uploaded:
        st.session_state["df_melted"] = process_file(uploaded)
        st.success("File processed!")

    st.markdown("---")
    link = st.text_input("Google Drive share URL")
    if st.button("Load from Google Drive") and link:
        url = convert_to_direct_url(link)
        if url:
            st.session_state["df_melted"] = process_file(url)
            st.success("Loaded from Drive!")

    if "df_melted" in st.session_state:
        st.dataframe(st.session_state["df_melted"].head())

# =============================================================================
#                          PAGE 2: MAIN DATA & PLOTS
# =============================================================================
def main_data_page():
    st.title("Main Data")
    if "df_melted" not in st.session_state:
        st.error("Please upload a file first.")
        return
    df = st.session_state["df_melted"]

    st.sidebar.header("Main Data Filters")
    mn, mx = df["Date"].min(), df["Date"].max()
    sd, ed = st.sidebar.date_input("Date Range", [mn, mx])
    pct = st.sidebar.checkbox("Show Percentages", True)
    med = st.sidebar.checkbox("Show Median Comparison", True)

    df = df[(df["Date"] >= pd.Timestamp(sd)) & (df["Date"] <= pd.Timestamp(ed))]

    st.sidebar.header("Filter Options")
    person = st.sidebar.selectbox("Select Name", df["Name"].unique())
    df_p = df[df["Name"] == person]

    st.sidebar.header("Select Shifts")
    opts = sorted(df_p["Shift"].unique())
    sel = [s for s in opts if st.sidebar.checkbox(s, True)]
    df_p = df_p[df_p["Shift"].isin(sel)]

    # Shift Distribution
    st.subheader(f"Shift Distribution for {person}")
    cnt = df_p["Shift"].value_counts()
    if pct:
        cnt = cnt / cnt.sum() * 100
    all_sel = df[df["Shift"].isin(sel)]
    med_cnt = all_sel.groupby("Name")["Shift"].value_counts().unstack(fill_value=0).median(axis=0)
    if pct:
        med_cnt = med_cnt / med_cnt.sum() * 100
    keys = sorted(set(cnt.index).union(med_cnt.index))
    cnt, med_cnt = cnt.reindex(keys, 0), med_cnt.reindex(keys, 0)

    fig, ax = plt.subplots(figsize=(10,5))
    x = np.arange(len(keys))
    w = 0.4
    ax.bar(x, cnt, w, label=person, color="skyblue")
    if med:
        ax.bar(x+w, med_cnt, w, label="Median", color="orange")
    ax.set_xticks(x + w/2); ax.set_xticklabels(keys, rotation=45, ha="right")
    ax.set_ylabel("Percentage" if pct else "Count")
    ax.legend()
    st.pyplot(fig)

    # Weekend vs Weekday
    st.subheader(f"Weekday vs. Weekend for {person}")
    df_p["Day"] = df_p["Date"].dt.day_name()
    tot = len(df_p)
    wknd = df_p["Day"].isin(["Saturday","Sunday"]).sum()
    wd = tot - wknd
    if pct and tot>0:
        wknd, wd = wknd/tot*100, wd/tot*100
    if med:
        aw = df.groupby("Name").apply(lambda x: x["Date"].dt.day_name().isin(["Saturday","Sunday"]).sum())
        am = df.groupby("Name").apply(lambda x: (~x["Date"].dt.day_name().isin(["Saturday","Sunday"])).sum())
        mw = aw.median(); md = am.median()
        if pct and (mw+md)>0:
            mw, md = mw/(mw+md)*100, md/(mw+md)*100
    fig, ax = plt.subplots(figsize=(6,4))
    labels = ["Weekdays","Weekends"]
    vals = [wd,wknd]
    ax.bar(labels, vals, color=["blue","red"], label=person)
    if med:
        ax.bar(labels, [md,mw], alpha=0.5, color="orange", label="Median")
    ax.set_ylabel("Percentage" if pct else "Count")
    ax.legend()
    st.pyplot(fig)

# =============================================================================
#                    PAGE 3: ADMINISTRATIVE TIME ANALYSIS
# =============================================================================
def admin_time_page():
    st.title("Administrative Time Analysis")
    if "df_melted" not in st.session_state:
        st.error("Upload first.")
        return
    df = st.session_state["df_melted"]

    st.sidebar.header("Admin Time Filters")
    mn, mx = df["Date"].min(), df["Date"].max()
    sd, ed = st.sidebar.date_input("Date Range", [mn, mx], key="adm_date")
    pct = st.sidebar.checkbox("Show Percentages", True, key="adm_pct")
    med = st.sidebar.checkbox("Show Median Comparison", True, key="adm_med")
    df = df[(df["Date"]>=sd)&(df["Date"]<=ed)]

    st.sidebar.header("Staff & Options")
    include_cst = st.sidebar.checkbox("Only with CST", False)
    names = df["Name"].unique()
    if include_cst:
        has = df[df["Shift"]=="CST"].groupby("Name").size()>0
        names = [n for n in names if has.get(n,False)]
    names = [n for n in names if "JNR" not in n]
    sel = st.sidebar.multiselect("Select Staff", names, default=names)

    def get_admin_hours(r):
        s = r["Shift"]
        if s=="CST": return 10
        if s in ["HB IC PM","HB 21C PM"]: return 3
        if s=="MIC": return 5
        if s in ["HB AM EDSTTA","HB IC AM"]:
            return 5 if r["Date"].weekday()<5 else 0
        return 0

    df["AH"] = df.apply(get_admin_hours,axis=1)
    gp = df[df["Name"].isin(sel)].groupby("Name").agg(
        TotalAH=("AH","sum"), TotalShifts=("Shift","count")
    )
    gp["Admin%"] = gp["TotalAH"]/(gp["TotalShifts"]*10)*100

    fig, ax = plt.subplots(figsize=(8,5))
    bars = ax.bar(gp.index, gp["Admin%"], color="skyblue")
    ax.set_ylim(0,100)
    ax.set_ylabel("Admin %")
    ax.set_title("Administrative % by Staff")
    if st.sidebar.checkbox("Show Annotations", True, key="adm_annot"):
        for b in bars:
            h=b.get_height(); ax.text(b.get_x()+b.get_width()/2,h+1,f"{h:.1f}%",ha="center")
    st.pyplot(fig)

# =============================================================================
#                    PAGE 4: HB ADMINISTRATIVE TIME ANALYSIS
# =============================================================================
def hb_admin_time_page():
    st.title("HB Administrative Time Analysis")
    if "df_melted" not in st.session_state:
        st.error("Upload first.")
        return
    df = st.session_state["df_melted"]

    st.sidebar.header("HB Time Filters")
    mn, mx = df["Date"].min(), df["Date"].max()
    sd, ed = st.sidebar.date_input("Date Range (HB)", [mn, mx], key="hb_date")
    pct = st.sidebar.checkbox("Show Percentages", True, key="hb_pct")
    med = st.sidebar.checkbox("Show Median Comparison", True, key="hb_med")
    df_hb = df[(df["Date"]>=sd)&(df["Date"]<=ed)]
    df_hb = df_hb[df_hb["Shift"].str.upper().str.startswith("HB")]
    if df_hb.empty:
        st.info("No HB shifts.")
        return

    def get_admin_hours(r):
        s=r["Shift"]
        if s=="CST": return 10
        if s in ["HB IC PM","HB 21C PM"]: return 3
        if s=="MIC": return 5
        if s in ["HB AM EDSTTA","HB IC AM"]:
            return 5 if r["Date"].weekday()<5 else 0
        return 0

    df_hb["AH"] = df_hb.apply(get_admin_hours,axis=1)
    gp = df_hb.groupby("Name").agg(
        TotalAH=("AH","sum"), TotalShifts=("Shift","count")
    )
    gp["Admin%"] = gp["TotalAH"]/(gp["TotalShifts"]*10)*100

    if med:
        all_gp = gp.copy()
        median_pct = all_gp["Admin%"].median()

    sel = st.sidebar.multiselect("Select Staff", gp.index.tolist(), default=gp.index.tolist())
    disp = gp.loc[sel]

    fig, ax = plt.subplots(figsize=(8,5))
    x = np.arange(len(disp))
    w=0.4
    ax.bar(x, disp["Admin%"], w, label="Staff", color="skyblue")
    if med:
        ax.bar(x+w, [median_pct]*len(disp), w, label="Median", color="orange")
    ax.set_xticks(x + (w/2 if med else 0))
    ax.set_xticklabels(disp.index, rotation=45, ha="right")
    ax.set_ylabel("Admin %" if pct else "Hours")
    ax.set_ylim(0,100)
    ax.set_title("HB Admin % Comparison")
    ax.legend()
    st.pyplot(fig)

# =============================================================================
#                            PAGE NAVIGATION
# =============================================================================
page = st.sidebar.radio(
    "Navigation",
    ["Upload File", "Main Data", "Administrative Time", "HB Administrative Time"]
)
if page == "Upload File":
    upload_page()
elif page == "Main Data":
    main_data_page()
elif page == "Administrative Time":
    admin_time_page()
elif page == "HB Administrative Time":
    hb_admin_time_page()

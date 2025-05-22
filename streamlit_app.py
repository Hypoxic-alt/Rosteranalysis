import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# … [all of your existing helper functions and pages stay here] …

# =============================================================================
#                    PAGE 4: HB ADMINISTRATIVE TIME ANALYSIS
# =============================================================================
def hb_admin_time_page():
    st.title("HB Administrative Time Analysis")

    if "df_melted" not in st.session_state or st.session_state["df_melted"] is None:
        st.error("No file uploaded yet. Please go to 'Upload File' and upload one.")
        return

    df_melted = st.session_state["df_melted"]

    # ----- Date range picker for HB page (unique key) -----
    st.sidebar.header("HB Time Filters")
    min_date = df_melted["Date"].min()
    max_date = df_melted["Date"].max()
    hb_start, hb_end = st.sidebar.date_input(
        "Select Date Range (HB)", [min_date, max_date], key="hb_date_range"
    )

    # ----- Percentage / Median toggles (unique keys) -----
    hb_show_percentage = st.sidebar.checkbox(
        "Show Percentages", value=True, key="hb_show_percentage"
    )
    hb_show_median = st.sidebar.checkbox(
        "Show Median Comparison", value=True, key="hb_show_median"
    )

    # ----- Filter to date window -----
    df_hb = df_melted[
        (df_melted["Date"] >= pd.Timestamp(hb_start))
        & (df_melted["Date"] <= pd.Timestamp(hb_end))
    ].copy()

    # ----- Keep only HB-prefixed shifts -----
    df_hb = df_hb[df_hb["Shift"].str.upper().str.startswith("HB")]

    if df_hb.empty:
        st.info("No HB shifts found in this date range.")
        return

    # ----- Admin hours mapping (same as on Admin page) -----
    def get_admin_hours(row):
        s = row["Shift"]
        if s == "CST":
            return 10
        elif s in ["HB IC PM", "HB 21C PM"]:
            return 3
        elif s == "MIC":
            return 5
        elif s in ["HB AM EDSTTA", "HB IC AM"]:
            return 5 if row["Date"].weekday() < 5 else 0
        else:
            return 0

    df_hb["AdminHours"] = df_hb.apply(get_admin_hours, axis=1)

    # ----- Aggregate per user -----
    grouped = df_hb.groupby("Name").agg(
        TotalAdminHours=pd.NamedAgg("AdminHours", "sum"),
        TotalHBShifts=pd.NamedAgg("Shift", "count")
    )
    grouped["Admin%"] = (grouped["TotalAdminHours"] / (grouped["TotalHBShifts"] * 10) * 100).round(2)

    # ----- Median for HB page only -----
    if hb_show_median:
        all_hb = df_hb.groupby("Name").agg(
            AdminHrs=pd.NamedAgg("AdminHours", "sum"),
            HBShifts=pd.NamedAgg("Shift", "count")
        )
        all_hb["Admin%"] = all_hb["AdminHrs"] / (all_hb["HBShifts"] * 10) * 100
        median_pct = all_hb["Admin%"].median()

    # ----- User selection -----
    users = list(grouped.index)
    selected = st.sidebar.multiselect("Select Staff Members:", users, default=users)

    display = grouped.loc[selected]

    # ----- Plotting -----
    st.subheader("HB Admin Time % by Staff")
    fig, ax = plt.subplots(figsize=(8, 5))

    x = np.arange(len(display))
    width = 0.4

    ax.bar(
        x,
        display["Admin%"],
        width,
        label="Selected Staff",
        color="skyblue",
        align="center"
    )
    if hb_show_median:
        ax.bar(
            x + width,
            [median_pct] * len(display),
            width,
            label="Median (All HB Staff)",
            color="orange",
            align="center"
        )

    ax.set_xticks(x + (width / 2 if hb_show_median else 0))
    ax.set_xticklabels(display.index, rotation=45, ha="right")
    ax.set_ylabel("Percentage" if hb_show_percentage else "Admin Hours")
    ax.set_ylim(0, 100 if hb_show_percentage else None)
    ax.set_title("HB Administrative Time Comparison")
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

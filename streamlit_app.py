# =============================================================================
#                    PAGE 3: ADMINISTRATIVE TIME ANALYSIS (BY USER)
# =============================================================================
def admin_time_page():
    st.title("Administrative Time Analysis by User")
    
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
    df_filtered = df_melted[
        (df_melted["Date"] >= pd.Timestamp(start_date)) &
        (df_melted["Date"] <= pd.Timestamp(end_date))
    ].copy()
    
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

    # Compute admin hours for each record
    df_filtered["AdminHours"] = df_filtered.apply(get_admin_hours, axis=1)
    
    # ------------------- PREPARE USER LIST -----------------------
    # Exclude any names containing "JNR" (case-insensitive)
    df_filtered = df_filtered[~df_filtered["Name"].str.contains("JNR", case=False, na=False)]
    all_users = sorted(df_filtered["Name"].unique())
    
    # Multiselect widget for selecting users (defaults to all users)
    selected_users = st.sidebar.multiselect("Select Users", options=all_users, default=all_users)
    
    if not selected_users:
        st.warning("Please select at least one user.")
        return
    
    # ------------------- COMPUTE ADMINISTRATIVE TIME PERCENTAGES PER USER -----------------------
    # Group the data by Name for only the selected users
    user_groups = df_filtered[df_filtered["Name"].isin(selected_users)].groupby("Name")
    
    admin_percentages = {}
    for name, group in user_groups:
        total_admin_hours = group["AdminHours"].sum()
        total_shifts = len(group)
        # Each shift is worth 10 hours maximum
        percentage = (total_admin_hours / (total_shifts * 10)) * 100 if total_shifts > 0 else 0
        admin_percentages[name] = percentage
    
    # Convert to DataFrame for plotting (and sort by name)
    admin_df = pd.DataFrame(list(admin_percentages.items()), columns=["Name", "AdminPercentage"]).sort_values("Name")
    
    # ------------------- PLOT ADMINISTRATIVE TIME -----------------------
    st.subheader("Administrative Time Percentage by User")
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(admin_df["Name"], admin_df["AdminPercentage"], color="skyblue")
    
    ax.set_xlabel("User")
    ax.set_ylabel("Administrative Time (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Administrative Time as Percentage per User")
    plt.xticks(rotation=45, ha="right")
    
    # Annotate each bar with its percentage value
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.1f}%', xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom')
    
    st.pyplot(fig)

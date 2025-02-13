import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

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

    # Convert column headers to string (dates are in the second row)
    date_headers = df.iloc[2, 1:].dropna().values  # Extract actual dates from row 3
    df_cleaned.columns = ["Name"] + list(date_headers)  # Assign corrected headers

    # Reshape data to long format
    df_melted = df_cleaned.melt(id_vars=["Name"], var_name="Date", value_name="Shift")

    # Convert Date column to proper datetime format
    df_melted["Date"] = pd.to_datetime(df_melted["Date"], errors='coerce')

    # Drop rows where shift data is missing
    df_melted = df_melted.dropna(subset=["Shift"])

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

    # Display Date Range Above Chart
    if not filtered_df.empty and filtered_df["Date"].notna().any():
        min_date = filtered_df["Date"].min().strftime("%d-%b-%Y")
        max_date = filtered_df["Date"].max().strftime("%d-%b-%Y")
        st.subheader(f"Date Range: {min_date} to {max_date}")
    else:
        st.subheader("No data available for selected shifts.")

    # Visualization - Shift Distribution
    st.subheader(f"Shift Distribution for {selected_name}")
    shift_counts = filtered_df["Shift"].value_counts()

    # Create Bar Chart
    fig, ax = plt.subplots()
    shift_counts.plot(kind="bar", ax=ax, color="skyblue")
    ax.set_ylabel("Count")
    ax.set_xlabel("Shift Type")
    ax.set_title(f"Shift Distribution for {selected_name}")
    st.pyplot(fig)

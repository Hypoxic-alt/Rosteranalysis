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
    df = pd.read_excel(df, sheet_name=sheet_name)
    
    # Data Cleaning
    df_cleaned = df.iloc[1:].reset_index(drop=True)
    df_cleaned.columns = df_cleaned.iloc[0]  # First row becomes header
    df_cleaned = df_cleaned[1:].reset_index(drop=True)  # Remove duplicate header row
    df_cleaned.rename(columns={df_cleaned.columns[0]: "Name"}, inplace=True)
    df_cleaned = df_cleaned.dropna(axis=1, how='all')  # Drop empty columns
    df_cleaned = df_cleaned.dropna(axis=0, how='all')  # Drop empty rows
    
    # Reshape data
    df_melted = df_cleaned.melt(id_vars=["Name"], var_name="Date", value_name="Shift")
    df_melted["Date"] = pd.to_datetime(df_melted["Date"], errors='coerce')
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

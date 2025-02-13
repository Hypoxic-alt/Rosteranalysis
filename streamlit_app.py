import streamlit as st
import pandas as pd

# Streamlit Dashboard
st.title("Work Schedule Dashboard")

# File uploader
uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx"])

if uploaded_file:
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
    
    # Filters
    names = st.multiselect("Select Names:", df_melted["Name"].unique())
    dates = st.date_input("Select Date Range:", [])
    
    filtered_df = df_melted
    if names:
        filtered_df = filtered_df[filtered_df["Name"].isin(names)]
    if dates:
        filtered_df = filtered_df[(filtered_df["Date"] >= dates[0]) & (filtered_df["Date"] <= dates[-1])]
    
    st.dataframe(filtered_df)
    
    # Visualizations
    st.subheader("Shift Distribution")
    shift_counts = filtered_df["Shift"].value_counts()
    st.bar_chart(shift_counts)


import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import folium
from folium.plugins import MarkerCluster
import streamlit as st
from babel.numbers import format_currency
from streamlit_folium import st_folium
from folium.plugins import FastMarkerCluster


sns.set(style='whitegrid')

# Cache for creating daily orders DataFrame
@st.cache_data
def create_daily_orders_df(df):
    daily_orders_df = df.resample(rule='D', on='order_approved_at').agg({
        "order_id": "nunique",
        "payment_value": "sum"
    })
    daily_orders_df = daily_orders_df.reset_index()
    daily_orders_df.rename(columns={
        "order_id": "order_count",
        "payment_value": "revenue"
    }, inplace=True)
    return daily_orders_df

@st.cache_data
def create_sum_order_items_df(df):
    sum_order_items_df = df.groupby("product_category_name_english")['payment_value'].sum().sort_values(ascending=False).reset_index()
    return sum_order_items_df

@st.cache_data
def create_sum_order_items_by_order_id_df(df):
    sum_order_items_df = df.groupby("product_category_name_english")['order_id'].nunique().sort_values(ascending=False).reset_index()
    sum_order_items_df.rename(columns={"order_id": "total_orders"}, inplace=True)
    return sum_order_items_df

@st.cache_data
def create_bystate_df(df):
    bystate_df = df.groupby('customer_state').agg(
        customer_count=('customer_id', 'nunique'),
        seller_count=('seller_id', 'nunique')
    ).reset_index()
    bystate_df.columns = ['state', 'customer_count', 'seller_count']
    return bystate_df

@st.cache_data
def create_rfm_df(df, recent_date):
    rfm_df = df.groupby(by="customer_id", as_index=False).agg({
        "order_approved_at": "max",
        "order_id": "nunique",
        "payment_value": "sum"
    })

    rfm_df.columns = ["customer_id", "max_order_timestamp", "frequency", "monetary"]
    rfm_df["recency"] = rfm_df["max_order_timestamp"].apply(lambda x: (recent_date - x).days)
    rfm_df.drop("max_order_timestamp", axis=1, inplace=True)
    return rfm_df

# Cache for loading the dataset
@st.cache_data
def load_data():
    df = pd.read_csv("main_data.csv")
    datetime_columns = ["order_approved_at",
                        "order_delivered_customer_date",
                        "order_delivered_carrier_date",
                        "order_estimated_delivery_date"]
    df.sort_values(by="order_approved_at", inplace=True)
    for column in datetime_columns:
        df[column] = pd.to_datetime(df[column], errors='coerce')
    return df

# Load the dataset
df = load_data()

# Calculate recent_date from the full dataset (before applying the filter)
recent_date = df["order_approved_at"].max()

# Streamlit sidebar for filtering by date range
min_date = df["order_approved_at"].min()
max_date = df["order_approved_at"].max()

with st.sidebar:
    st.image("https://raw.githubusercontent.com/viragohuegah/logo/refs/heads/main/logo_shop.png")
    start_date, end_date = st.date_input(
        label='Rentang Waktu', min_value=min_date,
        max_value=max_date,
        value=[min_date, max_date]
    )

# Filter the dataset based on the selected date range
main_df = df[(df["order_approved_at"] >= str(start_date)) & 
              (df["order_approved_at"] <= str(end_date))]

# Create cached dataframes using the filtered data
daily_orders_df = create_daily_orders_df(main_df)
sum_order_items_df = create_sum_order_items_df(main_df)
sum_order_items_by_order_id_df = create_sum_order_items_by_order_id_df(main_df)
bystate_df = create_bystate_df(main_df)

# Create the RFM dataframe using the filtered data but with the recent_date based on the full dataset
rfm_df = create_rfm_df(main_df, recent_date)

#=====================================================================================================================
st.title('Welcome to QISHOP E-Commerce Dashboard! :ribbon:')
#=====================================================================================================================
# Daily Orders
st.header('Daily Orders')

col1, col2 = st.columns(2)

with col1:
    total_orders = daily_orders_df.order_count.sum()
    st.metric("Total orders", value=total_orders)
with col2:
    total_revenue = format_currency(daily_orders_df.revenue.sum(), "BRL", locale='pt_BR') 
    st.metric("Total Revenue", value=total_revenue)

fig, ax = plt.subplots(figsize=(16, 8))
ax.plot(
    daily_orders_df["order_approved_at"],
    daily_orders_df["order_count"],
    marker='o', 
    linewidth=2,
    color="#FFD700"
)
ax.tick_params(axis='y', labelsize=20)
ax.tick_params(axis='x', labelsize=15)

st.pyplot(fig)

#=========================================================================================================================================
# Product
st.header("Best and Worst Performing Product")

fig, ax = plt.subplots(nrows=1, ncols=2, figsize=(35, 20))
colors = ["#FFD700", "#F5F5DC", "#F5F5DC", "#F5F5DC", "#F5F5DC"]

# Best Performing Products
sns.barplot(x="total_orders", y="product_category_name_english", data=sum_order_items_by_order_id_df.head(5), palette=colors, ax=ax[0])
ax[0].set_ylabel(None)
ax[0].set_xlabel(None)
ax[0].set_title("Best Performing Product", loc="center", fontsize=60)
ax[0].tick_params(axis='y', labelsize=36)
ax[0].tick_params(axis='x', labelsize=36)

for i in ax[0].patches:
    ax[0].text(i.get_width() + 0.2, i.get_y() + i.get_height()/2, 
               f'{int(i.get_width())}', ha='right', va='center', fontsize=36, color='black', weight='bold')

# Worst Performing Products
sns.barplot(x="total_orders", y="product_category_name_english", data=sum_order_items_by_order_id_df.sort_values(by="total_orders", ascending=True).head(5), palette=colors, ax=ax[1])
ax[1].set_ylabel(None)
ax[1].set_xlabel(None)
ax[1].invert_xaxis()
ax[1].yaxis.set_label_position("right")
ax[1].yaxis.tick_right()
ax[1].set_title("Worst Performing Product", loc="center", fontsize=60)
ax[1].tick_params(axis='y', labelsize=36)
ax[1].tick_params(axis='x', labelsize=36)

for i in ax[1].patches:
    ax[1].text(i.get_width() - 0.2, i.get_y() + i.get_height()/2, 
               f'{int(i.get_width())}', ha='left', va='center', fontsize=36, color='black', weight='bold')

st.pyplot(fig)

#================================================================================================================================
# Adding the new pie chart for review scores
st.header("Our Ratings by Customers")

# Group by 'review_score' and sort by the count in descending order
review_score_counts = df.groupby('review_score')['order_id'].count().sort_values(ascending=False)

# Create a color palette with shades of gold
colors = ['#CFC38C', '#D9CF9F', '#E3DAB3', '#EDE5C6', '#F5F5DC']

plt.figure(figsize=(10, 8))  

plt.pie(
    review_score_counts, 
    labels=review_score_counts.index, 
    autopct='%1.1f%%',  # Show percentages
    startangle=140,  # Starting angle for the pie chart
    colors=colors,  # Use the generated shades
    textprops={'fontsize': 12, 'fontweight': 'bold'}  # Smaller font size for labels

)

# Create a legend for the frequencies with descending order of counts
plt.legend(
    labels=[f'Score {score}: {count}' for score, count in zip(review_score_counts.index, review_score_counts)],
    loc='upper right', 
    fontsize=10, # Smaller font size for the legend
)

# Display the pie chart
st.pyplot(plt)

#=================================================================================================================================
# Customer & Seller Distribution
st.header("Our Customers and Sellers")

fig, ax = plt.subplots(nrows=1, ncols=2, figsize=(30, 40))

colors = ['#FFD700' if i == 0 else '#F5F5DC' for i in range(len(bystate_df))]

sns.barplot(
    x="customer_count", 
    y="state", 
    data=bystate_df.sort_values(by="customer_count", ascending=False),
    palette=colors, 
    ax=ax[0]
)
ax[0].set_ylabel(None)
ax[0].set_xlabel(None)
ax[0].set_title("States with Most Customers", loc="center", fontsize=42)
ax[0].tick_params(axis='y', labelsize=20)
ax[0].tick_params(axis='x', labelsize=20)

for i in ax[0].patches:
    ax[0].text(i.get_width() + 0.2, i.get_y() + i.get_height()/2, 
               f'{int(i.get_width())}', ha='left', va='center', fontsize=25, color='black', weight='bold')

sns.barplot(
    x="seller_count", 
    y="state", 
    data=bystate_df.sort_values(by="seller_count", ascending=False),
    palette=colors, 
    ax=ax[1]
)
ax[1].set_ylabel(None)
ax[1].set_xlabel(None)
ax[1].invert_xaxis()
ax[1].yaxis.set_label_position("right")
ax[1].yaxis.tick_right()
ax[1].set_title("States with Most Sellers", loc="center", fontsize=42)
ax[1].tick_params(axis='y', labelsize=20)
ax[1].tick_params(axis='x', labelsize=20)

for i in ax[1].patches:
    ax[1].text(i.get_width() - 0.2, i.get_y() + i.get_height()/2, 
               f'{int(i.get_width())}', ha='right', va='center', fontsize=25, color='black', weight='bold')

st.pyplot(fig)

#====================================================================================================================

# Streamlit subheader for RFM metrics
st.header("Best Customer Based on RFM Parameters")

# Displaying the RFM summary metrics
col1, col2, col3 = st.columns(3)

with col1:
    avg_recency = round(rfm_df.recency.mean(), 1)
    st.metric("Average Recency (days)", value=avg_recency)

with col2:
    avg_frequency = round(rfm_df.frequency.mean(), 2)
    st.metric("Average Frequency", value=avg_frequency)

with col3:
    # Formatting for Brazilian Real (BRL)
    avg_monetary = format_currency(rfm_df.monetary.mean(), "BRL", locale='pt_BR')
    st.metric("Average Monetary", value=avg_monetary)

# Create a shortened version of customer_id for plotting
rfm_df['short_customer_id'] = rfm_df['customer_id'].apply(lambda x: x[:8])  # Display first 8 characters

# Plotting with shortened customer_id and previous color scheme
fig, ax = plt.subplots(nrows=1, ncols=3, figsize=(20, 6))  # Smaller figsize for better alignment

# Color palette for the bars (consistent gold/yellow)
colors = ['#D4AF37'] * 5  # Uniform gold color

# Plot for Recency
sns.barplot(y="recency", x="short_customer_id", 
            data=rfm_df.sort_values(by="recency", ascending=True).head(5), 
            palette=colors, ax=ax[0])
ax[0].set_ylabel(None)
ax[0].set_xlabel(None)
ax[0].set_title("By Recency (days)", loc="center", fontsize=20)
ax[0].tick_params(axis='x', labelsize=14)

# Plot for Frequency
sns.barplot(y="frequency", x="short_customer_id", 
            data=rfm_df.sort_values(by="frequency", ascending=False).head(5), 
            palette=colors, ax=ax[1])
ax[1].set_ylabel(None)
ax[1].set_xlabel(None)
ax[1].set_title("By Frequency", loc="center", fontsize=20)
ax[1].tick_params(axis='x', labelsize=14)

# Plot for Monetary
sns.barplot(y="monetary", x="short_customer_id", 
            data=rfm_df.sort_values(by="monetary", ascending=False).head(5), 
            palette=colors, ax=ax[2])
ax[2].set_ylabel(None)
ax[2].set_xlabel(None)
ax[2].set_title("By Monetary", loc="center", fontsize=20)
ax[2].tick_params(axis='x', labelsize=14)

for axis in ax:
    axis.tick_params(axis='x', rotation=45)

# Display the plot in Streamlit
st.pyplot(fig)

#=====================================================================================================================
# 
# Menghapus duplikasi berdasarkan 'seller_id'
unique_sellers_df = df.drop_duplicates(subset='seller_id')
unique_customers_df = df.drop_duplicates(subset='customer_id')

# Check if the required columns exist in the DataFrame
if 'geolocation_lat_customer' not in df.columns or 'geolocation_lng_customer' not in df.columns:
    st.error("Missing customer geolocation data.")
if 'geolocation_lat_seller' not in df.columns or 'geolocation_lng_seller' not in df.columns:
    st.error("Missing seller geolocation data.")

# Tentukan lokasi rata-rata pelanggan untuk peta
map_center_customer = [
    unique_customers_df['geolocation_lat_customer'].mean(), 
    unique_customers_df['geolocation_lng_customer'].mean()
]

# Tentukan lokasi rata-rata penjual untuk peta
map_center_seller = [
    unique_sellers_df['geolocation_lat_seller'].mean(), 
    unique_sellers_df['geolocation_lng_seller'].mean()
]

# Prepare customer location data (lat, lng)
customer_locations = [
    [lat, lng] for lat, lng in zip(unique_customers_df['geolocation_lat_customer'], 
                                   unique_customers_df['geolocation_lng_customer'])
]

mymap_customer = folium.Map(
    location=map_center_customer, 
    zoom_start=6, 
)

# Use FastMarkerCluster for customer locations
FastMarkerCluster(data=customer_locations).add_to(mymap_customer)

# Prepare seller location data (lat, lng)
seller_locations = [
    [lat, lng] for lat, lng in zip(unique_sellers_df['geolocation_lat_seller'], 
                                   unique_sellers_df['geolocation_lng_seller'])
]

mymap_seller = folium.Map(
    location=map_center_seller, 
    zoom_start=6, 
)

# Use FastMarkerCluster for seller locations
FastMarkerCluster(data=seller_locations).add_to(mymap_seller)

# Display the maps in Streamlit
st.header("Customer and Seller Geolocation Distribution")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Distribution of Customers")
    st_folium(mymap_customer, width=700, height=400)
    st.caption('Copyright (c) Viragohuegah 2024')

with col2:
    st.subheader("Distribution of Sellers")
    st_folium(mymap_seller, width=700, height=400)

if __name__ == "__main__":
    pass

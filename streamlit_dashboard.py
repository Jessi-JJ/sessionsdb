import streamlit as st
import pymongo
from pymongo import MongoClient
import pandas as pd
import plotly.express as px
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Ecommerce Sessions Dashboard",
    page_icon="📊",
    layout="wide"
)

# Connection to Azure Cosmos DB
@st.cache_resource
def get_database():
    """Connect to Azure Cosmos DB for MongoDB"""
    # Get connection string from Streamlit secrets or environment variable
    connection_string = st.secrets["cosmos_db"]["connection_string"]
    
    # Alternative: Use environment variable
    # import os
    # connection_string = os.getenv("COSMOS_CONNECTION_STRING")
    
    client = MongoClient(connection_string)
    return client['ecommerce']

# Load data from database
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_sessions():
    """Load all sessions from database"""
    db = get_database()
    sessions = list(db.sessions.find())
    return pd.DataFrame(sessions)

# Dashboard Header
st.title("🛒 Ecommerce Session Analytics Dashboard")
st.markdown("---")

# Load data
try:
    df = load_sessions()
    
    # Convert datetime strings to datetime objects
    df['startTime'] = pd.to_datetime(df['startTime'])
    df['lastActivity'] = pd.to_datetime(df['lastActivity'])
    
    # Extract nested fields for easier analysis
    df['device'] = df['deviceInfo'].apply(lambda x: x.get('device', 'Unknown'))
    df['browser'] = df['deviceInfo'].apply(lambda x: x.get('browser', 'Unknown'))
    df['source'] = df['sessionMetadata'].apply(lambda x: x.get('source', 'Unknown'))
    df['sales'] = df['sessionMetadata'].apply(lambda x: x.get('sales', 0))
    df['pageViews'] = df['sessionMetadata'].apply(lambda x: x.get('pageViews', 0))
    df['duration'] = df['sessionMetadata'].apply(lambda x: x.get('duration', 0))
    df['session_type'] = df['sessionTags'].apply(lambda x: x.get('type', 'Unknown'))
    df['segment'] = df['sessionTags'].apply(lambda x: x.get('segment', 'Unknown'))
    df['category'] = df['sessionTags'].apply(lambda x: x.get('category', 'Unknown'))
    


    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Date range filter
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(df['startTime'].min().date(), df['startTime'].max().date())
    )

    # Device filter
    devices = st.sidebar.multiselect(
        "Device Type",
        options=df['device'].unique(),
        default=df['device'].unique()
    )
    
    # Session type filter
    session_types = st.sidebar.multiselect(
        "Session Type",
        options=df['session_type'].unique(),
        default=df['session_type'].unique()
    )

    # Apply filters
    filtered_df = df[
        (df['startTime'].dt.date >= date_range[0]) &
        (df['startTime'].dt.date <= date_range[1]) &
        (df['device'].isin(devices)) &
        (df['session_type'].isin(session_types))
    ]
    

    # Download button
    st.sidebar.markdown('---')
    csv = filtered_df.to_csv(index=False)
    st.sidebar.download_button(
        label="Download Filtered Data as CSV",
        data=csv,
        file_name="session_data.csv",
        mime="text/csv"
    ) 
    
    # Key Metrics Row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Sessions", len(filtered_df))
    
    with col2:
        total_sales = filtered_df['sales'].sum()
        st.metric("Total Sales", f"${total_sales:,.2f}")
    
    with col3:
        avg_duration = filtered_df['duration'].mean() / 60  # Convert to minutes
        st.metric("Avg Duration", f"{avg_duration:.1f} min")
    
    with col4:
        conversion_rate = (filtered_df['session_type'] == 'converted').sum() / len(filtered_df) * 100
        st.metric("Conversion Rate", f"{conversion_rate:.1f}%")
    
    with col5:
        avg_pages = filtered_df['pageViews'].mean()
        st.metric("Avg Page Views", f"{avg_pages:.1f}")
    
    st.markdown("---")
    
    # Charts Row 1
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Sessions by Device")
        device_counts = filtered_df['device'].value_counts()
        fig1 = px.pie(
            values=device_counts.values,
            names=device_counts.index,
            title="Device Distribution"
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        st.subheader("Session Type Distribution")
        type_counts = filtered_df['session_type'].value_counts()
        fig2 = px.bar(
            x=type_counts.index,
            y=type_counts.values,
            labels={'x': 'Session Type', 'y': 'Count'},
            title="Session Types"
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    # Charts Row 2
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Sales by Traffic Source")
        sales_by_source = filtered_df.groupby('source')['sales'].sum().sort_values(ascending=False)
        fig3 = px.bar(
            x=sales_by_source.index,
            y=sales_by_source.values,
            labels={'x': 'Source', 'y': 'Sales ($)'},
            title="Sales by Source"
        )
        st.plotly_chart(fig3, use_container_width=True)
    
    with col2:
        st.subheader("Customer Segments")
        segment_counts = filtered_df['segment'].value_counts()
        fig4 = px.pie(
            values=segment_counts.values,
            names=segment_counts.index,
            title="Customer Segments"
        )
        st.plotly_chart(fig4, use_container_width=True)
    
    # Time Series Chart
    st.subheader("Sessions Over Time")
    sessions_by_date = filtered_df.groupby(filtered_df['startTime'].dt.date).size()
    fig5 = px.line(
        x=sessions_by_date.index,
        y=sessions_by_date.values,
        labels={'x': 'Date', 'y': 'Number of Sessions'},
        title="Daily Sessions"
    )
    st.plotly_chart(fig5, use_container_width=True)
    
    # Advanced Analytics Section
    st.markdown("---")
    st.subheader("Advanced Analytics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Cart Abandonment Rate",
            f"{(filtered_df['session_type'] == 'cart_abandoned').sum() / len(filtered_df) * 100:.1f}%"
        )
    
    with col2:
        avg_sales_per_session = filtered_df['sales'].mean()
        st.metric("Avg Sales/Session", f"${avg_sales_per_session:.2f}")
    
    with col3:
        bounce_rate = (filtered_df['session_type'] == 'bounced').sum() / len(filtered_df) * 100
        st.metric("Bounce Rate", f"{bounce_rate:.1f}%")
    
    # Sales by Category
    st.subheader("Sales by Product Category")
    sales_by_category = filtered_df.groupby('category')['sales'].sum().sort_values(ascending=False)
    fig6 = px.bar(
        x=sales_by_category.index,
        y=sales_by_category.values,
        labels={'x': 'Category', 'y': 'Sales ($)'},
        title="Top Categories by Sales"
    )
    st.plotly_chart(fig6, use_container_width=True)
    

except Exception as e:
    st.error(f"Error connecting to database: {str(e)}")
    st.info("Please ensure your connection string is configured in .streamlit/secrets.toml")
    st.code("""
# Add this to .streamlit/secrets.toml:
[cosmos_db]
connection_string = "your-cosmos-db-connection-string"
    """)

# Footer
st.markdown("---")
st.markdown("**Dashboard powered by Streamlit + Azure Cosmos DB**")
st.markdown("App created by Jessi Jaramillo with help from Claude AI (Anthropic, 2025)")

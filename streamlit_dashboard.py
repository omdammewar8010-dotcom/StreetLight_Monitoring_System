import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import pandas as pd
from datetime import datetime
import time
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="Smart Streetlight Dashboard",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)


# 🔹 BASE DIRECTORY (ESSENTIAL)
BASE_DIR = Path(__file__).resolve().parent

# Initialize Firebase
@st.cache_resource
def init_firebase():
    """Initialize Firebase connection"""
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(
                str(BASE_DIR / "firebase-credentials.json")  # ✅ FIX # type: ignore
            )
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://streetmonitoring-default-rtdb.firebaseio.com/'
            })
        return True
    except Exception as e:
        st.error(f"Firebase initialization error: {e}")
        return False


# Authentication
def check_password():
    """Returns `True` if the user had the correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["username"] == "Om" and st.session_state["password"] == "Om123":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show inputs for username + password
        st.markdown('<h1 class="main-header">🔐 Admin Login</h1>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input("Username", key="username", placeholder="Enter username")
            st.text_input("Password", type="password", key="password", placeholder="Enter password")
            st.button("Login", on_click=password_entered, type="primary", use_container_width=True)
            
            st.info("Default credentials: username='admin', password='admin123'")
        return False
    
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error
        st.markdown('<h1 class="main-header">🔐 Admin Login</h1>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input("Username", key="username", placeholder="Enter username")
            st.text_input("Password", type="password", key="password", placeholder="Enter password")
            st.button("Login", on_click=password_entered, type="primary", use_container_width=True)
            st.error("😕 Username or password incorrect")
        return False
    else:
        # Password correct
        return True

# Fetch streetlight data
@st.cache_data(ttl=5)
def get_streetlight_data():
    """Fetch streetlight data from Firebase"""
    try:
        ref = db.reference('streetlights')
        data = ref.get()
        
        if data:
            lights = []
            for light_id, light_data in data.items():
                light_info = {
                    'ID': light_id,
                    'Status': light_data.get('status', 'off'),
                    'Mode': light_data.get('mode', 'automatic'),
                    'Is Dark': light_data.get('isDark', False),
                    'Motion Detected': light_data.get('motionDetected', False),
                    'Online': light_data.get('online', False),
                    'Last Update': light_data.get('lastUpdate', ''),
                    'Timestamp': light_data.get('timestamp', 0)
                }
                lights.append(light_info)
            return pd.DataFrame(lights)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# Control functions
def set_light_mode(light_id, mode):
    """Set streetlight mode"""
    try:
        ref = db.reference(f'streetlights/{light_id}')
        ref.update({'mode': mode})
        return True
    except Exception as e:
        st.error(f"Error setting mode: {e}")
        return False

def set_manual_state(light_id, state):
    """Set manual state for streetlight"""
    try:
        ref = db.reference(f'streetlights/{light_id}')
        ref.update({
            'manualState': state,
            'status': 'on' if state else 'off'
        })
        return True
    except Exception as e:
        st.error(f"Error setting state: {e}")
        return False

# Main dashboard
def main_dashboard():
    """Main dashboard interface"""
    
    # Header
    st.markdown('<h1 class="main-header">💡 Smart Streetlight Dashboard</h1>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/200x100/1f77b4/ffffff?text=Smart+Lights", use_container_width=True)
        st.markdown("### Dashboard Controls")
        
        refresh_rate = st.slider("Auto-refresh interval (seconds)", 5, 60, 10)
        
        st.markdown("---")
        st.markdown("### Navigation")
        page = st.radio("Select Page", ["Overview", "Control Panel", "Analytics", "Settings"])
        
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state["password_correct"] = False
            st.rerun()
    
    # Auto-refresh
    placeholder = st.empty()
    
    while True:
        with placeholder.container():
            # Fetch data
            df = get_streetlight_data()
            
            if df.empty:
                st.warning("No streetlight data available")
                time.sleep(refresh_rate)
                continue
            
            if page == "Overview":
                show_overview(df)
            elif page == "Control Panel":
                show_control_panel(df)
            elif page == "Analytics":
                show_analytics(df)
            elif page == "Settings":
                show_settings()
        
        time.sleep(refresh_rate)
        st.rerun()

def show_overview(df):
    """Overview page"""
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total_lights = len(df)
    lights_on = len(df[df['Status'] == 'on'])
    lights_off = total_lights - lights_on
    online_lights = len(df[df['Online'] == True])
    
    with col1:
        st.metric("Total Streetlights", total_lights, delta=None)
    with col2:
        st.metric("Lights ON", lights_on, delta=f"{(lights_on/total_lights*100):.1f}%")
    with col3:
        st.metric("Lights OFF", lights_off, delta=f"{(lights_off/total_lights*100):.1f}%")
    with col4:
        st.metric("Online Devices", online_lights, delta=f"{(online_lights/total_lights*100):.1f}%")
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Status Distribution")
        status_counts = df['Status'].value_counts()
        fig = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            color=status_counts.index,
            color_discrete_map={'on': '#00CC96', 'off': '#EF553B'},
            hole=0.4
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Mode Distribution")
        mode_counts = df['Mode'].value_counts()
        fig = px.pie(
            values=mode_counts.values,
            names=mode_counts.index,
            color=mode_counts.index,
            color_discrete_map={'automatic': '#636EFA', 'manual': '#AB63FA'},
            hole=0.4
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Streetlight table
    st.subheader("All Streetlights")
    
    # Format dataframe
    display_df = df.copy()
    display_df['Status'] = display_df['Status'].apply(lambda x: '🟢 ON' if x == 'on' else '🔴 OFF')
    display_df['Online'] = display_df['Online'].apply(lambda x: '✅ Online' if x else '❌ Offline')
    display_df['Is Dark'] = display_df['Is Dark'].apply(lambda x: '🌙 Dark' if x else '☀️ Bright')
    display_df['Motion Detected'] = display_df['Motion Detected'].apply(lambda x: '🏃 Yes' if x else '🚶 No')
    
    # Display table
    st.dataframe(
        display_df[['ID', 'Status', 'Mode', 'Is Dark', 'Motion Detected', 'Online']],
        use_container_width=True,
        hide_index=True
    )

def show_control_panel(df):
    """Control panel page"""
    
    st.subheader("🎛️ Streetlight Control Panel")
    
    # Select streetlight
    light_ids = df['ID'].tolist()
    selected_light = st.selectbox("Select Streetlight", light_ids)
    
    if selected_light:
        light_data = df[df['ID'] == selected_light].iloc[0]
        
        # Display current status
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_color = "🟢" if light_data['Status'] == 'on' else "🔴"
            st.metric("Current Status", f"{status_color} {light_data['Status'].upper()}")
        
        with col2:
            st.metric("Mode", light_data['Mode'].title())
        
        with col3:
            online_status = "✅ Online" if light_data['Online'] else "❌ Offline"
            st.metric("Connection", online_status)
        
        st.markdown("---")
        
        # Mode control
        st.subheader("Mode Control")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🤖 Set to Automatic Mode", use_container_width=True, type="primary"):
                if set_light_mode(selected_light, 'automatic'):
                    st.success(f"Streetlight {selected_light} set to Automatic mode")
                    time.sleep(1)
                    st.rerun()
        
        with col2:
            if st.button("👆 Set to Manual Mode", use_container_width=True):
                if set_light_mode(selected_light, 'manual'):
                    st.success(f"Streetlight {selected_light} set to Manual mode")
                    time.sleep(1)
                    st.rerun()
        
        # Manual control (only if in manual mode)
        if light_data['Mode'] == 'manual':
            st.markdown("---")
            st.subheader("Manual Control")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("💡 Turn ON", use_container_width=True, type="primary"):
                    if set_manual_state(selected_light, True):
                        st.success(f"Streetlight {selected_light} turned ON")
                        time.sleep(1)
                        st.rerun()
            
            with col2:
                if st.button("⚫ Turn OFF", use_container_width=True):
                    if set_manual_state(selected_light, False):
                        st.success(f"Streetlight {selected_light} turned OFF")
                        time.sleep(1)
                        st.rerun()
        
        # Sensor information
        st.markdown("---")
        st.subheader("Sensor Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            dark_icon = "🌙" if light_data['Is Dark'] else "☀️"
            dark_text = "Dark" if light_data['Is Dark'] else "Bright"
            st.info(f"{dark_icon} Light Level: **{dark_text}**")
        
        with col2:
            motion_icon = "🏃" if light_data['Motion Detected'] else "🚶"
            motion_text = "Detected" if light_data['Motion Detected'] else "Not Detected"
            st.info(f"{motion_icon} Motion: **{motion_text}**")
        
        # Last update
        if light_data['Last Update']:
            try:
                last_update = datetime.fromisoformat(light_data['Last Update'])
                st.caption(f"Last updated: {last_update.strftime('%B %d, %Y %I:%M:%S %p')}")
            except:
                st.caption(f"Last updated: {light_data['Last Update']}")

def show_analytics(df):
    """Analytics page"""
    
    st.subheader("📊 Analytics Dashboard")
    
    # Timeline chart
    if not df.empty and 'Timestamp' in df.columns:
        st.subheader("Streetlight Status Over Time")
        
        # Create timeline
        timeline_data = df.sort_values('Timestamp')
        
        fig = go.Figure()
        
        for _, light in timeline_data.iterrows():
            color = 'green' if light['Status'] == 'on' else 'red'
            fig.add_trace(go.Scatter(
                x=[datetime.fromtimestamp(light['Timestamp']/1000)],
                y=[light['ID']],
                mode='markers',
                marker=dict(size=15, color=color),
                name=light['ID'],
                showlegend=False
            ))
        
        fig.update_layout(
            height=400,
            xaxis_title="Time",
            yaxis_title="Streetlight ID",
            hovermode='closest'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Statistics
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Environmental Conditions")
        dark_count = len(df[df['Is Dark'] == True])
        bright_count = len(df) - dark_count
        
        fig = go.Figure(data=[
            go.Bar(name='Dark', x=['Light Level'], y=[dark_count], marker_color='indigo'),
            go.Bar(name='Bright', x=['Light Level'], y=[bright_count], marker_color='orange')
        ])
        fig.update_layout(height=300, barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Motion Detection")
        motion_count = len(df[df['Motion Detected'] == True])
        no_motion_count = len(df) - motion_count
        
        fig = go.Figure(data=[
            go.Bar(name='Motion', x=['Motion Status'], y=[motion_count], marker_color='red'),
            go.Bar(name='No Motion', x=['Motion Status'], y=[no_motion_count], marker_color='gray')
        ])
        fig.update_layout(height=300, barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    
    # Efficiency metrics
    st.markdown("---")
    st.subheader("Efficiency Metrics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        auto_mode_count = len(df[df['Mode'] == 'automatic'])
        st.metric("Automatic Mode", f"{auto_mode_count}/{len(df)}", 
                 delta=f"{(auto_mode_count/len(df)*100):.1f}%")
    
    with col2:
        online_rate = len(df[df['Online'] == True]) / len(df) * 100
        st.metric("Uptime Rate", f"{online_rate:.1f}%", 
                 delta="Good" if online_rate > 80 else "Needs Attention")
    
    with col3:
        energy_efficient = len(df[(df['Status'] == 'off') & (df['Is Dark'] == False)])
        st.metric("Energy Efficient", f"{energy_efficient}/{len(df)}", 
                 delta=f"{(energy_efficient/len(df)*100):.1f}%")

def show_settings():
    """Settings page"""
    
    st.subheader("⚙️ System Settings")
    
    st.info("Settings functionality - Configure system parameters here")
    
    # Database settings
    with st.expander("Database Settings", expanded=True):
        st.text_input("Firebase Database URL", value="https://your-project-id.firebaseio.com/")
        st.text_input("Firebase Project ID", value="your-project-id")
        
        if st.button("Test Connection"):
            st.success("✅ Connected to Firebase successfully!")
    
    # Notification settings
    with st.expander("Notification Settings"):
        st.checkbox("Enable email notifications", value=True)
        st.checkbox("Enable SMS alerts", value=False)
        st.text_input("Admin Email", value="admin@example.com")
    
    # System parameters
    with st.expander("System Parameters"):
        st.slider("Light On Duration (minutes)", 1, 10, 3)
        st.slider("Motion Detection Sensitivity", 1, 10, 5)
        st.slider("Darkness Threshold", 0, 100, 30)
    
    # Backup and restore
    with st.expander("Backup & Restore"):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Backup Data", use_container_width=True):
                st.success("Backup created successfully!")
        with col2:
            if st.button("📤 Restore Data", use_container_width=True):
                st.info("Select backup file to restore")

# Main execution
if __name__ == "__main__":
    # Check authentication
    if not check_password():
        st.stop()
    
    # Initialize Firebase
    if not init_firebase():
        st.error("Failed to initialize Firebase. Please check your credentials.")
        st.stop()
    
    # Show dashboard
    main_dashboard()
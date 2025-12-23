import streamlit as st
import pandas as pd
import folium
import requests
from streamlit_folium import st_folium
from math import radians, cos, sin, asin, sqrt
from datetime import datetime

# --- HELPER FUNCTIONS ---
def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 2 * asin(sqrt(a)) * 3956

def get_driving_distance(c_lat, c_lon, s_lat, s_lon):
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{c_lon},{c_lat};{s_lon},{s_lat}?overview=false"
        response = requests.get(url, timeout=5)
        data = response.json()
        if data['code'] == 'Ok':
            return data['routes'][0]['distance'] * 0.000621371
        return None
    except:
        return None

st.set_page_config(page_title="CEF School Search - Tennessee", layout="wide")

# --- SESSION STATE ---
if 'active_school' not in st.session_state:
    st.session_state.active_school = None
if 'driving_data' not in st.session_state:
    st.session_state.driving_data = {}
if 'last_search_key' not in st.session_state:
    st.session_state.last_search_key = ""

st.title("CEF School Search - Tennessee")

@st.cache_data
def load_data():
    try:
        churches = pd.read_csv('TN_Churches.csv', encoding='latin1')
        schools = pd.read_csv('TN_PublicSchools.csv', encoding='latin1')
        schools.columns = schools.columns.str.strip()
        schools['Latitude'] = pd.to_numeric(schools['Latitude'], errors='coerce')
        schools['Longitude'] = pd.to_numeric(schools['Longitude'], errors='coerce')
        return churches.dropna(subset=['LATITUDE', 'LONGITUDE']), schools.dropna(subset=['Latitude', 'Longitude'])
    except Exception as e:
        st.error(f"Error loading files: {e}")
        return None, None

churches_df, schools_df = load_data()

if churches_df is not None:
    # --- SIDEBAR ---
    st.sidebar.header("Search Parameters")
    
    # 1. City Search
    city_search = st.sidebar.text_input("1a. Search City:", "")
    all_cities = sorted(churches_df['CITY'].unique().astype(str).tolist())
    filt_cities = [c for c in all_cities if city_search.lower() in c.lower()]
    
    # NEW: Default to an empty selection for the city/church
    city_options = ["--- Select a City ---"] + filt_cities
    selected_city = st.sidebar.selectbox("1b. Select City:", city_options)

    # 2. Church Search
    if selected_city != "--- Select a City ---":
        city_filt_churches = churches_df[churches_df['CITY'] == selected_city]
        church_search = st.sidebar.text_input("2. Search Church Name:", "")
        avail_churches = sorted(city_filt_churches['CONAME'].unique().tolist())
        filt_church_list = [c for c in avail_churches if church_search.lower() in c.lower()]
        church_options = ["--- Select a Church ---"] + filt_church_list
        selected_church_name = st.sidebar.selectbox("3. Select Church:", church_options)
    else:
        selected_church_name = "--- Select a Church ---"

    radius_miles = st.sidebar.slider("4. Radius (Miles):", 0.5, 20.0, 3.0, 0.5)

    # --- MAIN LAYOUT ---
    col_left, col_right = st.columns([3, 2])

    # Check if a church is actually selected
    has_selection = selected_church_name != "--- Select a Church ---"

    with col_left:
        st.subheader("Map View")
        
        if has_selection:
            # NORMAL VIEW (CHURCH SELECTED)
            church_data = churches_df[churches_df['CONAME'] == selected_church_name].iloc[0]
            c_lat, c_lon = float(church_data['LATITUDE']), float(church_data['LONGITUDE'])
            
            st.markdown(f"<h4 style='color: #0056b3; margin-top: -15px;'>📍 {selected_church_name} ({radius_miles} Mile Radius)</h4>", unsafe_allow_html=True)
            
            m = folium.Map(location=[c_lat, c_lon], zoom_start=13)
            folium.Circle([c_lat, c_lon], radius=radius_miles * 1609.34, color='red', fill=True, fill_opacity=0.05).add_to(m)
            folium.Marker([c_lat, c_lon], tooltip=selected_church_name, icon=folium.Icon(color='red', icon='cross', prefix='fa')).add_to(m)
            
            # Filter Schools
            schools_df['Air_Dist'] = schools_df.apply(lambda r: haversine(c_lon, c_lat, r['Longitude'], r['Latitude']), axis=1)
            nearby_schools = schools_df[schools_df['Air_Dist'] <= radius_miles].copy()
            
            for _, row in nearby_schools.iterrows():
                is_active = (row['School'] == st.session_state.active_school)
                folium.Marker(
                    [row['Latitude'], row['Longitude']],
                    tooltip=row['School'],
                    icon=folium.Icon(color="darkblue" if is_active else "blue", icon='graduation-cap', prefix='fa')
                ).add_to(m)
        else:
            # STATEWIDE VIEW (DEFAULT)
            st.info("👋 Welcome! Please select a City and Church in the sidebar to begin your search.")
            # Center of Tennessee
            m = folium.Map(location=[35.5175, -86.5804], zoom_start=7, scrollWheelZoom=False)

        map_output = st_folium(m, use_container_width=True, height=550)

    with col_right:
        if has_selection:
            # ... (All your existing Results logic goes here: Calculate, Export, and Dataframe)
            st.markdown(f"#### 🏫 Schools within {radius_miles} miles")
            # [Add the rest of your Result logic here as per previous versions]
        else:
            # Instructions Overlay
            st.markdown("""
            ### 🏁 Getting Started
            1. Use the **Sidebar** on the left.
            2. Search for a **City** in Tennessee.
            3. Select a **Church** from that city.
            4. Adjust your **Radius** to see nearby schools.
            
            *The map will automatically zoom to your selection and find schools within range.*
            """)
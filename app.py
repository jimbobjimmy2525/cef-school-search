import streamlit as st
import pandas as pd
import folium
import requests
from streamlit_folium import st_folium
from math import radians, cos, sin, asin, sqrt
from datetime import datetime

# --- REVISION TRACKING ---
# v1.1.0: Reverted to stable base with air/road columns and map highlighting.
APP_VERSION = "v1.1.0"

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

st.set_page_config(page_title=f"CEF School Search - {APP_VERSION}", layout="wide")

# --- BETA BANNER ---
st.warning(f"🚀 **BETA VERSION {APP_VERSION}** | This tool is in active development. Please report any discrepancies.")

# --- SESSION STATE ---
if 'active_school' not in st.session_state:
    st.session_state.active_school = None
if 'driving_data' not in st.session_state:
    st.session_state.driving_data = {}
if 'last_search_id' not in st.session_state:
    st.session_state.last_search_id = ""

st.title(f"CEF School Search - Tennessee ({APP_VERSION})")

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
    
    city_search = st.sidebar.text_input("1a. Search City:", "")
    all_cities = sorted(churches_df['CITY'].unique().astype(str).tolist())
    filt_cities = [c for c in all_cities if city_search.lower() in c.lower()]
    
    city_options = ["--- Select a City ---"] + filt_cities
    selected_city = st.sidebar.selectbox("1b. Select City:", city_options)

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

    # --- RESET LOGIC ---
    current_search_id = f"{selected_church_name}_{radius_miles}"
    if st.session_state.last_search_id != current_search_id:
        st.session_state.driving_data = {}
        st.session_state.active_school = None
        st.session_state.last_search_id = current_search_id

    # --- MAIN LAYOUT ---
    col_left, col_right = st.columns([3, 2])
    has_selection = selected_church_name != "--- Select a Church ---"

    with col_left:
        st.subheader("Map View")
        
        if has_selection:
            church_data = churches_df[churches_df['CONAME'] == selected_church_name].iloc[0]
            c_lat, c_lon = float(church_data['LATITUDE']), float(church_data['LONGITUDE'])
            
            st.markdown(f"<h4 style='color: #0056b3; margin-top: -15px;'>📍 {selected_church_name}</h4>", unsafe_allow_html=True)
            
            m = folium.Map(location=[c_lat, c_lon], zoom_start=13)
            folium.Circle([c_lat, c_lon], radius=radius_miles * 1609.34, color='red', fill=True, fill_opacity=0.05).add_to(m)
            folium.Marker([c_lat, c_lon], tooltip=selected_church_name, icon=folium.Icon(color='red', icon='cross', prefix='fa')).add_to(m)
            
            schools_df['Air_Dist'] = schools_df.apply(lambda r: haversine(c_lon, c_lat, r['Longitude'], r['Latitude']), axis=1)
            nearby_schools = schools_df[schools_df['Air_Dist'] <= radius_miles].copy()
            nearby_schools['Driving_Miles'] = nearby_schools['School'].map(st.session_state.driving_data)

            for _, row in nearby_schools.iterrows():
                is_active = (row['School'] == st.session_state.active_school)
                folium.Marker(
                    [row['Latitude'], row['Longitude']],
                    tooltip=row['School'],
                    icon=folium.Icon(color="darkblue" if is_active else "blue", icon='graduation-cap', prefix='fa'),
                    z_index_offset=1000 if is_active else 0
                ).add_to(m)
            
            st_folium(m, use_container_width=True, height=550, key="active_map")
        else:
            st.info("👋 Welcome! Use the sidebar to select a city and church.")
            m = folium.Map(location=[35.8601, -86.6602], zoom_start=7)
            tn_bounds = [[34.98, -90.31], [36.68, -81.64]]
            folium.Rectangle(bounds=tn_bounds, color="#0056b3", weight=2, fill=True, fill_opacity=0.1).add_to(m)
            m.fit_bounds(tn_bounds)
            st_folium(m, use_container_width=True, height=550, key="start_map")

    with col_right:
        if has_selection:
            st.markdown(f"#### 🏫 Schools near {selected_church_name}")
            st.write(f"Showing {len(nearby_schools)} schools within {radius_miles} miles.")
            
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if not nearby_schools.empty and not st.session_state.driving_data:
                    if st.button("🚗 Calculate Driving Miles", use_container_width=True):
                        with st.spinner('Calculating...'):
                            results = {row['School']: get_driving_distance(c_lat, c_lon, row['Latitude'], row['Longitude']) for _, row in nearby_schools.iterrows()}
                            st.session_state.driving_data = results
                        st.rerun()
                elif st.session_state.driving_data:
                    st.button("✅ Distances Calculated", disabled=True, use_container_width=True)

            with btn_col2:
                if not nearby_schools.empty:
                    clean_name = "".join([c if c.isalnum() else "_" for c in selected_church_name])
                    csv = nearby_schools.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Export School List", data=csv, file_name=f"{datetime.now().strftime('%y_%m%d')}-{clean_name}.csv", use_container_width=True)

            if not nearby_schools.empty:
                sort_col = 'Driving_Miles' if st.session_state.driving_data else 'Air_Dist'
                nearby_schools = nearby_schools.sort_values(sort_col)

                display_df = nearby_schools[['School', 'Air_Dist', 'Driving_Miles']].copy()
                display_df['Driving_Miles'] = display_df['Driving_Miles'].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "Click Calc")

                def highlight_row(row):
                    return ['background-color: #002b5c; color: white; font-weight: bold'] * len(row) if st.session_state.active_school == row.School else [''] * len(row)

                st.dataframe(
                    display_df.style.apply(highlight_row, axis=1),
                    hide_index=True, 
                    use_container_width=True, 
                    height=300,
                    column_config={
                        "Air_Dist": st.column_config.NumberColumn("Air Mi", format="%.2f"),
                        "Driving_Miles": st.column_config.TextColumn("Road Mi")
                    }
                )
                
                school_options = ["None Selected"] + sorted(nearby_schools['School'].tolist())
                current_idx = school_options.index(st.session_state.active_school) if st.session_state.active_school in school_options else 0
                selected_from_list = st.selectbox("Highlight a school:", school_options, index=current_idx)
                
                if selected_from_list != "None Selected" and selected_from_list != st.session_state.active_school:
                    st.session_state.active_school = selected_from_list
                    st.rerun()

                if st.session_state.active_school and st.session_state.active_school in nearby_schools['School'].values:
                    info = nearby_schools[nearby_schools['School'] == st.session_state.active_school].iloc[0]
                    with st.container(border=True):
                        st.write(f"**{info['School']}**")
                        st.write(f"📍 {info['Address']}, {info['City']}")
                        
                        dist_msg = f"📏 Air: {info['Air_Dist']:.2f} mi"
                        if pd.notnull(info['Driving_Miles']):
                            dist_msg += f" | 🚗 Road: {info['Driving_Miles']:.2f} mi"
                        st.write(dist_msg)
                        
                        gmaps_url = f"https://www.google.com/maps/dir/?api=1&origin={c_lat},{c_lon}&destination={info['Latitude']},{info['Longitude']}&travelmode=driving"
                        st.link_button("🌐 Open Directions in Google Maps", gmaps_url, use_container_width=True)
                        if st.button("Clear Selection", use_container_width=True):
                            st.session_state.active_school = None
                            st.rerun()
        else:
            st.markdown("### 🏁 Getting Started\n1. Select a **City**\n2. Select a **Church**\n3. View Results")
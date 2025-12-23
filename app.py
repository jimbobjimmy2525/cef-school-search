import streamlit as st
import pandas as pd
import folium
import requests
from streamlit_folium import st_folium
from math import radians, cos, sin, asin, sqrt
from datetime import datetime

# 1. Haversine for initial radius filtering
def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 2 * asin(sqrt(a)) * 3956

# 2. OSRM Road Distance Calculation
def get_driving_distance(c_lat, c_lon, s_lat, s_lon):
    try:
        # OSRM expects coordinates in Lon,Lat format
        url = f"http://router.project-osrm.org/route/v1/driving/{c_lon},{c_lat};{s_lon},{s_lat}?overview=false"
        response = requests.get(url, timeout=5)
        data = response.json()
        if data['code'] == 'Ok':
            # Distance is in meters, convert to miles (1 meter = 0.000621371 miles)
            return data['routes'][0]['distance'] * 0.000621371
        return None
    except:
        return None

st.set_page_config(page_title="CEF School Search - Tennessee", layout="wide")

if 'active_school' not in st.session_state:
    st.session_state.active_school = None

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
    city_search = st.sidebar.text_input("1a. Search City:", "")
    all_cities = sorted(churches_df['CITY'].unique().astype(str).tolist())
    filt_cities = [c for c in all_cities if city_search.lower() in c.lower()]
    city_options = ["All Tennessee Cities"] + filt_cities
    selected_city = st.sidebar.selectbox("1b. Select City:", city_options)

    city_filt_churches = churches_df if selected_city == "All Tennessee Cities" else churches_df[churches_df['CITY'] == selected_city]

    church_search = st.sidebar.text_input(f"2. Search Church Name:", "")
    avail_churches = sorted(city_filt_churches['CONAME'].unique().tolist())
    filt_church_list = [c for c in avail_churches if church_search.lower() in c.lower()]
    if not filt_church_list: filt_church_list = avail_churches

    selected_church_name = st.sidebar.selectbox(f"3. Church in {selected_city}:", filt_church_list)
    radius_miles = st.sidebar.slider("4. Radius (Miles):", 0.5, 20.0, 3.0, 0.5)

    # --- CALCULATIONS ---
    church_data = city_filt_churches[city_filt_churches['CONAME'] == selected_church_name].iloc[0]
    c_lat, c_lon = float(church_data['LATITUDE']), float(church_data['LONGITUDE'])

    # Step A: Straight-line filter (Fast)
    schools_df['Air_Dist'] = schools_df.apply(lambda r: haversine(c_lon, c_lat, r['Longitude'], r['Latitude']), axis=1)
    nearby_schools = schools_df[schools_df['Air_Dist'] <= radius_miles].copy()

    # Step B: Driving distance (External Request - only for filtered results)
    if not nearby_schools.empty:
        with st.spinner('Calculating actual road distances...'):
            nearby_schools['Driving_Miles'] = nearby_schools.apply(
                lambda r: get_driving_distance(c_lat, c_lon, r['Latitude'], r['Longitude']), axis=1
            )
        nearby_schools = nearby_schools.sort_values('Driving_Miles')

    # Safety: Reset active school if missing
    if st.session_state.active_school and st.session_state.active_school not in nearby_schools['School'].values:
        st.session_state.active_school = None

    date_prefix = datetime.now().strftime("%y_%m%d")
    clean_church_name = "".join([c if c.isalnum() else "_" for c in selected_church_name])
    dynamic_filename = f"{date_prefix}-{clean_church_name}-{radius_miles}mi.csv"

    # --- LAYOUT ---
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("Map View")
        m = folium.Map(location=[c_lat, c_lon], zoom_start=13, scrollWheelZoom=False)
        folium.Circle([c_lat, c_lon], radius=radius_miles * 1609.34, color='red', fill=True, fill_opacity=0.05).add_to(m)
        
        lat_change = radius_miles / 69.0
        lon_change = radius_miles / (69.0 * cos(radians(c_lat)))
        m.fit_bounds([[c_lat - lat_change, c_lon - lon_change], [c_lat + lat_change, c_lon + lon_change]])

        folium.Marker([c_lat, c_lon], tooltip=selected_church_name, icon=folium.Icon(color='red', icon='cross', prefix='fa')).add_to(m)

        for _, row in nearby_schools.iterrows():
            is_active = (row['School'] == st.session_state.active_school)
            icon_color = "green" if is_active else "blue"
            folium.Marker(
                [row['Latitude'], row['Longitude']],
                tooltip=row['School'],
                icon=folium.Icon(color=icon_color, icon='graduation-cap', prefix='fa'),
                z_index_offset=1000 if is_active else 1
            ).add_to(m)

        map_output = st_folium(m, use_container_width=True, height=550, key="map")
        
        if map_output and map_output.get("last_object_clicked_tooltip"):
            clicked = map_output["last_object_clicked_tooltip"]
            if clicked in nearby_schools['School'].values and clicked != st.session_state.active_school:
                st.session_state.active_school = clicked
                st.rerun()

    with col_right:
        st.subheader(f"Results ({len(nearby_schools)})")
        
        school_options = ["None Selected"] + nearby_schools['School'].tolist()
        try:
            current_idx = school_options.index(st.session_state.active_school) if st.session_state.active_school in school_options else 0
        except ValueError:
            current_idx = 0

        selected_from_list = st.selectbox("Search/Select to highlight on map:", school_options, index=current_idx)
        
        if selected_from_list != "None Selected" and selected_from_list != st.session_state.active_school:
            st.session_state.active_school = selected_from_list
            st.rerun()

        def highlight_row(row):
            return ['background-color: #d1f2eb' if st.session_state.active_school == row.School else '' for _ in row]

        if not nearby_schools.empty:
            # Table now shows Driving Distance
            display_cols = ['School', 'Driving_Miles', 'City']
            styled_df = nearby_schools[display_cols].style.apply(highlight_row, axis=1)
            st.dataframe(
                styled_df, 
                hide_index=True, 
                use_container_width=True, 
                height=300,
                column_config={"Driving_Miles": st.column_config.NumberColumn("Driving Mi", format="%.2f")}
            )
        else:
            st.write("No schools found.")
        
        if st.session_state.active_school and st.session_state.active_school in nearby_schools['School'].values:
            info = nearby_schools[nearby_schools['School'] == st.session_state.active_school].iloc[0]
            with st.container(border=True):
                st.markdown(f"#### ✅ {info['School']}")
                st.write(f"📍 **Address:** {info['Address']}, {info['City']} TN")
                st.write(f"📞 **Phone:** {info['Phone1']}")
                st.metric("Road Distance", f"{info['Driving_Miles']:.2f} miles")
                if st.button("Clear Selection"):
                    st.session_state.active_school = None
                    st.rerun()

    # Export
    csv = nearby_schools.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(label="📥 Export Results (CSV)", data=csv, file_name=dynamic_filename, mime="text/csv")
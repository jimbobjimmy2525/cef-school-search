import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from math import radians, cos, sin, asin, sqrt

# Haversine formula to calculate distance in miles
def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 2 * asin(sqrt(a)) * 3956

st.set_page_config(page_title="CEF School Search - Tennessee", layout="wide")

# Updated Title
st.title("CEF School Search - Tennessee")

@st.cache_data
def load_data():
    try:
        # Load data with latin1 encoding for Windows CSV compatibility
        churches = pd.read_csv('TN_Churches.csv', encoding='latin1')
        schools = pd.read_csv('TN_PublicSchools.csv', encoding='latin1')
        
        # Clean school column names
        schools.columns = schools.columns.str.strip()
        
        # Ensure coordinates are numeric
        schools['Latitude'] = pd.to_numeric(schools['Latitude'], errors='coerce')
        schools['Longitude'] = pd.to_numeric(schools['Longitude'], errors='coerce')
        
        return churches.dropna(subset=['LATITUDE', 'LONGITUDE']), schools.dropna(subset=['Latitude', 'Longitude'])
    except Exception as e:
        st.error(f"Error loading files: {e}")
        return None, None

churches_df, schools_df = load_data()

if churches_df is not None:
    # --- SIDEBAR SEARCH & FILTERS ---
    st.sidebar.header("Search Parameters")
    
    # 1. DYNAMIC CITY SEARCH
    city_search_term = st.sidebar.text_input("1a. Search for a City:", "")
    
    all_cities = sorted(churches_df['CITY'].unique().astype(str).tolist())
    
    # Filter city list based on user typing
    filtered_city_options = [city for city in all_cities if city_search_term.lower() in city.lower()]
    city_final_list = ["All Tennessee Cities"] + filtered_city_options
    
    if len(city_final_list) == 1 and city_search_term:
        st.sidebar.warning("No cities match that search.")
        city_final_list = ["All Tennessee Cities"] + all_cities

    selected_city = st.sidebar.selectbox("1b. Select City:", city_final_list)

    # Filter church data based on city selection
    if selected_city == "All Tennessee Cities":
        city_filtered_churches = churches_df
    else:
        city_filtered_churches = churches_df[churches_df['CITY'] == selected_city]

    # 2. Church Name Search
    church_search_term = st.sidebar.text_input(f"2. Search Church in {selected_city}:", "")
    
    available_churches = sorted(city_filtered_churches['CONAME'].unique().tolist())
    filtered_church_list = [c for c in available_churches if church_search_term.lower() in c.lower()]
    
    if not filtered_church_list:
        filtered_church_list = available_churches

    # 3. Dynamic Select Church Dropdown
    default_church = "All in One Kingdom Church"
    idx = 0
    if not church_search_term and default_church in filtered_church_list:
        idx = filtered_church_list.index(default_church)
    
    church_label = f"3. Select Church in: {selected_city}"
    selected_church_name = st.sidebar.selectbox(church_label, filtered_church_list, index=idx)
    
    # Subtitle with selected church name
    st.subheader(f"Nearby Schools for: {selected_church_name}")

    # 4. Radius Slider
    radius_miles = st.sidebar.slider("4. Set Search Radius (Miles):", 0.5, 20.0, 3.0, 0.5)

    # --- DATA CALCULATION ---
    church_data = city_filtered_churches[city_filtered_churches['CONAME'] == selected_church_name].iloc[0]
    c_lat, c_lon = float(church_data['LATITUDE']), float(church_data['LONGITUDE'])

    schools_df['Distance'] = schools_df.apply(
        lambda r: haversine(c_lon, c_lat, r['Longitude'], r['Latitude']), axis=1
    )
    
    nearby_schools = schools_df[schools_df['Distance'] <= radius_miles].sort_values('Distance')

    # --- LAYOUT: MAP & LIST ---
    col_map, col_details = st.columns([2, 1])

    with col_map:
        m = folium.Map(location=[c_lat, c_lon], zoom_start=13)
        
        # Radius Circle
        folium.Circle(
            [c_lat, c_lon], 
            radius=radius_miles * 1609.34, 
            color='red', 
            fill=True, 
            fill_opacity=0.05
        ).add_to(m)

        # Smart Map Resizing (Fit Bounds)
        lat_change = radius_miles / 69.0
        lon_change = radius_miles / (69.0 * cos(radians(c_lat)))
        m.fit_bounds([[c_lat - lat_change, c_lon - lon_change], [c_lat + lat_change, c_lon + lon_change]])

        # Markers
        folium.Marker(
            [c_lat, c_lon], 
            tooltip="CHURCH: " + selected_church_name, 
            icon=folium.Icon(color='red', icon='cross', prefix='fa')
        ).add_to(m)

        for _, row in nearby_schools.iterrows():
            folium.Marker(
                [row['Latitude'], row['Longitude']],
                tooltip=row['School'],
                icon=folium.Icon(color='blue', icon='graduation-cap', prefix='fa')
            ).add_to(m)

        map_output = st_folium(m, width=800, height=600, key="map")

    with col_details:
        st.write(f"### Found {len(nearby_schools)} Schools")
        
        st.dataframe(
            nearby_schools[['School', 'Distance', 'City']],
            column_config={"Distance": st.column_config.NumberColumn("Miles", format="%.2f")},
            hide_index=True,
            use_container_width=True
        )
        
        st.divider()
        # School Details Metrics Card
        if map_output and map_output.get("last_object_clicked_tooltip"):
            school_name = map_output["last_object_clicked_tooltip"]
            if school_name in nearby_schools['School'].values:
                info = nearby_schools[nearby_schools['School'] == school_name].iloc[0]
                
                with st.container(border=True):
                    st.markdown(f"### {info['School']}")
                    st.write(f"📍 **Address:** {info['Address']}")
                    st.write(f"🏙️ **City/State:** {info['City']}, {info['State']}")
                    st.write(f"📮 **Zip Code:** {info['Zipcode']}")
                    st.write(f"📞 **Phone:** {info['Phone1']}")
                    st.metric("Proximity", f"{info['Distance']:.2f} miles")
            else:
                st.info("Click a blue marker to see details.")
        else:
            st.info("Click a blue marker to see details.")

    # Sidebar Export
    csv = nearby_schools.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button("Export Results to CSV", csv, "cef_results.csv", "text/csv")

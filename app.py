# ... (Calculations and Map View code above remains the same)

    with col_right:
        # NEW: Dynamic and Informative Header
        st.markdown(f"#### 🏫 Schools within {radius_miles} miles of {selected_church_name} ({len(nearby_schools)})")
        
        if not nearby_schools.empty and not st.session_state.driving_data:
            if st.button("🚗 Calculate Driving Miles (OSRM)", use_container_width=True):
                with st.spinner('Requesting road routes...'):
                    results = {}
                    for _, row in nearby_schools.iterrows():
                        dist = get_driving_distance(c_lat, c_lon, row['Latitude'], row['Longitude'])
                        results[row['School']] = dist
                    st.session_state.driving_data = results
                st.rerun()

# ... (Rest of the list, details card, and export code remains the same)
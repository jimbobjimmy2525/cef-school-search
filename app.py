# ... (Calculations and Map View code above remain the same)

    with col_right:
        st.markdown(f"#### 🏫 Schools within {radius_miles} miles of {selected_church_name} ({len(nearby_schools)})")
        
        # Grouped Action Buttons
        btn_col1, btn_col2 = st.columns(2)
        
        with btn_col1:
            if not nearby_schools.empty and not st.session_state.driving_data:
                if st.button("🚗 Calculate Driving Miles", use_container_width=True):
                    with st.spinner('Requesting road routes...'):
                        results = {}
                        for _, row in nearby_schools.iterrows():
                            dist = get_driving_distance(c_lat, c_lon, row['Latitude'], row['Longitude'])
                            results[row['School']] = dist
                        st.session_state.driving_data = results
                    st.rerun()
            elif st.session_state.driving_data:
                st.button("✅ Distances Calculated", disabled=True, use_container_width=True)

        with btn_col2:
            # Moved Export Button here with the new name
            if not nearby_schools.empty:
                csv = nearby_schools.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Export Current School List",
                    data=csv,
                    file_name=dynamic_filename,
                    mime="text/csv",
                    use_container_width=True
                )

        # ... (Rest of the list selection and details card code)
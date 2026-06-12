import streamlit as st
import sqlite3
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime

# ==========================================
# 1. DATABASE INITIALIZATION & STRUCTURE
# ==========================================
def init_db():
    conn = sqlite3.connect("warehouse_marketplace.db")
    cursor = conn.cursor()
    
    # Warehouses Table (Updated with Coordinates for Delivery-style Pin drops)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warehouses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_name TEXT,
            location TEXT,
            latitude REAL,
            longitude REAL,
            total_capacity INTEGER,
            available_capacity INTEGER,
            clear_height INTEGER,
            floor_load REAL,
            loading_mechanism TEXT,
            storage_type TEXT,
            price_per_sqft REAL,
            is_verified INTEGER DEFAULT 0
        )
    """)
    
    # Bookings Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            renter_name TEXT,
            warehouse_id INTEGER,
            requested_space INTEGER,
            start_date TEXT,
            end_date TEXT,
            status TEXT,
            FOREIGN KEY(warehouse_id) REFERENCES warehouses(id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect("warehouse_marketplace.db")

# ==========================================
# 2. APP HEADER & LAYOUT CONFIGURATION
# ==========================================
st.set_page_config(page_title="FlexiWarehouse India", layout="wide")
st.title("📦 FlexiWarehouse Prototype")
st.caption("An Andrew Ng-inspired Lean MVP for On-Demand Indian Warehousing")

tab1, tab2, tab3 = st.tabs(["🔍 Renter Portal (Demand)", "🏭 Host Portal (Supply)", "🛡️ Admin Controls"])

# ==========================================
# TAB 1: RENTER PORTAL (DEMAND)
# ==========================================
with tab1:
    st.header("Find Short-Term Warehouse Space")
    
    # Search Filters Column Layout
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        search_city = st.text_input("Enter City/Logistics Hub", placeholder="e.g., Bhiwandi, JNPT, Pune")
    with col2:
        filter_type = st.selectbox("Storage Category", ["All", "Ambient", "Cold Storage", "Pallet Racks", "Open Yard"])
    with col3:
        min_space = st.number_input("Minimum Space (Sq. Ft.)", min_value=0, value=0, step=500)
    with col4:
        min_height = st.number_input("Min Clear Height (Ft.)", min_value=0, value=0, step=5)
    with col5:
        dock_type = st.selectbox("Loading Infrastructure", ["All", "Hydraulic Dock Levelers", "Manual Dock / Ramps", "Ground Level (Forklifts)", "Ground Level (Mobile Cranes)", "Ground Level (Manual Labour Only)"])
        
    # Build dynamic SQL query based on filters
    conn = get_db_connection()
    query = "SELECT * FROM warehouses WHERE available_capacity >= ? AND clear_height >= ?"
    params = [min_space, min_height]
    
    if search_city:
        query += " AND location LIKE ?"
        params.append(f"%{search_city}%")
    if filter_type != "All":
        query += " AND storage_type = ?"
        params.append(filter_type)
    if dock_type != "All":
        query += " AND loading_mechanism = ?"
        params.append(dock_type)
        
    df_warehouses = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    if df_warehouses.empty:
        st.info("No warehouses match your exact structural or loading criteria right now.")
    else:
        # MAP VIEW OVERVIEW (Delivery App Style Exploration)
        st.subheader("🗺️ Interactive Network Map Explorer")
        
        # Center the map canvas near Mumbai/Bhiwandi hubs cluster defaults
        map_center_lat = df_warehouses['latitude'].mean() if not df_warehouses['latitude'].isnull().all() else 19.2812
        map_center_lng = df_warehouses['longitude'].mean() if not df_warehouses['longitude'].isnull().all() else 73.0482
        
        renter_map = folium.Map(location=[map_center_lat, map_center_lng], zoom_start=11, control_scale=True)
        
        # Plot existing coordinates onto Renter view canvas map
        for index, row in df_warehouses.iterrows():
            if pd.notnull(row['latitude']) and pd.notnull(row['longitude']):
                popup_content = f"""
                <b>Warehouse #{row['id']}</b><br>
                Rate: ₹{row['price_per_sqft']}/Sq.Ft<br>
                Space: {row['available_capacity']} Sq.Ft available
                """
                folium.Marker(
                    location=[row['latitude'], row['longitude']],
                    popup=folium.Popup(popup_content, max_width=250),
                    icon=folium.Icon(color="blue", icon="info-sign")
                ).add_to(renter_map)
        
        # Render the Map object to frontend
        st_folium(renter_map, width="100%", height=400, key="renter_exploration_map")
        
        st.markdown("---")
        st.subheader("Available Spaces List")
        df_warehouses['Verification Status'] = df_warehouses['is_verified'].apply(lambda x: "✅ Verified" if x == 1 else "⏳ Pending Review")
        
        for index, row in df_warehouses.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    st.markdown(f"### Warehouse #{row['id']} - {row['location']}")
                    st.markdown(f"**Coords:** `{row['latitude']:.4f}, {row['longitude']:.4f}`")
                    st.markdown(f"📐 **Clear Height:** {row['clear_height']} ft. | 🏗️ **Floor Load:** {row['floor_load']} T/m²")
                    st.markdown(f"🚛 **Unloading Setup:** `{row['loading_mechanism']}`")
                with c2:
                    st.write(f"🔹 **Type:** {row['storage_type']}")
                    st.write(f"🔹 **Available Space:** {row['available_capacity']:,} Sq. Ft. / {row['total_capacity']:,} Sq. Ft.")
                with c3:
                    st.metric(label="Price / Sq. Ft. / Month", value=f"₹{row['price_per_sqft']}")
                    
                    with st.popover("Book Space"):
                        st.write("### Request Booking Allocation")
                        renter_name = st.text_input("Your Company/Brand Name", key=f"rname_{row['id']}")
                        space_req = st.number_input("Space Required (Sq. Ft.)", min_value=1, max_value=int(row['available_capacity']), value=int(min(500, row['available_capacity'])), key=f"space_{row['id']}")
                        s_date = st.date_input("Start Date", min_value=datetime.today(), key=f"sdate_{row['id']}")
                        e_date = st.date_input("End Date", min_value=datetime.today(), key=f"edate_{row['id']}")
                        
                        if st.button("Submit Booking Request", key=f"btn_{row['id']}", type="primary"):
                            if renter_name:
                                conn = get_db_connection()
                                cursor = conn.cursor()
                                cursor.execute("""
                                    INSERT INTO bookings (renter_name, warehouse_id, requested_space, start_date, end_date, status)
                                    VALUES (?, ?, ?, ?, ?, 'Pending Review')
                                """, (renter_name, int(row['id']), int(space_req), str(s_date), str(e_date)))
                                conn.commit()
                                conn.close()
                                st.success("🎉 Request submitted successfully!")
                            else:
                                st.error("Please enter your company name.")

# ==========================================
# TAB 2: HOST PORTAL (SUPPLY)
# ==========================================
with tab2:
    st.header("List Your Empty Warehouse Capacity")
    st.write("Provide explicit structural dimensions, inbound bay setups, and drop a location pin.")
    
    # DELIVERY APP STYLE LOCATION PICKER INSTANTIATION
    st.markdown("### 📍 Drop Location Pin")
    st.caption("Click on the map precisely where your warehouse gate is located to capture geographic parameters automatically.")
    
    # Default Map centering context around Mumbai region logistics cluster zone
    m = folium.Map(location=[19.2812, 73.0482], zoom_start=10)
    
    # Catching map viewport return states
    map_data = st_folium(m, width="100%", height=350, key="host_picker_map")
    
    # Isolating latitude and longitude data values on execution
    selected_lat = None
    selected_lng = None
    
    if map_data and map_data.get("last_clicked"):
        selected_lat = map_data["last_clicked"]["lat"]
        selected_lng = map_data["last_clicked"]["lng"]
        st.success(f"📍 Location Captured: Latitude {selected_lat:.5f}, Longitude {selected_lng:.5f}")
    else:
        st.warning("⚠️ Please click a point on the map widget above to bind coordinates before clicking submit below.")
        
    with st.form("host_onboarding_form", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        with col_a:
            owner = st.text_input("Owner / Authorized Signatory Name")
            loc = st.text_input("Exact Facility Address / Logistics Hub Location")
            st_type = st.selectbox("Storage Category Profile", ["Ambient", "Cold Storage", "Pallet Racks", "Open Yard"])
            price = st.number_input("Desired Rental Rate (₹ per Sq. Ft. per Month)", min_value=1.0, step=0.5)
        with col_b:
            tot_cap = st.number_input("Total Capacity (Sq. Ft.)", min_value=100, step=1000)
            avail_cap = st.number_input("Currently Available Capacity (Sq. Ft.)", min_value=0, step=1000)
            c_height = st.number_input("Clear Height (Ft.)", min_value=10, max_value=60, value=25, step=1)
            f_load = st.number_input("Floor Load Capacity (Tons per Sq. Meter)", min_value=1.0, max_value=15.0, value=5.0, step=0.5)
            
            # Base selection dropdown
            load_mech_base = st.selectbox("Bay Loading/Unloading Setup", ["Hydraulic Dock Levelers", "Manual Dock / Ramps", "Ground Level (No Dock)"])
            
            # CONDITIONAL BLOCK
            ground_resource = "Not Applicable"
            if load_mech_base == "Ground Level (No Dock)":
                ground_resource = st.selectbox(
                    "Select On-Site Equipment Available for Ground Loading:",
                    ["Forklifts", "Mobile Cranes", "Manual Labour Only"]
                )
            
        submit_listing = st.form_submit_button("List Space on Network", type="primary")
        
        if submit_listing:
            if not selected_lat or not selected_lng:
                st.error("Submission blocked. You must drop a map marker location pin first.")
            elif owner and loc:
                if avail_cap > tot_cap:
                    st.error("Available capacity cannot be greater than total warehouse capacity.")
                else:
                    final_mechanism = load_mech_base
                    if load_mech_base == "Ground Level (No Dock)":
                        final_mechanism = f"Ground Level ({ground_resource})"
                        
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO warehouses (owner_name, location, latitude, longitude, total_capacity, available_capacity, clear_height, floor_load, loading_mechanism, storage_type, price_per_sqft)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (owner, loc, float(selected_lat), float(selected_lng), tot_cap, avail_cap, c_height, f_load, final_mechanism, st_type, price))
                    conn.commit()
                    conn.close()
                    st.success(f"✨ Warehouse listing recorded successfully with spatial pin coordinates!")
            else:
                st.error("Please fill out all identity and address fields before submitting.")

# ==========================================
# TAB 3: ADMIN CONTROLS
# ==========================================
with tab3:
    st.header("Internal Operator Management Dashboard")
    
    conn = get_db_connection()
    df_unverified = pd.read_sql_query("SELECT * FROM warehouses WHERE is_verified = 0", conn)
    df_all_bookings = pd.read_sql_query("SELECT * FROM bookings", conn)
    conn.close()
    
    st.subheader("⚠️ Pending Warehouse Verifications")
    if df_unverified.empty:
        st.success("All facilities on the network are currently vetted and fully verified!")
    else:
        for idx, row in df_unverified.iterrows():
            with st.container(border=True):
                cx, cy = st.columns([4, 1])
                with cx:
                    st.write(f"**ID:** {row['id']} | **Owner:** {row['owner_name']} | **Location:** {row['location']}")
                    st.caption(f"Spatial Tag: Lat {row['latitude']:.4f}, Lng {row['longitude']:.4f}")
                    st.caption(f"Specs: {row['storage_type']} — Height: {row['clear_height']}ft | Floor Load: {row['floor_load']}T/m² | Dock Setup: {row['loading_mechanism']}")
                with cy:
                    if st.button("Verify Listing", key=f"verify_{row['id']}", type="primary"):
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("UPDATE warehouses SET is_verified = 1 WHERE id = ?", (int(row['id']),))
                        conn.commit()
                        conn.close()
                        st.rerun()

    st.markdown("---")
    st.subheader("📋 Master Bookings Ledger")
    if df_all_bookings.empty:
        st.info("No transactions have been processed by users yet.")
    else:
        st.dataframe(df_all_bookings, use_container_width=True)
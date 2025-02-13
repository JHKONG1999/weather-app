import streamlit as st
import pandas as pd 
import requests
import json 
from datetime import date
import mysql.connector  
import io
from fpdf import FPDF

#Establish Connection to Database
def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1", 
        port=3306, 
        user="root",
        password="", 
        database="myweather"  
    )

#Function to Save Data to Database
def save_weather_data(country, city, start_date, temp, speed, common_dir):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO weather (country, city, search_date, temperature, wind_speed, wind_direction)
         VALUES (%s, %s, %s, %s, %s, %s)
    """
    values = (country, city, start_date, temp, speed, common_dir)
    cursor.execute(query, values)
    conn.commit()
    cursor.close()
    conn.close()

#Retrieve data from database
def get_weather_history():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM weather ORDER BY timestamp DESC")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data

# Delete function
def delete_weather_record(record_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM weather WHERE id = %s", (record_id,))
    conn.commit()
    cursor.close()
    conn.close()

# Update function
def update_weather_record(record_id, new_country, new_city, new_date):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE weather 
        SET country = %s, city = %s, search_date = %s
        WHERE id = %s
    """, (new_country, new_city, new_date, record_id))
    conn.commit()
    cursor.close()
    conn.close()

# Function to generate CSV file
def export_csv(data):
    df = pd.DataFrame(data)
    csv_file = df.to_csv(index=False).encode('utf-8')
    return csv_file

# Function to generate PDF file
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", style="B", size=14)
        self.cell(0, 10, "Weather History Report", ln=True, align="C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", size=10)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

def export_pdf(data):
    pdf = PDF(orientation="L")  # Set Landscape mode for more space
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", style="B", size=10)
    pdf.set_fill_color(200, 200, 200)

    # Define column widths for better layout
    col_widths = [15, 35, 35, 30, 25, 30, 35, 50] 

    # Table Headers
    headers = ["ID", "Country", "City", "Date", "Temp (°C)", "Wind (m/s)", "Wind Direction", "Timestamp"]

    #Table Data
    for i, header in enumerate(headers):  # Loop through headers
        for j in range(1):  # This enforces height consistency (10)
            pdf.cell(col_widths[i], 10, header, border=1, align="C", fill=True)  
    pdf.ln() 

    # Table Data - Using for j
    pdf.set_font("Arial", size=10)  # Regular font for data
    for row in data:
        for i, value in enumerate([
            row["id"], row["country"], row["city"], row["search_date"],
            f"{row['temperature']}°C", f"{row['wind_speed']} m/s", row["wind_direction"], row["timestamp"]
        ]):
            for j in range(1):  # Enforcing uniform height (10)
                pdf.cell(col_widths[i], 10, str(value), border=1, align="C")
        pdf.ln()

    pdf_output = io.BytesIO()
    pdf_output.write(pdf.output(dest='S').encode('latin1'))  # Convert output to BytesIO
    pdf_output.seek(0)  # Move to the beginning of the file

    return pdf_output

#Read the files
file="worldcities.csv"
data= pd.read_csv("worldcities.csv")

#Title and description
st.title('Welcome to My Weather App!')
st.write('Plan your journey with our Weather App!')

#Sidebar
st.sidebar.header('Introduction')
st.sidebar.markdown("---")
st.sidebar.write("Welcome to **My Weather App!** This app soon will be the coolest AI Product in the town!")
st.sidebar.write("No matter who you are—a business professional, a student, or an adventurer—don't let the weather hold you back! 🌤️🌍 Stay ahead of unpredictable conditions and make every moment count with your loved ones. Because great journeys begin with great planning! 🚀💙")
st.sidebar.write("")
st.sidebar.write("**User Guide:**")
st.sidebar.write("1. Pick a country")
st.sidebar.write("2. Pick a city")
st.sidebar.write("3. Pick a date")
st.sidebar.write("4. Click on the 'Search Weather' button!")
st.sidebar.write("")
st.sidebar.write("")
st.sidebar.write("")
st.sidebar.markdown("---")
st.sidebar.write("👤 Creator: ***Kong Jun Hao***")
st.sidebar.write("👤Partner with: ***Product Manager Accelerator***")
st.sidebar.write("")
st.sidebar.write("Check us on Linked-in!")
st.sidebar.write("[***Kong Jun Hao***](https://www.linkedin.com/in/kong-jun-hao-/) & [***PM Accelerator***](https://www.linkedin.com/school/pmaccelerator/about/)")
st.sidebar.write("**Data source**: [Open-meteo.com](https://open-meteo.com/)")
st.sidebar.write("**App Version 1.0**")

# Select Country & City
country_set = sorted(set(data.loc[:,"country"]))
country = st.selectbox('Select a country', options=country_set)

country_data = data.loc[data.loc[:,"country"] == country,:]

city_set = sorted(country_data.loc[:,"city_ascii"]) 

city = st.selectbox('Select a city', options=city_set)

lat = float(country_data.loc[data.loc[:,"city_ascii"] == city, "lat"])
lng = float(country_data.loc[data.loc[:,"city_ascii"] == city, "lng"])

# Create two columns for Date Selection
col1, _ = st.columns([1,1])

# Select start and end dates in separate columns
with col1:
    start_date = st.date_input("Select start date", value=date.today(), min_value=date.today())

st.write("")

# Search Button
if st.button("🔍 Search Weather"):
    if lat and lng:
        # API call
        response = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current_weather=true")

        if response.status_code == 200:
            weather_data = response.json()
            current = weather_data["current_weather"]
            temp = current["temperature"]
            speed = current["windspeed"]
            direction = current["winddirection"]

            #Calculate Wind Direction
            def get_wind_direction(direction):
                directions = [
                    "N", "N/NE", "NE", "E/NE", "E", "E/SE", "SE", "S/SE",
                    "S", "S/SW", "SW", "W/SW", "W", "W/NW", "NW", "N/NW"
                ]

            # Increment added or substracted from degree values for wind direction
                ddeg = 11.25
                index = round(direction / ddeg) % 32  # Normalize to 32 sectors
                return directions[index // 2]  # Convert 32 sectors into 16 labels

            common_dir= get_wind_direction(direction)

            #Display Whether Result
            st.subheader(f"Current weather as of   ***{start_date}***")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(label="Temperature", value=f"{temp} °C")

            with col2:
                st.metric(label="Wind Speed", value=f"{speed} m/s")

            with col3:
                st.metric(label="Wind Direction", value=f"{common_dir}")

            save_weather_data(country, city, start_date, temp, speed, common_dir)
            st.success("✅ Data stored successfully!")
            
    else:
        st.error("Failed to fetch weather data.")

else:
    st.warning("Please enter all fields.")

st.write("")
st.write("")
st.subheader("**History**")

data = get_weather_history()
if data:
    df = pd.DataFrame(data, columns=["id", "country", "city","search_date","temperature","wind_speed","wind_direction","timestamp"]) 
 
 # Export Buttons
    col1, col2, col3 = st.columns([6, 2, 2])

    with col2:
        csv_data = export_csv(data)
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name="weather_history.csv",
            mime="text/csv"
        )

    with col3:
        pdf_data = export_pdf(data)
        st.download_button(
            label="📥 Download PDF",
            data=pdf_data,
            file_name="weather_history.pdf",
            mime="application/pdf"
        )

    # Create delete buttons for each row
    for index, row in df.iterrows():
        record_id = row["id"]

        # Initialize edit mode in session state **before rendering any widget**
        if f"edit_{record_id}" not in st.session_state:
            st.session_state[f"edit_{record_id}"] = False

        # Display normal row if not in edit mode
        if not st.session_state[f"edit_{record_id}"]:
            col1, col2, col3 = st.columns([8, 1, 1])
            col1.write(f"**{row['city']} ({row['country']})** | {row['temperature']}°C | {row['wind_speed']} m/s | {row['wind_direction']} | {row['search_date']}") 
            
            # Delete button
            if col2.button("🗑️", key=f"delete_{record_id}"):
                delete_weather_record(record_id)
                st.warning(f"Deleted record {record_id}. Refreshing...")
                st.experimental_rerun()  # Refresh table instantly

            # Update Button
            if col3.button("✏️", key=f"edit_toggle_{record_id}"):
                st.session_state[f"edit_{record_id}"] = True
                st.experimental_rerun()

        # If edit mode is active, show input fields
        else:
            st.write(f"**Updating Record {record_id}**")
            new_country = st.text_input("Country", row["country"], key=f"new_country_{record_id}")
            new_city = st.text_input("City", row["city"], key=f"new_city_{record_id}")
            new_date = st.date_input("Search Date", value=pd.to_datetime(row["search_date"]), key=f"new_date_{record_id}")

            col1, col2 = st.columns(2)

            # Save changes button
            if col1.button("✅ Save", key=f"save_{record_id}"):
                update_weather_record(record_id, new_country, new_city, new_date)
                st.success(f"Updated record {record_id} successfully! Refreshing...")
                st.session_state[f"edit_{record_id}"] = False  # Exit edit mode
                st.experimental_rerun()

            # Cancel Edit Button
            if col2.button("❌ Cancel", key=f"cancel_{record_id}"):
                st.session_state[f"edit_{record_id}"] = False  # Exit edit mode
                st.experimental_rerun()

    else:
        st.write("No weather history available.")
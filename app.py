import streamlit as st
import openai
import os
import requests
import matplotlib.pyplot as plt
import numpy as np
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

st.title("🔋 AnIrgy EV Charging Advisor")

# Inputs
zip_code = st.text_input("Enter your ZIP Code", value="90210")
# Utility Provider
@st.cache_data(show_spinner=False)
def get_utilities_by_zip(zip_code):
    url = (
        f"https://api.openei.org/utility_rates?"
        f"version=latest&format=json&api_key={os.getenv('OPENEI_API_KEY')}"
        f"&zip={zip_code}"
    )
    response = requests.get(url).json()
    utilities = sorted(list({item["utility"] for item in response.get("items", [])}))
    return utilities

if zip_code:
    utilities = get_utilities_by_zip(zip_code)
    if utilities:
        utility_company = st.selectbox("Select Your Utility Provider", utilities)
    else:
        st.warning("⚠️ No utilities found for that ZIP.")
        utility_company = ""

# EV Make Dropdown
@st.cache_data(show_spinner=False)
def get_ev_makes():
    url = "https://vpic.nhtsa.dot.gov/api/vehicles/GetAllMakes?format=json"
    response = requests.get(url).json()
    makes = sorted([item["Make_Name"] for item in response["Results"]])
    return makes

make = st.selectbox("Select EV Make", get_ev_makes(), index=get_ev_makes().index("CADILLAC") if "CADILLAC" in get_ev_makes() else 0)

# EV Model Dropdown based on Make
@st.cache_data(show_spinner=False)
def get_models_for_make(make):
    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/GetModelsForMake/{make}?format=json"
    response = requests.get(url).json()
    models = sorted(list({item["Model_Name"] for item in response["Results"]}))
    return models

default_models = get_models_for_make(make)
model_default_index = default_models.index("LYRIQ") if "LYRIQ" in default_models else 0
model = st.selectbox("Select Model", default_models, index=model_default_index)

battery_kwh = st.slider("How many kWh do you need to charge?", 10, 100, 30)
charging_rate = st.number_input("Charging rate (kW)", value=11.5)
# rate_off_peak = st.number_input("Off-Peak rate ($/kWh)", value=0.15)
# rate_peak = st.number_input("Peak rate ($/kWh)", value=0.45)
# rate_mid_peak = st.number_input("Mid-Peak rate ($/kWh)", value=0.25)
weather = st.text_input("Today's weather (optional)", value="90°F and sunny")

# Vehicle Info via NHTSA
st.markdown("🚘 Vehicle Lookup via NHTSA")
nhtsa_url = f"https://vpic.nhtsa.dot.gov/api/vehicles/GetModelsForMake/{make}?format=json"
nhtsa_response = requests.get(nhtsa_url).json()

found_model = False
for item in nhtsa_response.get("Results", []):
    if model.lower() in item["Model_Name"].lower():
        st.success(f"✅ Found model: {item['Model_Name']}")
        found_model = True
        break

if not found_model:
    st.warning("⚠️ Model not found via NHTSA. Double-check spelling or try another.")

# Map using OpenStreetMap
st.markdown("🗺️ Regional Map (OpenStreetMap)")
osm_map_url = f"https://staticmap.openstreetmap.de/staticmap.php?center={zip_code}&zoom=10&size=600x300&maptype=mapnik"
st.image(osm_map_url, caption=f"Map for ZIP {zip_code}")

# Utility Rate Placeholder
st.markdown("💡 Utility Rate Lookup via OpenEI")
openei_api_key = os.getenv("OPENEI_API_KEY")

@st.cache_data(show_spinner=False)
def fetch_utility_rates(zip_code, utility_name):
    try:
        url = (
            f"https://api.openei.org/utility_rates?"
            f"version=latest&format=json&api_key={openei_api_key}"
            f"&zip={zip_code}"
        )
        response = requests.get(url).json()
        results = response.get("items", [])
        for item in results:
            if utility_name.lower() in item.get("utility", "").lower():
                return item
        return None
    except Exception as e:
        return {"error": str(e)}

rate_info = fetch_utility_rates(zip_code, utility_company)

if rate_info and "error" not in rate_info:
    st.success(f"✅ Found rate: {rate_info['name']}")
    st.write(f"📉 Flat rate: ${rate_info.get('flatdemandcharge', 'N/A')}")
    st.write(f"📅 TOU schedule: {rate_info.get('energyweekdays', 'N/A')}")
else:
    st.warning("⚠️ Could not find utility rate info for this provider.")

# --- Extract structured output from GPT response ---
def extract_start_and_duration(gpt_text):
    try:
        start_match = re.search(r"Start Time:\s*([0-2]?[0-9]:[0-5][0-9])", gpt_text)
        duration_match = re.search(r"Duration\s*\(hours\):\s*([\d\.]+)", gpt_text)

        start_time = start_match.group(1) if start_match else None
        duration = float(duration_match.group(1)) if duration_match else None

        return start_time, duration
    except Exception:
        return None, None

# Button
if st.button("Get Charging Advice") and zip_code and utility_company:
    with st.spinner("Analyzing based on real utility data..."):
        rate_str = (
            f"Rate name: {rate_info['name']}\n"
            f"Flat rate: ${rate_info.get('flatdemandcharge', 'N/A')}\n"
            f"TOU schedule: {rate_info.get('energyweekdays', 'N/A')}"
            if rate_info else "No specific rate info found"
            )

        # Prompt engineering
        prompt = f"""
        You are an expert EV charging and energy advisor.

        A user has provided the following info:
        - ZIP code: {zip_code}
        - Utility company: {utility_company}
        - EV: {make} {model}
        - EV needs to charge approximately {battery_kwh} kWh
        
        Utility Rate Info:
        {rate_str}

        Based on current TOU rates, regional grid demand patterns, and common utility programs, give the best 2-3 hour window to charge their EV for lowest cost and grid benefit.

        Be specific but concise and include:
        - A generic image of their EV
        - A regional map with pinpoint of their rough location
        - TOU rate assumptions (based on location); include estimate rates that would be closest to what the chosen utility would have
        - Time window to charge in this format:
            Start Time: HH:MM (24-hour format)
            Duration (hours): X.XX
        - Estimated cost
        
"""

    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
    )
    st.markdown("🔋Here is your certified AnIrgy Charging Recommendation")
    gpt_output = response.choices[0].message.content
    st.write(gpt_output)
    
    gpt_output = response.choices[0].message.content
    
    # --- Try to extract charging window ---
    start_time_str, duration_hrs = extract_start_and_duration(gpt_output)
    
    # --- Fallback to user input if needed ---
    if not start_time_str or not duration_hrs:
        st.warning("⚠️ GPT did not return structured output. Please enter charging time manually.")
        start_time_input = st.time_input("Charging start time", value=datetime.strptime("00:00", "%H:%M").time())
        start_time_str = start_time_input.strftime("%H:%M")
        duration_hrs = st.number_input("Charging duration (hours)", min_value=0.5, max_value=8.0, step=0.25, value=2.5)
    
    # --- Generate Charging Chart ---
    st.markdown("📈 Estimated Charging Curve")
    
    start_dt = datetime.strptime(start_time_str, "%H:%M")
    end_dt = start_dt + timedelta(hours=duration_hrs)
    
    hours = [datetime.strptime("00:00", "%H:%M") + timedelta(hours=i) for i in range(25)]
    hour_labels = [dt.strftime("%H:%M") for dt in hours]
    
    percent_per_hour = (battery_kwh / (charging_rate * duration_hrs)) * (100) / duration_hrs
    battery_percentage = []
    
    for t in hours:
        if start_dt <= t <= end_dt:
            pct = (t - start_dt).seconds / 3600 * percent_per_hour
            battery_percentage.append(min(pct, 100))
        elif t > end_dt:
            battery_percentage.append(battery_percentage[-1])
        else:
            battery_percentage.append(0)
    
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(hour_labels, battery_percentage, marker='o')
    ax.set_xticks(hour_labels[::2])
    ax.set_ylim(0, 100)
    ax.set_ylabel("Battery %")
    ax.set_xlabel("Time of Day")
    ax.set_title("🔋 Charging Curve")
    ax.grid(True)
    
    st.pyplot(fig)
    
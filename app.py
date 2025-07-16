import streamlit as st
import openai
import os
import requests
from dotenv import load_dotenv

# Load API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

st.title("🔋 AnIrgy EV Charging Advisor")

# Inputs
zip_code = st.text_input("Enter your ZIP code")
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

make = st.selectbox("Select EV Make", get_ev_makes())

# EV Model Dropdown based on Make ---
@st.cache_data(show_spinner=False)
def get_models_for_make(make):
    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/GetModelsForMake/{make}?format=json"
    response = requests.get(url).json()
    models = sorted(list({item["Model_Name"] for item in response["Results"]}))
    return models

model = st.selectbox("Select Model", get_models_for_make(make))
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

        Be specific and include:
        - A generic image of their EV
        - A regional map with pinpoint of their rough location
        - TOU rate assumptions (based on location)
        - Time window to charge
        - Estimated cost
        - Any relevant tips (e.g., solar, rebates, off-peak savings)
        - A secondary option
        - A brief explanation
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
    st.write(response.choices[0].message.content)

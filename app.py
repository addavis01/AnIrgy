import streamlit as st
import openai
import os
from dotenv import load_dotenv

# Load API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

st.title("🔋 AnIrgy EV Charging Advisor")

# Inputs
zip_code = st.text_input("Enter your ZIP code")
utility_company = st.text_input("Enter your utility company name")
ev_make_model = st.text_input("Enter your EV Make and Model")
battery_kwh = st.slider("How many kWh do you need to charge?", 10, 100, 30)
charging_rate = st.number_input("Charging rate (kW)", value=11.5)
rate_off_peak = st.number_input("Off-Peak rate ($/kWh)", value=0.15)
rate_peak = st.number_input("Peak rate ($/kWh)", value=0.45)
rate_mid_peak = st.number_input("Mid-Peak rate ($/kWh)", value=0.25)
weather = st.text_input("Today's weather (optional)", value="90°F and sunny")

# Button
if st.button("Get Charging Advice") and zip_code and utility_company:
    with st.spinner("Analyzing local energy data..."):

        # Prompt engineering
        prompt = f"""
        You are an expert EV charging and energy advisor.

        A user has provided the following info:
        - ZIP code: {zip_code}
        - Utility company: {utility_company}
        - EV needs to charge approximately {battery_kwh} kWh

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
    st.markdown("###🔋Here is your certified AnIgery Charging Recommendation")
    st.write(response.choices[0].message.content)

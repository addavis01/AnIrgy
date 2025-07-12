import streamlit as st
import openai
import os
from dotenv import load_dotenv

# Load API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

st.title("🔋 AnIrgy EV Charging Advisor")

# Inputs
energy_needed = st.number_input("Energy needed (kWh)", value=30)
charging_rate = st.number_input("Charging rate (kW)", value=11.5)
rate_off_peak = st.number_input("Off-Peak rate ($/kWh)", value=0.15)
rate_peak = st.number_input("Peak rate ($/kWh)", value=0.45)
rate_mid_peak = st.number_input("Mid-Peak rate ($/kWh)", value=0.25)
weather = st.text_input("Today's weather (optional)", value="90°F and sunny")

# Run
if st.button("Find Best Charging Window"):
    prompt = f"""
You are an expert in EV charging and cost optimization. A user has the following:

- TOU plan:
  - Peak: ${rate_peak}/kWh (4–9 PM)
  - Off-Peak: ${rate_off_peak}/kWh (12 AM–3 PM)
  - Mid-Peak: ${rate_mid_peak}/kWh (all other times)
- Charging rate: {charging_rate} kW
- Energy needed: {energy_needed} kWh
- Peak household load: 6–9 PM
- Weather: {weather}

Recommend:
- The best 2–3 hour window to charge
- Estimated cost
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

    st.write(response.choices[0].message.content)

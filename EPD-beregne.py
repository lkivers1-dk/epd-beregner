import streamlit as st
import pandas as pd

# ---------- LOAD DATA ----------
@st.cache_data
def load_data():
    df = pd.read_excel("materialedata.xlsx", header=3, engine="openpyxl")
    df.columns = df.columns.str.strip()
    return df

df = load_data()

materialer = [m for m in df["Materiale"].tolist() if m != "Transport"]

# ---------- FUNCTIONS ----------

def get_value(materiale, kolonne):
    return df[df["Materiale"] == materiale][kolonne].values[0]


def beregn_lag(tykkelse, materiale):

    result = {}

    for modul in ["A1","A2","A3","A4","C1","C2","C3","C4","D"]:
        faktor = get_value(materiale, modul)
        result[modul] = tykkelse * faktor  # kgCO2e/m2

    return result


# ---------- GUI ----------

st.title("LCA beregner")

længde = st.number_input("Længde (m)", value=1.0)
højde = st.number_input("Højde (m)", value=1.0)

t_iso = st.number_input("Tykkelse isolering (mm)", value=200)
t_for = st.number_input("Tykkelse forplade (mm)", value=70)
t_bag = st.number_input("Tykkelse bagplade (mm)", value=150)

mat_iso = st.selectbox("Isolering", materialer)
mat_for = st.selectbox("Forplade", materialer)
mat_bag = st.selectbox("Bagplade", materialer)

afstand = st.number_input("Transportafstand (km)", value=50.0)


# ---------- CALCULATION ----------

if st.button("Beregn"):

    areal = længde * højde

    res_iso = beregn_lag(t_iso/1000 , mat_iso)
    res_for = beregn_lag(t_for/1000 , mat_for)
    res_bag = beregn_lag(t_bag/1000 , mat_bag)

    moduler = ["A1","A2","A3","A4","C1","C2","C3","C4","D"]

    # ---------- MATERIAL TABLE ----------

    result_df = pd.DataFrame({

        "Materiale": [
            f"Forplade ({mat_for})",
            f"Isolering ({mat_iso})",
            f"Bagplade ({mat_bag})"
        ],

        **{
            m: [res_for[m], res_iso[m], res_bag[m]]
            for m in moduler
        }

    })

    result_df["Total"] = result_df[moduler].sum(axis=1)

    # ---------- TRANSPORT ----------

    # Hvis transport stadig skal beregnes på ton:
    # Her antager vi at transportfaktor er kgCO2e/ton/km
    # og at du manuelt kender elementets ton (ellers kræver densitet)

    transport_factor = get_value("Transport", "A4")

    # Her bruges areal * samlet tykkelse som "m3"
    samlet_tykkelse = t_iso + t_for + t_bag
    volumen = areal * samlet_tykkelse

    # Hvis Excel transportfaktor er pr m3/km:
    transport_co2 = volumen * afstand * transport_factor

    transport_pr_m2 = transport_co2 / areal

    transport_row = pd.DataFrame([{
        "Materiale": f"Transport ({afstand} km)",
        "A1": 0,
        "A2": 0,
        "A3": 0,
        "A4": transport_pr_m2,
        "C1": 0,
        "C2": 0,
        "C3": 0,
        "C4": 0,
        "D": 0,
        "Total": transport_pr_m2
    }])

    result_df = pd.concat([result_df, transport_row], ignore_index=True)

    # ---------- TOTAL ----------

    total_row = pd.DataFrame([{
        "Materiale": "TOTAL",
        **{m: result_df[m].sum() for m in moduler},
        "Total": result_df["Total"].sum()
    }])

    result_df = pd.concat([result_df, total_row], ignore_index=True)

    # ---------- DISPLAY ----------

    st.subheader("Resultat (kgCO₂e / m²)")
    st.dataframe(result_df.round(3), use_container_width=True)

# -*- coding: utf-8 -*-

# ---------- LOAD EXCEL ----------
import streamlit as st
import pandas as pd
import openpyxl
st.write("openpyxl loaded")

@st.cache_data
def load_data():
    try:
        df = pd.read_excel("materialedata.xlsx", header=3, engine="openpyxl")
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Fejl ved indlæsning af Excel: {e}")
        st.stop()

df = load_data()

materialer = df["Materiale"].tolist()

# ---------- FUNCTIONS ----------

def get_value(materiale, kolonne):
    return df[df["Materiale"] == materiale][kolonne].values[0]


def beregn_lca(volumen, materiale):

    densitet = get_value(materiale, "Densitet")
    vægt = volumen * densitet

    result = {}

    for modul in ["A1","A2","A3","A4","C1","C2","C3","C4","D"]:
        faktor = get_value(materiale, modul)
        result[modul] = vægt * faktor

    result["vægt"] = vægt

    return result


# ---------- GUI ----------

st.title("LCA beregner for sandwich element")

st.subheader("Geometri")

længde = st.number_input("Længde (m)", value=1.0)
bredde = st.number_input("Bredde (m)", value=1.0)

st.subheader("Tykkelser")

t_iso = st.number_input("Isolering (m)", value=0.2)
t_for = st.number_input("Forplade (m)", value=0.07)
t_bag = st.number_input("Bagplade (m)", value=0.07)

st.subheader("Materialer")

# fjern "Transport" fra materialevalg
materialer_valg = [m for m in materialer if m != "Transport"]

mat_iso = st.selectbox("Isolering materiale", materialer_valg)
mat_for = st.selectbox("Forplade materiale", materialer_valg)
mat_bag = st.selectbox("Bagplade materiale", materialer_valg)

st.subheader("Transport")

afstand = st.number_input("Transportafstand (km)", value=50.0)

# ---------- CALCULATION ----------

if st.button("Beregn LCA"):

    areal = længde * bredde

    vol_iso = areal * t_iso
    vol_for = areal * t_for
    vol_bag = areal * t_bag

    res_iso = beregn_lca(vol_iso, mat_iso)
    res_for = beregn_lca(vol_for, mat_for)
    res_bag = beregn_lca(vol_bag, mat_bag)

    moduler = ["A1","A2","A3","A4","C1","C2","C3","C4","D"]

    # ---------- MATERIAL TABLE (kgCO2e/m2) ----------

    result_df = pd.DataFrame({

        "Materiale": [
            f"Forplade ({mat_for})",
            f"Isolering ({mat_iso})",
            f"Bagplade ({mat_bag})"
        ],

        "A1": [res_for["A1"]/areal, res_iso["A1"]/areal, res_bag["A1"]/areal],
        "A2": [res_for["A2"]/areal, res_iso["A2"]/areal, res_bag["A2"]/areal],
        "A3": [res_for["A3"]/areal, res_iso["A3"]/areal, res_bag["A3"]/areal],
        "A4": [res_for["A4"]/areal, res_iso["A4"]/areal, res_bag["A4"]/areal],
        "C1": [res_for["C1"]/areal, res_iso["C1"]/areal, res_bag["C1"]/areal],
        "C2": [res_for["C2"]/areal, res_iso["C2"]/areal, res_bag["C2"]/areal],
        "C3": [res_for["C3"]/areal, res_iso["C3"]/areal, res_bag["C3"]/areal],
        "C4": [res_for["C4"]/areal, res_iso["C4"]/areal, res_bag["C4"]/areal],
        "D":  [res_for["D"]/areal,  res_iso["D"]/areal,  res_bag["D"]/areal]
    })

    result_df["Total"] = result_df[moduler].sum(axis=1)

    # ---------- TRANSPORT CALCULATION ----------

    total_vægt = (
        res_iso["vægt"] +
        res_for["vægt"] +
        res_bag["vægt"]
    )

    transport_factor = get_value("Transport", "A4")

    transport_co2 = total_vægt * afstand * transport_factor

    transport_pr_m2 = transport_co2 / areal

    transport_row = pd.DataFrame([{

        "Materiale": f"Transport til byggeplads ({afstand} km)",

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

    # ---------- TOTAL ROW ----------

    total_row = pd.DataFrame([{

        "Materiale": "TOTAL",

        **{m: result_df[m].sum() for m in moduler},

        "Total": result_df["Total"].sum()

    }])

    result_df = pd.concat([result_df, total_row], ignore_index=True)

    result_df = result_df.round(3)

    total_lca_pr_m2 = result_df.iloc[-1]["Total"]

    # ---------- DISPLAY ----------

    st.subheader("LCA resultat (kgCO₂e / m²)")

    st.dataframe(result_df, use_container_width=True)

    st.write(f"Areal: {areal:.2f} m²")

    st.write(f"Total vægt: {total_vægt:.1f} kg")

    st.write(f"Transportafstand: {afstand:.1f} km")

    st.write(f"Total LCA: {total_lca_pr_m2:.3f} kgCO₂e/m²")

import streamlit as st
import pandas as pd
import json
import uuid
import os

# =====================================================
# KONFIGURATION
# =====================================================

ØVRIGE_INDIKATORER = [
    "AP", "ODP", "PER", "PENR",
    "ADPF", "EP", "ADPE", "POCP"
]

GWP_MODULER = ["A1","A2","A3","C3","C4","D"]

# =====================================================
# UTILITIES
# =====================================================

def generate_id():
    return str(uuid.uuid4()).upper()


@st.cache_data
def load_data():
    base_path = os.path.dirname(__file__)
    file_path = os.path.join(base_path, "materialedata_lca.xlsx")

    df = pd.read_excel(file_path, header=3, engine="openpyxl")
    df.columns = df.columns.str.strip()

    return df


df = load_data()
forplader = df[df["Type"] == "Forplade"]["Materiale"].dropna().tolist()
isoleringer = df[df["Type"] == "Isolering"]["Materiale"].dropna().tolist()
bagplader = df[df["Type"] == "Bagplade"]["Materiale"].dropna().tolist()


# =====================================================
# DATA FUNCTIONS
# =====================================================

def get_value(materiale, kolonne):

    match = df[df["Materiale"].str.strip().str.lower()
               == materiale.strip().lower()]

    if match.empty:
        st.error(f"Materiale '{materiale}' findes ikke i Excel")
        st.stop()

    value = match[kolonne].values[0]

    try:
        return float(value)
    except:
        return 0.0


def beregn_lag(tykkelse_m, materiale):

    result = {}

    # ----------- GWP opdelt -----------
    for modul in GWP_MODULER:
        kolonne = f"{modul} - GWP"
        faktor = get_value(materiale, kolonne)

        result.setdefault(modul, {})
        result[modul]["GWP"] = tykkelse_m * faktor

    # ----------- Øvrige indikatorer -----------
    for indikator in ØVRIGE_INDIKATORER:

        # A1-A3 samlet
        kolonne = f"A1-A3 - {indikator}"
        faktor = get_value(materiale, kolonne)

        result.setdefault("A1to3", {})
        result["A1to3"][indikator] = tykkelse_m * faktor

        # C3
        kolonne = f"C3 - {indikator}"
        faktor = get_value(materiale, kolonne)

        result.setdefault("C3", {})
        result["C3"][indikator] = tykkelse_m * faktor

        # C4
        kolonne = f"C4 - {indikator}"
        faktor = get_value(materiale, kolonne)

        result.setdefault("C4", {})
        result["C4"][indikator] = tykkelse_m * faktor

        # D
        kolonne = f"D - {indikator}"
        faktor = get_value(materiale, kolonne)

        result.setdefault("D", {})
        result["D"][indikator] = tykkelse_m * faktor

    return result


# =====================================================
# JSON BUILDER
# =====================================================

def build_json(grouped_stages, samlet_tykkelse_m, mass_factor):

    produkt_ID = generate_id()
    samlet_tykkelse_mm = round(1000 * samlet_tykkelse_m)

    data = []

    # -------- PRODUCT --------
    data.append({
        "Node": {
            "Product": {
                "id": produkt_ID,
                "name": {
                    "English": f"MBE wall {samlet_tykkelse_mm}mm",
                    "German": "",
                    "Norwegian": "",
                    "Danish": f"MBE væg {samlet_tykkelse_mm}mm"
                },
                "comment": {
                    "English": "",
                    "German": "",
                    "Norwegian": "",
                    "Danish": ""
                },
                "source": "User",
                "uncertainty_factor": 1.0
            }
        }
    })

    # -------- STAGES --------
    for stage, indikator_data in grouped_stages.items():

        stage_id = generate_id()

        data.append({
            "Node": {
                "Stage": {
                    "id": stage_id,
                    "name": {
                        "English": f"MBE wall {samlet_tykkelse_mm}mm ({stage})",
                        "German": "",
                        "Norwegian": "",
                        "Danish": f"MBE væg {samlet_tykkelse_mm}mm ({stage})"
                    },
                    "comment": {
                        "English": "",
                        "German": "",
                        "Norwegian": "",
                        "Danish": ""
                    },
                    "source": "User",
                    "valid_to": "2029-02-20",
                    "stage": stage,
                    "stage_unit": "M3",
                    "indicator_unit": "M3",
                    "stage_factor": 1.0,
                    "mass_factor": float(mass_factor),
                    "indicator_factor": 1.0,
                    "scale_factor": 1.0,
                    "external_source": "MBE Auto Generator",
                    "external_id": "",
                    "external_version": "",
                    "external_url": "",
                    "compliance": "A1",
                    "data_type": "Specific",
                    "indicators": indikator_data
                }
            }
        })

        # ProductToStage
        data.append({
            "Edge": [
                {
                    "ProductToStage": {
                        "id": generate_id(),
                        "excluded_scenarios": [],
                        "enabled": True
                    }
                },
                produkt_ID,
                stage_id
            ]
        })

        # CategoryToStage
        data.append({
            "Edge": [
                {
                    "CategoryToStage": generate_id()
                },
                "1389423d-f9f7-490d-94c7-2ff87bfb9203",
                stage_id
            ]
        })

    return data


# =====================================================
# GUI
# =====================================================

st.title("MBE's LCA beregner")
st.write("Vi arbejder på altid at holde vores beregner opdateret med de nyeste værdier")
st.write("Det er ikke MBE´s ansvar at indtastninger kan lade sig gøre, men er du i tvivl - så kontakt ki@midtjydskbeton.dk")
st.write("Det samme gælder hvis I skal bruge en projektEPD til et fælles projekt, så kan de sendes ved henvendelse til ki@midtjydskbeton.dk")

længde = st.number_input("Længde (m)", value=1.0)
højde = st.number_input("Højde (m)", value=1.0)

t_iso = st.number_input("Tykkelse isolering (mm)", value=200)
t_for = st.number_input("Tykkelse forplade (mm)", value=70)
t_bag = st.number_input("Tykkelse bagplade (mm)", value=150)

mat_for = st.selectbox("Forplade", forplader)
mat_iso = st.selectbox("Isolering", isoleringer)
mat_bag = st.selectbox("Bagplade", bagplader)

afstand = st.number_input("Transportafstand (km)", value=50.0)


# =====================================================
# BEREGNING
# =====================================================

if st.button("Beregn"):

    areal = længde * højde

    t_iso_m = t_iso / 1000
    t_for_m = t_for / 1000
    t_bag_m = t_bag / 1000

    res_iso = beregn_lag(t_iso_m, mat_iso)
    res_for = beregn_lag(t_for_m, mat_for)
    res_bag = beregn_lag(t_bag_m, mat_bag)

    # Densitet
    dens_for = get_value(mat_for, "Densitet")
    dens_iso = get_value(mat_iso, "Densitet")
    dens_bag = get_value(mat_bag, "Densitet")

    mass_factor = (
        t_for_m * dens_for +
        t_iso_m * dens_iso +
        t_bag_m * dens_bag
    )

    # Transport (kun GWP)
    transport_row = df[df["Type"] == "Transport"]

    if transport_row.empty:
        transport_factor = 0.0
    else:
            transport_factor = float(transport_row["A4 - GWP"].values[0])

    samlet_tykkelse_m = t_iso_m + t_for_m + t_bag_m
    volumen = areal * samlet_tykkelse_m
    transport_pr_m2 = (volumen * afstand * transport_factor) / areal

    # ---------------- GWP grouping ----------------
    grouped_stages = {}

    # A1-A3 GWP
    gwp_A1A3 = (
        res_for["A1"]["GWP"] + res_for["A2"]["GWP"] + res_for["A3"]["GWP"] +
        res_iso["A1"]["GWP"] + res_iso["A2"]["GWP"] + res_iso["A3"]["GWP"] +
        res_bag["A1"]["GWP"] + res_bag["A2"]["GWP"] + res_bag["A3"]["GWP"]
    )

    grouped_stages["A1to3"] = {"GWP": gwp_A1A3}

    # A4 GWP
    gwp_A4 = (
        transport_pr_m2
    )

    grouped_stages["A4"] = {"GWP": gwp_A4}

    # C3
    grouped_stages["C3"] = {
        "GWP":
            res_for["C3"]["GWP"] +
            res_iso["C3"]["GWP"] +
            res_bag["C3"]["GWP"]
    }

    # D
    grouped_stages["D"] = {
        "GWP":
            res_for["D"]["GWP"] +
            res_iso["D"]["GWP"] +
            res_bag["D"]["GWP"]
    }

    samlet_belastning = sum(stage["GWP"] for stage in grouped_stages.values())
    samlet_tykkelse_mm = round(1000 * samlet_tykkelse_m)

    st.markdown("---")
    st.write(f"Der er regnet med transportafstand til byggeplads på {afstand:.1f} km")
    st.write(f"En samlet CO2 belastning på {samlet_belastning:.2f} kg CO₂e/m²")
    st.write(f"og en samlet tykkelse på {samlet_tykkelse_mm} mm.")
    st.write(f"armeringsmængde i bagplade er sat svarende til 11 kg pr m² ved en 200mm væg")

    data = build_json(grouped_stages, samlet_tykkelse_m, mass_factor)

    json_string = json.dumps(data, indent=4, ensure_ascii=False)

    st.download_button(
        "Download LCAByg JSON",
        json_string,
        file_name="MBE_LCA_output.json",
        mime="application/json"
    )
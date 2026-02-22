import streamlit as st
import pandas as pd
import random
import json
import uuid

def generate_id():
    return str(uuid.uuid4()).upper()

# ---------- LOAD DATA ----------
@st.cache_data
def load_data():
    df = pd.read_excel("materialedata_lca.xlsx", header=3, engine="openpyxl")
    df.columns = df.columns.str.strip()
    return df

df = load_data()

materialer = df["Materiale"].tolist()

# ---------- FUNCTIONS ----------

def get_value(materiale, kolonne):
    match = df[df["Materiale"].str.strip().str.lower() 
               == materiale.strip().lower()]
    if match.empty:
        st.error(f"Materiale '{materiale}' findes ikke i Excel")
        st.stop()
    return match[kolonne].values[0]


def beregn_lag(tykkelse_m, materiale):
    result = {}
    for modul in ["A1 - GWP","A2 - GWP","A3 - GWP","A4 - GWP","C1 - GWP","C2 - GWP","C3 - GWP","C4 - GWP","D - GWP"]:
        faktor = get_value(materiale, modul)
        result[modul] = tykkelse_m * faktor  # kgCO2e/m2
    return result


def excel_guid():
    def rand_hex(max_value, length):
        return format(random.randint(0, max_value), 'X').zfill(length)

    guid = (
        rand_hex(4294967295, 8) + "-" +
        rand_hex(42949, 4) + "-" +
        rand_hex(42949, 4) + "-" +
        rand_hex(42949, 4) + "-" +
        rand_hex(4294967295, 8) +
        rand_hex(42949, 4)
    )

    return guid

# ---------- GUI ----------

st.title("MBE's LCA beregner")
st.write("Angiv værdier herunder og få et estimat på værdier, som MBE kan levere")
st.write("For at få præcise værdier anbefales det altid at tage fat i MBE (ki@midtjydskbeton.dk) ")
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

    # tykkelser i meter
    t_iso_m = t_iso / 1000
    t_for_m = t_for / 1000
    t_bag_m = t_bag / 1000

    res_iso = beregn_lag(t_iso_m, mat_iso)
    res_for = beregn_lag(t_for_m, mat_for)
    res_bag = beregn_lag(t_bag_m, mat_bag)

    moduler = ["A1 - GWP","A2 - GWP","A3 - GWP","A4 - GWP","C1 - GWP","C2 - GWP","C3 - GWP","C4 - GWP","D - GWP"]

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

    # ---------- TRANSPORT (SELVSTÆNDIG LINJE) ----------

    transport_factor = get_value("Transport", "A4 - GWP")

    samlet_tykkelse_m = t_iso_m + t_for_m + t_bag_m
    volumen = areal * samlet_tykkelse_m  # m3

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

    formatted_df = result_df.style.format(
        {col: "{:.3e}" for col in result_df.columns if col != "Materiale"}
    )

    st.dataframe(formatted_df, use_container_width=True)

    # ---------- SUMMARY TEXT ----------

    samlet_belastning = result_df.iloc[-1]["Total"]

    st.markdown("---")

    st.write(f"Der er regnet med transportafstand til byggeplads på {afstand:.1f} km")
    st.write(f"En samlet CO2 belastning på {float(samlet_belastning):.2f} kg CO₂e/m²")
    st.write(f"og en samlet tykkelse på {round(1000 * samlet_tykkelse_m)} mm.")

    # ==============================
    # LCAByg JSON GENERATOR
    # ==============================

    # ---- Generér IDs ----
    produkt_ID = generate_id()

    stage_ids = {
        "A1to3": generate_id(),
        "C3": generate_id(),
        "C4": generate_id(),
        "D": generate_id()
        }
    
    edge_ids = {
        stage: generate_id()
        for stage in stage_ids
        }

    category_to_stage_ids = {
        stage: generate_id()
        for stage in stage_ids
        }

    # ---- Udtræk summer fra TOTAL-rækken ----
    total_row = result_df[result_df["Materiale"] == "TOTAL"].iloc[0]

    gwp_A1A3 = total_row["A1"] + total_row["A2"] + total_row["A3"]
    gwp_C3 = total_row["C3"]
    gwp_C4 = total_row["C4"]
    gwp_D = total_row["D"]
    
    samlet_tykkelse_mm = round(1000 * samlet_tykkelse_m)
    
    data = []
    
    # ------------------------
    # PRODUCT NODE
    # ------------------------
    
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
                "source": "User",
                "uncertainty_factor": 1.0
                }
            }
        })
    
    # ------------------------
    # STAGE GENERATOR
    # ------------------------
    
    stage_values = {
        "A1to3": gwp_A1A3,
        "C3": gwp_C3,
        "C4": gwp_C4,
        "D": gwp_D
        }
    
    for stage, gwp_value in stage_values.items():
        
        # Stage node
        data.append({
            "Node": {
                "Stage": {
                    "id": stage_ids[stage],
                    "name": {
                        "English": f"MBE wall {samlet_tykkelse_mm}mm ({stage})",
                        "German": "",
                        "Norwegian": "",
                        "Danish": f"MBE væg {samlet_tykkelse_mm}mm ({stage})"
                        },
                    "source": "User",
                    "valid_to": "2029-02-20",
                    "stage": stage,
                    "stage_unit": "M3",
                    "indicator_unit": "M3",
                    "stage_factor": 1.0,
                    "mass_factor": 2439.72,
                    "indicator_factor": 1.0,
                    "scale_factor": 1.0,
                    "external_source": "MBE Auto Generator",
                    "external_id": "",
                    "external_version": "",
                    "external_url": "",
                    "compliance": "A1",
                    "data_type": "Specific",
                    "indicators": {
                        "GWP": float(gwp_value),
                        "AP": 0.0,
                        "EP": 0.0,
                        "POCP": 0.0,
                        "ADPE": 0.0,
                        "ADPF": 0.0,
                        "PENR": 0.0,
                        "PER": 0.0,
                        "ODP": 0.0,
                        "SENR": 0.0,
                        "SER": 0.0
                        }
                    }
                }
            })

        # ProductToStage edge
        data.append({
            "Edge": [
                {
                    "ProductToStage": {
                        "id": edge_ids[stage],
                        "excluded_scenarios": [],
                        "enabled": True
                        }
                    },
                produkt_ID,
                stage_ids[stage]
                ]
            })
        
        # CategoryToStage edge (standard kategori-id beholdt)
        data.append({
            "Edge": [
                {
                    "CategoryToStage": category_to_stage_ids[stage]
                    },
                "1389423d-f9f7-490d-94c7-2ff87bfb9203",
                stage_ids[stage]
                ]
            })
        
        # ------------------------
        # DOWNLOAD BUTTON
        # ------------------------
        
        json_string = json.dumps(data, indent=4, ensure_ascii=False)
        
        st.download_button(
            label="Download LCAByg JSON",
            data=json_string,
            file_name=f"MBE_LCA_{samlet_tykkelse_mm}mm.txt",
            mime="application/json"
            )
            
  
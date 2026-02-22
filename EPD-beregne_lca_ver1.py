import streamlit as st
import pandas as pd
import random
import json

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
    for modul in ["A1-GWP","A2-GWP","A3-GWP","A4-GWP","C1-GWP","C2-GWP","C3-GWP","C4-GWP","D-GWP"]:
        faktor = get_value(materiale, modul)
        result[modul] = tykkelse_m * faktor  # kgCO2e/m2
    return result

#Værdier hentes til generering af LCAByg-fil
#def beregn_lca(materiale):
#    result = {}
#    for modlca in ["A1","A2","A3","A4","C1","C2","C3","C4","D"]:
#        faktor = get_value(materiale, modlca)
#        result[modlca] = faktor  # kgCO2e/m2
#    return result



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

    # ---------- TRANSPORT (SELVSTÆNDIG LINJE) ----------

    transport_factor = get_value("Transport", "A4")

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
        
  
#Lav en LCAByg fil i JSON


# Indsæt din JSON-data her som Python-objekt

produkt_ID = guid
ProductToStage_ID = guid
ProductToStage_A1A3_ID = guid
ProductToStage_C3_ID = guid
ProductToStage_C4_ID = guid
ProductToStage_D_ID = guid
CTStage_A1A3_ID = guid
CTStage_C3_ID = guid
CTStage_C4_ID = guid
CTStage_D_ID = guid
Stage_A1A3_ID = guid
Stage_C3_ID = guid
Stage_C4_ID = guid
Stage_D_ID = guid

data = [
    {
        "Node": {
            "Product": {
                "id": "{produkt_ID},"
                "name": {
                    "English": "Project MBE from midtjydskbeton.dk {samlet_tykkelse_m}",
                    "German": "",
                    "Norwegian": "",
                    "Danish": "Projekt MBE fra midtjydskbeton.dk {samlet_tykkelse_m}"
                },
                "source": "User",
                "comment": {
                    "English": "",
                    "Norwegian": "",
                    "German": "",
                    "Danish": ""
                },
                "uncertainty_factor": 1.0
            }
        }
    }
    # resten af din struktur indsættes her
    "Edge": [{"ProductToStage": { "id: {ProductToStage_ID}",
"excluded_scenarios": [],
"enabled": true}},
"{produkt_ID}",
"{Stage_A1A3_ID}]},"
{"Edge": [{
"ProductToStage": {
"id": "{ProductToStage_A1A3_ID}",
"excluded_scenarios": [],
"enabled": true}},
"{produkt_ID}",
"{Stage_C3_ID}"]},
{
"Edge": [{
"ProductToStage": {
"id": "{ProductToStage_C3_ID}",
"excluded_scenarios": [],
"enabled": true}},
"produkt_ID",
"{Stage_C4_ID}"]},
{
"Edge": [{
"ProductToStage": {"id": "{ProductToStage_C4_ID}",
"excluded_scenarios": [],
"enabled": true}},
"{produkt_ID}",
"{Stage_D_ID}"]
},{
"Node": {
"Stage": {
"id": "{Stage_A1A3_ID}",
"name": {
"Danish": "Projekt MBE fra midtjydskbeton.dk {samlet_tykkelse_m}  (A1-A3)","German":"","Norwegian":"","English": "Project MBE11 mar25 massive wall (A1-A3)"},
"comment": {"English": "" ,"Norwegian":"" ,"German": "" ,"Danish": ""},
"source": "User",
"valid_to": "2029-02-20",
"stage": "A1to3",
"stage_unit": "M3",
"indicator_unit": "M3",
"stage_factor": 1.0,
"mass_factor": 2439.72,
"indicator_factor": 1.0,
"scale_factor": 1.0,
"external_source": "EPD Norge - Projekt",
"external_id": "",
"external_version": "",
"external_url": "",
"compliance": "A1",
"data_type": "Specific",
"indicators": {
"POCP": 0.531441028823,
"ADPE": 0.001770506245,
"EP": 0.006020217105,
"SENR": 0.0,
"ADPF": 2069.89535450987,
"PENR": 2070.0534874347,
"PER": 1236.9975607484,
"ODP": 0.000015025675,
"AP": 0.787489711888,
"SER": 0.0,
"GWP": 236.625168967543
}
}
}
},{
"Edge": [{
"CategoryToStage": "{CTStage_A1A3_ID}"},
"1389423d-f9f7-490d-94c7-2ff87bfb9203",
"{Stage_A1A3_ID}"]
},{
"Node": {
"Stage": {
"id": "{Stage_C3_ID}",
"name": {
"Danish": "ProjektEPD MBE fra midtjydskbeton.dk {samlet_tykkelse_m} (C3)","German":"","Norwegian":"","English": "Project MBE11 mar25 massive wall (C3)" },
"comment": {"English": "" ,"Norwegian":"" ,"German": "" ,"Danish": ""},
"source": "User",
"valid_to": "2029-02-20",
"stage": "C3",
"stage_unit": "M3",
"indicator_unit": "M3",
"stage_factor": 1.0,
"mass_factor": 2439.72,
"indicator_factor": 1.0,
"scale_factor": 1.0,
"external_source": "EPD Norge - Projekt",
"external_id": "",
"external_version": "",
"external_url": "",
"compliance": "A1",
"data_type": "Specific",
"indicators": {
"POCP": 0.012424479175,
"ADPE": 0.000020874376,
"EP": 0.000103244629,
"SENR": 0.0,
"ADPF": 50.821330750170,
"PENR": 32.583265716611,
"PER": 26.034377546472,
"ODP": 0.000000325257,
"AP": 0.013611318627,
"SER": 0.0,
"GWP": 3.636997730553
}
}
}
},{
"Edge": [{
"CategoryToStage": "{CTStage_C3_ID}"},
"1389423d-f9f7-490d-94c7-2ff87bfb9203",
"{Stage_C3_ID}"]
},{
"Node": {
"Stage": {
"id": "{Stage_C4_ID}",
"name": {
"Danish": "ProjektEPD MBE fra midtjydskbeton.dk {samlet_tykkelse_m} (C4)","German":"","Norwegian":"","English": "Project MBE11 mar25 massive wall (C4)" },
"comment": {"English": "" ,"Norwegian":"" ,"German": "" ,"Danish": ""},
"source": "User",
"valid_to": "2029-02-20",
"stage": "C4",
"stage_unit": "M3",
"indicator_unit": "M3",
"stage_factor": 1.0,
"mass_factor": 2439.72,
"indicator_factor": 1.0,
"scale_factor": 1.0,
"external_source": "EPD Norge - Projekt",
"external_id": "",
"external_version": "",
"external_url": "",
"compliance": "A1",
"data_type": "Specific",
"indicators": {
"POCP": 0.003792120830,
"ADPE": 0.000002909348,
"EP": 0.000002454550,
"SENR": 0.0,
"ADPF": 10.607129148095,
"PENR": 10.607378993499,
"PER": 0.163277716803,
"ODP": 0.000000160056,
"AP": 0.003208205711,
"SER": 0.0,
"GWP": 0.329123956392
}
}
}
},{
"Edge": [{
"CategoryToStage": "{CTStage_C4_ID}"},
"1389423d-f9f7-490d-94c7-2ff87bfb9203",
"{Stage_C4_ID}"]
},{
"Node": {
"Stage": {
"id": "{Stage_D_ID}",
"name": {
"Danish": "ProjektEPD MBE fra midtjydskbeton.dk {samlet_tykkelse_m} (D)","German":"","Norwegian":"","English": "Project MBE11 mar25 massive wall (D)" },
"comment": {"English": "" ,"Norwegian":"" ,"German": "" ,"Danish": ""},
"source": "User",
"valid_to": "2029-02-20",
"stage": "D",
"stage_unit": "M3",
"indicator_unit": "M3",
"stage_factor": 1.0,
"mass_factor": 2439.72,
"indicator_factor": 1.0,
"scale_factor": 1.0,
"external_source": "EPD Norge - Projekt",
"external_id": "",
"external_version": "",
"external_url": "",
"compliance": "A1",
"data_type": "Specific",
"indicators": {
"POCP": -0.248621695542,
"ADPE": -0.001138151800,
"EP": -0.002579607721,
"SENR": 0.0,
"ADPF": -421.078645777261,
"PENR": -425.735362042971,
"PER": -57.276978086970,
"ODP": -0.008239073372,
"AP": -0.243562461584,
"SER": 0.0,
"GWP": -44.921155897105
}
}
}
},{
"Edge": [{
"CategoryToStage": "{CTStage_D_ID}"},
"1389423d-f9f7-490d-94c7-2ff87bfb9203",
"{Stage_D_ID}"]
}]
]

# Gem som txt-fil
output_path = "epd_output.txt"

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("Fil gemt:", output_path)

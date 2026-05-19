import streamlit as st
import pandas as pd
import datetime

# Configurarea paginii
st.set_page_config(page_title="Rambursare Anticipată", page_icon="🏡", layout="centered")
st.title("🏡 Calculator Credit Sparkasse")

# Datele inițiale din scadențar
SOLD_START = 251075.00
DATA_START = datetime.date(2027, 12, 5)
RATA_STD = 1139.53
DOBANDA_FIXA = 0.03875

# --- MENIU LATERAL (SIDEBAR) ---
st.sidebar.header("⚙️ Setări și Plăți Extra")
var_rate = st.sidebar.number_input("Dobândă Var. Estimată An 11+ (%)", value=4.50, step=0.1) / 100

st.sidebar.markdown("---")
st.sidebar.markdown("### Plăți Anticipate")
recurent_extra = st.sidebar.number_input("➕ Plată extra LUNARĂ (€)", value=0.0, step=100.0, help="Suma pe care o plătești în plus în FIECARE lună.")

st.sidebar.markdown("**📌 Plăți unice (Lump Sum)**")
st.sidebar.caption("Adaugă sume mari în luni specifice (ex: în luna 12 plătesc 5000€)")

col1, col2 = st.sidebar.columns(2)
with col1:
    lump_m1 = st.number_input("În luna nr:", value=0, step=1, key="lm1")
    lump_m2 = st.number_input("În luna nr:", value=0, step=1, key="lm2")
with col2:
    lump_a1 = st.number_input("Suma (€):", value=0.0, step=500.0, key="la1")
    lump_a2 = st.number_input("Suma (€):", value=0.0, step=500.0, key="la2")

# --- LOGICA DE CALCUL ---
def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = int(sourcedate.year + month / 12)
    month = month % 12 + 1
    day = min(sourcedate.day, [31,29 if year%4==0 and not year%400==0 else 28,31,30,31,30,31,31,30,31,30,31][month-1])
    return datetime.date(year, month, day)

@st.cache_data
def calculeaza_scadentar(sold, rata_std, dob_fixa, dob_var, extra_lunar, l1, a1, l2, a2):
    data = []
    c_sold = sold
    c_data = DATA_START
    total_dobanda = 0
    
    for m in range(1, 430):
        if c_sold <= 0.01:
            break
            
        # Din luna 121 aplicăm dobânda variabilă
        d_rate = dob_fixa if m <= 120 else dob_var
        dobanda_luna = c_sold * (d_rate / 12)
        
        plata_obligatorie = min(rata_std, c_sold + dobanda_luna)
        principal = plata_obligatorie - dobanda_luna
        
        # Calculăm plățile extra
        extra = extra_lunar
        if m == l1: extra += a1
        if m == l2: extra += a2
        
        # Nu putem plăti în plus mai mult decât soldul rămas
        extra = min(extra, c_sold - principal)
        if extra < 0: extra = 0
        
        c_sold = c_sold - principal - extra
        total_dobanda += dobanda_luna
        
        data.append({
            "Lună": m,
            "Dată": c_data.strftime("%d.%m.%Y"),
            "Dobândă (%)": f"{d_rate*100:.2f}%",
            "Rată Fixă (€)": round(plata_obligatorie, 2),
            "Dobândă L. (€)": round(dobanda_luna, 2),
            "Principal (€)": round(principal, 2),
            "Extra (€)": round(extra, 2),
            "Sold Rămas (€)": round(c_sold, 2)
        })
        c_data = add_months(c_data, 1)
        
    return pd.DataFrame(data), total_dobanda, len(data)

# Calculăm varianta standard (fără plăți extra) și varianta curentă
df_baza, dob_baza, luni_baza = calculeaza_scadentar(SOLD_START, RATA_STD, DOBANDA_FIXA, var_rate, 0, 0, 0, 0, 0)
df_nou, dob_nou, luni_nou = calculeaza_scadentar(SOLD_START, RATA_STD, DOBANDA_FIXA, var_rate, recurent_extra, lump_m1, lump_a1, lump_m2, lump_a2)

# --- AFIȘARE INTERFAȚĂ ---
st.markdown("### 📊 Cum se schimbă creditul tău")

# Căsuțe metrice
c1, c2, c3 = st.columns(3)
c1.metric("Termini creditul în", f"{luni_nou//12} ani, {luni_nou%12} luni", f"-{luni_baza - luni_nou} luni salvate", delta_color="inverse")
c2.metric("Dobândă Bancă", f"{dob_nou:,.0f} €", f"-{(dob_baza - dob_nou):,.0f} € salvați", delta_color="inverse")
c3.metric("Anul Finalizării", df_nou.iloc[-1]['Dată'][-4:])

st.markdown("---")
st.markdown("### 📉 Evoluția Soldului")
st.caption("Vezi vizual cât de repede scade datoria față de varianta în care nu plătești nimic în avans.")

# Grafic comparativ
df_chart = pd.DataFrame({"Lună": range(1, luni_baza + 1)})
df_chart = df_chart.merge(df_baza[['Lună', 'Sold Rămas (€)']].rename(columns={'Sold Rămas (€)': 'Fără Extra'}), on='Lună', how='left')
df_chart = df_chart.merge(df_nou[['Lună', 'Sold Rămas (€)']].rename(columns={'Sold Rămas (€)': 'Cu Extra'}), on='Lună', how='left')
df_chart.set_index('Lună', inplace=True)
st.line_chart(df_chart, color=["#E74C3C", "#2ECC71"])

st.markdown("---")
st.markdown("### 🗓️ Scadențar Detaliat")
st.dataframe(df_nou, use_container_width=True)

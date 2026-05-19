import streamlit as st
import pandas as pd
import datetime
import requests

# Configurarea paginii
st.set_page_config(page_title="Rambursare Anticipată", page_icon="🏡", layout="centered")

# --- PRELUARE DATE SECRETE ---
try:
    BIN_ID = st.secrets["BIN_ID"]
    API_KEY = st.secrets["API_KEY"]
    USER_CORECT = st.secrets["APP_USER"]
    PAROLA_CORECTA = st.secrets["APP_PASS"]
except KeyError:
    st.error("⚠️ Lipsesc setările secrete din Streamlit (Secrets)!")
    st.stop()

URL_BIN = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
HEADERS = {
    'X-Master-Key': API_KEY,
    'Content-Type': 'application/json'
}

# --- ECRANUL DE LOGARE ---
if 'logat' not in st.session_state:
    st.session_state.logat = False

if not st.session_state.logat:
    st.title("🔒 Autentificare Sparkasse")
    st.write("Introdu datele pentru a-ți accesa istoricul plăților.")
    
    with st.form("login_form"):
        user = st.text_input("Utilizator")
        parola = st.text_input("Parolă", type="password")
        submit = st.form_submit_button("Intră")
        
        if submit:
            if user == USER_CORECT and parola == PAROLA_CORECTA:
                st.session_state.logat = True
                st.rerun()
            else:
                st.error("❌ Utilizator sau parolă greșite!")
    st.stop()

# ==========================================
# APLICAȚIA (Logat)
# ==========================================

st.title("🏡 Calculator Credit Sparkasse")

def incarca_din_cloud():
    try:
        req = requests.get(URL_BIN, headers=HEADERS)
        date_cloud = req.json().get('record', {})
        # Curățăm testul '0':0 dacă încă e acolo
        st.session_state.plati_extra = {int(k): float(v) for k, v in date_cloud.items() if str(k) != "0"}
    except:
        st.session_state.plati_extra = {}

def salveaza_in_cloud():
    try:
        data_de_salvat = st.session_state.plati_extra
        if not data_de_salvat:
            data_de_salvat = {"0": 0} # Nu lăsăm baza de date goală
        requests.put(URL_BIN, json=data_de_salvat, headers=HEADERS)
        st.toast("☁️ Sincronizat în Cloud!", icon="✅")
    except:
        st.toast("Eroare la conectarea cu Cloud-ul", icon="⚠️")

if 'date_incarcate' not in st.session_state:
    incarca_din_cloud()
    st.session_state.date_incarcate = True

# Datele din contract
SOLD_START = 251075.00
DATA_START = datetime.date(2027, 12, 5)
RATA_STD = 1139.53
DOBANDA_FIXA = 0.03875

# --- MENIU LATERAL ---
st.sidebar.header(f"👤 Salut, {USER_CORECT.capitalize()}!")
if st.sidebar.button("🚪 Ieși din cont"):
    st.session_state.logat = False
    st.rerun()

st.sidebar.markdown("---")
var_rate = st.sidebar.number_input("Dobândă Var. Estimată An 11+ (%)", value=4.50, step=0.1) / 100

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔄 Plată extra LUNARĂ")
recurent_extra = st.sidebar.number_input("Suma în plus FIECARE lună (€)", value=0.0, step=100.0)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 Adaugă Plăți Unice")
col1, col2 = st.sidebar.columns(2)
with col1:
    luna_input = st.number_input("În luna nr:", min_value=1, value=1, step=1)
with col2:
    suma_input = st.number_input("Suma (€):", min_value=0.0, value=1000.0, step=100.0)

if st.sidebar.button("➕ Adaugă plata"):
    if suma_input > 0:
        if luna_input in st.session_state.plati_extra:
            st.session_state.plati_extra[luna_input] += suma_input
        else:
            st.session_state.plati_extra[luna_input] = suma_input
        salveaza_in_cloud()
        st.rerun()

if st.session_state.plati_extra:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Plăți Cloud:**")
    for luna in sorted(list(st.session_state.plati_extra.keys())):
        suma = st.session_state.plati_extra[luna]
        col_txt, col_btn = st.sidebar.columns([3, 1])
        col_txt.write(f"Luna {luna}: **{suma:,.0f} €**")
        if col_btn.button("❌", key=f"del_{luna}"):
            del st.session_state.plati_extra[luna]
            salveaza_in_cloud()
            st.rerun()

# --- CALCUL ---
def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = int(sourcedate.year + month / 12)
    month = month % 12 + 1
    day = min(sourcedate.day, [31,29 if year%4==0 and not year%400==0 else 28,31,30,31,30,31,31,30,31,30,31][month-1])
    return datetime.date(year, month, day)

def calculeaza_scadentar(sold, rata_std, dob_fixa, dob_var, extra_lunar, plati_unice_dict):
    data = []
    c_sold = sold
    c_data = DATA_START
    total_dobanda = 0
    for m in range(1, 430):
        if c_sold <= 0.01: break
        d_rate = dob_fixa if m <= 120 else dob_var
        dobanda_luna = c_sold * (d_rate / 12)
        plata_obligatorie = min(rata_std, c_sold + dobanda_luna)
        principal = plata_obligatorie - dobanda_luna
        
        extra = extra_lunar
        if m in plati_unice_dict: extra += plati_unice_dict[m]
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

df_baza, dob_baza, luni_baza = calculeaza_scadentar(SOLD_START, RATA_STD, DOBANDA_FIXA, var_rate, 0, {})
df_nou, dob_nou, luni_nou = calculeaza_scadentar(SOLD_START, RATA_STD, DOBANDA_FIXA, var_rate, recurent_extra, st.session_state.plati_extra)

# --- AFIȘARE ---
c1, c2, c3 = st.columns(3)
c1.metric("Termini creditul în", f"{luni_nou//12} ani, {luni_nou%12} luni", f"-{luni_baza - luni_nou} luni salvate", delta_color="inverse")
c2.metric("Dobândă Bancă", f"{dob_nou:,.0f} €", f"-{(dob_baza - dob_nou):,.0f} €", delta_color="inverse")
if len(df_nou) > 0:
    st.session_state.an_final = df_nou.iloc[-1]['Dată'][-4:]
st.metric("Anul Finalizării", st.session_state.get('an_final', 'N/A'))

df_chart = pd.DataFrame({"Lună": range(1, luni_baza + 1)})
df_chart = df_chart.merge(df_baza[['Lună', 'Sold Rămas (€)']].rename(columns={'Sold Rămas (€)': 'Fără Extra'}), on='Lună', how='left')
df_chart = df_chart.merge(df_nou[['Lună', 'Sold Rămas (€)']].rename(columns={'Sold Rămas (€)': 'Cu Extra'}), on='Lună', how='left')
df_chart.set_index('Lună', inplace=True)
st.line_chart(df_chart, color=["#E74C3C", "#2ECC71"])

def highlight_extra(val):
    try:
        if float(val) > 0: return 'background-color: #117A65; color: white; font-weight: bold;'
    except: pass
    return ''

if len(df_nou) > 0:
    df_styled = df_nou.style.format({
        "Rată Fixă (€)": "{:.2f}",
        "Dobândă L. (€)": "{:.2f}",
        "Principal (€)": "{:.2f}",
        "Extra (€)": "{:.2f}",
        "Sold Rămas (€)": "{:.2f}"
    }).map(highlight_extra, subset=['Extra (€)'])
    st.dataframe(df_styled, use_container_width=True)

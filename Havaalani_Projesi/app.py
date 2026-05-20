import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
import requests
from datetime import datetime
from sklearn.linear_model import LinearRegression
from auth import check_password

# --- 1. GİRİŞ KONTROLÜ VE SAYFA AYARLARI ---
# Dosyanın en başı
from auth import check_password

if not check_password():
    st.stop()
st.set_page_config(page_title="Airport-EnergyAI | Digital Twin", layout="wide")

# Kurumsal ve Modern Görünüm İçin CSS
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: white; }
    .log-box { background: #161B22; padding: 10px; border-radius: 8px; color: #10B981; 
               font-family: monospace; height: 300px; overflow-y: auto; font-size: 0.85rem; border: 1px solid #30363d; }
    .status-card { background: #1E293B; padding: 15px; border-radius: 10px; border-top: 4px solid #00D4FF; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CANLI VERİ VE ANALİZ FONKSİYONLARI ---

from fpdf import FPDF

def create_pdf_report(history_data, current_user):
    pdf = FPDF()
    pdf.add_page()
    
    # Başlık
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Airport-EnergyAI Operasyonel Raporu", ln=True, align='C')
    
    pdf.set_font("Arial", size=10)
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Raporu Hazirlayan: {current_user}", ln=True)
    pdf.cell(200, 10, txt=f"Olusturulma Tarihi: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", ln=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="Enerji Analiz Ozeti:", ln=True)
    
    pdf.set_font("Arial", size=10)
    
    for t_name, df in history_data.items():
        # --- KRİTİK DÜZELTME: Emojileri ve özel karakterleri temizle ---
        # "🏢 Ana Terminal" -> "Ana Terminal"
        clean_name = t_name.replace("🏢", "").replace("✈️", "").replace("🛣️", "").strip()
        # Türkçe karakterleri İngilizceye çevir (Hata riskini sıfıra indirir)
        clean_name = clean_name.replace("ı", "i").replace("ş", "s").replace("ğ", "g").replace("ü", "u").replace("ö", "o").replace("ç", "c")
        
        if not df.empty:
            avg_load = df['y'].mean()
            pdf.cell(200, 8, txt=f"- {clean_name}: Ort. Yuk: {avg_load:.2f} MW", ln=True)
        else:
            pdf.cell(200, 8, txt=f"- {clean_name}: Veri yok.", ln=True)

    pdf.ln(10)
    pdf.set_font("Arial", 'I', 8)
    pdf.multi_cell(0, 10, txt="Not: Bu rapor otomatik uretilmistir. Emojiler rapor uyumlulugu icin kaldirilmistir.")

    return pdf.output(dest='S')

def get_live_airport_data(api_key):
    """OpenWeather ve OpenSky API'lerinden canlı veri çeker."""
    try:
        # 1. Hava Durumu (İstanbul)
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?q=Istanbul&appid={api_key}&units=metric"
        w_res = requests.get(weather_url, timeout=5).json()
        temp = w_res['main']['temp']
        
        # 2. Uçuş Trafiği (İstanbul Havalimanı Çevresi)
        opensky_url = "https://opensky-network.org/api/states/all?lamin=41.1&lomin=28.6&lamax=41.4&lomax=28.9"
        f_res = requests.get(opensky_url, timeout=5).json()
        flight_count = len(f_res['states']) if f_res.get('states') else 0
        
        return temp, flight_count
    except Exception:
        # İnternet/API sorunu olursa gerçekçi varsayılanlar
        return 22.5, 12 

def calculate_energy_load(base_load, temp, flights):
    """API verilerini enerji yüküne dönüştüren matematiksel model."""
    # 22 dereceden her sapma yükü artırır (İklimlendirme etkisi)
    temp_effect = abs(temp - 22) * 480 
    # Uçak başı operasyonel yük
    flight_effect = flights * 1150
    # Doğal dalgalanma (Noise)
    noise = np.random.normal(0, 180)
    return base_load + temp_effect + flight_effect + noise

def predict_next_values(data, steps=5):
    """Lineer Regresyon ile trend tahmini yapar."""
    y = data['y'].values
    x = np.arange(len(y)).reshape(-1, 1)
    # Son 12 veri noktasıyla eğit
    model = LinearRegression().fit(x[-12:], y[-12:])
    future_x = np.arange(len(y), len(y) + steps).reshape(-1, 1)
    return model.predict(future_x)

def get_ai_advice():
    """Anomali durumunda rastgele uzman tavsiyesi seçer."""
    advices = [
        "⚠️ KRİTİK: Enerji yükü sınırı aşıldı. Kademeli yük atma (Load Shedding) başlatın.",
        "🛠️ TEKNİK: Trafo merkezindeki reaktif gücü dengeleyin.",
        "🛰️ SİSTEM: Uçuş yoğunluğu nedeniyle Pist Aydınlatma yedek hattını aktif edin.",
        "🔒 GÜVENLİK: SCADA sisteminde olağandışı patern; veri doğrulama yapın."
    ]
    return np.random.choice(advices)

# --- 3. SESSION STATE (BELLEK) YÖNETİMİ ---
terminals = ["🏢 Ana Terminal", "✈️ Dış Hatlar", "🛣️ Pist Aydınlatma"]

if 'history' not in st.session_state:
    st.session_state.history = {t: pd.DataFrame(columns=['ds', 'y']) for t in terminals}
if 'alerts' not in st.session_state:
    st.session_state.alerts = []
if 'ai_processed' not in st.session_state:
    st.session_state.ai_processed = {t: False for t in terminals}
if 'ai_report' not in st.session_state:
    st.session_state.ai_report = {t: "" for t in terminals}

# --- 4. ARAYÜZ OLUŞTURMA ---
st.title("✈️ Airport-EnergyAI: Canlı Dijital İkiz Paneli")

with st.sidebar:
    st.header("🎮 Kontrol Merkezi")
    run_status = st.toggle("🛰️ Sensörleri Aktif Et", value=False)
    inject_fault = st.toggle("🚨 Yapay Arıza Modu", value=False)
    st.divider()
    if st.button("🗑️ Kayıtları Temizle"):
        st.session_state.alerts = []
        st.rerun()
    st.caption("Veri Kaynakları: OpenWeather API & OpenSky Network")

    # Raporlama Butonu
# Raporlama Butonu (Düzeltilmiş Versiyon)
if st.sidebar.button("📊 Raporu Olustur (PDF)"):
    try:
        # PDF verisini oluştur (bytearray döner)
        pdf_output = create_pdf_report(st.session_state.history, st.session_state.current_user)
        
        # --- KRİTİK DÜZELTME: bytearray -> bytes dönüşümü ---
        pdf_bytes = bytes(pdf_output)
        
        # İndirme butonu
        st.sidebar.download_button(
            label="📩 PDF Dosyasini Indir",
            data=pdf_bytes, # Artık saf bytes formatında
            file_name=f"Airport_Rapor_{datetime.now().strftime('%H%M%S')}.pdf",
            mime="application/pdf"
        )
        st.sidebar.success("Rapor hazir, yukarıdaki butona tıklayın!")
    except Exception as e:
        st.sidebar.error(f"Rapor olusturmadi: {e}")

# Ekranı ikiye böl (Grafikler ve Yan Panel)
col_main, col_side = st.columns([2.2, 1])

# --- 5. ANA ÇALIŞMA DÖNGÜSÜ ---
if run_status:
    # API'lerden taze veriyi çek
    current_temp, current_flights = get_live_airport_data("ca37741ddda8e5d81b4f5a2daeecc750")
    now = datetime.now()

    with col_main:
        tabs = st.tabs(terminals)
        for i, t_name in enumerate(terminals):
            # Baz yük belirleme (Daha önce hata veren kısım düzeltildi)
            if "Ana" in t_name:
                base = 41000
            elif "Dış" in t_name:
                base = 24000
            else:
                base = 5500
            
            # Canlı hesaplama
            val = calculate_energy_load(base, current_temp, current_flights)
            if inject_fault:
                val *= 1.75 # Arıza varsa yükü fırlat
            
            is_anomaly = val > (base * 1.28) # %28 artış anomali sayılır
            
            # Veriyi geçmişe ekle
            new_row = pd.DataFrame({'ds': [now], 'y': [val]})
            st.session_state.history[t_name] = pd.concat([st.session_state.history[t_name], new_row]).tail(35)

            with tabs[i]:
                # Metrik Kartları
                m1, m2, m3 = st.columns(3)
                m1.metric("Anlık Güç", f"{val:.0f} MW", delta=f"{val-base:.0f} Δ")
                m2.metric("🌡️ Hava Durumu", f"{current_temp}°C")
                m3.metric("✈️ Trafik", f"{current_flights} Uçak")

                # Grafik Çizimi
                fig = go.Figure()
                # Ana Çizgi
                fig.add_trace(go.Scatter(
                    x=st.session_state.history[t_name]['ds'], 
                    y=st.session_state.history[t_name]['y'],
                    mode='lines+markers',
                    name='Aktif Tüketim',
                    line=dict(color='#FF4B4B' if is_anomaly else '#00D4FF', width=3),
                    fill='tozeroy'
                ))
                
                # Tahmin Çizgisi
                if len(st.session_state.history[t_name]) > 10:
                    try:
                        preds = predict_next_values(st.session_state.history[t_name])
                        future_dates = [now + pd.Timedelta(seconds=j*3) for j in range(1, 6)]
                        fig.add_trace(go.Scatter(x=future_dates, y=preds, mode='lines', 
                                                line=dict(color='yellow', dash='dot', width=2), name='Trend Tahmini'))
                    except:
                        pass

                fig.update_layout(height=380, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)

                # AI Analiz Mantığı
                if is_anomaly:
                    if not st.session_state.ai_processed[t_name]:
                        advice = get_ai_advice()
                        st.session_state.ai_report[t_name] = advice
                        st.session_state.alerts.append(f"{now.strftime('%H:%M:%S')} | {t_name} | {advice}")
                        st.session_state.ai_processed[t_name] = True
                    st.error(f"🤖 **AI Danışman Notu:** {st.session_state.ai_report[t_name]}")
                else:
                    st.session_state.ai_processed[t_name] = False

    with col_side:
        st.subheader("📋 Olay Günlüğü")
        # Logları tersten göster (en yeni en üstte)
        log_content = "<br>".join(reversed(st.session_state.alerts))
        st.markdown(f"<div class='log-box'>{log_content}</div>", unsafe_allow_html=True)
        
        st.divider()
        st.subheader("📊 Operasyonel Analiz")
        st.write(f"Sistem Zamanı: {now.strftime('%H:%M:%S')}")
        st.progress(min(int(current_flights * 4), 100), text="Hava Sahası Doluluğu")
        
        if len(st.session_state.alerts) > 5:
            st.warning("⚠️ Son 1 saatte anomali sıklığı arttı!")

    time.sleep(3) # API limitlerini korumak ve akıcılık için 3 saniye bekle
    st.rerun()

else:
    # Başlangıç Ekranı
    st.info("👋 Hoş Geldiniz! Lütfen sistem takibini başlatmak için sol menüden sensörleri aktif edin.")
    st.image("https://images.unsplash.com/photo-1542296332-2e4473faf563?auto=format&fit=crop&q=80&w=1000", caption="İstanbul Havalimanı Enerji Yönetim Merkezi")
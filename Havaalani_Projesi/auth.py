import sqlite3
import bcrypt
import streamlit as st
import time

# --- 1. VERİTABANI ALT YAPISI ---
def init_db():
    """Veritabanını ve kullanıcılar tablosunu oluşturur."""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT)''')
    conn.commit()
    conn.close()

# --- 2. GÜVENLİK FONKSİYONLARI ---
def hash_password(password):
    """Şifreyi güvenli bir şekilde hashler (Salt + Hash)."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_hashes(password, hashed):
    """Gelen şifre ile veritabanındaki hash'i karşılaştırır."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed)
    except:
        return False

# --- 3. VERİTABANI İŞLEMLERİ ---
def create_user(username, password):
    """Yeni kullanıcı kaydeder."""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        # Kullanıcı adını temizle (başındaki/sonundaki boşlukları sil)
        username = username.strip()
        hashed_pw = hash_password(password)
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # Kullanıcı adı zaten varsa
    finally:
        conn.close()

def login_user(username, password):
    """Kullanıcı bilgilerini doğrular."""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    username = username.strip()
    c.execute("SELECT password FROM users WHERE username=?", (username,))
    user_data = c.fetchone()
    conn.close()
    
    if user_data:
        return check_hashes(password, user_data[0])
    return False

# --- 4. STREAMLIT GİRİŞ/KAYIT EKRANI ---
def check_password():
    init_db() # Veritabanı kontrolü
    
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        # Görsel Tasarım
        st.markdown("<h1 style='text-align: center;'>✈️ Airport-EnergyAI</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; color: #8B5CF6;'>Güvenlik Kapısı</h3>", unsafe_allow_html=True)
        
        tab_login, tab_signup = st.tabs(["🔑 Giriş Yap", "📝 Yeni Kayıt"])
        
        # --- GİRİŞ SEKMESİ ---
        with tab_login:
            with st.form("login_form"):
                user_in = st.text_input("Kullanıcı Adı")
                pw_in = st.text_input("Şifre", type="password")
                submit_l = st.form_submit_button("Sisteme Gir")
                
                if submit_l:
                    if login_user(user_in, pw_in):
                        st.session_state.authenticated = True
                        st.session_state.current_user = user_in
                        st.success("Doğrulama Başarılı! Yönlendiriliyorsunuz...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Kullanıcı adı veya şifre hatalı.")

        # --- KAYIT SEKMESİ ---
        with tab_signup:
            with st.form("signup_form"):
                new_user = st.text_input("Kullanıcı Adı Belirleyin")
                new_pw = st.text_input("Şifre Belirleyin", type="password")
                confirm_pw = st.text_input("Şifreyi Tekrar Girin", type="password")
                submit_s = st.form_submit_button("Hesabı Oluştur")
                
                if submit_s:
                    if new_user == "" or new_pw == "":
                        st.warning("Alanlar boş bırakılamaz.")
                    elif new_pw != confirm_pw:
                        st.error("Şifreler birbiriyle eşleşmiyor.")
                    elif len(new_pw) < 4:
                        st.error("Şifre en az 4 karakter olmalıdır.")
                    else:
                        if create_user(new_user, new_pw):
                            st.success("Kayıt başarıyla oluşturuldu! Giriş yapabilirsiniz.")
                        else:
                            st.error("Bu kullanıcı adı zaten sistemde kayıtlı.")
        
        return False
    
    return True
import streamlit as st
import random
import string
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import sqlite3
import hashlib

# --- Veritabanı Bağlantısı ---
conn = sqlite3.connect("guvenbank.db", detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS otps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    otp TEXT,
    expiration TIMESTAMP
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS giris_kayitlari (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    login_time TIMESTAMP
)
""")
conn.commit()
# Şifre güncelleme tablosu
cursor.execute("""
CREATE TABLE IF NOT EXISTS sifre_guncelleme (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    new_password TEXT,
    usage_period TEXT,
    updated_at TIMESTAMP
)
""")
conn.commit()


# --- Şifre oluşturma fonksiyonu ---
def generate_password(length):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for _ in range(length))

# --- E-posta gönderme fonksiyonu ---
def send_email(to_email, password, expiration_time):
    your_email = "guvennbankk@gmail.com"
    your_app_password = "vtcwztskgrbupsux"

    subject = "Tek Kullanımlık Şifreniz"
    body = f"""
Merhaba,

İstediğiniz tek kullanımlık şifreniz aşağıdadır:

Şifre: {password}
Geçerlilik süresi: {expiration_time.strftime('%H:%M:%S')}

Lütfen bu şifreyi kimseyle paylaşmayın. Şifre 10 dakika sonra geçersiz olacaktır.

GüvenBank
"""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = your_email
    msg["To"] = to_email

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(your_email, your_app_password)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"E-posta gönderimi başarısız: {e}")
        return False

# --- Arayüz Stili ---
st.markdown("""
    <style>
    body {
        background-color: black;
    }
    .main {
        background-color: black;
    }
    .bank-container {
        padding: 30px;
        border-radius: 15px;
        box-shadow: none;
        max-width: 600px;
        margin: auto;
        margin-top: 40px;
        font-family: 'Segoe UI', sans-serif;
        color: black;
        background-color: transparent;
    }
    .bank-title {
        font-size: 32px;
        font-weight: bold;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
    .stButton>button {
        background-color: #003366;
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 16px;
    }
    </style>
""", unsafe_allow_html=True)

# --- Başlık ---
st.markdown('<div class="bank-container">', unsafe_allow_html=True)
st.markdown('<div class="bank-title">GüvenBank Giriş Paneli</div>', unsafe_allow_html=True)

# Oturum Değişkenleri
if "otp" not in st.session_state:
    st.session_state.otp = None
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "show_otp_option" not in st.session_state:
    st.session_state.show_otp_option = False
if "otp_sent" not in st.session_state:
    st.session_state.otp_sent = False

# --- Kullanıcı Giriş Alanı ---
st.subheader("Giriş Yap")
name = st.text_input("Ad Soyad")
password = st.text_input("Şifre", type="password")

if st.button("Giriş Yap"):
    if name and password:
        if name.lower() == "admin" and password == "admin_2025!":
            st.success("Admin olarak giriş yapıldı. Giriş kayıtları gösteriliyor:")
            cursor.execute("SELECT * FROM giris_kayitlari")
            records = cursor.fetchall()
            for record in records:
                st.write(f"Ad: {record[1]}, Giriş Zamanı: {record[2]}")
        else:
            st.error("Geçersiz kullanıcı adı veya şifre!")
    else:
        st.error("Lütfen tüm alanları doldurun.")

# --- Tek Kullanımlık Şifre Seçeneği ---
st.subheader("Tek Kullanımlık Şifre")
if st.button("Şifre Al (Tek Kullanımlık)"):
    st.session_state.show_otp_option = True

# --- Şifre Al Formu ---
if st.session_state.show_otp_option and not st.session_state.otp_sent:
    name2 = st.text_input("Ad Soyad (Tek Kullanımlık Şifre için)")
    email = st.text_input("E-posta Adresiniz")
    length = st.slider("Şifre uzunluğu:", 6, 20, 10)

    if st.button("Gönder"):
        if name2 and email:
            otp = generate_password(length)
            expiration = datetime.now() + timedelta(minutes=10)
            st.session_state.otp = otp
            st.session_state.otp_expiration = expiration
            st.session_state.otp_sent = True

            cursor.execute("INSERT INTO otps (name, email, otp, expiration) VALUES (?, ?, ?, ?)",
                           (name2, email, otp, expiration))
            conn.commit()

            if send_email(email, otp, expiration):
                st.success(f"Şifre başarıyla {email} adresine gönderildi!")
            else:
                st.error("Şifre gönderilemedi.")
        else:
            st.warning("Lütfen tüm alanları doldurun.")

# --- Tek Kullanımlık Şifre ile Giriş ---
if st.session_state.otp_sent:
    otp_input = st.text_input("E-posta ile Gelen Şifreyi Girin")
    if st.button("Şifreyle Giriş Yap"):
        cursor.execute("SELECT id, name, expiration FROM otps WHERE otp = ?", (otp_input,))
        result = cursor.fetchone()

if result:
    otp_id, user_name, expiration_db = result
    if isinstance(expiration_db, str):
        expiration_db = datetime.strptime(expiration_db, '%Y-%m-%d %H:%M:%S.%f')
    if datetime.now() < expiration_db:
        cursor.execute("DELETE FROM otps WHERE id = ?", (otp_id,))
        conn.commit()

        # Şifreyi SHA-256 ile hashle
        hashed_password = hashlib.sha256(new_password.encode()).hexdigest()

        # Hash'lenmiş şifreyi veritabanına kaydet
        cursor.execute("INSERT INTO sifre_guncelleme (name, new_password, usage_period, updated_at) VALUES (?, ?, ?, ?)",
                   (st.session_state.get('user_name', 'Kullanıcı'), hashed_password, usage_frequency, datetime.now()))
        conn.commit()

        st.success("Giriş Başarılı!")
        st.session_state.authenticated = True
        st.session_state.otp_sent = False
        st.session_state.user_name = user_name
    else:
        st.error("Şifrenizin süresi dolmuş!")
else:
    st.error("Geçersiz şifre!")

            

# --- Başarılı Giriş Sonrası ---
# --- Başarılı Giriş Sonrası ---
# --- Başarılı Giriş Sonrası ---
if st.session_state.authenticated:
    st.markdown("""
        <h2 style='text-align:center; color:green;'>✔ Giriş Yaptınız!</h2>
        <p style='text-align:center;'>
            <a href='https://beyza-cmd.github.io/guvenbank-app.py/' target='_blank' style='
                font-size:18px;
                color:#003366;
                text-decoration:none;
                font-weight:bold;
            '>👉 GüvenBank Uygulamasına Git</a>
        </p>
    """, unsafe_allow_html=True)
    # Profil ve Şifre Güncelleme Paneli
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:right;'>👤 <strong>{st.session_state.get('user_name', 'Kullanıcı')}</strong></div>", unsafe_allow_html=True)

    with st.expander("🔐 Profil Ayarları - Şifre Güncelle"):
        st.subheader("Şifrenizi Güncelleyin")

        new_password = st.text_input("Yeni Şifre", type="password")
        new_password_repeat = st.text_input("Yeni Şifre (Tekrar)", type="password")
        usage_frequency = st.selectbox("Yeni şifre kullanım süresi", ["3 ay", "6 ay", "9 ay"])

        if st.button("Şifreyi Güncelle"):
            if new_password != new_password_repeat:
                st.error("Şifreler uyuşmuyor!")
            elif not new_password:
                st.error("Şifre boş olamaz!")
            else:
                # Şifreyi veritabanına kayıt etme örneği (kendi veritabanı şema yapına göre değiştir)
                cursor.execute("INSERT INTO giris_kayitlari (name, login_time) VALUES (?, ?)",
                               (st.session_state.get('user_name', 'Kullanıcı'), datetime.now()))
                conn.commit()
                st.success("✅ Yeni şifreniz başarıyla oluşturuldu!")




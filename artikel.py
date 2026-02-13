import streamlit as st
import feedparser
import google.generativeai as genai
import requests
import time
import itertools
from base64 import b64encode

# --- KONFIGURASI UI ---
st.set_page_config(page_title="GeminiPress Pro - Dashboard", layout="wide")

# Custom CSS untuk tampilan lebih modern
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .stTextArea textarea { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True) # <--- Pakai HTML, bukan STDIO

st.title("🚀 GeminiPress Plus: Autoblog & Auto-Post")
st.subheader("Sistem AI Writer Otomatis dengan Rotasi API (Free Tier Friendly)")

# --- SIDEBAR: KONFIGURASI ---
with st.sidebar:
    st.header("🔑 API & Akses")
    
    # Input API Key Gemini per Baris
    api_input = st.text_area("List Gemini API Keys (Satu per baris)", value="gemini", height=150)
    keys = [k.strip() for k in api_input.split("\n") if k.strip()]
    key_cycle = itertools.cycle(keys) 

    # Input API Key Unsplash per Baris
    unsplash_input = st.text_area("List Unsplash Access Keys (Satu per baris)", height=150)
    u_keys = [uk.strip() for uk in unsplash_input.split("\n") if uk.strip()]
    u_key_cycle = itertools.cycle(u_keys) if u_keys else None

    st.divider()
    st.header("🌐 WordPress Settings")
    wp_url = st.text_input("URL WordPress", placeholder="https://websitekamu.com")
    wp_user = st.text_input("Username WP")
    wp_pass = st.text_input("Application Password", type="password", help="Dapatkan di WP Admin > Users > Profile")
    wp_status = st.selectbox("Status Postingan", ["draft", "publish"])

    st.divider()
    st.header("📋 Sumber Konten")
    rss_url = st.text_input("RSS Feed URL", "https://news.google.com/rss/search?q=teknologi&hl=id&gl=ID&ceid=ID:id")
    limit_post = st.number_input("Jumlah Postingan", min_value=1, max_value=20, value=5)

# --- FUNGSI CORE ---

def get_unsplash_image(query, cycle_obj):
    """Mencari gambar di Unsplash dengan rotasi key."""
    if not cycle_obj:
        return "https://via.placeholder.com/800x400?text=Unsplash+Key+Kosong", "Unknown"
    
    current_u_key = next(cycle_obj)
    url = f"https://api.unsplash.com/photos/random?query={query}&client_id={current_u_key}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return data['urls']['regular'], data['user']['name']
    except:
        pass
    return "https://via.placeholder.com/800x400?text=Gambar+Tidak+Ditemukan", "Unknown"

def post_to_wordpress(title, content, img_url, img_keyword):
    """Kirim hasil artikel ke WordPress via REST API."""
    if not wp_url or not wp_user or not wp_pass:
        return "⚠️ Data WP tidak lengkap. Artikel hanya tampil di sini."

    user_pass = f"{wp_user}:{wp_pass}"
    token = b64encode(user_pass.encode()).decode()
    headers = {'Authorization': f'Basic {token}'}

    # Menyusun konten dengan Gambar di bagian paling atas
    html_content = f"""
    <figure class="wp-block-image size-large">
        <img src="{img_url}" alt="{img_keyword}" style="border-radius:10px;"/>
        <figcaption>Ilustrasi: {img_keyword}</figcaption>
    </figure>
    {content}
    """

    post_data = {
        'title': title,
        'content': html_content,
        'status': wp_status,
    }

    try:
        url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts"
        response = requests.post(url, headers=headers, json=post_data)
        if response.status_code == 201:
            return f"✅ Berhasil! Status: {wp_status.upper()}"
        else:
            return f"❌ Gagal WP: {response.json().get('message', 'Error')}"
    except Exception as e:
        return f"❌ Koneksi Error: {str(e)}"

def generate_ai_content(title, current_key):
    """Minta Gemini menulis artikel dan memberikan keyword gambar."""
    genai.configure(api_key=current_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    Bertindaklah sebagai penulis blog profesional.
    Tulis ulang judul berita ini menjadi artikel blog yang menarik dan SEO friendly: {title}
    
    Ketentuan:
    1. Minimal 500 kata.
    2. Format HTML (gunakan <h2>, <p>, <ul>).
    3. Bahasa Indonesia yang enak dibaca.
    4. Di baris paling akhir sendiri, tuliskan tepat seperti ini: KEYWORD: [1 kata kunci bahasa inggris saja]
    """
    try:
        response = model.generate_content(prompt)
        text = response.text
        # Parsing keyword
        if "KEYWORD:" in text:
            artikel, keyword = text.split("KEYWORD:")
            keyword = keyword.strip().replace("[", "").replace("]", "")
        else:
            artikel, keyword = text, "technology"
        return artikel, keyword
    except Exception as e:
        st.error(f"Error pada API Key {current_key[:5]}: {str(e)}")
        return None, None

# --- TOMBOL EKSEKUSI ---

if st.button("🚀 MULAI PROSES AUTOBLOG"):
    if not keys:
        st.error("Masukkan minimal satu Gemini API Key!")
    else:
        st.info("📡 Sedang mengambil berita dari RSS...")
        feed = feedparser.parse(rss_url)
        
        if not feed.entries:
            st.warning("RSS Feed kosong atau URL salah.")
        else:
            processed_count = 0
            for entry in feed.entries[:limit_post]:
                current_api_key = next(key_cycle)
                
                with st.expander(f"📝 Memproses: {entry.title}", expanded=True):
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        st.caption(f"🔑 API: {current_api_key[:8]}***")
                        with st.spinner("AI sedang menulis..."):
                            artikel, img_kw = generate_ai_content(entry.title, current_api_key)
                        
                        if artikel:
                            with st.spinner("Mencari gambar..."):
                                img_url, photographer = get_unsplash_image(img_kw, u_key_cycle)
                            st.image(img_url, caption=f"Foto oleh {photographer} (Unsplash)")
                        
                    with col2:
                        if artikel:
                            st.markdown("### Preview Hasil")
                            st.success(f"Keyword Gambar: {img_kw}")
                            
                            # Kirim ke WordPress
                            wp_msg = post_to_wordpress(entry.title, artikel, img_url, img_kw)
                            st.info(wp_msg)
                            
                            # Tampilkan sedikit isi artikel
                            st.code(artikel[:300] + "...", language="html")
                            processed_count += 1
                        else:
                            st.error("Gagal membuat konten untuk artikel ini.")
                
                time.sleep(2) # Jeda aman
            
            st.balloons()
            st.success(f"Selesai! {processed_count} artikel telah diproses.")
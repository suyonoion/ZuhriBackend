from fastapi import FastAPI
import requests
import math
from datetime import datetime, timedelta, timezone

app = FastAPI()

# ================= RUTE AKAR (DETAK JANTUNG MONITORING) ================= #
@app.get("/")
def kalibrasi_awal():
    return {
        "status": "Ekuilibrium Tercapai",
        "matriks": "Zuhri Formalism Backend Aktif",
        "ruang_waktu": "Operasional"
    }

# ================= KONSOL PERHITUNGAN GEOMETRIS SPASIAL ================= #
def hitung_jarak_haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def format_waktu_wib(timestamp_ms):
    dt_utc = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)
    dt_wib = dt_utc + timedelta(hours=7)
    bulan_indo = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agt", "Sep", "Okt", "Nov", "Des"]
    return f"{dt_wib.day:02d} {bulan_indo[dt_wib.month - 1]} {dt_wib.year}, {dt_wib.strftime('%H:%M')} WIB"

# ================= GERBANG TRANSMISI DATA UTAMA ================= #
@app.get("/sinkronisasi")
def get_sinkronisasi(lat: float = -6.9535, lon: float = 110.2312, lokasi_nama: str = "Blorok, Brangsong, Kab. Kendal"):
    list_hourly = []
    list_daily = []
    
    # KOREKSI TEMPORAL SINKRON
    now_wib = datetime.now(timezone.utc) + timedelta(hours=7)
    waktu_sekarang_str = now_wib.strftime("%Y-%m-%dT%H:00")
    
    # --- SUBSISTEM 1: TERMODINAMIKA (ATMOSFER / CUACA) ---
    try:
        meteo_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation,cloud_cover,wind_speed_10m&hourly=temperature_2m,precipitation_probability&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=Asia%2FJakarta"
        res_meteo = requests.get(meteo_url, timeout=5).json()
        
        current = res_meteo["current"]
        suhu_str = f"{current['temperature_2m']}°C"
        angin_str = f"{current['wind_speed_10m']} km/j"
        rh_str = f"{current['relative_humidity_2m']}%"
        awan_str = f"{current['cloud_cover']}%"
        presipitasi_str = f"{current['precipitation']} mm/j"

        # PROYEKSI ATMOSFER PER-JAM (6 JAM KEDEPAN)
        hourly_times = res_meteo["hourly"]["time"]
        start_idx = 0
        for idx, ht in enumerate(hourly_times):
            if ht >= waktu_sekarang_str:
                start_idx = idx
                break
                
        for i in range(start_idx, start_idx + 6):
            if i < len(hourly_times):
                dt_obj = datetime.strptime(hourly_times[i], "%Y-%m-%dT%H:%M")
                hari_indo = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"][dt_obj.weekday()]
                jam_str = f"{hari_indo}, {dt_obj.strftime('%H:%M')}"
                suhu_h = res_meteo["hourly"]["temperature_2m"][i]
                prob_h = res_meteo["hourly"]["precipitation_probability"][i]
                list_hourly.append({"waktu": jam_str, "suhu": f"{suhu_h}°C", "probabilitas_hujan": f"{prob_h}%"})

        # PROYEKSI ATMOSFER HARIAN (3 HARI KEDEPAN)
        daily_times = res_meteo["daily"]["time"]
        for i in range(1, 4):
            if i < len(daily_times):
                dt_obj = datetime.strptime(daily_times[i], "%Y-%m-%d")
                hari_indo = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"][dt_obj.weekday()]
                bulan_indo = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agt", "Sep", "Okt", "Nov", "Des"]
                tgl_str = f"{hari_indo}, {dt_obj.day} {bulan_indo[dt_obj.month - 1]}"
                
                list_daily.append({
                    "hari": tgl_str, 
                    "suhu_max": f"{res_meteo['daily']['temperature_2m_max'][i]}°C", 
                    "suhu_min": f"{res_meteo['daily']['temperature_2m_min'][i]}°C", 
                    "prob_hujan": f"{res_meteo['daily']['precipitation_probability_max'][i]}%"
                })
    except Exception:
        suhu_str = angin_str = rh_str = awan_str = presipitasi_str = "Ruptur"

    # --- SUBSISTEM 2: LITOSFER (GEODYNAMICS / GEMPA BUMI) ---
    list_domestik = []
    list_global = []
    lokal_gempa = None
    jarak_terpendek = float('inf')

    try:
        usgs_url = "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&limit=100"
        res_usgs = requests.get(usgs_url, timeout=8).json()
        
        for feature in res_usgs["features"]:
            props = feature["properties"]
            geom = feature["geometry"]["coordinates"]
            
            # Ekstraksi Koordinat Fisis Absolut
            lon_epi = float(geom[0])
            lat_epi = float(geom[1])
            kedalaman_epi = f"{float(geom[2])} km"
            
            # REKAYASA FOTON: Mengubah Halaman HTML Menjadi Tensor Citra Peta Statis Valid (.png)
            url_visual_usgs = f"https://static-maps.yandex.ru/1.x/?ll={lon_epi},{lat_epi}&z=4&l=map&pt={lon_epi},{lat_epi},pm2rdm"
            
            mag = props["mag"] if props["mag"] is not None else 0.0
            place = props["place"] or "Unknown Location"
            waktu_wib = format_waktu_wib(props["time"])
            
            jarak_fisis = hitung_jarak_haversine(lat, lon, lat_epi, lon_epi)
            nama_tempat = place.split(" of ")[-1] if " of " in place else place

            # Saringan Lokasi Terdekat dari Titik Pijak Gawai (Anchor Radar)
            if jarak_fisis < jarak_terpendek:
                jarak_terpendek = jarak_fisis
                lokal_gempa = {
                    "place": nama_tempat, 
                    "mag": mag, 
                    "dist": jarak_fisis,
                    "lat": lat_epi,
                    "lon": lon_epi,
                    "depth": kedalaman_epi,
                    "url": url_visual_usgs
                }

            # Pemetaan Distribusi Regional Domestik
            if "Indonesia" in place or "Java" in place or "Sumatra" in place or "Sulawesi" in place or jarak_fisis <= 2500.0:
                status, warna = ("[AWAS] Destruktif", "Red") if mag >= 6.0 else ("[SIAGA] Guncangan Kuat", "Orange") if mag >= 5.0 else ("[WASPADA] Aktivitas Minor", "Yellow")
                list_domestik.append({
                    "negara": "Indonesia / Perbatasan", 
                    "entitas": nama_tempat, 
                    "jenis": "Gempa Tektonik", 
                    "probabilitas": "100% Faktual", 
                    "skala": f"{mag} SR", 
                    "bahaya": status, 
                    "waktu": waktu_wib, 
                    "warna_kode": warna,
                    "latitude": lat_epi,
                    "longitude": lon_epi,
                    "kedalaman": kedalaman_epi,
                    "url_peta": url_visual_usgs
                })
            # Pemetaan Distribusi Global (M >= 5.0)
            elif mag >= 5.0:
                status, warna = ("[AWAS] Keruntuhan Fatal", "Red") if mag >= 6.0 else ("[SIAGA] Guncangan Signifikan", "Orange")
                negara = place.split(", ")[-1] if ", " in place else "Global"
                list_global.append({
                    "negara": negara, 
                    "entitas": nama_tempat, 
                    "jenis": "Gempa Tektonik", 
                    "probabilitas": "100% Faktual", 
                    "skala": f"{mag} SR", 
                    "bahaya": status, 
                    "waktu": waktu_wib, 
                    "warna_kode": warna,
                    "latitude": lat_epi,
                    "longitude": lon_epi,
                    "kedalaman": kedalaman_epi,
                    "url_peta": url_visual_usgs
                })

        # INTEGRASI STRUKTUR PENUH: Mengisi Variabel Kosong Pada Kartu Utama Beranda (Lokal)
        if lokal_gempa:
            mag_lokal, dist_lokal = lokal_gempa["mag"], lokal_gempa["dist"]
            if mag_lokal >= 6.0 and dist_lokal <= 500.0: lokal_warna, lokal_status = "Red", "[AWAS] Ruptur Destruktif Dekat!"
            elif mag_lokal >= 5.0 and dist_lokal <= 1000.0: lokal_warna, lokal_status = "Orange", "[SIAGA] Guncangan Terdeteksi!"
            elif dist_lokal <= 2000.0: lokal_warna, lokal_status = "Yellow", "[WASPADA] Domestik Terdekat"
            else: lokal_warna, lokal_status = "Green", "[INFO] Litosfer Sekitar Stabil"
            
            bencana_dict = {
                "lokasi": f"{lokal_gempa['place']} ({int(dist_lokal)} km)", 
                "skala": f"{mag_lokal} SR", 
                "status_bahaya": lokal_status, 
                "kode_warna": lokal_warna,
                "latitude": lokal_gempa["lat"],
                "longitude": lokal_gempa["lon"],
                "kedalaman": lokal_gempa["depth"],
                "url_peta": lokal_gempa["url"]
            }
        else:
            bencana_dict = {
                "lokasi": "Litosfer Stabil", "skala": "-", "status_bahaya": "Standby", "kode_warna": "Gray",
                "latitude": 0.0, "longitude": 0.0, "kedalaman": "-", "url_peta": "-"
            }
            
    except Exception:
        bencana_dict = {
            "lokasi": "Gagal Mengakses Satelit USGS", "skala": "-", "status_bahaya": "Ruptur Server", "kode_warna": "Red",
            "latitude": 0.0, "longitude": 0.0, "kedalaman": "-", "url_peta": "-"
        }

    # --- SUBSISTEM 3: STRUKTUR PENGGABUNGAN MATRIKS RESPONS JSON FINAL ---
    return {
        "meta_lokasi": lokasi_nama,
        "cuaca": {"suhu": suhu_str, "angin": angin_str, "kelembapan": rh_str, "awan": awan_str, "presipitasi": presipitasi_str},
        "proyeksi_cuaca": {"per_jam": list_hourly, "harian": list_daily},
        "bencana": bencana_dict,
        "data_domestik": list_domestik[:15],
        "data_global": list_global[:15]
    }

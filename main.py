from fastapi import FastAPI
import requests
import math
from datetime import datetime, timedelta, timezone

app = FastAPI()

# Rute Ekuilibrium Dasar (Root)
@app.get("/")
def kalibrasi_awal():
    return {
        "status": "Ekuilibrium Tercapai",
        "matriks": "Zuhri Formalism Backend Aktif",
        "ruang_waktu": "Operasional"
    }

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

# INJEKSI PARAMETER GPS DINAMIS (Default: Desa Blorok, Brangsong)
@app.get("/sinkronisasi")
def get_sinkronisasi(lat: float = -6.9535, lon: float = 110.2312, lokasi_nama: str = "Blorok, Brangsong, Kab. Kendal"):
    list_hourly = []
    list_daily = []
    
    # KALIBRASI TEMPORAL: Pembulatan Waktu Fisis Saat Ini ke Resolusi Jam (Menghilangkan Menit)
    now_wib = datetime.now(timezone.utc) + timedelta(hours=7)
    waktu_sekarang_str = now_wib.strftime("%Y-%m-%dT%H:00")
    
    try:
        meteo_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation,cloud_cover,wind_speed_10m&hourly=temperature_2m,precipitation_probability&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=Asia%2FJakarta"
        res_meteo = requests.get(meteo_url, timeout=5).json()
        
        current = res_meteo["current"]
        suhu_str = f"{current['temperature_2m']}°C"
        angin_str = f"{current['wind_speed_10m']} km/j"
        rh_str = f"{current['relative_humidity_2m']}%"
        awan_str = f"{current['cloud_cover']}%"
        presipitasi_str = f"{current['precipitation']} mm/j"

        # EKSEKUSI PROYEKSI PER-JAM (Masa Depan Mutlak)
        hourly_times = res_meteo["hourly"]["time"]
        
        # Mencari indeks satelit yang secara fisis cocok atau lebih besar dari jam saat ini
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

        # EKSEKUSI PROYEKSI HARIAN
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

    # LITOSFER USGS (DIKALIBRASI DENGAN KOORDINAT GPS BLOROK)
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
            lon_epi, lat_epi = geom[0], geom[1]
            mag = props["mag"] if props["mag"] is not None else 0.0
            place = props["place"] or "Unknown Location"
            waktu_wib = format_waktu_wib(props["time"])
            
            jarak_fisis = hitung_jarak_haversine(lat, lon, lat_epi, lon_epi)
            nama_tempat = place.split(" of ")[-1] if " of " in place else place

            if jarak_fisis < jarak_terpendek:
                jarak_terpendek = jarak_fisis
                lokal_gempa = {"place": f"{nama_tempat} ({int(jarak_fisis)} km)", "mag": mag, "dist": jarak_fisis}

            if "Indonesia" in place or "Java" in place or "Sumatra" in place or "Sulawesi" in place or jarak_fisis <= 2500.0:
                status, warna = ("[AWAS] Destruktif", "Red") if mag >= 6.0 else ("[SIAGA] Guncangan Kuat", "Orange") if mag >= 5.0 else ("[WASPADA] Aktivitas Minor", "Yellow")
                list_domestik.append({"negara": "Indonesia / Perbatasan", "entitas": f"{nama_tempat} ({int(jarak_fisis)} km)", "jenis": "Gempa Tektonik", "probabilitas": "100% Faktual", "skala": f"{mag} SR", "bahaya": status, "waktu": waktu_wib, "warna_kode": warna})
            elif mag >= 5.0:
                status, warna = ("[AWAS] Keruntuhan Fatal", "Red") if mag >= 6.0 else ("[SIAGA] Guncangan Signifikan", "Orange")
                negara = place.split(", ")[-1] if ", " in place else "Global"
                list_global.append({"negara": negara, "entitas": nama_tempat, "jenis": "Gempa Tektonik", "probabilitas": "100% Faktual", "skala": f"{mag} SR", "bahaya": status, "waktu": waktu_wib, "warna_kode": warna})

        if lokal_gempa:
            mag_lokal, dist_lokal = lokal_gempa["mag"], lokal_gempa["dist"]
            if mag_lokal >= 6.0 and dist_lokal <= 500.0: lokal_warna, lokal_status = "Red", "[AWAS] Ruptur Destruktif Dekat!"
            elif mag_lokal >= 5.0 and dist_lokal <= 1000.0: lokal_warna, lokal_status = "Orange", "[SIAGA] Guncangan Terdeteksi!"
            elif dist_lokal <= 2000.0: lokal_warna, lokal_status = "Yellow", "[WASPADA] Domestik Terdekat"
            else: lokal_warna, lokal_status = "Green", "[INFO] Litosfer Sekitar Stabil"
            lokasi_str, skala_str = lokal_gempa["place"], f"{mag_lokal} SR"
        else:
            lokasi_str, skala_str, lokal_status, lokal_warna = "Litosfer Stabil", "-", "Standby", "Gray"
    except Exception:
        lokasi_str, skala_str, lokal_status, lokal_warna = "Gagal Mengakses Satelit", "-", "Ruptur Server", "Red"

    return {
        "meta_lokasi": lokasi_nama, # Parameter dinamis baru
        "cuaca": {"suhu": suhu_str, "angin": angin_str, "kelembapan": rh_str, "awan": awan_str, "presipitasi": presipitasi_str},
        "proyeksi_cuaca": {"per_jam": list_hourly, "harian": list_daily},
        "bencana": {"lokasi": lokasi_str, "skala": skala_str, "status_bahaya": lokal_status, "kode_warna": lokal_warna},
        "data_domestik": list_domestik[:15],
        "data_global": list_global[:15]
    }

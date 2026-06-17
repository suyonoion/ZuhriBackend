from fastapi import FastAPI
import requests
import math
from datetime import datetime, timedelta, timezone

app = FastAPI()

# KOORDINAT ABSOLUT PUSAT EVALUASI SPASIAL
KENDAL_LAT = -6.92
KENDAL_LON = 110.20

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
    bulan = bulan_indo[dt_wib.month - 1]
    return f"{dt_wib.day:02d} {bulan} {dt_wib.year}, {dt_wib.strftime('%H:%M')} WIB"

@app.get("/sinkronisasi")
def get_sinkronisasi():
    # 1. EKSTRAKSI TERMODINAMIKA ATMOSFER (CURRENT, HOURLY, DAILY)
    list_hourly = []
    list_daily = []
    try:
        # Penambahan gerbang hourly dan daily dengan zona waktu fisis Asia/Jakarta
        meteo_url = f"https://api.open-meteo.com/v1/forecast?latitude={KENDAL_LAT}&longitude={KENDAL_LON}&current=temperature_2m,relative_humidity_2m,precipitation,cloud_cover,wind_speed_10m&hourly=temperature_2m,precipitation_probability&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=Asia%2FJakarta"
        res_meteo = requests.get(meteo_url, timeout=5).json()
        
        # --- A. DATA AKTUAL (NOWCAST) ---
        current = res_meteo["current"]
        raw_suhu = current["temperature_2m"]
        raw_angin = current["wind_speed_10m"]
        raw_rh = current["relative_humidity_2m"]
        raw_awan = current["cloud_cover"]
        raw_presipitasi = current["precipitation"]
        current_time = current["time"] # Contoh: "2026-06-17T14:00"
        
        suhu_str = f"{raw_suhu}°C [Ruptur Termal]" if raw_suhu >= 36.0 or raw_suhu <= 18.0 else f"{raw_suhu}°C"
        angin_str = f"{raw_angin} km/j [Anomali]" if raw_angin >= 40.0 else f"{raw_angin} km/j"
        rh_str = f"{raw_rh}%"
        awan_str = f"{raw_awan}%"
        presipitasi_str = f"{raw_presipitasi} mm/j [Deras]" if raw_presipitasi >= 10.0 else f"{raw_presipitasi} mm/j"

        # --- B. PROYEKSI PER-JAM (NEXT 6 HOURS) ---
        hourly_times = res_meteo["hourly"]["time"]
        try:
            start_idx = hourly_times.index(current_time) + 1
        except ValueError:
            start_idx = 0
            
        for i in range(start_idx, start_idx + 6):
            if i < len(hourly_times):
                jam = hourly_times[i][-5:] # Mengambil HH:MM
                suhu_h = res_meteo["hourly"]["temperature_2m"][i]
                prob_h = res_meteo["hourly"]["precipitation_probability"][i]
                list_hourly.append({"waktu": jam, "suhu": f"{suhu_h}°C", "probabilitas_hujan": f"{prob_h}%"})

        # --- C. PROYEKSI HARIAN (NEXT 3 DAYS) ---
        daily_times = res_meteo["daily"]["time"]
        for i in range(1, 4): # Melewati indeks 0 (hari ini)
            if i < len(daily_times):
                hari_date = daily_times[i][-5:] # Mengambil MM-DD
                suhu_max = res_meteo["daily"]["temperature_2m_max"][i]
                suhu_min = res_meteo["daily"]["temperature_2m_min"][i]
                prob_max = res_meteo["daily"]["precipitation_probability_max"][i]
                list_daily.append({"hari": hari_date, "suhu_max": f"{suhu_max}°C", "suhu_min": f"{suhu_min}°C", "prob_hujan": f"{prob_max}%"})
            
    except Exception:
        suhu_str = angin_str = rh_str = awan_str = presipitasi_str = "Ruptur"

    # 2. EKSTRAKSI DAN KLASIFIKASI ARRAY LITOSFER (USGS) - Tetap Utuh
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
            
            jarak_fisis = hitung_jarak_haversine(KENDAL_LAT, KENDAL_LON, lat_epi, lon_epi)
            nama_tempat = place.split(" of ")[-1] if " of " in place else place

            if jarak_fisis < jarak_terpendek:
                jarak_terpendek = jarak_fisis
                lokal_gempa = {"place": f"{nama_tempat} ({int(jarak_fisis)} km)", "mag": mag, "dist": jarak_fisis}

            if "Indonesia" in place or "Java" in place or "Sumatra" in place or "Sulawesi" in place or jarak_fisis <= 2500.0:
                if mag >= 6.0: status, warna = "[AWAS] Destruktif", "Red"
                elif mag >= 5.0: status, warna = "[SIAGA] Guncangan Kuat", "Orange"
                else: status, warna = "[WASPADA] Aktivitas Minor", "Yellow"

                list_domestik.append({
                    "negara": "Indonesia / Perbatasan", "entitas": f"{nama_tempat} ({int(jarak_fisis)} km)",
                    "jenis": "Gempa Tektonik", "probabilitas": "100% Faktual", "skala": f"{mag} SR",
                    "bahaya": status, "waktu": waktu_wib, "warna_kode": warna
                })

            elif mag >= 5.0:
                status, warna = ("[AWAS] Keruntuhan Fatal", "Red") if mag >= 6.0 else ("[SIAGA] Guncangan Signifikan", "Orange")
                negara = place.split(", ")[-1] if ", " in place else "Global"
                
                list_global.append({
                    "negara": negara, "entitas": nama_tempat, "jenis": "Gempa Tektonik",
                    "probabilitas": "100% Faktual", "skala": f"{mag} SR", "bahaya": status,
                    "waktu": waktu_wib, "warna_kode": warna
                })

        if lokal_gempa:
            mag_lokal, dist_lokal = lokal_gempa["mag"], lokal_gempa["dist"]
            if mag_lokal >= 6.0 and dist_lokal <= 500.0: lokal_warna, lokal_status = "Red", "[AWAS] Ruptur Destruktif Dekat!"
            elif mag_lokal >= 5.0 and dist_lokal <= 1000.0: lokal_warna, lokal_status = "Orange", "[SIAGA] Guncangan Terdeteksi!"
            elif dist_lokal <= 2000.0: lokal_warna, lokal_status = "Yellow", "[WASPADA] Domestik Terdekat"
            else: lokal_warna, lokal_status = "Green", "[INFO] Litosfer Sekitar Stabil"
            lokasi_str, skala_str = lokal_gempa["place"], f"{mag_lokal} SR"
        else:
            lokasi_str, skala_str, lokal_status, lokal_warna = "Litosfer Stabil", "-", "Standby", "Gray"

    except Exception as e:
        lokasi_str, skala_str, lokal_status, lokal_warna = "Gagal Mengakses Satelit", "-", "Ruptur Server", "Red"

    # 3. TRANSMISI MATRIKS FINAL MENUJU ANDROID DEVICE
    return {
        "cuaca": {
            "suhu": suhu_str,
            "angin": angin_str,
            "kelembapan": rh_str,
            "awan": awan_str,
            "presipitasi": presipitasi_str
        },
        "proyeksi_cuaca": {
            "per_jam": list_hourly,
            "harian": list_daily
        },
        "bencana": {
            "lokasi": lokasi_str,
            "skala": skala_str,
            "status_bahaya": lokal_status,
            "kode_warna": lokal_warna
        },
        "data_domestik": list_domestik[:15],
        "data_global": list_global[:15]
    }

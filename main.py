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
    """Konversi waktu satelit universal (ms) ke waktu fisis lokal WIB (UTC+7)"""
    dt_utc = datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)
    dt_wib = dt_utc + timedelta(hours=7)
    # Format bahasa Indonesia fisis: DD Mon YYYY, HH:MM WIB
    bulan_indo = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agt", "Sep", "Okt", "Nov", "Des"]
    bulan = bulan_indo[dt_wib.month - 1]
    return f"{dt_wib.day:02d} {bulan} {dt_wib.year}, {dt_wib.strftime('%H:%M')} WIB"

@app.get("/sinkronisasi")
def get_sinkronisasi():
    # 1. EKSTRAKSI TERMODINAMIKA ATMOSFER (5 PARAMETER FISIS)
    try:
        meteo_url = f"https://api.open-meteo.com/v1/forecast?latitude={KENDAL_LAT}&longitude={KENDAL_LON}&current=temperature_2m,relative_humidity_2m,precipitation,cloud_cover,wind_speed_10m"
        res_meteo = requests.get(meteo_url, timeout=5).json()
        current = res_meteo["current"]
        
        raw_suhu = current["temperature_2m"]
        raw_angin = current["wind_speed_10m"]
        raw_rh = current["relative_humidity_2m"]
        raw_awan = current["cloud_cover"]
        raw_presipitasi = current["precipitation"]
        
        suhu_str = f"{raw_suhu}°C [Ruptur Termal]" if raw_suhu >= 36.0 or raw_suhu <= 18.0 else f"{raw_suhu}°C"
        angin_str = f"{raw_angin} km/j [Anomali]" if raw_angin >= 40.0 else f"{raw_angin} km/j"
        rh_str = f"{raw_rh}%"
        awan_str = f"{raw_awan}%"
        presipitasi_str = f"{raw_presipitasi} mm/j [Deras]" if raw_presipitasi >= 10.0 else f"{raw_presipitasi} mm/j"
            
    except Exception:
        suhu_str = angin_str = rh_str = awan_str = presipitasi_str = "Ruptur"

    # 2. EKSTRAKSI DAN KLASIFIKASI ARRAY LITOSFER (USGS)
    list_domestik = []
    list_global = []
    
    # Penampung Litosfer Lokal (Prioritas Alarm)
    lokal_gempa = None
    jarak_terpendek = float('inf')

    try:
        # Menarik 100 data aktivitas seismik terbaru untuk memastikan zona global dan domestik terisi
        usgs_url = "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&limit=100"
        res_usgs = requests.get(usgs_url, timeout=8).json()
        
        for feature in res_usgs["features"]:
            props = feature["properties"]
            geom = feature["geometry"]["coordinates"]
            
            lon_epi = geom[0]
            lat_epi = geom[1]
            mag = props["mag"] if props["mag"] is not None else 0.0
            place = props["place"] or "Unknown Location"
            waktu_wib = format_waktu_wib(props["time"])
            
            jarak_fisis = hitung_jarak_haversine(KENDAL_LAT, KENDAL_LON, lat_epi, lon_epi)
            nama_tempat = place.split(" of ")[-1] if " of " in place else place

            # --- A. PENYARINGAN RADAR LOKAL (JARAK TERDEKAT) ---
            if jarak_fisis < jarak_terpendek:
                jarak_terpendek = jarak_fisis
                lokal_gempa = {
                    "place": f"{nama_tempat} ({int(jarak_fisis)} km)",
                    "mag": mag,
                    "dist": jarak_fisis
                }

            # --- B. KLASIFIKASI DOMESTIK INDONESIA ---
            if "Indonesia" in place or "Java" in place or "Sumatra" in place or "Sulawesi" in place or jarak_fisis <= 2500.0:
                # Ambang Batas Domestik
                if mag >= 6.0:
                    status = "[AWAS] Destruktif"
                    warna = "Red"
                elif mag >= 5.0:
                    status = "[SIAGA] Guncangan Kuat"
                    warna = "Orange"
                else:
                    status = "[WASPADA] Aktivitas Minor"
                    warna = "Yellow"

                list_domestik.append({
                    "negara": "Indonesia / Perbatasan",
                    "entitas": f"{nama_tempat} ({int(jarak_fisis)} km)",
                    "jenis": "Gempa Tektonik",
                    "probabilitas": "100% Faktual",
                    "skala": f"{mag} SR",
                    "bahaya": status,
                    "waktu": waktu_wib,
                    "warna_kode": warna
                })

            # --- C. KLASIFIKASI GLOBAL (ZONA MERAH & ORANYE: MAG >= 5.0) ---
            elif mag >= 5.0:
                if mag >= 6.0:
                    status = "[AWAS] Keruntuhan Fatal"
                    warna = "Red"
                else:
                    status = "[SIAGA] Guncangan Signifikan"
                    warna = "Orange"

                # Ekstraksi nama negara dari string USGS (biasanya setelah koma)
                negara = place.split(", ")[-1] if ", " in place else "Global"
                
                list_global.append({
                    "negara": negara,
                    "entitas": nama_tempat,
                    "jenis": "Gempa Tektonik",
                    "probabilitas": "100% Faktual",
                    "skala": f"{mag} SR",
                    "bahaya": status,
                    "waktu": waktu_wib,
                    "warna_kode": warna
                })

        # Finalisasi Status Lokal (Kartu Alarm)
        if lokal_gempa:
            mag_lokal = lokal_gempa["mag"]
            dist_lokal = lokal_gempa["dist"]
            if mag_lokal >= 6.0 and dist_lokal <= 500.0:
                lokal_warna = "Red"
                lokal_status = "[AWAS] Ruptur Destruktif Dekat!"
            elif mag_lokal >= 5.0 and dist_lokal <= 1000.0:
                lokal_warna = "Orange"
                lokal_status = "[SIAGA] Guncangan Terdeteksi!"
            elif dist_lokal <= 2000.0:
                lokal_warna = "Yellow"
                lokal_status = "[WASPADA] Domestik Terdekat"
            else:
                lokal_warna = "Green"
                lokal_status = "[INFO] Litosfer Sekitar Stabil"
                
            lokasi_str = lokal_gempa["place"]
            skala_str = f"{mag_lokal} SR"
        else:
            lokasi_str = "Litosfer Stabil"
            skala_str = "-"
            lokal_status = "Standby"
            lokal_warna = "Gray"

    except Exception as e:
        lokasi_str = "Gagal Mengakses Satelit"
        skala_str = "-"
        lokal_status = "Ruptur Server"
        lokal_warna = "Red"

    # 3. TRANSMISI MATRIKS FINAL MENUJU ANDROID DEVICE
    return {
        "cuaca": {
            "suhu": suhu_str,
            "angin": angin_str,
            "kelembapan": rh_str,
            "awan": awan_str,
            "presipitasi": presipitasi_str
        },
        "bencana": {
            "lokasi": lokasi_str,
            "skala": skala_str,
            "status_bahaya": lokal_status,
            "kode_warna": lokal_warna
        },
        "data_domestik": list_domestik[:15], # Batasi maksimal 15 data agar memori UI tidak terbebani
        "data_global": list_global[:15]
    }

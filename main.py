from fastapi import FastAPI
import requests
import math

app = FastAPI()

# KOORDINAT ABSOLUT PUSAT EVALUASI SPASIAL (KENDAL, JAWA TENGAH)
KENDAL_LAT = -6.92
KENDAL_LON = 110.20

def hitung_jarak_haversine(lat1, lon1, lat2, lon2):
    """
    Rumus fisis kelengkungan bumi untuk menghitung jarak absolut (Radius = 6371 km)
    Menghasilkan output jarak dalam satuan Kilometer (km).
    """
    R = 6371.0 
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

@app.get("/sinkronisasi")
def get_sinkronisasi():
    # 1. EKSTRAKSI DAN EVALUASI MATRIKS ATMOSFER (OPEN-METEO)
    try:
        meteo_url = f"https://api.open-meteo.com/v1/forecast?latitude={KENDAL_LAT}&longitude={KENDAL_LON}&current=temperature_2m,wind_speed_10m"
        res_meteo = requests.get(meteo_url, timeout=5).json()
        raw_suhu = res_meteo["current"]["temperature_2m"]
        raw_angin = res_meteo["current"]["wind_speed_10m"]
        
        # Penilaian Parameter Termodinamika ZF
        if raw_suhu >= 36.0 or raw_suhu <= 18.0:
            suhu_str = f"{raw_suhu}°C [Ruptur Termal]"
        else:
            suhu_str = f"{raw_suhu}°C"
            
        if raw_angin >= 40.0:
            angin_str = f"{raw_angin} km/j [Anomali Kinetik]"
        else:
            angin_str = f"{raw_angin} km/j"
            
    except Exception:
        suhu_str = "-"
        angin_str = "-"

    # 2. EKSTRAKSI DAN EVALUASI MATRIKS LITOSFER (USGS - GEOPARSING)
    try:
        # Menarik 10 data aktivitas seismik terbaru di seluruh kerak bumi
        usgs_url = "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&limit=10"
        res_usgs = requests.get(usgs_url, timeout=5).json()
        
        target_gempa = None
        jarak_terpendek = float('inf')
        
        # Pemindaian Spasial: Mencari peristiwa terdekat atau yang paling berdampak secara fisis
        for feature in res_usgs["features"]:
            lon_episentrum = feature["geometry"]["coordinates"][0]
            lat_episentrum = feature["geometry"]["coordinates"][1]
            mag = feature["properties"]["mag"]
            place = feature["properties"]["place"] or "Unknown Location"
            
            jarak_fisis = hitung_jarak_haversine(KENDAL_LAT, KENDAL_LON, lat_episentrum, lon_episentrum)
            
            # Prioritas internal: Kunci peristiwa terdekat ke koordinat gawai
            if jarak_fisis < jarak_terpendek:
                jarak_terpendek = jarak_fisis
                target_gempa = {
                    "place": place,
                    "mag": mag,
                    "distance": jarak_fisis
                }
        
        if target_gempa:
            mag = target_gempa["mag"]
            dist = target_gempa["distance"]
            place = target_gempa["place"]
            
            # PROSES PENILAIAN THRESHOLD MATRIKS LOKAL (ZUHRI FORMALISM LOGIC)
            if mag >= 6.0 and dist <= 500.0:
                kode_warna = "Red"
                status = "[AWAS] Ruptur Destruktif Radius Dekat!"
            elif mag >= 5.0 and dist <= 1000.0:
                kode_warna = "Orange"
                status = "[SIAGA] Guncangan Signifikan Terdeteksi!"
            elif "Indonesia" in place or "Java" in place or dist <= 2000.0:
                kode_warna = "Yellow"
                status = "[WASPADA] Aktivitas Seismik Domestik"
            else:
                kode_warna = "Green"
                status = "[INFO] Getaran Jauh / Aman"
            
            # Format pemangkasan string lokasi agar pas dengan resolusi layar gawai
            nama_tempat = place.split(" of ")[-1] if " of " in place else place
            lokasi_str = f"{nama_tempat} ({int(dist)} km)"
            skala_str = f"{mag} SR"
        else:
            lokasi_str = "Litosfer Stabil"
            skala_str = "-"
            status = "Standby"
            kode_warna = "Gray"
            
    except Exception as e:
        lokasi_str = "Gagal Mengakses Satelit"
        skala_str = "-"
        status = "Ruptur Server"
        kode_warna = "Red"

    # TRANSMISI MATRIKS FINAL MENUJU ANDROID DEVICE
    return {
        "cuaca": {
            "suhu": suhu_str,
            "angin": angin_str
        },
        "bencana": {
            "lokasi": lokasi_str,
            "skala": skala_str,
            "status_bahaya": status,
            "kode_warna": kode_warna
        }
    }

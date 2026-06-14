from fastapi import FastAPI
import httpx
import asyncio

# Inisiasi Arsitektur Peladen
app = FastAPI(title="ZF Matriks Peladen")

@app.get("/")
def kalibrasi_awal():
    return {
        "status": "Ekuilibrium Tercapai",
        "matriks": "Zuhri Formalism Backend Aktif",
        "ruang_waktu": "Operasional"
    }

# Rute Transmisi Absolut untuk Android Widget
@app.get("/spasial/sinkronisasi")
async def get_sinkronisasi_matriks():
    # Koordinat Satelit Barat
    cuaca_url = "https://api.open-meteo.com/v1/forecast?latitude=-6.92&longitude=110.20&current_weather=true"
    gempa_url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson"

    # Penarikan Data Paralel (Asinkron)
    async with httpx.AsyncClient() as client:
        try:
            cuaca_req, gempa_req = await asyncio.gather(
                client.get(cuaca_url),
                client.get(gempa_url)
            )
            cuaca_data = cuaca_req.json()
            gempa_data = gempa_req.json()
        except Exception as e:
            return {"error": "Ruptur Transmisi Satelit"}

    # 1. Ekstraksi Parameter Termal
    try:
        suhu = cuaca_data["current_weather"]["temperature"]
        angin = cuaca_data["current_weather"]["windspeed"]
    except:
        suhu = "Distorsi"
        angin = "Distorsi"

    # 2. Ekstraksi Ruptur Litosfer & Translasi Publik
    lokasi = "Nihil Gempa Signifikan"
    skala = "-"
    status = "Aman"
    warna = "Green"

    features = gempa_data.get("features", [])
    if features:
        # Protokol Urgensi: Mengurutkan dari Skala Terbesar
        features.sort(key=lambda x: x["properties"]["mag"], reverse=True)
        ruptur = features[0]["properties"]
        
        # Lapis Translasi Lokasi (Filter ' of ')
        raw_lokasi = ruptur["place"]
        if " of " in raw_lokasi:
            lokasi = raw_lokasi.split(" of ")[-1][:25] + "..."
        else:
            lokasi = raw_lokasi[:25] + "..."
            
        mag = ruptur["mag"]
        skala = f"{mag} SR"
        
        # Batasan Formal Indikator Visual
        if mag >= 6.0:
            status = "[AWAS] Potensi Merusak!"
            warna = "Red"
        elif mag >= 5.0:
            status = "[WASPADA] Getaran Kuat"
            warna = "Orange"
        else:
            status = "[INFO] Getaran Ringan"
            warna = "Yellow"

    # Kompresi Data menjadi satu entitas fisis untuk Android
    return {
        "cuaca": {
            "suhu": f"{suhu}°C",
            "angin": f"{angin} km/j"
        },
        "bencana": {
            "lokasi": lokasi,
            "skala": skala,
            "status_bahaya": status,
            "kode_warna": warna
        }
    }

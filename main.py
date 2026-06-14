from fastapi import FastAPI

# Inisiasi Arsitektur Peladen
app = FastAPI(title="ZF Matriks Peladen")

# Rute Ekuilibrium Dasar (Root)
@app.get("/")
def kalibrasi_awal():
    return {
        "status": "Ekuilibrium Tercapai",
        "matriks": "Zuhri Formalism Backend Aktif",
        "ruang_waktu": "Operasional"
    }

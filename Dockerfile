# Matriks Kontainer Dasar (Python Steril)
FROM python:3.10-slim

# Menetapkan Ruang Isolasi
WORKDIR /code

# Injeksi Pustaka Mesin
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Menyalin Seluruh Matriks Logika Pusat
COPY . /code/

# Batasan Formal HF Spaces: Wajib berekspansi di Port 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]

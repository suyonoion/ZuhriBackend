# Matriks Kontainer Dasar (Python Steril)
FROM python:3.10-slim

# Injeksi Batasan Formal Keamanan HF (UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# Menetapkan Ruang Isolasi
WORKDIR /code

# Injeksi Pustaka Mesin
COPY --chown=user ./requirements.txt /code/
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Menyalin Seluruh Matriks Logika Pusat
COPY --chown=user . /code/

# Eksekusi di Port 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]

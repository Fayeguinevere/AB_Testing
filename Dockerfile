# 1. Gebruik een officiële Python-basisimage
FROM python:3.11-slim

# 2. Stel werkdirectory in binnen de container
WORKDIR /app

# 3. Kopieer alle bestanden naar de container
COPY . .

# 4. Installeer Python-afhankelijkheden
RUN pip install --no-cache-dir -r requirements.txt

# 5. Geef aan dat de app draait op poort 5000
EXPOSE 5000

# 6. Start de app met gunicorn (production server)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]

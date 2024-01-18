FROM python:3.9.18-bullseye 
RUN apt update && apt upgrade -y
RUN apt install -y\
    tesseract-ocr\
    tesseract-ocr-rus\
    libgl1

WORKDIR /app
COPY . .
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt
ENTRYPOINT python main.py
#FROM python:3.8-alpine3.14
FROM python:3.9.5-slim
ENV PYHTONUNBUFFERED=1
RUN apt-get update && apt-get -y install zbar-tools tesseract-ocr

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt
COPY . .
EXPOSE 3000
CMD ["uvicorn", "controller:app", "--port", "3000", "--host", "0.0.0.0"]
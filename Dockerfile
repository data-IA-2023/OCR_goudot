FROM python:3.9.5

ENV PYHTONUNBUFFERED=1
RUN apt-get update && apt-get -y install zbar-tools tesseract-ocr imagemagick
RUN apt-get -y install curl
RUN sh -c "curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -" \
    && apt-get update \
    && sh -c "curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list" \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt
COPY . .
EXPOSE 3000
CMD ["uvicorn", "controller:app", "--port", "3000", "--host", "0.0.0.0"]
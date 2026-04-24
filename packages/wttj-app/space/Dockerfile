FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./app.py

EXPOSE 7860

HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/_stcore/health')"

CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]

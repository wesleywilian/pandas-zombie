FROM python:3.8-bullseye

COPY main.py ./
COPY requirements.txt ./

RUN pip install -r requirements.txt
CMD python3 main.py

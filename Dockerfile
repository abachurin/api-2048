FROM python:3.11-slim-buster

WORKDIR /code
COPY requirements.txt ./requirements.txt
RUN apt-get update -y && apt-get install -y gcc
RUN pip3 install -r requirements.txt
COPY . .

ENV PYTHONPATH /code
RUN export PYTHONPATH=.
EXPOSE 5000
ENTRYPOINT ["python3"]
CMD ["main.py"]

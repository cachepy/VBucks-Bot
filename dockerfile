FROM python:3.10.8

RUN apt-get update
WORKDIR /usr/app

COPY  requirements.txt .

RUN pip install -r requirements.txt

COPY src/ .

CMD [ "python", "error.py" ]

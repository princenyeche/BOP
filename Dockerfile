FROM python:3.12.0a3-slim-bullseye

WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . .

EXPOSE 5000
CMD [ "/bin/sh", "runit.sh"]

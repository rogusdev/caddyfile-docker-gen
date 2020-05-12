FROM python:3.8.2-alpine3.11

WORKDIR /app

COPY ./requirements.txt ./requirements.txt
RUN pip install -r ./requirements.txt

COPY . ./

ENTRYPOINT [ "python" ]
CMD [ "src/app.py" ]

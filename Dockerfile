FROM python:3.12-slim

WORKDIR /stromvarsel

RUN --mount=type=bind,source=requirements.txt,target=requirements.txt \
pip install -r requirements.txt

COPY stromvarsel.py stromvarsel.py

CMD python stromvarsel.py
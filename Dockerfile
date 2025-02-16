FROM python:3.12

RUN mkdir -p /usr/src/app
COPY requirements.txt /usr/src/app/requirements.txt
WORKDIR /usr/src/app/
RUN pip install -r requirements.txt

COPY . /usr/src/app/
ENV PYTHONPATH "${PYTHONPATH}:/usr/src/app/"
CMD python main.py

FROM python:3.8.1-slim-buster

ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=cpp

USER root

WORKDIR /libs

COPY . /libs
RUN mkdir -p /libs/src/models
RUN mkdir -p /libs/src/data

RUN apt-get update
RUN apt-get install libgomp1
RUN pip install --upgrade pip
RUN pip install -U jupyter jupyter_contrib_nbextensions
COPY ./requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN jupyter nbextension enable --py widgetsnbextension

EXPOSE 8080

ENV BUILD_MODE=local
ENV SVC_NAME=churn-prediction-challenge
ENV JUPYTER_ENABLE_LAB=yes

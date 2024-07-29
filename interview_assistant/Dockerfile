FROM python:3.10-slim-bullseye

ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=cpp
WORKDIR /app

# Copy the rest of the application code into the container
COPY . /app
RUN pip install --upgrade pip
RUN apt-get update
RUN pip install -U jupyter jupyter_contrib_nbextensions
COPY ./requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN pip install protobuf==3.20.0

COPY ./src /app
# Expose the port the app runs on
EXPOSE 8080

ENV BUILD_MODE=local
ENV SVC_NAME=interview_assistant
ENV JUPYTER_ENABLE_LAB=yes

# Command to run the app
CMD ["python", "src/interview_assistant/main.py"]
FROM python

## Install SSH client
RUN apt-get update && apt-get install openssh-client && apt-get clean

## Initialize Pipenv environment
RUN pip install pipenv

WORKDIR /sentrynet

COPY Pipfile .
COPY Pipfile.lock .
RUN pipenv sync

## Now copy the source and your supplied config.yaml
COPY . .

RUN pipenv run python -m compileall .

ENTRYPOINT pipenv run python main.py config.yaml
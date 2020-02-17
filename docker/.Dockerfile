FROM continuumio/miniconda3

ENV ARGS=''

COPY . /app
WORKDIR /app

RUN conda install -c openbabel openbabel

RUN pip install requests
RUN pip install nanome

CMD python run.py ${ARGS}
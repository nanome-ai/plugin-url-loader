FROM continuumio/miniconda3

ENV PLUGIN_SERVER=plugins.nanome.ai

COPY . /app
WORKDIR /app

RUN conda install -c openbabel openbabel

RUN pip install requests
RUN pip install nanome

CMD python -m nanome_url_loader.URLLoader -a ${PLUGIN_SERVER}
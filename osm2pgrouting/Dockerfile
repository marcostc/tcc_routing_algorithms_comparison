FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependências necessárias
RUN apt-get update && \
    apt-get install -y software-properties-common wget gnupg2 dos2unix && \
    add-apt-repository ppa:ubuntugis/ppa && \
    apt-get update && \
    apt-get install -y osm2pgrouting postgresql-client && \
    rm -rf /var/lib/apt/lists/*

COPY wait-for-db-and-import.sh /wait-for-db-and-import.sh

# Converter finais de linha e definir permissão de execução
RUN dos2unix /wait-for-db-and-import.sh && \
    chmod +x /wait-for-db-and-import.sh

ENTRYPOINT ["/wait-for-db-and-import.sh"]

# proj/db/Dockerfile

FROM postgres:13

RUN apt-get update && \
    apt-get install -y postgis postgresql-13-postgis-3 postgresql-13-pgrouting osm2pgrouting

COPY init-db.sh /docker-entrypoint-initdb.d/init-db.sh
COPY rio_de_janeiro_parte.osm /data/rio_de_janeiro_parte.osm
COPY mapconfig.xml /data/mapconfig.xml

RUN chmod +x /docker-entrypoint-initdb.d/init-db.sh


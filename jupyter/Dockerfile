# proj/jupyter/Dockerfile

FROM jupyter/datascience-notebook

RUN pip install psycopg2-binary geopandas folium geopy

COPY notebooks/ /home/jovyan/work/

FROM jupyter/datascience-notebook

# Copiar o arquivo requirements.txt para o contêiner
COPY requirements.txt /tmp/

# Instalar as dependências Python
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copiar os notebooks para o diretório de trabalho do Jupyter
COPY notebooks/ /home/jovyan/work/

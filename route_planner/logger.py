# route_planner/logger.py

import logging
import os

def setup_logger(name, log_file, level=logging.INFO):
    """
    Configura um logger para gravar mensagens em um arquivo.

    Args:
        name (str): Nome do logger.
        log_file (str): Caminho do arquivo de log.
        level (int): Nível de logging.
    """
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler = logging.FileHandler(log_file)        
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger

# Configurar o logger principal
logger = setup_logger('route_planner', os.path.join(os.getcwd(), 'route_planner.log'))

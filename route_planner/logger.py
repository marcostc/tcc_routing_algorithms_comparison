# route_planner/logger.py

import logging

def setup_logger(name='route_planner', log_file='route_planner.log', level=logging.INFO):
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    # Evitar duplicação de logs
    logger.propagate = False

    return logger

logger = setup_logger()

# route_planner/main.py

import sys

import warnings
import logging

from route_planner.logger import logger
from route_planner.gui import RoutePlannerGUI

# Configurar o logger para capturar warnings
logging.captureWarnings(True)
warnings.simplefilter("default")  # Ajustar o filtro de warnings conforme necessário

# Obter o logger para warnings
warnings_logger = logging.getLogger("py.warnings")
warnings_logger.propagate = False  # Impedir que o logger de warnings envie mensagens para outros loggers

# Adicionar um manipulador para o logger de warnings
handler = logging.FileHandler('route_planner.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
warnings_logger.addHandler(handler)

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("Exceção não tratada", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

if __name__ == "__main__":
    RoutePlannerGUI()

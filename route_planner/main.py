# route_planner/main.py

import sys

from route_planner.logger import logger

from route_planner.gui import RoutePlannerGUI

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("Exceção não tratada", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

if __name__ == "__main__":
    RoutePlannerGUI()

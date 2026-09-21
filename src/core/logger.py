import logging
import os
from datetime import datetime

def setup_logger():
    # Ensure logs directory exists if we want to save to file
    # For now, print to console
    logger = logging.getLogger("PCSystem")
    logger.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    
    logger.addHandler(ch)
    return logger

logger = setup_logger()

import logging
import sys

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("pdf_utils").setLevel(logging.WARNING)
    logging.getLogger("pyhanko").setLevel(logging.WARNING)
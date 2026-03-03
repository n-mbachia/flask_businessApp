import logging
import os
from logging.handlers import RotatingFileHandler

class LoggingUtility:
    def __init__(self, app):
        self.app = app

    def configure_logging(self):
        """Configure application logging."""
        if not self.app.debug:
            if not os.path.exists('logs'):
                os.mkdir('logs')
            
            file_handler = RotatingFileHandler(
                'logs/app.log',
                maxBytes=10240,
                backupCount=10
            )
            
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            
            file_handler.setLevel(logging.INFO)
            self.app.logger.addHandler(file_handler)
            self.app.logger.setLevel(logging.INFO)
            self.app.logger.info('BusinessApp startup')
        
        # Set log level for all loggers to WARNING by default
        logging.basicConfig(level=logging.WARNING)
        
        # Set SQLAlchemy log level to WARNING to reduce noise
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
        
        # Set application logger level based on config
        if self.app.config.get('DEBUG'):
            self.app.logger.setLevel(logging.DEBUG)
            logging.basicConfig(level=logging.DEBUG)
        else:
            self.app.logger.setLevel(logging.INFO)
            logging.basicConfig(level=logging.INFO)

def configure_logging(app):
    logging_utility = LoggingUtility(app)
    logging_utility.configure_logging()

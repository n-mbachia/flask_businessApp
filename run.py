# run.py
import os
from dotenv import load_dotenv

# Load environment variables BEFORE importing app
load_dotenv()

from app import create_app, socketio

app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    if socketio is not None:
        socketio.run(app, debug=app.config.get('DEBUG', False))
    else:
        app.run()

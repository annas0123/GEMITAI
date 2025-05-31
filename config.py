import os

class Config:
    """Flask application configuration class."""
    # General configuration
    SECRET_KEY = 'your-secret-key'  # Change this in production
    MAX_CONTENT_LENGTH = 1024 * 1024 * 1024  # Limit uploads to 1GB
    
    @staticmethod
    def init_app(app):
        """Initialize application with the configuration."""
        # Make sure required directories exist
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        if not os.path.exists(app.config['OUTPUT_FOLDER']):
            os.makedirs(app.config['OUTPUT_FOLDER'])
        if not os.path.exists(app.config['PROCESSED_FOLDER']):
            os.makedirs(app.config['PROCESSED_FOLDER']) 
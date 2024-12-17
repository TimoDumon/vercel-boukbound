import os

class Config:
    # Secret key for security (used for sessions, CSRF, etc.)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key'
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres.hstybmdnkrtrsejimvei:KlctEw4xeCGGCZNd@aws-0-eu-central-1.pooler.supabase.com:6543/postgres'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # CSRF protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.environ.get('WTF_CSRF_SECRET_KEY') or 'a-different-random-string'

    # File upload configuration
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')  # Folder to store uploaded files
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Maximum file size: 16 MB

    # Allowed file extensions for uploads
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

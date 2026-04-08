from app import app

# Vercel Python runtime expects a module-level `app` (WSGI callable).
# Re-exporting keeps the existing Flask app unchanged.

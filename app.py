import os

from expense_tracker import create_app

if __name__ == "__main__":
    # Running this file starts the local debug server, so default to development.
    # Gunicorn imports app:app instead and gets production unless APP_ENV says otherwise.
    os.environ.setdefault("APP_ENV", "development")

# Served by gunicorn as "app:app".
app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])

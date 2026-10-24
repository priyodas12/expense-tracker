from expense_tracker import create_app

# Served by gunicorn as "app:app". Set APP_ENV=production there.
app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])

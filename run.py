from app import create_app
from app.model import User, db
from flask import redirect,url_for
app = create_app()
@app.route('/')
def index():
    return redirect(url_for('auth.login'))
@app.cli.command()
def initdb():
    """Initialize the database."""
    db.create_all()
    print('Database initialized')

if __name__ == '__main__':
    app.run(debug=True)
from flask import Blueprint, render_template

# Create a Blueprint object to group together related routes (views)
# 'dashboard' is the blueprints's name. and __name__ tells Flask where the code lives 
bp = Blueprint('dashboard', __name__)

@bp.route('/') # Register this function to handle GET requests to the root path '/'
def index():
    """
    Render the main index page.
    Visiting '/' in your browser will return the 'index.html' template.
    """
    return render_template('index.html') # Look into your templates folder for index.html template

@bp.route('/dashboard') # Register this function to handel GET requests to  /dashbaord
def dashboard():
    return render_template('dashboard.html') # Look into your templates/ folder for dashboard.html

@bp.route('/contact') # Register this function to handle GET requests to /contact
def contact():
    return render_template('contact.html') # Look into your templates/ folder for contact.html

@bp.route('/analytics') # Register this function to handle GET requests to /analytics
def analytics():
    return render_template('analytics/index.html') # Look into your templates/analytics/ folder for index.html

@bp.route('/incidents') # Register this function to handle GET requests to /incidents
def incidents():
    return render_template('incidents/index.html') # Look into your templates/incidents/ folder for index.html

@bp.route('/upload') # Register this function to handle GET requests to /upload
def upload():
    return render_template('upload.html') # Look into your templates/ folder for upload.html

@bp.route('/futures') # Register this function to handle GET requests to /futures
def futures():
    return render_template('futures.html') # Look into your templates/ folder for futures.html

@bp.route('/brokerage') # Register this function to handle GET requests to /brokerage
def brokerage():
    return render_template('brokerage.html') # Look into your templates/ folder for brokerage.html
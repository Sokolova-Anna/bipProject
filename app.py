from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import logging
from flask_cors import CORS
import pyotp
import qrcode
from io import BytesIO
from flask import send_file
from flask_swagger_ui import get_swaggerui_blueprint
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

logging.basicConfig(level=logging.DEBUG)

UPLOADED_PHOTOS = 'uploaded_photos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app = Flask(__name__)

CORS(app)

# Configure PostgreSQL database
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://pawuser:123456@localhost/pawpath_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = '93fb0ec21dd9e5a9d28dbfbdf9988c9cbfd185abf1a8f1f2'
app.config['UPLOAD_FOLDER'] = '/home/user_bip/bip_proj/paw-path/uploaded_photos'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to login if not authenticated

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

# Swagger configuration
SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.yaml'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': "PawPath API"}
)

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

@app.route('/static/swagger.yaml')
def swagger_yaml():
    return send_from_directory('.', 'swagger.yaml')

# Define the User model with Flask-Login's UserMixin
class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    login = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    pet_name = db.Column(db.String(50), nullable=True)
    pet_breed = db.Column(db.String(50), nullable=True)
    totp_secret = db.Column(db.String(100), nullable=True)
    banned = db.Column(db.Boolean, default=False, nullable=False)
    role = db.Column(db.String(10), default="user")

    def __init__(self, name, email, login, password, pet_name, pet_breed, role):
        self.name = name
        self.email = email
        self.login = login
        self.password = password
        self.pet_name = pet_name
        self.pet_breed = pet_breed
        self.totp_secret = pyotp.random_base32()
        self.banned = False
        self.role = role

# Define the MapLocation model
class MapLocation(db.Model):
    __tablename__ = 'map_locations'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    place_type = db.Column(db.String(50), nullable=False)
    verified = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(self, title, description, latitude, longitude, place_type, verified=False):
        self.title = title
        self.description = description
        self.latitude = latitude
        self.longitude = longitude
        self.place_type = place_type
        self.verified = verified

# Define the Review model
class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Float, nullable=False)
    text = db.Column(db.Text, nullable=True)
    photo = db.Column(db.String(255), nullable=True)
    confirmed = db.Column(db.Boolean, default=False, nullable=False)  # Add confirmed field

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('reviews', lazy=True))

    map_location_id = db.Column(db.Integer, db.ForeignKey('map_locations.id'), nullable=False)
    map_location = db.relationship('MapLocation', backref=db.backref('reviews', lazy=True))

    def __init__(self, rating, text, photo, user_id, map_location_id):
        self.rating = rating
        self.text = text
        self.photo = photo
        self.user_id = user_id
        self.map_location_id = map_location_id
        self.confirmed = False  # Default is unconfirmed

# Define the ReviewPhoto model to store multiple photos for each review
class ReviewPhoto(db.Model):
    __tablename__ = 'review_photos'

    id = db.Column(db.Integer, primary_key=True)
    photo = db.Column(db.String(255), nullable=False)

    review_id = db.Column(db.Integer, db.ForeignKey('reviews.id'), nullable=False)
    review = db.relationship('Review', backref=db.backref('photos', lazy=True))

    def __init__(self, photo, review_id):
        self.photo = photo
        self.review_id = review_id

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class MapLocationPhoto(db.Model):
    __tablename__ = 'location_photos'

    id = db.Column(db.Integer, primary_key=True)
    photo = db.Column(db.String(255), nullable=False)
    map_location_id = db.Column(db.Integer, db.ForeignKey('map_locations.id'), nullable=False)

    map_location = db.relationship('MapLocation', backref=db.backref('photos', lazy=True))

    def __init__(self, photo, map_location_id):
        self.photo = photo
        self.map_location_id = map_location_id

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/reviews', methods=['POST'])
@login_required
def create_review():
    rating = float(request.form.get('rating'))
    text = request.form.get('text')
    user_id = current_user.id
    map_location_id = request.form.get('map_location_id')

    new_review = Review(
        rating=rating,
        text=text,
        user_id=user_id,
        map_location_id=map_location_id
    )

    db.session.add(new_review)
    db.session.commit()

    # Create a folder for the specific review
    review_folder = os.path.join(app.config['UPLOAD_FOLDER'], f'review_{new_review.id}')
    if not os.path.exists(review_folder):
        os.makedirs(review_folder)

    photo_paths = []
    # Handle multiple photos
    if 'photos' in request.files:
        for file in request.files.getlist('photos'):
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(review_folder, filename)
                file.save(filepath)
                photo_paths.append(filepath)  # Store full file paths for each photo

                # Create an entry in the review_photos table for each photo
                new_photo = ReviewPhoto(photo=filepath, review_id=new_review.id)
                db.session.add(new_photo)

    db.session.commit()

    return jsonify({
        'message': 'Review created successfully!',
        'photo_paths': photo_paths  # Return full paths to the user
    }), 201

@app.route('/admin/get_unconfirmed_reviews', methods=['GET'])
@login_required
def get_unconfirmed_reviews():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized access'}), 403
    try:
        unconfirmed_reviews = Review.query.filter_by(confirmed=False).all()

        reviews_list = [{
            'id': review.id,
            'rating': review.rating,
            'text': review.text,
            'photo': review.photo,
            'user_id': review.user_id,
            'map_location_id': review.map_location_id
        } for review in unconfirmed_reviews]

        return jsonify(reviews_list), 200
    except Exception as e:
        logging.exception("Error retrieving unconfirmed reviews")
        return jsonify({'error': 'Failed to retrieve reviews'}), 500

@app.route('/admin/confirm_review/<int:review_id>', methods=['POST'])
@login_required
def confirm_review(review_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized access'}), 403
    try:
        review = Review.query.get(review_id)
        if not review:
            return jsonify({'error': 'Review not found'}), 404

        review.confirmed = True
        db.session.commit()

        return jsonify({'message': f'Review {review_id} has been confirmed successfully.'}), 200
    except Exception as e:
        logging.exception("Error confirming review")
        return jsonify({'error': 'Failed to confirm review', 'details': str(e)}), 500

@app.route('/get_reviews', methods=['GET'])
def get_reviews():
    try:
        reviews = Review.query.filter_by(confirmed=True).all()  # Only get confirmed reviews

        reviews_list = [{
            'id': review.id,
            'rating': review.rating,
            'text': review.text,
            'photo': review.photo,
            'user_id': review.user_id,
            'map_location_id': review.map_location_id
        } for review in reviews]

        return jsonify(reviews_list), 200
    except Exception as e:
        logging.exception("Error retrieving reviews")
        return jsonify({'error': 'Failed to retrieve reviews'}), 500


# Registration route
@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        login = data.get('login')
        password = data.get('password')
        pet_name = data.get('pet_name')
        pet_breed = data.get('pet_breed')

        if not name or not email or not login or not password:
            return jsonify({'error': 'Missing required fields'}), 400

        if User.query.filter_by(email=email).first() or User.query.filter_by(login=login).first():
            return jsonify({'error': 'User already exists'}), 400

        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

        new_user = User(
            name=name,
            email=email,
            login=login,
            password=password_hash,
            pet_name=pet_name,
            pet_breed=pet_breed,
            role="user"
        )

        db.session.add(new_user)
        db.session.commit()

        return jsonify({'message': 'User registered successfully!', 'user_id': new_user.id}), 201

    except Exception as e:
        logging.exception("Error during registration")
        return jsonify({'error': 'Something went wrong'}), 500

# Login route
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    login = data.get('login')
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(login=login, email=email).first()

    if user and bcrypt.check_password_hash(user.password, password):
        if user.banned:
            return jsonify({'error': 'You have been banned'}), 403
        
        # Log the user in using Flask-Login
        login_user(user)
        
        return jsonify({'message': 'Login successful, please verify with TOTP', 'user_id': user.id, 'role': user.role}), 200
    else:
        return jsonify({'error': 'Invalid credentials'}), 400

# QR code generation route
@app.route('/generate_qr/<int:user_id>')
def generate_qr(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    totp = pyotp.TOTP(user.totp_secret)
    uri = totp.provisioning_uri(user.email, issuer_name="PawPath")

    img = qrcode.make(uri)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return send_file(buf, mimetype="image/png")

# TOTP verification route
@app.route('/verify_totp', methods=['POST'])
def verify_totp():
    data = request.get_json()
    user_id = data.get('user_id')
    totp_code = data.get('totp_code')

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    totp = pyotp.TOTP(user.totp_secret)
    if totp.verify(totp_code):
        return jsonify({'message': 'TOTP verified successfully!'}), 200
    else:
        return jsonify({'error': 'Invalid TOTP code'}), 400

# Admin route - protected with login_required
@app.route('/admin')
@login_required
def admin_panel():
    if current_user.role == 'admin':
        return send_from_directory('frontend', 'admin.html')
    else:
        return jsonify({'error': 'Unauthorized access'}), 403

# Logout route
@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out successfully'}), 200

# Block user route - protected with login_required and admin role check
@app.route('/admin/block_user/<int:user_id>', methods=['POST'])
@login_required
def block_user(user_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized access'}), 403
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if user.banned:
            return jsonify({'message': 'User is already banned'}), 400

        user.banned = True
        db.session.commit()

        return jsonify({'message': f'User {user_id} has been banned successfully.'}), 200
    except Exception as e:
        logging.exception("Error during blocking user")
        return jsonify({'error': 'Failed to block user', 'details': str(e)}), 500

# Unblock user route - protected with login_required and admin role check
@app.route('/admin/unblock_user/<int:user_id>', methods=['POST'])
@login_required
def unblock_user(user_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized access'}), 403
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if not user.banned:
            return jsonify({'message': 'User is not banned'}), 400

        user.banned = False
        db.session.commit()

        return jsonify({'message': f'User {user_id} has been unbanned successfully.'}), 200
    except Exception as e:
        logging.exception("Error during unblocking user")
        return jsonify({'error': 'Failed to unblock user', 'details': str(e)}), 500

# Save location route
@app.route('/save_location', methods=['POST'])
@login_required
def save_location():
    try:
        # Collect form data
        data = request.form
        title = data.get('title')
        description = data.get('description')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        place_type = data.get('place_type')

        # Validate the data
        if not title or not latitude or not longitude or not place_type:
            return jsonify({'error': 'Missing required fields'}), 400

        # Create the new MapLocation instance
        new_location = MapLocation(
            title=title,
            description=description,
            latitude=latitude,
            longitude=longitude,
            place_type=place_type
        )

        # Save the location to the database
        db.session.add(new_location)
        db.session.commit()

        # Create a folder for the specific location to store photos
        location_folder = os.path.join(app.config['UPLOADED_PHOTOS'], f'location_{new_location.id}')
        if not os.path.exists(location_folder):
            os.makedirs(location_folder)

        photo_paths = []
        # Handle multiple photo uploads
        if 'photos' in request.files:
            for file in request.files.getlist('photos'):
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(location_folder, filename)
                    file.save(filepath)
                    photo_paths.append(filepath)

                    # Create an entry in the MapLocationPhoto table for each photo
                    new_photo = MapLocationPhoto(photo=filepath, map_location_id=new_location.id)
                    db.session.add(new_photo)

        db.session.commit()

        return jsonify({
            'message': 'Location saved successfully!',
            'photo_paths': photo_paths  # Return the full file paths to the user
        }), 201

    except Exception as e:
        logging.exception("Error during saving location")
        return jsonify({'error': 'Failed to save location', 'details': str(e)}), 500

# Retrieve verified locations
@app.route('/get_locations', methods=['GET'])
def get_locations():
    try:
        # Fetch all verified locations
        locations = MapLocation.query.filter_by(verified=True).all()

        locations_list = []
        for loc in locations:
            # Fetch associated photos for each location
            photos = [photo.photo for photo in loc.photos]

            locations_list.append({
                'id': loc.id,
                'title': loc.title,
                'description': loc.description,
                'latitude': loc.latitude,
                'longitude': loc.longitude,
                'place_type': loc.place_type,
                'photos': photos  # Include photo paths in the response
            })

        return jsonify(locations_list), 200
    except Exception as e:
        logging.exception("Error retrieving locations")
        return jsonify({'error': 'Failed to retrieve locations'}), 500

# Get unverified locations - admin only
@app.route('/admin/get_unverified_locations', methods=['GET'])
@login_required
def get_unverified_locations():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized access'}), 403
    try:
        unverified_locations = MapLocation.query.filter_by(verified=False).all()

        locations_list = [{
            'id': loc.id,
            'title': loc.title,
            'description': loc.description,
            'latitude': loc.latitude,
            'longitude': loc.longitude,
            'place_type': loc.place_type
        } for loc in unverified_locations]

        return jsonify(locations_list), 200
    except Exception as e:
        logging.exception("Error retrieving unverified locations")
        return jsonify({'error': 'Failed to retrieve locations'}), 500

# Verify location - admin only
@app.route('/admin/verify_location/<int:location_id>', methods=['POST'])
@login_required
def verify_location(location_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized access'}), 403
    try:
        location = MapLocation.query.get(location_id)
        if not location:
            return jsonify({'error': 'Location not found'}), 404

        location.verified = True
        db.session.commit()

        return jsonify({'message': f'Location {location_id} has been verified successfully.'}), 200
    except Exception as e:
        logging.exception("Error verifying location")
        return jsonify({'error': 'Failed to verify location', 'details': str(e)}), 500

# Serve index page
@app.route('/')
def serve_index():
    return send_from_directory('frontend', 'index.html')

# Serve admin page
@app.route('/admin')
@login_required
def admin():
    if current_user.role == 'admin':
        return send_from_directory('frontend', 'admin.html')
    else:
        return jsonify({'error': 'Unauthorized access'}), 403

# Serve static files
@app.route('/<path:path>')
def serve_static_files(path):
    return send_from_directory('frontend', path)

# Start the Flask app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')


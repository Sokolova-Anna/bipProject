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

logging.basicConfig(level=logging.DEBUG)


app = Flask(__name__)

CORS(app)

# Configure PostgreSQL database
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://pawuser:123456@localhost/pawpath_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Swagger configuration
SWAGGER_URL = '/swagger'  # Swagger UI will be available at localhost:5000/swagger
API_URL = '/static/swagger.yaml'  # Path to the Swagger YAML file

# Swagger UI blueprint setup
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': "PawPath API"}
)

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

@app.route('/static/swagger.yaml')
def swagger_yaml():
    return send_from_directory('.', 'swagger.yaml')

# Define the User model
class User(db.Model):

    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    login = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    pet_name = db.Column(db.String(50), nullable=True)
    pet_breed = db.Column(db.String(50), nullable=True)
    totp_secret = db.Column(db.String(100), nullable=True)  # TOTP
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

    def __init__(self, title, description, latitude, longitude, place_type):
        self.title = title
        self.description = description
        self.latitude = latitude
        self.longitude = longitude
        self.place_type = place_type


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

        # Add the new user to the database
        db.session.add(new_user)
        db.session.commit()

        return jsonify({'message': 'User registered successfully!', 'user_id': new_user.id}), 201

    except Exception as e:
        logging.exception("Error during registration")
        return jsonify({'error': 'Something went wrong'}), 500

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
        # Return a prompt for TOTP verification
        return jsonify({'message': 'Login successful, please verify with TOTP', 'user_id': user.id, 'role': user.role}), 200
    else:
        return jsonify({'error': 'Invalid credentials'}), 400


@app.route('/generate_qr/<int:user_id>')
def generate_qr(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Generate the TOTP URI
    totp = pyotp.TOTP(user.totp_secret)
    uri = totp.provisioning_uri(user.email, issuer_name="PawPath")

    # Create a QR code
    img = qrcode.make(uri)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return send_file(buf, mimetype="image/png")

@app.route('/verify_totp', methods=['POST'])
def verify_totp():
    data = request.get_json()
    user_id = data.get('user_id')
    totp_code = data.get('totp_code')

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Verify the TOTP code using the stored totp_secret
    totp = pyotp.TOTP(user.totp_secret)
    if totp.verify(totp_code):
        return jsonify({'message': 'TOTP verified successfully!'}), 200
    else:
        return jsonify({'error': 'Invalid TOTP code'}), 400
    

@app.route('/admin/block_user/<int:user_id>', methods=['POST'])
def block_user(user_id):
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
    

@app.route('/admin/unblock_user/<int:user_id>', methods=['POST'])
def unblock_user(user_id):
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


@app.route('/save_location', methods=['POST'])
def save_location():
    try:
        data = request.get_json()
        title = data.get('title')
        description = data.get('description')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        place_type = data.get('place_type')

        # Validate the data
        if not title or not latitude or not longitude or not place_type:
            return jsonify({'error': 'Missing required fields'}), 400

        # Create a new map location object
        new_location = MapLocation(
            title=title,
            description=description,
            latitude=latitude,
            longitude=longitude,
            place_type=place_type
        )

        # Save the new location to the database
        db.session.add(new_location)
        db.session.commit()

        return jsonify({'message': 'Location saved successfully!'}), 201

    except Exception as e:
        logging.exception("Error during saving location")  # This logs the detailed error
        return jsonify({'error': 'Failed to save location', 'details': str(e)}), 500

@app.route('/get_locations', methods=['GET'])
def get_locations():
    try:
        # Fetch all locations from the database
        locations = MapLocation.query.all()

        # Convert the location objects to a list of dictionaries
        locations_list = [{
            'id': loc.id,
            'title': loc.title,
            'description': loc.description,
            'latitude': loc.latitude,
            'longitude': loc.longitude,
            'place_type': loc.place_type
        } for loc in locations]

        return jsonify(locations_list), 200
    except Exception as e:
        logging.exception("Error retrieving locations")
        return jsonify({'error': 'Failed to retrieve locations'}), 500

@app.route('/')
def serve_index():
    return send_from_directory('frontend', 'index.html')

@app.route('/admin')
def admin_panel():
	return send_from_directory('frontend', 'admin.html')


@app.route('/<path:path>')
def serve_static_files(path):
    return send_from_directory('frontend', path)

# Start the Flask app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')



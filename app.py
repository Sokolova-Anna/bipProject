from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import logging
from flask_cors import CORS
import pyotp
import qrcode
from io import BytesIO
from flask import send_file

logging.basicConfig(level=logging.DEBUG)


app = Flask(__name__)

CORS(app)

# Configure PostgreSQL database
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://pawuser:123456@localhost/pawpath_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

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

    def __init__(self, name, email, login, password, pet_name, pet_breed):
        self.name = name
        self.email = email
        self.login = login
        self.password = password
        self.pet_name = pet_name
        self.pet_breed = pet_breed
        self.totp_secret = pyotp.random_base32()

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
            pet_breed=pet_breed
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
        # Return a prompt for TOTP verification
        return jsonify({'message': 'Login successful, please verify with TOTP', 'user_id': user.id}), 200
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

@app.route('/')
def serve_index():
    return send_from_directory('frontend', 'index.html')

@app.route('/<path:path>')
def serve_static_files(path):
    return send_from_directory('frontend', path)

# Start the Flask app
if __name__ == '__main__':
    app.run(debug=True)


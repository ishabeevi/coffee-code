from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bloodapp.db'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# ---------------------
# Database Model
# ---------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    blood_group = db.Column(db.String(10))
    location = db.Column(db.String(100))
    contact = db.Column(db.String(15))
    password = db.Column(db.String(200))
# ---------------------
# Blood Request Model
# ---------------------
class BloodRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blood_group = db.Column(db.String(10))
    location = db.Column(db.String(100))
    hospital = db.Column(db.String(100))
    emergency = db.Column(db.Boolean, default=False)
# ---------------------
# Home Route
# ---------------------
@app.route('/')
def home():
    return "Blood Donation App"

# ---------------------
# Register Route
# ---------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_pw = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        
        new_user = User(
            name=request.form['name'],
            blood_group=request.form['blood_group'],
            location=request.form['location'],
            contact=request.form['contact'],
            password=hashed_pw
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect('/login')
    
    return render_template('register.html')

# ---------------------
# Login Route
# ---------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(contact=request.form['contact']).first()
        
        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            return "Login Successful!"
        else:
            return "Invalid Credentials"
    
    return render_template('login.html')

# ---------------------
# Run App
# ---------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
# ---------------------
# Create Blood Request
# ---------------------
@app.route('/request', methods=['GET', 'POST'])
def create_request():
    if request.method == 'POST':
        new_request = BloodRequest(
            blood_group=request.form['blood_group'],
            location=request.form['location'],
            hospital=request.form['hospital'],
            emergency=True if request.form.get('emergency') else False
        )

        db.session.add(new_request)
        db.session.commit()

        return redirect('/requests')

    return render_template('request.html')
# ---------------------
# View Requests
# ---------------------
@app.route('/requests')
def view_requests():
    all_requests = BloodRequest.query.all()
    return render_template('view_requests.html', requests=all_requests)
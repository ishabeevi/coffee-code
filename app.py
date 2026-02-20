from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import date, timedelta
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bloodapp_secret_2025'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bloodapp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# ─────────────────────────────────────────────
# Blood Group Compatibility Map
# ─────────────────────────────────────────────
COMPATIBLE_DONORS = {
    'A+':  ['A+', 'A-', 'O+', 'O-'],
    'A-':  ['A-', 'O-'],
    'B+':  ['B+', 'B-', 'O+', 'O-'],
    'B-':  ['B-', 'O-'],
    'AB+': ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'],
    'AB-': ['A-', 'B-', 'AB-', 'O-'],
    'O+':  ['O+', 'O-'],
    'O-':  ['O-'],
}

# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────
class User(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    name           = db.Column(db.String(100), nullable=False)
    blood_group    = db.Column(db.String(10),  nullable=False)
    location       = db.Column(db.String(100), nullable=False)
    contact        = db.Column(db.String(15),  unique=True, nullable=False)
    password       = db.Column(db.String(200), nullable=False)
    available      = db.Column(db.Boolean, default=True)
    last_donation  = db.Column(db.Date, nullable=True)
    points         = db.Column(db.Integer, default=0)

    @property
    def can_donate(self):
        """Returns True if 90 days have passed since last donation (or never donated)."""
        if self.last_donation is None:
            return True
        return (date.today() - self.last_donation).days >= 90


class BloodRequest(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    blood_group  = db.Column(db.String(10),  nullable=False)
    location     = db.Column(db.String(100), nullable=False)
    hospital     = db.Column(db.String(100), nullable=False)
    emergency    = db.Column(db.Boolean, default=False)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at   = db.Column(db.Date, default=date.today)
    requester    = db.relationship('User', backref='requests')


# ─────────────────────────────────────────────
# Helper: get logged-in user
# ─────────────────────────────────────────────
def current_user():
    if 'user_id' in session:
        return db.session.get(User, session['user_id'])
    return None

# ─────────────────────────────────────────────
# Home
# ─────────────────────────────────────────────
@app.route('/')
def home():
    user = current_user()
    return render_template('index.html', user=user)

# ─────────────────────────────────────────────
# Register
# ─────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Check contact uniqueness
        existing = User.query.filter_by(contact=request.form['contact']).first()
        if existing:
            flash('Contact already registered. Please login.', 'error')
            return redirect(url_for('register'))

        hashed_pw = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        last_don = None
        raw_date = request.form.get('last_donation', '').strip()
        if raw_date:
            try:
                last_don = date.fromisoformat(raw_date)
            except ValueError:
                pass

        new_user = User(
            name          = request.form['name'],
            blood_group   = request.form['blood_group'].strip().upper(),
            location      = request.form['location'].strip().lower(),
            contact       = request.form['contact'].strip(),
            password      = hashed_pw,
            available     = True,
            last_donation = last_don,
            points        = 0
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Registered successfully! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# ─────────────────────────────────────────────
# Login
# ─────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(contact=request.form['contact'].strip()).first()
        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(url_for('home'))
        flash('Invalid contact or password.', 'error')

    return render_template('login.html')

# ─────────────────────────────────────────────
# Logout
# ─────────────────────────────────────────────
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('home'))

# ─────────────────────────────────────────────
# Post Blood Request
# ─────────────────────────────────────────────
@app.route('/request', methods=['GET', 'POST'])
def create_request():
    user = current_user()
    if not user:
        flash('Please login to post a blood request.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_req = BloodRequest(
            blood_group  = request.form['blood_group'].strip().upper(),
            location     = request.form['location'].strip().lower(),
            hospital     = request.form['hospital'].strip(),
            emergency    = (request.form.get('urgency') == 'emergency'),
            requester_id = user.id
        )
        db.session.add(new_req)
        db.session.commit()
        flash('Blood request posted!', 'success')
        return redirect(url_for('view_requests'))

    return render_template('request.html', user=user)

# ─────────────────────────────────────────────
# View All Requests (with tab: all / emergency)
# ─────────────────────────────────────────────
@app.route('/requests')
def view_requests():
    user = current_user()
    tab = request.args.get('tab', 'all')

    emergency_requests = BloodRequest.query.filter_by(emergency=True).order_by(BloodRequest.created_at.desc()).all()
    all_requests       = BloodRequest.query.order_by(BloodRequest.emergency.desc(), BloodRequest.created_at.desc()).all()

    return render_template('view_requests.html',
                           user=user,
                           all_requests=all_requests,
                           emergency_requests=emergency_requests,
                           tab=tab)

# ─────────────────────────────────────────────
# Smart Matching
# ─────────────────────────────────────────────
@app.route('/match/<int:req_id>')
def match_donors(req_id):
    user = current_user()
    blood_req = db.session.get(BloodRequest, req_id)
    if not blood_req:
        flash('Request not found.', 'error')
        return redirect(url_for('view_requests'))

    compatible_types = COMPATIBLE_DONORS.get(blood_req.blood_group, [blood_req.blood_group])

    # Fetch all available donors with compatible blood group
    candidates = User.query.filter(
        User.blood_group.in_(compatible_types),
        User.available == True
    ).all()

    # Filter: must satisfy 90-day rule; same location gets prioritized
    same_location = []
    other_location = []

    for donor in candidates:
        if not donor.can_donate:
            continue
        if donor.location.strip().lower() == blood_req.location.strip().lower():
            same_location.append(donor)
        else:
            other_location.append(donor)

    # Sort each group: emergency requests → higher points donors first
    key_fn = lambda d: -d.points
    same_location.sort(key=key_fn)
    other_location.sort(key=key_fn)

    matched_donors = same_location + other_location

    return render_template('match.html',
                           user=user,
                           blood_req=blood_req,
                           matched_donors=matched_donors)

# ─────────────────────────────────────────────
# Donate (marks donation, awards points)
# ─────────────────────────────────────────────
@app.route('/donate/<int:req_id>')
def donate(req_id):
    user = current_user()
    if not user:
        flash('Please login to donate.', 'error')
        return redirect(url_for('login'))

    blood_req = db.session.get(BloodRequest, req_id)
    if not blood_req:
        flash('Request not found.', 'error')
        return redirect(url_for('view_requests'))

    if not user.can_donate:
        days_left = 90 - (date.today() - user.last_donation).days
        flash(f'You must wait {days_left} more day(s) before donating again (90-day rule).', 'error')
        return redirect(url_for('match_donors', req_id=req_id))

    # Award points
    pts = 15 if blood_req.emergency else 10
    user.points += pts
    user.last_donation = date.today()
    db.session.commit()

    flash(f'🎉 Thank you for donating! You earned +{pts} points.', 'success')
    return redirect(url_for('leaderboard'))

# ─────────────────────────────────────────────
# Toggle Availability
# ─────────────────────────────────────────────
@app.route('/toggle-availability')
def toggle_availability():
    user = current_user()
    if not user:
        flash('Please login first.', 'error')
        return redirect(url_for('login'))

    user.available = not user.available
    db.session.commit()
    status = 'Available' if user.available else 'Not Available'
    flash(f'Your status is now: {status}', 'success')
    return redirect(url_for('profile'))

# ─────────────────────────────────────────────
# Profile
# ─────────────────────────────────────────────
@app.route('/profile')
def profile():
    user = current_user()
    if not user:
        flash('Please login first.', 'error')
        return redirect(url_for('login'))
    return render_template('profile.html', user=user)

# ─────────────────────────────────────────────
# Leaderboard
# ─────────────────────────────────────────────
@app.route('/leaderboard')
def leaderboard():
    user = current_user()
    top_donors = User.query.order_by(User.points.desc()).limit(20).all()
    return render_template('leaderboard.html', user=user, top_donors=top_donors)

# ─────────────────────────────────────────────
# Groups
# ─────────────────────────────────────────────
@app.route('/groups')
def groups():
    user = current_user()
    all_users = User.query.all()

    # Group by blood_group + location
    groups_data = {}
    for u in all_users:
        key = (u.blood_group.upper(), u.location.strip().lower().title())
        if key not in groups_data:
            groups_data[key] = []
        groups_data[key].append(u)

    # Sort keys: blood group alphabetically
    sorted_groups = sorted(groups_data.items(), key=lambda x: (x[0][0], x[0][1]))

    return render_template('groups.html', user=user, groups=sorted_groups)


# ─────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

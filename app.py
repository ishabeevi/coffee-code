from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import date, timedelta, datetime
import os
from sqlalchemy import inspect as sa_inspect, text

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'bloodapp_secret_2025')

# Use PostgreSQL on Render (DATABASE_URL env var), else fall back to SQLite locally
_db_url = os.environ.get('DATABASE_URL', 'sqlite:///bloodapp.db')
# Render sets postgres:// but SQLAlchemy requires postgresql://
if _db_url.startswith('postgres://'):
    _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = _db_url
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
    available_toggle = db.Column('available', db.Boolean, default=True)
    last_donation  = db.Column(db.Date, nullable=True)
    points         = db.Column(db.Integer, default=0)
    dob            = db.Column(db.Date, nullable=True)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)

    @property
    def age(self):
        """Returns the donor's age in years, or None if dob is not set."""
        if self.dob is None:
            return None
        today = date.today()
        return today.year - self.dob.year - (
            (today.month, today.day) < (self.dob.month, self.dob.day)
        )

    @property
    def age_eligible(self):
        """Returns True if donor is between 18 and 50 years old."""
        if self.age is None:
            return True  # no dob set – don't block
        return 18 <= self.age <= 50

    @property
    def can_donate(self):
        """Returns True if age-eligible AND 90 days have passed since last donation."""
        if not self.age_eligible:
            return False
        if self.last_donation is None:
            return True
        return (date.today() - self.last_donation).days >= 90

    @property
    def available(self):
        """Final availability: manual toggle MUST be On AND donor must be eligible to donate."""
        return self.available_toggle and self.can_donate


class BloodRequest(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    blood_group  = db.Column(db.String(10),  nullable=False)
    location     = db.Column(db.String(100), nullable=False)
    hospital     = db.Column(db.String(100), nullable=False)
    emergency    = db.Column(db.Boolean, default=False)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at   = db.Column(db.Date, default=date.today)
    requester    = db.relationship('User', backref='requests')

    def __init__(self, **kwargs):
        super(BloodRequest, self).__init__(**kwargs)


class Notification(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message    = db.Column(db.String(500), nullable=False)
    req_id     = db.Column(db.Integer, db.ForeignKey('blood_request.id'), nullable=True)
    is_read    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user       = db.relationship('User', backref='notifications')

    def __init__(self, **kwargs):
        super(Notification, self).__init__(**kwargs)


# ─────────────────────────────────────────────
# Helper: get logged-in user
# ─────────────────────────────────────────────
def current_user():
    if 'user_id' in session:
        return db.session.get(User, session['user_id'])
    return None

def get_compatible_donors(blood_group, location):
    compatible_types = COMPATIBLE_DONORS.get(blood_group, [blood_group])
    # Case-insensitive location match
    loc = location.strip().lower()
    return User.query.filter(
        User.blood_group.in_(compatible_types),
        User.location == loc,
        User.available_toggle == True
    ).all()

@app.context_processor
def inject_notifications():
    user = current_user()
    if user:
        unread_count = Notification.query.filter_by(user_id=user.id, is_read=False).count()
        return dict(unread_count=unread_count)
    return dict(unread_count=0)

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

        dob = None
        raw_dob = request.form.get('dob', '').strip()
        if raw_dob:
            try:
                dob = date.fromisoformat(raw_dob)
            except ValueError:
                pass

        new_user = User(
            name          = request.form['name'],
            blood_group   = request.form['blood_group'].strip().upper(),
            location      = request.form['location'].strip().lower(),
            contact       = request.form['contact'].strip(),
            password      = hashed_pw,
            available_toggle = True,
            last_donation = last_don,
            points        = 0,
            dob           = dob
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

        # Send notifications to compatible donors in the same location
        compatible = get_compatible_donors(new_req.blood_group, new_req.location)
        for donor in compatible:
            if donor.id != user.id: # Don't notify the requester
                msg = f"🚨 URGENT: {new_req.blood_group} donor needed at {new_req.hospital}!" if new_req.emergency else f"🩸 Blood Request: {new_req.blood_group} needed at {new_req.hospital}."
                notif = Notification(
                    user_id=donor.id,
                    message=msg,
                    req_id=new_req.id
                )
                db.session.add(notif)
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
        User.available_toggle == True
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

    if not user.age_eligible:
        flash(f'Sorry, donors must be between 18 and 50 years old. Your age ({user.age}) does not meet the eligibility criteria.', 'error')
        return redirect(url_for('match_donors', req_id=req_id))

    if not user.can_donate:
        days_left = 90 - (date.today() - user.last_donation).days
        flash(f'You must wait {days_left} more day(s) before donating again (90-day / 3-month rule).', 'error')
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

    user.available_toggle = not user.available_toggle
    db.session.commit()
    status = 'Available' if user.available else 'Not Available'
    if user.available_toggle and not user.can_donate:
        flash(f'Toggle set to On, but your status remains "{status}" due to donation cooldown.', 'success')
    else:
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
    return render_template('profile.html', user=user, today=date.today())

@app.route('/profile/<int:user_id>')
def public_profile(user_id):
    current_u = current_user()
    target_user = db.session.get(User, user_id)
    if not target_user:
        flash('Donor not found.', 'error')
        return redirect(url_for('groups'))
    
    return render_template('public_profile.html', 
                           user=current_u, 
                           target_user=target_user, 
                           today=date.today())

# ─────────────────────────────────────────────
# Leaderboard
# ─────────────────────────────────────────────
@app.route('/leaderboard')
def leaderboard():
    user = current_user()
    top_donors = User.query.order_by(User.points.desc()).limit(20).all()
    return render_template('leaderboard.html', user=user, top_donors=top_donors)

# ─────────────────────────────────────────────
# Notifications
# ─────────────────────────────────────────────
@app.route('/notifications')
def notifications():
    user = current_user()
    if not user:
        flash('Please login to view notifications.', 'error')
        return redirect(url_for('login'))
    
    # Get all notifications for the user, latest first
    all_notifs = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', user=user, notifications=all_notifs)

@app.route('/notifications/read/<int:notif_id>')
def read_notification(notif_id):
    user = current_user()
    if not user:
        return redirect(url_for('login'))
    
    notif = db.session.get(Notification, notif_id)
    if notif and notif.user_id == user.id:
        notif.is_read = True
        db.session.commit()
        if notif.req_id:
            return redirect(url_for('match_donors', req_id=notif.req_id))
    
    return redirect(url_for('notifications'))

@app.route('/notifications/read-all')
def read_all_notifications():
    user = current_user()
    if not user:
        return redirect(url_for('login'))
    
    Notification.query.filter_by(user_id=user.id, is_read=False).update({Notification.is_read: True})
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('notifications'))

# ─────────────────────────────────────────────
# Groups
# ─────────────────────────────────────────────
@app.route('/groups')
def groups():
    user = current_user()
    all_users = User.query.all()

    # Group primarily by location
    groups_data = {}
    for u in all_users:
        loc = u.location.strip().lower().title()
        if loc not in groups_data:
            groups_data[loc] = []
        groups_data[loc].append(u)

    # Sort locations alphabetically
    sorted_locations = sorted(groups_data.items(), key=lambda x: x[0])

    return render_template('groups.html', user=user, groups=sorted_locations)


# ─────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────
if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # ── Auto-migrate: add any missing columns so the DB never gets out of sync ──
        inspector = sa_inspect(db.engine)

        existing_user_cols = {c['name'] for c in inspector.get_columns('user')}
        if 'dob' not in existing_user_cols:
            db.session.execute(text('ALTER TABLE "user" ADD COLUMN dob DATE'))
            db.session.commit()
            print('[migration] Added column: user.dob')

        existing_req_cols = {c['name'] for c in inspector.get_columns('blood_request')}
        # Add future BloodRequest columns here the same way if needed

        # Re-create all tables at least once to ensure Notification table exists
        db.create_all()

    app.run(debug=True)

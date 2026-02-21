<p align="center">
  <img src="./img.png" alt="Project Banner" width="100%">
</p>

# LifeLink 🎯

## Basic Details

### Team Name: Coffee & Code

### Team Members
- Member 1: Ayisha Beevi A S - College of Engineering Attingal
- Member 2: Asna Sajeer - College of Engineering Attingal

### Hosted Project Link
[https://coffee-code-z4wg.onrender.com/register](https://coffee-code-z4wg.onrender.com/register)

### Project Description
LifeLink is an intelligent blood donation finder app that creates an efficient connection between seekers and donors. It transforms the act of donation into a rewarding experience through its gamified points system.

### The Problem statement
Finding a donor during an emergency is often critical and difficult. Traditional social media posts are inefficient and often fail to reach eligible donors in real-time. LifeLink solves this by providing a dedicated platform for instant matching.

### The Solution
We created a platform that connects patients in need with compatible donors instantly. The app features a points-based achievement system (Gamification) to encourage regular donations and build a committed community of life-savers.

---

## Technical Details

### Technologies/Components Used

**For Software:**
- Languages used: Python (Flask), HTML, CSS (Vanilla), JavaScript
- Frameworks used: Flask
- Libraries used: Flask-SQLAlchemy, Flask-Bcrypt, Datetime, SQLAlchemy
- Tools used: Antigravity AI, VS Code, Git, GitHub
- Database used: SQLite

---

## Features

Key features of LifeLink:
- **Registration and Login**: Secure user accounts with contact-based login.
- **Donor Availability Status**: Automatic 90-day cooldown tracking and manual availability toggle.
- **Points & Leaderboard System**: Donors earn points for every donation, competing on a global leaderboard.
- **Blood Request and Notification System**: Real-time notifications for donors compatible with new requests.
- **Emergency Blood Request Highlighting**: Urgent requests are prioritized and specially flagged.
- **Proactive Compatibility Matching**: Smart filtering based on blood group compatibility (e.g., O- can donate to all).

---

## Implementation

### For Software:

#### Installation
```bash
# Clone the repository
git clone https://github.com/ishabeevi/coffee-code.git
cd coffee-code

# install dependencies
pip install flask flask-sqlalchemy flask-bcrypt sqlalchemy
```

#### Run
```bash
python app.py
```

---

## Project Documentation

### For Software:

#### Screenshots
<img src="Screenshot 2026-02-21 082357.png">
<img src="Screenshot 2026-02-21 100710.png">
<img src="Screenshot 2026-02-21 082428.png">

#### Diagrams

**System Architecture:**
LifeLink follows a **Client-Server Architecture**. The Flask backend interacts with an SQLite database via SQLAlchemy ORM. The frontend is served using Jinja2 templates for dynamic content rendering.

**Application Workflow:**
1. User registers/logs in as a Donor.
2. Recipient posts a Blood Request (Emergency/Normal).
3. System matches compatible donors in the same location and sends Notifications.
4. Donor views the request and contacts the recipient.
5. After a successful donation, the donor earns points and enters a 90-day cooldown.

---

## Additional Documentation

### For Web Projects with Backend:

#### API Documentation

**Base URL:** `http://127.0.0.1:5000`

##### Endpoints

**POST /register**
- **Description:** Register a new donor.
- **Parameters:** `name`, `blood_group`, `location`, `contact`, `password`, `dob`, `last_donation`.

**POST /login**
- **Description:** Login to the donor account.
- **Parameters:** `contact`, `password`.

**POST /request**
- **Description:** Post a new blood request.
- **Parameters:** `blood_group`, `location`, `hospital`, `urgency`.

**GET /match/<int:req_id>**
- **Description:** Find matched donors for a specific request.
- **Response:** List of compatible and eligible donors.

**GET /toggle-availability**
- **Description:** Manually toggle the donor's availability status.

---

## AI Tools Used (Optional)

**Tool Used:** Antigravity AI (Google DeepMind)

**Purpose:** 
- Assisted in the design of the **Pastel Pink Cute Theme**.
- Implemented the **90-day cooldown logic** and **Notification system**.
- Optimized the **Location-based grouping** for donor communities.

**Percentage of AI-generated code:** ~70% (Assisted development)

**Human Contributions:**
- Feature ideation and problem scoping.
- UI/UX preferences and theme selection.
- Database schema conceptualization.
- Verification and testing.

---

## Team Contributions

- Ayisha Beevi A S: Backend development, API integration, and database management.
- Asna Sajeer: UI/UX design, documentation, and frontend implementation.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
## video
https://drive.google.com/file/d/1Kdtim0xN_Aa-A0lDoQ9K-xxIo1T4ZvkE/view?usp=sharing

Made with ❤️ at TinkerHub

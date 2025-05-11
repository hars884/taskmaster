from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    tasks = db.relationship('Task', backref='author', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140))
    description = db.Column(db.Text)
    deadline = db.Column(db.DateTime)
    reminder_sent = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    category = db.Column(db.String(20))  # daily, weekly, monthly, yearly, once
    repeat_days = db.Column(db.String(20))  # comma-separated days for weekly (e.g., "mon,wed,fri")
    reminder_type = db.Column(db.String(20))  # one_day, one_week, one_month, custom
    custom_reminder_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    completed = db.Column(db.Boolean, default=False)
    valid_until = db.Column(db.DateTime, nullable=True)
    logs = db.relationship('TaskLog', backref='task', lazy='dynamic')

    def should_remind(self):
        if self.completed:
            return False
            
        now = datetime.utcnow()
        if self.reminder_type == 'one_day' and not self.reminder_sent:
            return self.deadline - timedelta(days=1) <= now < self.deadline
        elif self.reminder_type == 'one_week' and not self.reminder_sent:
            return self.deadline - timedelta(weeks=1) <= now < self.deadline - timedelta(weeks=1) + timedelta(minutes=5)
        elif self.reminder_type == 'one_month' and not self.reminder_sent:
            return self.deadline - timedelta(days=30) <= now < self.deadline - timedelta(days=30) + timedelta(minutes=5)
        elif self.reminder_type == 'custom' and self.custom_reminder_date and not self.reminder_sent:
            return self.custom_reminder_date <= now < self.custom_reminder_date + timedelta(minutes=5)
        return False

    def is_recurring(self):
        return self.category in ['daily', 'weekly', 'monthly', 'yearly']
    
class MemorableDay(db.Model):
    __tablename__ = 'memorable_days'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140))
    date = db.Column(db.Date)
    reminder_days_before = db.Column(db.Integer)  # How many days before to remind
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    valid_until = db.Column(db.Date)

    def should_remind(self):
        today = datetime.utcnow().date()
        anniversary = self.date.replace(year=today.year)
        
        # Handle cases where the anniversary is in the next year
        if anniversary < today:
            anniversary = anniversary.replace(year=today.year + 1)
        
        days_until = (anniversary - today).days
        return days_until == self.reminder_days_before
class TaskLog(db.Model):
    __tablename__ = 'task_logs'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

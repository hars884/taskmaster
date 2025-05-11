from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Task, MemorableDay, TaskLog
from datetime import datetime, timedelta
import os
from werkzeug.security import generate_password_hash, check_password_hash
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///taskmaster.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper functions
def parse_repeat_days(form_data):
    days = []
    weekdays = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']
    for day in weekdays:
        if form_data.get(f'repeat_{day}'):
            days.append(day)
    return ','.join(days) if days else None

def calculate_next_deadline(task):
    """Calculate next deadline for recurring tasks"""
    if not check_task_validity(task):
        return None
        
    if task.category == 'daily':
        return task.deadline + timedelta(days=1)
    elif task.category == 'weekly' and task.repeat_days:
        current_weekday = task.deadline.weekday()
        days = task.repeat_days.split(',')
        day_indices = {'sun': 6, 'mon': 0, 'tue': 1, 'wed': 2, 
                      'thu': 3, 'fri': 4, 'sat': 5}
        
        for i in range(1, 8):
            next_day_index = (current_weekday + i) % 7
            for day in days:
                if day_indices[day] == next_day_index:
                    return task.deadline + timedelta(days=i)
    elif task.category == 'monthly':
        return task.deadline + timedelta(days=30)
    elif task.category == 'yearly':
        return task.deadline + timedelta(days=365)
    return None

def check_task_validity(task):
    """Check if task is still valid based on valid_until"""
    if task.valid_until is None:  # Lifelong
        return True
    return datetime.utcnow() < task.valid_until

def check_memorable_day_validity(day):
    """Check if memorable day is still valid based on valid_until"""
    if day.valid_until is None:  # Lifelong
        return True
    return datetime.utcnow().date() < day.valid_until

def check_incomplete_tasks():
    with app.app_context():
        now = datetime.utcnow()
        end_of_day = datetime(now.year, now.month, now.day, 23, 59, 59)
        
        if now.hour == 23 and now.minute >= 55:  # Run at 23:55
            tasks = Task.query.filter(
                Task.user_id == current_user.id,
                Task.deadline <= end_of_day,
                Task.completed == False,
                (Task.valid_until.is_(None) | (Task.valid_until >= now))
            ).all()
            
            for task in tasks:
                log = TaskLog(
                    task_id=task.id,
                    user_id=current_user.id,
                    notes="Not completed by deadline",
                    completed_at=now
                )
                db.session.add(log)
                
                if task.is_recurring() and check_task_validity(task):
                    new_deadline = calculate_next_deadline(task)
                    if new_deadline:
                        new_task = Task(
                            title=task.title,
                            description=task.description,
                            deadline=new_deadline,
                            user_id=task.user_id,
                            category=task.category,
                            repeat_days=task.repeat_days,
                            reminder_type=task.reminder_type,
                            custom_reminder_date=task.custom_reminder_date,
                            valid_until=task.valid_until,
                            reminder_sent=False,
                            completed=False
                        )
                        db.session.add(new_task)
            
            db.session.commit()

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_incomplete_tasks, trigger='cron', hour=23, minute=55)
scheduler.start()

# Auth routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Task routes
@app.route('/')
@login_required
def index():
    now = datetime.utcnow()
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.deadline).all()
    
    # Check for reminders
    for task in tasks:
        if task.should_remind():
            flash(f'Reminder: Task "{task.title}" is due soon!', 'info')
            task.reminder_sent = True
            db.session.commit()
    
    return render_template('index.html', tasks=tasks, now=now)

@app.route('/task/add', methods=['GET', 'POST'])
@login_required
def add_task():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        deadline_str = request.form['deadline']
        category = request.form['category']
        reminder_type = request.form['reminder_type']
        valid_until_str = request.form.get('valid_until')
        
        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
            valid_until = datetime.strptime(valid_until_str, '%Y-%m-%dT%H:%M') if valid_until_str else None
        except ValueError:
            flash('Invalid date format', 'error')
            return redirect(url_for('add_task'))
        
        custom_reminder_date = None
        if reminder_type == 'custom':
            custom_reminder_str = request.form.get('custom_reminder_date')
            if custom_reminder_str:
                try:
                    custom_reminder_date = datetime.strptime(custom_reminder_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    flash('Invalid reminder date format', 'error')
                    return redirect(url_for('add_task'))
        
        repeat_days = None
        if category == 'weekly':
            repeat_days = parse_repeat_days(request.form)
        
        task = Task(
            title=title,
            description=description,
            deadline=deadline,
            user_id=current_user.id,
            category=category,
            repeat_days=repeat_days,
            reminder_type=reminder_type,
            custom_reminder_date=custom_reminder_date,
            valid_until=valid_until
        )
        
        db.session.add(task)
        db.session.commit()
        flash('Task added successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('add_task.html')

@app.route('/task/edit/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    if task.user_id != current_user.id:
        flash('You cannot edit this task', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        task.title = request.form['title']
        task.description = request.form['description']
        deadline_str = request.form['deadline']
        task.category = request.form['category']
        task.reminder_type = request.form['reminder_type']
        valid_until_str = request.form.get('valid_until')
        
        try:
            task.deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
            task.valid_until = datetime.strptime(valid_until_str, '%Y-%m-%dT%H:%M') if valid_until_str else None
        except ValueError:
            flash('Invalid date format', 'error')
            return redirect(url_for('edit_task', task_id=task_id))
        
        if task.reminder_type == 'custom':
            custom_reminder_str = request.form.get('custom_reminder_date')
            if custom_reminder_str:
                try:
                    task.custom_reminder_date = datetime.strptime(custom_reminder_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    flash('Invalid reminder date format', 'error')
                    return redirect(url_for('edit_task', task_id=task_id))
        else:
            task.custom_reminder_date = None
        
        if task.category == 'weekly':
            task.repeat_days = parse_repeat_days(request.form)
        else:
            task.repeat_days = None
        
        db.session.commit()
        flash('Task updated successfully!', 'success')
        return redirect(url_for('index'))
    
    # Convert datetime to HTML datetime-local format
    deadline_formatted = task.deadline.strftime('%Y-%m-%dT%H:%M') if task.deadline else ''
    custom_reminder_formatted = task.custom_reminder_date.strftime('%Y-%m-%dT%H:%M') if task.custom_reminder_date else ''
    valid_until_formatted = task.valid_until.strftime('%Y-%m-%dT%H:%M') if task.valid_until else ''
 
    return render_template('edit_task.html', task=task, 
                         deadline_formatted=deadline_formatted,
                         custom_reminder_formatted=custom_reminder_formatted,
                         valid_until_formatted=valid_until_formatted)

@app.route('/task/delete/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    if task.user_id != current_user.id:
        flash('You cannot delete this task', 'error')
        return redirect(url_for('index'))
    
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/task/complete/<int:task_id>', methods=['POST'])
@login_required
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    if task.user_id != current_user.id:
        flash('You cannot complete this task', 'error')
        return redirect(url_for('index'))
    
    # Create log entry
    log = TaskLog(
        task_id=task.id,
        user_id=current_user.id,
        notes=request.form.get('notes', '')
    )
    db.session.add(log)
    
    # Handle recurring tasks
    if task.is_recurring() and check_task_validity(task):
        new_deadline = calculate_next_deadline(task)
        if new_deadline:
            new_task = Task(
                title=task.title,
                description=task.description,
                deadline=new_deadline,
                user_id=task.user_id,
                category=task.category,
                repeat_days=task.repeat_days,
                reminder_type=task.reminder_type,
                custom_reminder_date=task.custom_reminder_date,
                valid_until=task.valid_until,
                reminder_sent=False,
                completed=False
            )
            db.session.add(new_task)
    
    # Mark current task as completed
    task.completed = True
    db.session.commit()
    
    flash('Task completed and logged!', 'success')
    return redirect(url_for('index'))

@app.route('/task/logs/<int:task_id>')
@login_required
def task_logs(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    logs = task.logs.order_by(TaskLog.completed_at.desc()).all()
    return render_template('task_logs.html', task=task, logs=logs)

# Memorable Day routes
@app.route('/memorable-days')
@login_required
def memorable_days():
    now = datetime.utcnow().date()
    memorable_days_list = MemorableDay.query.filter_by(user_id=current_user.id).order_by(MemorableDay.date).all()
    
    # Check for reminders
    for day in memorable_days_list:
        if day.should_remind():
            flash(f'Reminder: {day.title} is coming up in {day.reminder_days_before} days!', 'info')
    
    return render_template('memorable_days.html', memorable_days=memorable_days_list, now=now)

@app.route('/memorable-day/add', methods=['GET', 'POST'])
@login_required
def add_memorable_day():
    if request.method == 'POST':
        title = request.form['title']
        date_str = request.form['date']
        reminder_days_before = int(request.form['reminder_days_before'])
        notes = request.form.get('notes', '')
        valid_until_str = request.form.get('valid_until')
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            valid_until = datetime.strptime(valid_until_str, '%Y-%m-%d').date() if valid_until_str else None
        except ValueError:
            flash('Invalid date format', 'error')
            return redirect(url_for('add_memorable_day'))
        
        memorable_day = MemorableDay(
            title=title,
            date=date,
            reminder_days_before=reminder_days_before,
            user_id=current_user.id,
            notes=notes,
            valid_until=valid_until
        )
        
        db.session.add(memorable_day)
        db.session.commit()
        flash('Memorable day added successfully!', 'success')
        return redirect(url_for('memorable_days'))
    
    return render_template('add_memorable_day.html')

@app.route('/memorable-day/edit/<int:day_id>', methods=['GET', 'POST'])
@login_required
def edit_memorable_day(day_id):
    memorable_day = MemorableDay.query.get_or_404(day_id)
    
    if memorable_day.user_id != current_user.id:
        flash('You cannot edit this memorable day', 'error')
        return redirect(url_for('memorable_days'))
    
    if request.method == 'POST':
        memorable_day.title = request.form['title']
        date_str = request.form['date']
        memorable_day.reminder_days_before = int(request.form['reminder_days_before'])
        memorable_day.notes = request.form.get('notes', '')
        valid_until_str = request.form.get('valid_until')
        
        try:
            memorable_day.date = datetime.strptime(date_str, '%Y-%m-%d').date()
            memorable_day.valid_until = datetime.strptime(valid_until_str, '%Y-%m-%d').date() if valid_until_str else None
        except ValueError:
            flash('Invalid date format', 'error')
            return redirect(url_for('edit_memorable_day', day_id=day_id))
        
        db.session.commit()
        flash('Memorable day updated successfully!', 'success')
        return redirect(url_for('memorable_days'))
    
    date_formatted = memorable_day.date.strftime('%Y-%m-%d') if memorable_day.date else ''
    valid_until_formatted = memorable_day.valid_until.strftime('%Y-%m-%d') if memorable_day.valid_until else ''
    return render_template('edit_memorable_day.html', 
                         memorable_day=memorable_day, 
                         date_formatted=date_formatted,
                         valid_until_formatted=valid_until_formatted)

@app.route('/memorable-day/delete/<int:day_id>', methods=['POST'])
@login_required
def delete_memorable_day(day_id):
    memorable_day = MemorableDay.query.get_or_404(day_id)
    
    if memorable_day.user_id != current_user.id:
        flash('You cannot delete this memorable day', 'error')
        return redirect(url_for('memorable_days'))
    
    db.session.delete(memorable_day)
    db.session.commit()
    flash('Memorable day deleted successfully!', 'success')
    return redirect(url_for('memorable_days'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
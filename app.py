from flask import Flask, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
import secrets

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:harshu8564@localhost:5432/task'  # Add your correct password
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.secret_key = secrets.token_hex(32)
db = SQLAlchemy(app)

# User table
class Userlo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usernam = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f"<User {self.usernam}>"

# Task table
class Tasks(db.Model):
    tid = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey('userlo.id'), nullable=False)
    task = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    remark = db.Column(db.String(100), nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(15), nullable=False)

    user = db.relationship('Userlo', backref=db.backref('tasks', lazy=True))

    def __repr__(self):
        return f"<Task {self.tid}>"

# User details table
class Usrdetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False)
    occupation = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<User {self.name}>"

# Home route redirects to login
@app.route('/')
def home():
    return redirect(url_for('login'))

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        usr = Userlo.query.filter_by(usernam=username).first()
        if usr and usr.password == password:
            session['id'] = usr.id
            return redirect(url_for('homepage'))
        else:
            error = "Please enter the correct username and password."
            return render_template('login.html', error=error)
    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    session.pop('id', None)
    return redirect(url_for('login'))

# Homepage route with session validation
@app.route('/homepage', methods=['GET', 'POST'])
def homepage():
    if 'id' not in session:
        return redirect(url_for('login'))
    
    taskb = Tasks.query.filter_by(uid=session['id']).all()
    return render_template("home.html", tasks=taskb)

# Edit task route
@app.route('/edit/<int:tid>', methods=['GET', 'POST'])
def edit_task(tid):
    task = Tasks.query.get(tid)
    if not task:
        return redirect(url_for('homepage'))

    if request.method == 'POST':
        task.task = request.form['task']
        task.remark = request.form['remark']
        task.deadline = request.form['deadline']
        db.session.commit()
        return redirect(url_for('homepage'))
    
    return render_template('edit.html', task=task)

# Update task status route
@app.route('/update_status/<int:tid>', methods=['POST'])
def update_status(tid):
    task = Tasks.query.get(tid)
    if not task:
        return redirect(url_for('homepage'))

    # Cycle through status
    if task.status == 'Incomplete':
        task.status = 'Ongoing'
    elif task.status == 'Ongoing':
        task.status = 'Complete'
    else:
        task.status = 'Incomplete'

    db.session.commit()
    return redirect(url_for('homepage'))

# Add task route
@app.route('/addtask', methods=['GET', 'POST'])
def taskadder():
    if 'id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        task = request.form['task']
        date = request.form['date']
        remark = request.form['remark']
        deadline = request.form['deadline']

        if not all([task, date, remark, deadline]):
            error = "Please enter all details."
            return render_template('add.html', error=error)

        new_task = Tasks(uid=session['id'], task=task, date=date, remark=remark, deadline=deadline, status="Incomplete")
        db.session.add(new_task)
        db.session.commit()
        
        return redirect(url_for('homepage'))

    return render_template('add.html')  

# Add user route
@app.route('/adduser', methods=["GET", "POST"])
def adduser():
    if request.method == 'POST':
        name = request.form['name']
        occupation = request.form['occ']  # Fixed typo from "occupuation"
        email = request.form['email']
        usern = request.form['usrn']
        passw = request.form['pw']

        if not all([name, occupation, email, usern, passw]):
            error = "Please enter all details."
            return render_template('adduser.html', error=error)

        existing_user = Userlo.query.filter_by(usernam=usern).first()
        if existing_user:
            error = "Username already exists. Please choose a different one."
            return render_template('adduser.html', error=error)

        new_user = Userlo(usernam=usern, password=passw)
        db.session.add(new_user)
        db.session.commit()

        new_user_details = Usrdetail(id=new_user.id, name=name, occupation=occupation, email=email)
        db.session.add(new_user_details)
        db.session.commit()

        return redirect(url_for('homepage'))
    
    return render_template('adduser.html')

# Initialize database and run the app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

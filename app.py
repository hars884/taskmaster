from flask import Flask, redirect, render_template, request, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:roobika@localhost:5432/task'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'

db = SQLAlchemy(app)

class userlo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usernam = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f"<User {self.usernam}>"

class tasks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    remark = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(10), nullable=False)

    def __repr__(self):
        return f"<Task {self.id}>"

class usrdetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False)
    occubation = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<User {self.name}>"

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    username = request.form['username']
    password = request.form['password']
    user = userlo.query.filter_by(usernam=username).first()
    if user and user.password == password:
        session['username'] = username
        return redirect(url_for('home'))
    else:
        return "Invalid credentials, try again!"

@app.route('/signup', methods=['POST'])
def signup_post():
    email = request.form.get('email')
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    if password != confirm_password:
        return "Passwords do not match, try again!"
    if userlo.query.filter_by(usernam=username).first():
        return "Username already exists!"
    new_user = userlo(usernam=username, password=password)
    db.session.add(new_user)
    db.session.commit()
    session['username'] = username
    return redirect(url_for('home'))

@app.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    usr = tasks.query.all()
    edit_id = request.args.get('edit', type=int)  # Get ?edit=<id> from URL
    edit_task = tasks.query.get(edit_id) if edit_id else None
    return render_template('home.html', usr=usr, edit_task=edit_task)

@app.route('/add_task', methods=['POST'])
def add_task():
    if 'username' not in session:
        return redirect(url_for('login'))
    task = request.form['task']
    date = datetime.strptime(request.form['date'], '%Y-%m-%d')
    remark = request.form['remark']
    status = request.form['status']
    new_task = tasks(task=task, date=date, remark=remark, status=status)
    db.session.add(new_task)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/edit_task/<int:task_id>', methods=['POST'])
def edit_task(task_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    task = tasks.query.get_or_404(task_id)
    task.task = request.form['task']
    task.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
    task.remark = request.form['remark']
    task.status = request.form['status']
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
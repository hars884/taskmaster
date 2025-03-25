from flask import Flask,redirect,render_template,request,session,url_for
from flask_sqlalchemy import SQLAlchemy
import secrets

app=Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:harshu8564@localhost:5432/task'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.secret_key=(secrets.token_hex(32))
db = SQLAlchemy(app)

class userlo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usernam = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f"<User {self.usernam}>"

class tasks(db.Model):
    tid = db.Column(db.Integer, primary_key=True)  # Auto-incremented primary key
    uid = db.Column(db.Integer, db.ForeignKey('userlo.id'), nullable=False)  # Foreign key
    task = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    remark = db.Column(db.String(100), nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(15), nullable=False)

    user = db.relationship('userlo', backref=db.backref('tasks', lazy=True))  # Optional for easy querying

    def __repr__(self):
        return f"<Task {self.tid}>"


class usrdetail(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String(30), nullable=False)
    occupation=db.Column(db.String(30), nullable=False)
    email=db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<User {self.name}>"

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login',methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        usr = userlo.query.filter_by(usernam=username).first()
        if usr and usr.password == password:
            session['id'] = usr.id
            return redirect(url_for('homepage'))
        else:
            error = "Please enter correct username and password."
            return render_template('login.html', error=error)
    return render_template('login.html')

@app.route('/homepage',methods=['GET','POST'])
def homepage():
    taskb=tasks.query.filter_by(uid=session['id'])
    if taskb:
        return render_template("home.html",taskf=taskb)
    return render_template("home.html")

@app.route('/addtask',methods=['GET','POST'])
def taskadder():
    if request.method == 'POST':
        task=request.form['task']
        date=request.form['date']
        remark=request.form['remark']
        deadline=request.form['deadline']
        if not all([task, date, remark, deadline]):
            error = "Please enter all details."
            return render_template('add.html', error=error)

        tsk = tasks(uid=session['id'], task=task, date=date, remark=remark, deadline=deadline, status="incomplete")
        db.session.add(tsk)
        db.session.commit()
        
        return redirect(url_for('homepage'))

    return render_template('add.html')

@app.route('/adduser',methods=["GET","POST"])
def adduser():
    if request.method=='POST':
        name=request.form['name']
        occupuation=request.form['occ']
        email=request.form['email']
        usern=request.form['usrn']
        passw=request.form['pw']
        if not all([name, occupuation, email, usern, passw]):
            error = "Please enter all details."
            return render_template('adduser.html', error=error)
        existing_user = userlo.query.filter_by(usernam=usern).first()
        if existing_user:
            error = "Username already exists. Please choose a different one."
            return render_template('adduser.html', error=error)
        tsk = userlo(usernam=usern, password=passw)
        db.session.add(tsk)
        db.session.commit()

        tsk2 = usrdetail(id=tsk.id, name=name, occupation=occupuation, email=email)
        db.session.add(tsk2)
        db.session.commit()

        return redirect(url_for('homepage'))
    return render_template('adduser.html')


if __name__ == '__main__':
    with app.app_context():
        db.create_all() 
    app.run(debug=True)
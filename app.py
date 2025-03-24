from flask import Flask,redirect,render_template,request,session,url_for
from flask_sqlalchemy import SQLAlchemy

app=Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:harshu8564@localhost/TASK'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)

class userlo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usernam = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f"<User {self.usernam}>"

class tasks(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    task=db.Column(db.String(100), nullable=False)
    date=db.Column(db.Date, nullable=False)
    remark=db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<User {self.id}>"

class usrdetail(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String(30), nullable=False)
    occubation=db.Column(db.String(30), nullable=False)
    email=db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<User {self.name}>"

@app.route('/')
def home():
    render_template(url_for("login"))

@app.route('login',methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        usr=userlo.query.filter_by(usernam=username)
        if usr and usr.password == password:
            session['id'] = usr.id
            return redirect(url_for('homepage'))
        else:
            error = "Please enter correct username and password."
            return render_template('login.html', error=error)
    return render_template("login.html")

@app.route('home',method=['GET','POST'])
def homepage():
    taskb=tasks.query.filter_by(id=session['id'])
    return render_template("home.html",taskf=taskb) 

@app.
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
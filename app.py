from flask import Flask,redirect,render_template,request,url_for
from flask_sqlalchemy import SQLAlchemy

app=Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:roobika@localhost:5432/task'
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
    status=db.Column(db.String(10), nullable=False)

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
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    username = request.form['username']
    password = request.form['password']

    if username == "admin" and password == "password":
        return redirect(url_for('home'))  
    else:
        return "Invalid credentials, try again!"

@app.route('/signup', methods=['POST'])
def signup_post():
    email = request.form.get('email')
    username = request.form.get('username')  # Ensure the form has a username field
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if password != confirm_password:
        return "Passwords do not match, try again!"
    return redirect(url_for('home'))


@app.route('/home')
def home():
    usr=tasks.query.all()
    return render_template('home.html',usr=usr)

if __name__ == '__main__':
    app.run(debug=True)
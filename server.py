#pylint:disable=print-statement

from flask import Flask,render_template,request,redirect,session,flash  # Import Flask to allow us to create our app.
import re, md5, os, binascii
from mysqlconnection import MySQLConnector
from datetime import datetime, timedelta
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
app = Flask(__name__)    # Global variable __name__ tells Flask whether or not we are running the file
app.secret_key = 'ThisIsSecret'                        # directly, or importing it as a module.
mysql = MySQLConnector(app,'walldb')

@app.route('/')          # The "@" symbol designates a "decorator" which attaches the following
                         # function to the '/' route. This means that whenever we send a request to
                         # localhost:5000/ we will run the following "hello_world" function.
def starter():
    return render_template('index.html')  
  
@app.route('/registration', methods=['POST'])
def registration():
    if len(request.form['first_name']) < 2 or len(request.form['last_name']) < 2:
        isError = True
    elif len(request.form['password']) < 8:
        isError = True
    elif any(not char.isalpha() for char in request.form['first_name']) == True or any(not char.isalpha() for char in request.form['last_name']) == True:
        isError = True
    elif not EMAIL_REGEX.match(request.form['email']):
        isError = True
    elif request.form['password'] != request.form['password_confirmation']:
        isError = True
    else:
        isError = False
    
    if isError == True: 
        flash('First and last name must be at least 2 characters long!','error')
        flash('First and last name must contain only letters!','error')
        flash("Password must exceed 8 characters!",'error')
        flash('Email must be in a valid format!','error')
        flash('Password and confirmation must match!','error')
        return redirect('/')
    else:
        first = request.form['first_name']
        last = request.form['last_name']
        password = request.form['password']
        email = request.form['email']
        salt =  binascii.b2a_hex(os.urandom(15))
        hashed_pw = md5.new(password + salt).hexdigest()
        insertquery = "INSERT INTO users(first_name,last_name,password,email,salt,created_at,updated_at) VALUES (:first, :last, :hashed_pw, :email, :salt, NOW(), NOW())"
        query_data = { 'first': first, 'last': last, 'hashed_pw': hashed_pw, 'email': email,'salt': salt}
        mysql.query_db(insertquery, query_data)
        flash('Thank you for registering!')
        idquery = "SELECT id FROM users WHERE email = :email LIMIT 1"
        data = {'email': email}
        check = mysql.query_db(idquery, data)
        session['user'] = check[0]['id']    
        return redirect('/wall')

@app.route('/login',methods=['POST'])
def login():
    password = request.form['pass']
    mailquery = "SELECT * FROM users WHERE email = :mail LIMIT 1"
    data = {'mail': request.form['mail']}
    check = mysql.query_db(mailquery, data)
    if len(check) == 0:
        flash('Invalid login information!','invalid')
    else: 
        encrypted_password = md5.new(password + check[0]['salt']).hexdigest()
        if check[0]['password'] == encrypted_password:
            session['user'] = check[0]['id']
            print session['user']
            return redirect('/wall')
        else: 
            flash('Invalid login information!','invalid')
    return redirect('/')

@app.route('/wall')
def wall():

    # postquery = "SELECT * FROM posts"
    postquery = "SELECT * FROM users JOIN posts ON users.id = posts.user_id"
    wallposts = mysql.query_db(postquery)
    # commentquery = "SELECT * FROM comments"
    commentquery = "SELECT * FROM users JOIN comments ON users.id = comments.user_id"
    wallcomments = mysql.query_db(commentquery)
    namequery = "SELECT first_name FROM users WHERE id = {}".format(session['user'])
    name = mysql.query_db(namequery)
    return render_template('wall.html', posts = wallposts, comments = wallcomments, user = name, now = datetime.now(), thirty = timedelta(minutes=30))
    
@app.route('/message', methods=['POST'])
def message():
    postquery = "INSERT INTO posts (content, created_at, updated_at, user_id) VALUES (:post, NOW(), NOW(),:userid)"
    postdata = {'post' : request.form['posts'], 'userid' : session['user']}
    mysql.query_db(postquery,postdata)
    return redirect('/wall')

@app.route('/comment', methods=['POST'])
def comment():
    comm = request.form['comment']
    commentquery = "INSERT INTO comments (reply, created_at, updated_at, post_id, user_id) VALUES (:reply, NOW(), NOW(), :postid, :userid)"
    querydata = {'reply' : comm, 'postid': request.form['postid'], 'userid' : session['user'] }
    mysql.query_db(commentquery, querydata)
    return redirect('/wall')

@app.route('/delete', methods=['POST'])
def delete():
    if request.form['texttype'] == 'comment':
        query = "DELETE FROM comments WHERE id = :id"
        data = {'id': request.form['comment']}
        mysql.query_db(query, data)
    elif request.form['texttype'] == 'post':
        query1 = "DELETE FROM comments WHERE post_id = :id"
        data1 = {'id': request.form['post']}
        mysql.query_db(query1, data1)
        query2 = "DELETE FROM posts WHERE id = :id"
        data2 = {'id': request.form['post']}
        mysql.query_db(query2, data2)
    return redirect('/wall')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')
app.run(debug=True)      # Run the app in debug mode.
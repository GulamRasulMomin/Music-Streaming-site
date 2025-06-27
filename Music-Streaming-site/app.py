from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
import psycopg2
import os
import re

app = Flask(__name__)
app.secret_key = "supersecretkey"
# Database connection
conn = psycopg2.connect(
    dbname="music_streaming",
    user="postgres",
    password="",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

class User:

    def history(email,song_id):
        cursor.execute("select history from users where email = %s",(email,))
        history = cursor.fetchone()[0]
        if history != None:
            if history.count(song_id) == 0:
                history.insert(0,song_id)
                cursor.execute("update users set history = %s where email = %s",(history,email,))
                conn.commit()
            else :
                history.remove(song_id)
                history.insert(0,song_id)
                cursor.execute("update users set history = %s where email = %s",(history,email))
                conn.commit()
        else:
            history = [song_id]
            cursor.execute("update users set history = %s where email = %s",(history,email))
            conn.commit()
        


class Songs :

    def add_views(email,song_id):
        cursor.execute("select history from users where email = %s",(email,))
        history = cursor.fetchone()[0]
        cursor.execute("select views from songs where song_id = %s",(song_id,))
        views = cursor.fetchone()[0]
        if history != None:
            if history.count(song_id) == 0:
                views = views + 1 if views != None else 1
                cursor.execute("update songs set views = %s where song_id = %s",(views,song_id,))
                conn.commit()

        else:
            views = views + 1 if views != None else 1
            cursor.execute("update songs set views = %s where song_id = %s",(views,song_id,))
            conn.commit()

@app.route('/')
def base():
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        user_name = request.form['name']
        phone = request.form['phone']
        password = request.form['password']

        if not validate_email(email):
            error = 'Invalid email'
            return render_template('signup.html',error=error)
        
        if not validate_username(user_name):
            error = 'Invalid username'
            return render_template('signup.html',error=error)
        
        if not validate_phone(phone):
            error = 'Invalid phone number'
            return render_template('signup.html',error=error)
        
        if not validate_password(password):
            error = 'Password must contain at least 8 characters, one uppercase, one lowercase, one number and one special character'
            return render_template('signup.html',error=error)

        # Check if user already exists
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
           error = 'User already exists'
           return render_template('signup.html',error=error)

        # Insert user into database
        cursor.execute(
            "INSERT INTO users (email, user_name, phone, password) VALUES (%s, %s, %s, %s)",
            (email, user_name, phone, password)
        )
        conn.commit()

        return redirect(url_for('index',email=email))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cursor.execute("SELECT password FROM users WHERE email = %s", (email,))
        result = cursor.fetchone()
        if result and result[0] == password:
            return redirect(url_for('index',email=email))
        else:    
            error = 'Invalid email or password'       
            return render_template('login.html',error=error)
    return render_template('login.html')

@app.route('/index')
def index():
    cursor.execute("SELECT * FROM songs")
    songs = cursor.fetchall()
    email = request.args.get('email')
    return render_template('index.html', songs=songs, email=email)

@app.route('/log_play', methods=['POST'])
def log_play():
    data = request.json
    song_id = int(data['song_id'])
    email = data['email']
    Songs.add_views(email,song_id)
    User.history(email, song_id)
    cursor.execute("SELECT favourite FROM users WHERE email = %s", (email,))
    favourite = cursor.fetchone()[0]
    flag = False
    if favourite != None:
        if favourite.count(song_id) != 0:
            flag = True
    return jsonify({'status': 'success', 'favourite': flag}), 200

@app.route('/favourite', methods=['POST'])
def favourite():
    data = request.json
    song_id = int(data['song_id'])
    email = data['email']
    cursor.execute("SELECT favourite FROM users WHERE email = %s", (email,))
    favourite = cursor.fetchone()[0]
    if favourite != None:
        if favourite.count(song_id) == 0:
            favourite.append(song_id)
            cursor.execute("update users set favourite = %s where email = %s",(favourite,email))
            conn.commit()
    else:
        favourite = [song_id]
        cursor.execute("update users set favourite = %s where email = %s",(favourite,email))
        conn.commit()
    return jsonify({'status': 'success'}), 200

@app.route('/unfavourite', methods=['POST'])
def unfavourite():
    data = request.json
    song_id = int(data['song_id'])
    email = data['email']
    cursor.execute("SELECT favourite FROM users WHERE email = %s", (email,))
    favourite = cursor.fetchone()[0]
    if favourite != None:
        if favourite.count(song_id) != 0:
            favourite.remove(song_id)
            cursor.execute("update users set favourite = %s where email = %s",(favourite,email))
            conn.commit()
    return jsonify({'status': 'success'}), 200

@app.route('/library')
def library():
    email = request.args.get('email')
    cursor.execute("SELECT * FROM songs WHERE song_id IN (SELECT UNNEST(history) FROM users WHERE email = %s)", (email,))
    history = cursor.fetchall()
    return render_template('library.html', history=history, email=email)

@app.route('/favouriteSongs')
def favouriteSongs():
    email = request.args.get('email')
    cursor.execute("SELECT * FROM songs WHERE song_id IN (SELECT UNNEST(favourite) FROM users WHERE email = %s)", (email,))
    favourite = cursor.fetchall()
    return render_template('favouriteSongs.html', favourite=favourite, email=email)

@app.route('/explore')
def explore():
    cursor.execute("SELECT * FROM songs ORDER BY views DESC LIMIT 5")
    Populer_songs = cursor.fetchall()
    email = request.args.get('email')
    return render_template('explore.html', email=email, Populer_songs=Populer_songs)

@app.route('/profile')
def profile():
    email = request.args.get('email')
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    Users_details =cursor.fetchone()
    return render_template('profile.html',email=email, Users_details=Users_details)

@app.route('/search', methods=['GET', 'POST'])
def search():
    email = request.args.get('email')
    if request.method == 'POST':
        search = request.form['search']
        cursor.execute("SELECT * FROM songs WHERE song_name ILIKE %s OR album ILIKE %s OR artist ILIKE %s", (f'%{search}%', f'%{search}%', f'%{search}%'))
        search_songs = cursor.fetchall()
        return render_template('search.html', email=email, search_songs=search_songs)
        
    return render_template('search.html', email=email)

@app.route('/admin/', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        song_name = request.form['song_name']
        artist = request.form['artist']
        album = request.form['album']
        type = request.form['type']
        cover = request.files['cover']
        music = request.files['music']

        cover.save(os.path.join('static/images', song_name+".png"))
        music.save(os.path.join('static/music', song_name+".mp3"))


        # Insert song into databasejuj
        cursor.execute(
            "INSERT INTO songs (song_name, artist, album, type) VALUES (%s, %s, %s, %s)",
            (song_name, artist, album, type)
        )
        conn.commit()

        return redirect(url_for('admin'))
    return render_template('admin.html')

def validate_email(email):
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email))

def validate_username(username):
    pattern = r'^[a-zA-Z0-9_ ]{3,20}$'
    return bool(re.match(pattern, username))

def validate_phone(phone):
    pattern = r'^(\+\d{1,3})?\d{10}$' 
    return bool(re.match(pattern, phone))

def validate_password(password):
    pattern = r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
    return bool(re.match(pattern, password))

if __name__ == '__main__':
    app.run(debug=True)

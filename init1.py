#Import Flask Library
from flask import Flask, render_template, request, session, url_for, redirect
import pymysql.cursors
import hashlib

#Initialize the app from Flask
app = Flask(__name__)

#Configure MySQL
conn = pymysql.connect(host='localhost',
                       user='root',
                       password='',
                       db='airport',
                       charset='utf8mb4',
					   port=3307,
                       cursorclass=pymysql.cursors.DictCursor)

#Define a route to hello function
@app.route('/')
def hello():
	return render_template('home.html')


#Define route to search for a flight 
@app.route('/search_flights', methods=['POST'])
def search_flights():
    source = request.form['source']
    destination = request.form['destination']
    departure_date = request.form['departure_date']
    return_date = request.form.get('return_date')  # optional

    cursor = conn.cursor(dictionary=True)
    if return_date:
        query = """
        SELECT * FROM flight
        WHERE departure_airport_code LIKE %s
          AND arrival_airport_code LIKE %s
          AND departure_date >= %s
          AND arrival_date <= %s
        """
        cursor.execute(query, (f"%{source}%", f"%{destination}%", departure_date, return_date))
    else:
        query = """
        SELECT * FROM flight
        WHERE departure_airport LIKE %s
          AND arrival_airport LIKE %s
          AND departure_datetime >= %s
        """
        cursor.execute(query, (f"%{source}%", f"%{destination}%", departure_date))

    flights = cursor.fetchall()
    cursor.close()

    return render_template('home.html', flights=flights)

# #Define route for login
# @app.route('/login')
# def login():
# 	return render_template('login.html')


#Define route for register
from flask import request, render_template, session
import pymysql
import hashlib

@app.route('/register', methods=['POST'])
def register():
    user_type = request.form['user_type']
    password = request.form['password']
    hashed_pw = hashlib.md5(password.encode()).hexdigest()
    cursor = conn.cursor()

    if user_type == 'customer':
        # Grab all required customer fields
        email = request.form['email']
        name = request.form['customer_name']
        building_number = request.form['building_number']
        street = request.form['street']
        city = request.form['cust_city']
        state = request.form['state']
        phone = request.form['cust_phone_number']
        passport_number = request.form['passport_number']
        passport_exp_date = request.form['passport_expiration_date']
        passport_country = request.form['passport_country']
        dob = request.form['cust_DOB']

        # Check if customer already exists
        cursor.execute("SELECT * FROM customer WHERE customer_email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            return render_template('home.html', error="Customer already exists.")

        # Insert into customer table
        insert_customer = """
            INSERT INTO customer (
                customer_email, customer_name, cust_password, building_number, street_number, cust_city, state,
                cust_phone_number, passport_number, passport_expiration_date, passport_country, cust_DOB
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_customer, (
            email, name, hashed_pw, building_number, street, city, state,
            phone, passport_number, passport_exp_date, passport_country, dob
        ))
        conn.commit()

    elif user_type == 'staff':
        # Grab all staff fields
        airline_name = request.form['airline_name']
        username = request.form['username']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        dob = request.form['date_of_birth']

        # Check if staff already exists
        cursor.execute("SELECT * FROM airline_staff WHERE username = %s", (username,))
        if cursor.fetchone():
            cursor.close()
            return render_template('home.html', error="Staff already exists.")

        # Insert into staff table
        insert_staff = """
            INSERT INTO airline_staff (
                airline_name, username, password, first_name, last_name, date_of_birth
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_staff, (
            airline_name, username, hashed_pw, first_name, last_name, dob
        ))
        conn.commit()

    cursor.close()
    return render_template('home.html', success=f"{user_type.capitalize()} registered successfully.")


@app.route('/loginAuth', methods=['POST'])
def loginAuth():
    user_type = request.form['user_type']
    username = request.form['username']
    password = request.form['password']
    hashed_pw = hashlib.md5(password.encode()).hexdigest()

    cursor = conn.cursor()

    if user_type == 'customer':
        query = "SELECT * FROM customer WHERE email = %s AND password = %s"
    else:
        query = "SELECT * FROM airline_staff WHERE username = %s AND password = %s"

    cursor.execute(query, (username, hashed_pw))
    data = cursor.fetchone()
    cursor.close()

    if data:
        session['username'] = username
        session['user_type'] = user_type
        if user_type == 'customer':
            return render_template('customer_home.html', name=data['name'])
        else:
            return render_template('staff_home.html', name=data['name'])
    else:
        return render_template('home.html', login_error="Invalid username or password")

# #Authenticates the login
# @app.route('/loginAuth', methods=['GET', 'POST'])
# def loginAuth():
# 	#grabs information from the forms
# 	username = request.form['username']
# 	password = request.form['password']

# 	#cursor used to send queries
# 	cursor = conn.cursor()
# 	#executes query
# 	query = 'SELECT * FROM user WHERE username = %s and password = %s'
# 	cursor.execute(query, (username, password))
# 	#stores the results in a variable
# 	data = cursor.fetchone()
# 	#use fetchall() if you are expecting more than 1 data row
# 	cursor.close()
# 	error = None
# 	if(data):
# 		#creates a session for the the user
# 		#session is a built in
# 		session['username'] = username
# 		return redirect(url_for('home'))
# 	else:
# 		#returns an error message to the html page
# 		error = 'Invalid login or username'
# 		return render_template('login.html', error=error)

#Authenticates the register
@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
	#grabs information from the forms
	username = request.form['username']
	password = request.form['password']

	#cursor used to send queries
	cursor = conn.cursor()
	#executes query
	query = 'SELECT * FROM user WHERE username = %s'
	cursor.execute(query, (username))
	#stores the results in a variable
	data = cursor.fetchone()
	#use fetchall() if you are expecting more than 1 data row
	error = None
	if(data):
		#If the previous query returns data, then user exists
		error = "This user already exists"
		return render_template('register.html', error = error)
	else:
		ins = 'INSERT INTO user VALUES(%s, %s)'
		cursor.execute(ins, (username, password))
		conn.commit()
		cursor.close()
		return render_template('index.html')

@app.route('/home')
def home():
    
    username = session['username']
    cursor = conn.cursor();
    query = 'SELECT ts, blog_post FROM blog WHERE username = %s ORDER BY ts DESC'
    cursor.execute(query, (username))
    data1 = cursor.fetchall() 
    for each in data1:
        print(each['blog_post'])
    cursor.close()
    return render_template('home.html', username=username, posts=data1)

		
@app.route('/post', methods=['GET', 'POST'])
def post():
	username = session['username']
	cursor = conn.cursor();
	blog = request.form['blog']
	query = 'INSERT INTO blog (blog_post, username) VALUES(%s, %s)'
	cursor.execute(query, (blog, username))
	conn.commit()
	cursor.close()
	return redirect(url_for('home'))

@app.route('/logout')
def logout():
	session.pop('username')
	return redirect('/')


app.secret_key = 'some key that you will never guess'
#Run the app on localhost port 5000
#debug = True -> you don't have to restart flask
#for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
	app.run('127.0.0.1', 5000, debug = True)

# Import Flask Library
from flask import Flask, render_template, request, session, url_for, redirect
import pymysql.cursors
import hashlib
import traceback #remember to add this library

# Initialize the app from Flask
app = Flask(__name__)

# Configure MySQL
conn = pymysql.connect(host='localhost',
                       user='root',
                       password='',
                       db='airport', #different than ameena's code
                       charset='utf8mb4',
                       port= 3307, #different than ameena's code
                       cursorclass=pymysql.cursors.DictCursor)

# Home route
@app.route('/', methods=['GET', 'POST'])
def home():
    cursor = conn.cursor() 

    # Get airport codes for the dropdown
    cursor.execute("SELECT code FROM airport")
    airport_codes = [row['code'] for row in cursor.fetchall()]

    if 'username' in session and 'user_type' in session:
        return redirect(url_for(f"{session['user_type']}_home"))

    flights = []

    if request.method == 'POST':
        source = request.form['source']
        destination = request.form['destination']
        departure_date = request.form['departure_date']
        return_date = request.form.get('return_date')

        if return_date:
            query = """
                SELECT * FROM flight
                WHERE departure_airport_code LIKE %s
                  AND arrival_airport_code LIKE %s
                  AND DATE(departure_date) >= %s
                  AND DATE(arrival_date) <= %s
            """
            cursor.execute(query, (f"%{source}%", f"%{destination}%", departure_date, return_date))
        else:
            query = """
                SELECT * FROM flight
                WHERE departure_airport_code LIKE %s
                  AND arrival_airport_code LIKE %s
                  AND DATE(departure_date) >= %s
            """
            cursor.execute(query, (f"%{source}%", f"%{destination}%", departure_date))

        flights = cursor.fetchall()

    cursor.close()
    return render_template('home.html', flights=flights, airport_codes=airport_codes)

'''
@app.route('/login')
def login():
    return render_template('login.html')
'''
@app.route('/register')
def register():
    #print("Entering register")
    cursor = conn.cursor()
    cursor.execute("SELECT airline_name FROM airline")
    airlines = [row['airline_name'] for row in cursor.fetchall()]
    cursor.close()
    return render_template('register.html', airlines=airlines)

@app.route('/loginAuth', methods=['POST'])
def loginAuth():
    user_type = request.form['user_type']
    username = request.form['username']
    password = request.form['password']
    hashed_pw = hashlib.md5(password.encode()).hexdigest()
    print("Printing hashed password")
    print(hashed_pw)

    cursor = conn.cursor()
    if user_type == 'customer':
        print("entering costumer")
        cursor.execute("SELECT * FROM customer WHERE customer_email = %s AND cust_password = %s", (username, hashed_pw))
    else:
        print("entering staff")
        cursor.execute("SELECT * FROM airline_staff WHERE username = %s AND password = %s", (username, hashed_pw))

    data = cursor.fetchone()
    cursor.close()

    if data:
        session['username'] = username
        session['user_type'] = user_type
        print("redirect to user type home here")
        return redirect(url_for(f"{user_type}_home"))
    else:
        return render_template('home.html', login_error="Invalid username or password")

#Code for checking errors
def get_airline_names():
    cursor = conn.cursor()
    cursor.execute("SELECT airline_name FROM airline")
    result = [row['airline_name'] for row in cursor.fetchall()]
    cursor.close()
    return result

@app.route('/registerAuth', methods=['POST'])
def registerAuth():
    #print("I am here")
    try:
        user_type = request.form['user_type']
        password = request.form['password']
        hashed_pw = hashlib.md5(password.encode()).hexdigest()
        cursor = conn.cursor()

        if user_type == 'customer':
            #print("Erro during ")
            email = request.form['email']
            cursor.execute('SELECT * FROM customer WHERE customer_email = %s', (email,))
            if cursor.fetchone():
                return render_template('register.html', error="Customer already exists")

            insert_query = '''
                INSERT INTO customer (customer_email, customer_name, cust_password, building_number, street_number, cust_city, state,
                                    cust_phone_number, passport_number, passport_expiration_date, passport_country, cust_DOB)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            '''
            cursor.execute(insert_query, (
                email,
                request.form['customer_name'],
                hashed_pw,
                request.form['building_number'],
                request.form['street'],
                request.form['cust_city'],
                request.form['state'],
                request.form['cust_phone_number'],
                request.form['passport_number'],
                request.form['passport_expiration_date'],
                request.form['passport_country'],
                request.form['cust_DOB']
            ))

        elif user_type == 'staff':
            print("Working until here")
            username = request.form['username']
            airline_name = request.form['airline_name']

            cursor.execute('SELECT * FROM airline WHERE airline_name = %s', (airline_name,))
            if not cursor.fetchone():
                return render_template('register.html', error="Airline does not exist")

            cursor.execute('SELECT * FROM airline_staff WHERE username = %s', (username,))
            if cursor.fetchone():
                return render_template('register.html', error="Staff user already exists")

            insert_query = '''
                INSERT INTO airline_staff (username, airline_name, password, first_name, last_name, date_of_birth)
                VALUES (%s, %s, %s, %s, %s, %s)
            '''
            cursor.execute(insert_query, (
                username,
                airline_name,
                hashed_pw,
                request.form['first_name'],
                request.form['last_name'],
                request.form['date_of_birth']
            ))
        else:
            return render_template('register.html', error="Invalid user type")

        conn.commit()
        cursor.close()
        return redirect(url_for('home'))
    
    except Exception as e:
        conn.rollback()
        print("An error occurred during registration:")
        print(traceback.format_exc())  # This prints full error to your terminal
        airlines = get_airline_names()
        return render_template('register.html', error="Internal error during registration", airlines=airlines)

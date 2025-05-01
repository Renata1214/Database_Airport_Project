# Import Flask Library
from flask import Flask, render_template, request, session, url_for, redirect
import pymysql.cursors
import hashlib

# Initialize the app from Flask
app = Flask(__name__)

# Configure MySQL
conn = pymysql.connect(host='localhost',
                       user='root',
                       password='',
                       db='airline',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)

# Home route
@app.route('/', methods=['GET', 'POST'])
def home():
    if 'username' in session and 'user_type' in session:
        return redirect(url_for(f"{session['user_type']}_home"))

    if request.method == 'POST':
        source = request.form['source']
        destination = request.form['destination']
        departure_date = request.form['departure_date']
        return_date = request.form.get('return_date')

        cursor = conn.cursor()
        if return_date:
            query = """
                SELECT * FROM flight
                WHERE departure_airport_code LIKE %s
                  AND arrival_airport_code LIKE %s
                  AND DATE(departure_datetime) >= %s
                  AND DATE(arrival_datetime) <= %s
            """
            cursor.execute(query, (f"%{source}%", f"%{destination}%", departure_date, return_date))
        else:
            query = """
                SELECT * FROM flight
                WHERE departure_airport_code LIKE %s
                  AND arrival_airport_code LIKE %s
                  AND DATE(departure_datetime) >= %s
            """
            cursor.execute(query, (f"%{source}%", f"%{destination}%", departure_date))

        flights = cursor.fetchall()
        cursor.close()
        return render_template('home.html', flights=flights)

    return render_template('home.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
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

    cursor = conn.cursor()
    if user_type == 'customer':
        cursor.execute("SELECT * FROM customer WHERE email = %s AND password = %s", (username, hashed_pw))
    else:
        cursor.execute("SELECT * FROM airline_staff WHERE username = %s AND password = %s", (username, hashed_pw))

    data = cursor.fetchone()
    cursor.close()

    if data:
        session['username'] = username
        session['user_type'] = user_type
        return redirect(url_for(f"{user_type}_home"))
    else:
        return render_template('home.html', login_error="Invalid username or password")

@app.route('/registerAuth', methods=['POST'])
def registerAuth():
    user_type = request.form['user_type']
    password = request.form['password']
    hashed_pw = hashlib.md5(password.encode()).hexdigest()
    cursor = conn.cursor()

    if user_type == 'customer':
        email = request.form['email']
        cursor.execute('SELECT * FROM customer WHERE email = %s', (email,))
        if cursor.fetchone():
            return render_template('register.html', error="Customer already exists")

        insert_query = '''
            INSERT INTO customer (email, name, password, building_number, street, city, state,
                                  phone_number, passport_number, passport_expiration, passport_country, date_of_birth)
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

@app.route('/staff_home', methods=['GET', 'POST'])
def staff_home():
    if session.get('user_type') != 'staff':
        return redirect('/')

    username = session['username']
    cursor = conn.cursor()
    cursor.execute('SELECT airline_name FROM airline_staff WHERE username = %s', (username,))
    airline_name = cursor.fetchone()['airline_name']

    if request.method == 'POST':
        source = request.form.get('source')
        destination = request.form.get('destination')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        query = '''
            SELECT * FROM flight
            WHERE airline_name = %s
              AND (%s IS NULL OR departure_airport_code = %s)
              AND (%s IS NULL OR arrival_airport_code = %s)
              AND (%s IS NULL OR DATE(departure_datetime) >= %s)
              AND (%s IS NULL OR DATE(departure_datetime) <= %s)
            ORDER BY departure_datetime ASC
        '''
        cursor.execute(query, (
            airline_name,
            source, source,
            destination, destination,
            start_date, start_date,
            end_date, end_date
        ))
    else:
        query = '''
            SELECT * FROM flight
            WHERE airline_name = %s
              AND departure_datetime >= NOW()
              AND departure_datetime <= DATE_ADD(NOW(), INTERVAL 30 DAY)
            ORDER BY departure_datetime ASC
        '''
        cursor.execute(query, (airline_name,))

    flights = cursor.fetchall()
    cursor.close()
    return render_template('staff_home.html', flights=flights, airline=airline_name)

@app.route('/flight_customers/<airline_name>/<flight_num>/<departure_datetime>')
def flight_customers(airline_name, flight_num, departure_datetime):
    if session.get('user_type') != 'staff':
        return redirect('/')

    cursor = conn.cursor()
    query = '''
        SELECT customer.email, purchase.purchase_date
        FROM ticket
        JOIN purchase ON ticket.ticket_id = purchase.ticket_id
        JOIN customer ON customer.email = purchase.customer_email
        WHERE ticket.airline_name = %s AND ticket.flight_number = %s AND ticket.departure_datetime = %s
    '''
    cursor.execute(query, (airline_name, flight_num, departure_datetime))
    customers = cursor.fetchall()
    cursor.close()

    return render_template('flight_customers.html', customers=customers, flight_number=flight_num)

@app.route('/add_flight')
def add_flight():
    return render_template('add_flight.html')

@app.route('/change_flight_status')
def change_flight_status():
    return render_template('change_flight_status.html')

@app.route('/add_airplane', methods=['GET'])
def add_airplane():
    if session.get('user_type') != 'staff':
        return "Unauthorized", 403

    cursor = conn.cursor()
    cursor.execute("SELECT airline_name FROM airline_staff WHERE username = %s", (session['username'],))
    result = cursor.fetchone()
    cursor.close()

    if not result:
        return "Staff not found", 404

    airline_name = result['airline_name']
    return render_template('add_airplane.html', airline_name=airline_name)

@app.route('/submit_airplane', methods=['POST'])
def submit_airplane():
    if session.get('user_type') != 'staff':
        return "Unauthorized", 403

    cursor = conn.cursor()
    cursor.execute("SELECT airline_name FROM airline_staff WHERE username = %s", (session['username'],))
    result = cursor.fetchone()

    if not result:
        return "Staff not found", 404

    airline_name = result['airline_name']
    num_seats = request.form.get('num_seats')
    company = request.form.get('manufacturing_company')

    if not num_seats or not company:
        return "Missing fields", 400

    cursor.execute("SELECT MAX(airplane_id) AS max_id FROM airplane")
    max_id = cursor.fetchone()['max_id']
    new_id = 1 if max_id is None else max_id + 1

    insert = '''INSERT INTO airplane (airplane_id, airline_name, num_seats, manufacturing_company)
                VALUES (%s, %s, %s, %s)'''
    cursor.execute(insert, (new_id, airline_name, num_seats, company))
    conn.commit()

    cursor.execute("SELECT * FROM airplane WHERE airline_name = %s", (airline_name,))
    airplanes = cursor.fetchall()
    cursor.close()

    return render_template('airplanes_confirmation.html', airline_name=airline_name, airplanes=airplanes)

@app.route('/add_airport')
def add_airport():
    return render_template('add_airport.html')

@app.route('/view_ratings')
def view_ratings():
    return render_template('view_ratings.html')

@app.route('/view_reports')
def view_reports():
    return render_template('view_reports.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_type', None)
    return redirect('/')

app.secret_key = 'some key that you will never guess'

if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug=True)

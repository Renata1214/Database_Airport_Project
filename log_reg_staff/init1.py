from flask import Flask, render_template, request, session, url_for, redirect
import pymysql.cursors
import hashlib
import traceback
import re

app = Flask(__name__)
app.secret_key = 'some key that you will never guess'

# Configure MySQL
conn = pymysql.connect(host='localhost',
                       user='root',
                       password='',
                       db='airport', 
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)

@app.route('/', methods=['GET', 'POST'])
def home():
    cursor = conn.cursor()
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
        cursor.execute("SELECT * FROM customer WHERE customer_email = %s AND cust_password = %s", (username, hashed_pw))
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
    try:
        user_type = request.form['user_type']
        password = request.form['password']
        hashed_pw = hashlib.md5(password.encode()).hexdigest()
        cursor = conn.cursor()

        if user_type == 'customer':
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

        conn.commit()
        cursor.close()
        return redirect(url_for('home'))

    except Exception:
        conn.rollback()
        print(traceback.format_exc())
        airlines = get_airline_names()
        return render_template('register.html', error="Internal error during registration", airlines=airlines)

@app.route('/staff_home', methods=['GET', 'POST'])
def staff_home():
    if session.get('user_type') != 'staff':
        return redirect('/')

    cursor = conn.cursor()
    airline_name = get_airline_for_staff(session['username'])

    cursor.execute("SELECT airplane_id FROM airplane")
    airplanes = cursor.fetchall()

    cursor.execute("SELECT code FROM airport")
    airports = cursor.fetchall()

    if request.method == 'POST':
        source = request.form.get('source') or None
        destination = request.form.get('destination') or None
        start_date = request.form.get('start_date') or None
        end_date = request.form.get('end_date') or None

        query = '''
            SELECT * FROM flight
            WHERE airline_name = %s
              AND (%s IS NULL OR departure_airport_code = %s)
              AND (%s IS NULL OR arrival_airport_code = %s)
              AND (%s IS NULL OR DATE(departure_date) >= %s)
              AND (%s IS NULL OR DATE(departure_date) <= %s)
            ORDER BY departure_date ASC
        '''
        cursor.execute(query, (
            airline_name,
            source, source,
            destination, destination,
            start_date, start_date,
            end_date, end_date
        ))
    else:
        cursor.execute('''
            SELECT * FROM flight
            WHERE airline_name = %s
              AND departure_date >= CURDATE()
              AND departure_date <= DATE_ADD(CURDATE(), INTERVAL 30 DAY)
            ORDER BY departure_date ASC
        ''', (airline_name,))

    flights = cursor.fetchall()
    cursor.close()

    return render_template('staff_home.html', flights=flights, airline=airline_name, airplanes=airplanes, airports=airports)

@app.route('/staff/customers/<airline>/<flight_number>/<departure_date>/<departure_time>')
def view_customers(airline, flight_number, departure_date, departure_time):
    if session.get('user_type') != 'staff':
        return redirect('/')

    cursor = conn.cursor()

    query = '''
        SELECT DISTINCT customer.customer_email, customer.customer_name
        FROM customer
        JOIN purchase ON customer.customer_email = purchase.customer_email
        JOIN ticket ON purchase.ticket_id = ticket.ticket_id
        WHERE ticket.airline_name = %s
          AND ticket.flight_number = %s
          AND ticket.departure_date = %s
          AND ticket.departure_time = %s
    '''
    cursor.execute(query, (airline, flight_number, departure_date, departure_time))
    customers = cursor.fetchall()
    cursor.close()

    return render_template('view_customers.html', 
                           airline=airline,
                           flight_number=flight_number,
                           departure_date=departure_date,
                           departure_time=departure_time,
                           customers=customers)


@app.route('/staff/create_flight', methods=['POST'])
def create_flight():
    if session.get('user_type') != 'staff':
        return redirect('/')
    data = request.form.to_dict()
    data['airline_name'] = get_airline_for_staff(session['username'])
    create_flight_in_db(data)
    return redirect('/staff_home')

@app.route('/staff/change_status', methods=['POST'])
def change_status():
    if session.get('user_type') != 'staff':
        return redirect('/')
    update_flight_status(
        request.form['flight_number'],
        request.form['departure_date'],
        request.form['new_status']
    )
    return redirect('/staff_home')

@app.route('/staff/add_airplane', methods=['POST'])
def add_airplane():
    if session.get('user_type') != 'staff':
        return redirect('/')
    username = session['username']
    airline_name = get_airline_for_staff(username)

    seats = int(request.form['seats'])
    manufacturer = request.form['manufacturing_company']

    cursor = conn.cursor()
    cursor.execute("SELECT airplane_id FROM airplane WHERE airline_name = %s ORDER BY airplane_id DESC LIMIT 1", (airline_name,))
    latest = cursor.fetchone()
    if latest:
        match = re.search(r'(\d+)', latest['airplane_id'])
        new_id = f"A{int(match.group(1)) + 1:03}" if match else "A001"
    else:
        new_id = "A001"

    try:
        cursor.execute("""
            INSERT INTO airplane (airplane_id, airline_name, seats, manufacturing_company)
            VALUES (%s, %s, %s, %s)
        """, (new_id, airline_name, seats, manufacturer))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("Error adding airplane:", e)
    finally:
        cursor.close()

    return redirect('/staff_home')

@app.route('/staff/add_airport', methods=['POST'])
def add_airport():
    if session.get('user_type') != 'staff':
        return redirect('/')
    add_airport_to_db(request.form.to_dict())
    return redirect('/staff_home')

@app.route('/staff_home/ratings')
def view_ratings():
    if session.get('user_type') != 'staff':
        return redirect('/')
    airline_name = get_airline_for_staff(session['username'])

    query = """
    SELECT 
        f.flight_number,
        f.departure_date,
        f.departure_time,
        AVG(r.rate) AS average_rating
    FROM flight f
    LEFT JOIN review r 
        ON f.airline_name = r.airline_name 
        AND f.flight_number = r.flight_number 
        AND f.departure_date = r.departure_date 
        AND f.departure_time = r.departure_time
    WHERE f.airline_name = %s
    GROUP BY f.flight_number, f.departure_date, f.departure_time
    ORDER BY f.departure_date DESC, f.departure_time DESC
    """
    cursor = conn.cursor()
    cursor.execute(query, (airline_name,))
    flights = cursor.fetchall()

    # Get full reviews for all flights
    review_query = """
    SELECT 
        flight_number,
        departure_date,
        departure_time,
        customer_email,
        rate,
        comment
    FROM review
    WHERE airline_name = %s
    ORDER BY departure_date DESC, departure_time DESC
    """
    cursor.execute(review_query, (airline_name,))
    all_reviews = cursor.fetchall()

    return render_template('view_ratings.html', flights=flights, reviews=all_reviews)

@app.route('/staff_home/reports', methods=['GET', 'POST'])
def staff_reports():
    if session.get('user_type') != 'staff':
        return redirect('/')

    cursor = conn.cursor()
    airline_name = get_airline_for_staff(session['username'])

    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    if request.method == 'POST' and start_date and end_date:
        query = '''
            SELECT f.flight_number, f.departure_date, COUNT(p.ticket_id) AS tickets_sold
            FROM flight f
            LEFT JOIN ticket t ON f.airline_name = t.airline_name 
                              AND f.flight_number = t.flight_number
                              AND f.departure_date = t.departure_date
                              AND f.departure_time = t.departure_time
            LEFT JOIN purchase p ON t.ticket_id = p.ticket_id
            WHERE f.airline_name = %s
              AND f.departure_date BETWEEN %s AND %s
            GROUP BY f.flight_number, f.departure_date
            ORDER BY f.departure_date ASC
        '''
        cursor.execute(query, (airline_name, start_date, end_date))
    else:
        # Default: next 30 days
        query = '''
            SELECT f.flight_number, f.departure_date, COUNT(p.ticket_id) AS tickets_sold
            FROM flight f
            LEFT JOIN ticket t ON f.airline_name = t.airline_name 
                              AND f.flight_number = t.flight_number
                              AND f.departure_date = t.departure_date
                              AND f.departure_time = t.departure_time
            LEFT JOIN purchase p ON t.ticket_id = p.ticket_id
            WHERE f.airline_name = %s
              AND f.departure_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)
            GROUP BY f.flight_number, f.departure_date
            ORDER BY f.departure_date ASC
        '''
        cursor.execute(query, (airline_name,))

    results = cursor.fetchall()
    cursor.close()

    # Prepare data for chart
    labels = [f"{r['flight_number']} ({r['departure_date']})" for r in results]
    data = [r['tickets_sold'] for r in results]

    return render_template('view_reports.html', 
                           airline=airline_name,
                           results=results,
                           labels=labels,
                           data=data,
                           start_date=start_date,
                           end_date=end_date)

# --- Helper Functions ---
def get_airline_names():#not in use
    with conn.cursor() as cursor:
        cursor.execute("SELECT airline_name FROM airline")
        return [row['airline_name'] for row in cursor.fetchall()]

def get_airline_for_staff(username):
    with conn.cursor() as cursor:
        cursor.execute("SELECT airline_name FROM airline_staff WHERE username = %s", (username,))
        result = cursor.fetchone()
        return result['airline_name'] if result else None

def create_flight_in_db(data):
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO flight (airline_name, flight_number, departure_date, departure_time, airplane_id, airplane_airline_name, departure_airport_code,
                                arrival_airport_code, arrival_date, arrival_time, base_price, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data['airline_name'], data['flight_number'], data['departure_date'], data['departure_time'],
            data['airplane_id'], data['airplane_airline_name'], data['departure_airport_code'], data['arrival_airport_code'],
            data['arrival_date'], data['arrival_time'], data['base_price'], data.get('status', 'on-time')
        ))
    conn.commit()

def update_flight_status(flight_number, departure_datetime, new_status):
    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE flight SET status = %s WHERE flight_number = %s AND departure_date = %s
        """, (new_status, flight_number, departure_datetime))
    conn.commit()

def add_airport_to_db(data):
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO airport (code, airport_name, city, country)
            VALUES (%s, %s, %s, %s)
        """, (data['code'], data['airport_name'], data['city'], data['country']))
    conn.commit()
    
#--------------------------------------------------------------------------------------------------

@app.route('/customer_home')
def customer_home():
    return render_template('customer_home.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_type', None)
    return redirect('/')



if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug=True)

from flask import Flask, render_template, request, session, url_for, redirect, flash
from datetime import datetime, timedelta, time
import pymysql.cursors
import hashlib
import traceback
import re

app = Flask(__name__)
app.secret_key = 'some key that you will never guess'
REFERENCE_DATETIME= datetime.now()
staff_code_main = "1234"
# Configure MySQL
conn = pymysql.connect(host='localhost',
                       user='root',
                       password='',
                       db='airport', 
                       charset='utf8mb4',
                       port = 3307,
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
                  AND departure_date >= %s
                  AND DATE(departure_date) >= %s
                  AND DATE(arrival_date) <= %s
            """
            cursor.execute(query, (
                f"%{source}%",
                f"%{destination}%",
                REFERENCE_DATETIME,
                departure_date,
                return_date
            ))
        else:
            query = """
                SELECT * FROM flight
                WHERE departure_airport_code LIKE %s
                  AND arrival_airport_code LIKE %s
                  AND departure_date >= %s
                  AND DATE(departure_date) >= %s
            """
            cursor.execute(query, (
                f"%{source}%",
                f"%{destination}%",
                REFERENCE_DATETIME,
                departure_date
            ))

        flights = cursor.fetchall()

    cursor.close()
    return render_template('home.html', flights=flights, airport_codes=airport_codes)

@app.route('/register')
def register():
    cursor = conn.cursor()
    cursor.execute("SELECT airline_name FROM airline")
    airlines = [row['airline_name'] for row in cursor.fetchall()]
    cursor.close()
    return render_template('register.html', airlines=airlines, staff_code=staff_code_main)

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
        # reg_code = request.form['registration_code']
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
            reg_code = request.form['registration_code']
            if reg_code == staff_code_main:
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
                print("Submitted reg_code:", repr(reg_code))
                print("Expected staff_code_main:", repr(staff_code_main))
                flash('Unauthorized: Invalid registration code for staff.', 'danger')
                return redirect(url_for('home'))
            
        conn.commit()
        cursor.close()
        return redirect(url_for('home'))

    except Exception:
        # print("Submitted reg_code:", repr(reg_code))
        # print("Expected staff_code_main:", repr(staff_code_main))
        conn.rollback()
        print(traceback.format_exc())
        airlines = get_airline_names()
        return render_template('register.html', error="Internal error during registration", airlines=airlines)

@app.route('/staff_home', methods=['GET', 'POST'])
def staff_home():
    if session.get('user_type') != 'staff':
        return redirect('/')

    cursor = conn.cursor()
    username = session['username']
    airline_name = get_airline_for_staff(username)

    cursor.execute("SELECT airplane_id FROM airplane")
    airplanes = cursor.fetchall()

    cursor.execute("SELECT code FROM airport")
    airports = cursor.fetchall()

    # Fetch staff's phone numbers and emails
    cursor.execute("SELECT phone_number FROM staff_phone_number WHERE username = %s", (username,))
    phone_numbers = cursor.fetchall()

    cursor.execute("SELECT email FROM staff_email WHERE username = %s", (username,))
    emails = cursor.fetchall()

    # Flight filtering logic
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

    return render_template(
        'staff_home.html',
        flights=flights,
        airline=airline_name,
        airplanes=airplanes,
        airports=airports,
        phone_numbers=phone_numbers,
        emails=emails
    )

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
    data['flight_number'] = generate_flight_number(data['airline_name'])  # Auto-generate flight number

    create_flight_in_db(data)
    return redirect('/staff_home')

@app.route('/staff/change_status', methods=['POST'])
def change_status():
    if session.get('user_type') != 'staff':
        return redirect('/')
    
    success = update_flight_status(
        request.form['flight_number'],
        request.form['departure_date'],
        request.form['new_status']
    )

    if success:
        flash('Flight status updated successfully.', 'success')
    else:
        flash('Cannot update: Flight already departed.', 'error')

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

    # Extract the first letter of the airline_name and convert to uppercase
    prefix = airline_name[0].upper()

    # Query the latest airplane_id that starts with this prefix
    cursor.execute(
        "SELECT airplane_id FROM airplane WHERE airline_name = %s AND airplane_id LIKE %s ORDER BY airplane_id DESC LIMIT 1",
        (airline_name, f"{prefix}%")
    )
    latest = cursor.fetchone()

    if latest:
        match = re.search(rf'{prefix}(\d+)', latest['airplane_id'])
        new_id = f"{prefix}{int(match.group(1)) + 1:03}" if match else f"{prefix}001"
    else:
        new_id = f"{prefix}001"

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

@app.route('/staff/add_phone', methods=['POST'])
def add_phone():
    if session.get('user_type') != 'staff':
        return redirect('/')
    
    username = session['username']
    phone = request.form['phone_number']
    
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO staff_phone_number (username, phone_number) VALUES (%s, %s)", (username, phone))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(e)
    finally:
        cursor.close()
    
    return redirect('/staff_home')


@app.route('/staff/add_email', methods=['POST'])
def add_email():
    if session.get('user_type') != 'staff':
        return redirect('/')
    
    username = session['username']
    email = request.form['email']
    
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO staff_email (username, email) VALUES (%s, %s)", (username, email))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(e)
    finally:
        cursor.close()
    
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
            SELECT 
                f.flight_number, f.departure_date,
                f.departure_airport_code, f.arrival_airport_code,
                COUNT(p.ticket_id) AS tickets_sold,
                AVG(r.rate) AS avg_rating
            FROM flight f
            LEFT JOIN ticket t ON f.airline_name = t.airline_name 
                              AND f.flight_number = t.flight_number
                              AND f.departure_date = t.departure_date
                              AND f.departure_time = t.departure_time
            LEFT JOIN purchase p ON t.ticket_id = p.ticket_id
            LEFT JOIN review r ON f.airline_name = r.airline_name
                              AND f.flight_number = r.flight_number
                              AND f.departure_date = r.departure_date
                              AND f.departure_time = r.departure_time
            WHERE f.airline_name = %s
              AND f.departure_date BETWEEN %s AND %s
            GROUP BY f.flight_number, f.departure_date, f.departure_airport_code, f.arrival_airport_code
            ORDER BY f.departure_date ASC
        '''
        cursor.execute(query, (airline_name, start_date, end_date))
    else:
        query = '''
            SELECT 
                f.flight_number, f.departure_date,
                f.departure_airport_code, f.arrival_airport_code,
                COUNT(p.ticket_id) AS tickets_sold,
                AVG(r.rate) AS avg_rating
            FROM flight f
            LEFT JOIN ticket t ON f.airline_name = t.airline_name 
                              AND f.flight_number = t.flight_number
                              AND f.departure_date = t.departure_date
                              AND f.departure_time = t.departure_time
            LEFT JOIN purchase p ON t.ticket_id = p.ticket_id
            LEFT JOIN review r ON f.airline_name = r.airline_name
                              AND f.flight_number = r.flight_number
                              AND f.departure_date = r.departure_date
                              AND f.departure_time = r.departure_time
            WHERE f.airline_name = %s
              AND f.departure_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)
            GROUP BY f.flight_number, f.departure_date, f.departure_airport_code, f.arrival_airport_code
            ORDER BY f.departure_date ASC
        '''
        cursor.execute(query, (airline_name,))

    flights = cursor.fetchall()
    cursor.close()
    return render_template("view_reports.html", flights=flights, airline=airline_name)

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

def generate_flight_number(airline_name):
    with conn.cursor() as cursor:
        # Extract max numeric part from existing flight numbers for this airline
        cursor.execute("""
            SELECT MAX(CAST(SUBSTRING(flight_number, 2) AS UNSIGNED)) AS max_num
            FROM flight
            WHERE airline_name = %s
            AND LENGTH(flight_number) = 5
            AND flight_number REGEXP '^[A-Z][0-9]{4}$'
        """, (airline_name,))
        result = cursor.fetchone()
        max_num = result['max_num'] if result and result['max_num'] is not None else 0
        next_num = max_num + 1

        # Use first letter of airline as prefix (you could expand to 2 letters if needed)
        prefix = airline_name[0].upper()
        return f"{prefix}{str(next_num).zfill(4)}"

def create_flight_in_db(data):
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO flight (
                airline_name, flight_number, departure_date, departure_time, 
                airplane_id, airplane_airline_name, departure_airport_code,
                arrival_airport_code, arrival_date, arrival_time, base_price, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data['airline_name'], data['flight_number'], data['departure_date'], data['departure_time'],
            data['airplane_id'], data['airplane_airline_name'], data['departure_airport_code'], data['arrival_airport_code'],
            data['arrival_date'], data['arrival_time'], data['base_price'], data.get('status', 'on-time')
        ))
    conn.commit()

def update_flight_status(flight_number, departure_date, new_status):
    airline_name = get_airline_for_staff(session['username'])
    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE flight
            SET status = %s
            WHERE airline_name = %s
              AND flight_number = %s
              AND departure_date = %s
              AND departure_date >= CURDATE()
        """, (new_status, airline_name, flight_number, departure_date))
        updated_rows = cursor.rowcount
    conn.commit()
    return updated_rows > 0

def add_airport_to_db(data):
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO airport (code, airport_name, city, country)
            VALUES (%s, %s, %s, %s)
        """, (data['code'], data['airport_name'], data['city'], data['country']))
    conn.commit()
    
#--------------------------------------------------------------------------------------------------
@app.route('/customer_home', methods=['GET', 'POST'])
def customer_home():
    if session.get('user_type') != 'customer':
        return redirect('/')

    email = session['username']
    cursor = conn.cursor()

    cursor.execute("SELECT customer_name FROM customer WHERE customer_email = %s", (email,))
    name_result = cursor.fetchone()
    customer_name = name_result['customer_name'] if name_result else email

    cursor.execute("SELECT code FROM airport")
    airport_names = [row['code'] for row in cursor.fetchall()]

    # Base query
    my_flights_query = '''
        SELECT f.*, t.ticket_id
        FROM flight f
        JOIN ticket t ON f.airline_name = t.airline_name AND f.flight_number = t.flight_number
                      AND f.departure_date = t.departure_date AND f.departure_time = t.departure_time
        JOIN purchase p ON p.ticket_id = t.ticket_id
        WHERE p.customer_email = %s
    '''
    params = [email]
    show_past = False
    filtered = False

    # Handle form submissions
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'view_flights':
            filtered = True
            source = request.form.get('source_filter', '').strip()
            destination = request.form.get('destination_filter', '').strip()
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')

            if source:
                my_flights_query += '''
                    AND (f.departure_airport_code LIKE %s OR f.departure_airport_code IN
                         (SELECT code FROM airport WHERE city LIKE %s))'''
                params.extend([f"%{source}%", f"%{source}%"])

            if destination:
                my_flights_query += '''
                    AND (f.arrival_airport_code LIKE %s OR f.arrival_airport_code IN
                         (SELECT code FROM airport WHERE city LIKE %s))'''
                params.extend([f"%{destination}%", f"%{destination}%"])

            if start_date:
                my_flights_query += " AND f.departure_date >= %s"
                params.append(start_date)

            if end_date:
                my_flights_query += " AND f.departure_date <= %s"
                params.append(end_date)

        elif action == 'show_past':
            show_past = True
            my_flights_query += " AND f.departure_date < CURDATE()"
        elif action == 'view_future':
            # No filters needed, just show future flights
            my_flights_query += " AND f.departure_date >= CURDATE()"

    # Apply default filter if not searching or requesting past
    if not filtered and not show_past:
        my_flights_query += " AND f.departure_date >= CURDATE()"

    cursor.execute(my_flights_query, tuple(params))
    my_flights = cursor.fetchall()

    # Review and cancellation eligibility
    for flight in my_flights:
        if isinstance(flight['departure_time'], timedelta):
            total_seconds = flight['departure_time'].seconds
            hours, minutes = divmod(total_seconds // 60, 60)
            dep_time = time(hours, minutes)
        else:
            dep_time = flight['departure_time']

        dep_datetime = datetime.combine(flight['departure_date'], dep_time)
        now = datetime.now()
        flight['can_cancel'] = (dep_datetime - now) > timedelta(hours=24)
        flight['can_review'] = dep_datetime < now

    cursor.close()
    return render_template('customer_home.html', my_flights=my_flights, airport_codes=airport_names, customer_name=customer_name)

@app.route('/search_flights', methods=['GET', 'POST'])
def search_flights():
    if session.get('user_type') != 'customer':
        return redirect('/')

    cursor = conn.cursor()
    cursor.execute("SELECT code FROM airport")
    airport_names = [row['code'] for row in cursor.fetchall()]

    search_results = []

    if request.method == 'POST':
        source = request.form['source']
        destination = request.form['destination']
        departure_date = request.form.get('departure_date')
        return_date = request.form.get('return_date')

        query = '''
            SELECT * FROM flight
            WHERE departure_airport_code = %s AND arrival_airport_code = %s AND departure_date >= CURDATE()
        '''
        params = [source, destination]

        if departure_date:
            query += ' AND departure_date = %s'
            params.append(departure_date)

        if return_date:
            query += '''
                UNION ALL
                SELECT * FROM flight
                WHERE departure_airport_code = %s AND arrival_airport_code = %s
                AND departure_date = %s
                AND departure_date >= CURDATE()
            '''
            params.extend([destination, source, return_date])

        cursor.execute(query, tuple(params))
        raw_flights = cursor.fetchall()

        # Enrich flights with dynamic pricing
        search_results = []
        for flight in raw_flights:
            # Get seating capacity
            cursor.execute('''
                SELECT seats FROM airplane
                WHERE airplane_id = %s AND airline_name = %s
            ''', (flight['airplane_id'], flight['airplane_airline_name']))
            airplane = cursor.fetchone()

            if not airplane:
                continue  # skip this flight if airplane info is missing

            capacity = airplane['seats']

            # Count how many tickets are already sold
            cursor.execute('''
                SELECT COUNT(*) AS count
                FROM ticket
                WHERE airline_name = %s AND flight_number = %s AND departure_date = %s AND departure_time = %s
            ''', (
                flight['airline_name'],
                flight['flight_number'],
                flight['departure_date'],
                flight['departure_time']
            ))
            sold = cursor.fetchone()['count']
            demand_ratio = sold / capacity

            # Calculate final price
            base_price = flight['base_price']
            final_price = round(base_price * 1.2, 2) if demand_ratio >= 0.6 else round(base_price, 2)

            # Attach to flight dict
            flight['final_price'] = final_price
            search_results.append(flight)

    cursor.close()
    return render_template('search_flights.html',
                           airport_names=airport_names,
                           search_results=search_results)




@app.route('/cancel_ticket', methods=['GET', 'POST'])
def cancel_ticket():
    if session.get('user_type') != 'customer':
        return redirect('/')

    email = session['username']

    if request.method == 'GET':
        # Show confirmation page
        return render_template('cancel_ticket.html',
                               ticket_id=request.args['ticket_id'],
                               airline_name=request.args['airline_name'],
                               flight_number=request.args['flight_number'],
                               departure_date=request.args['departure_date'],
                               departure_time=request.args['departure_time'])

    # POST — perform cancellation
    ticket_id = request.form['ticket_id']

    try:
        cursor = conn.cursor()

        # Step 1: Get the flight departure date & time for this ticket
        cursor.execute('''
            SELECT f.departure_date, f.departure_time
            FROM flight f
            JOIN ticket t ON f.airline_name = t.airline_name
                          AND f.flight_number = t.flight_number
                          AND f.departure_date = t.departure_date
                          AND f.departure_time = t.departure_time
            WHERE t.ticket_id = %s
        ''', (ticket_id,))
        result = cursor.fetchone()

        if not result:
            return "Flight or ticket not found.", 404

        dep_date = result['departure_date']
        dep_time = result['departure_time']

        # Handle case if time is a timedelta instead of datetime.time
        if isinstance(dep_time, timedelta):
            hours, remainder = divmod(dep_time.seconds, 3600)
            minutes = (remainder // 60)
            dep_time = time(hours, minutes)

        flight_datetime = datetime.combine(dep_date, dep_time)

        # Check if flight is more than 24 hours in the future
        if flight_datetime - datetime.now() < timedelta(hours=24):
            flash("Ticket cannot be canceled less than 24 hours before departure.", "danger")
            return redirect('/customer_home')


        # Step 2: Delete from purchase first (FK dependency)
        cursor.execute('''
            DELETE FROM purchase
            WHERE ticket_id = %s AND customer_email = %s
        ''', (ticket_id, email))

        # Step 3: Delete the ticket itself
        cursor.execute('''
            DELETE FROM ticket
            WHERE ticket_id = %s
        ''', (ticket_id,))

        conn.commit()
        cursor.close()
        flash("Your ticket has been successfully canceled.", "success")
        return redirect('/customer_home')


    except Exception as e:
        conn.rollback()
        print("Error during cancellation:", e)
        return "Error during cancellation.", 500


@app.route('/review_flight', methods=['GET', 'POST'])
def review_flight():
    if session.get('user_type') != 'customer':
        return redirect('/')

    email = session['username']

    if request.method == 'GET':
        return render_template('review_form.html',
                               airline_name=request.args['airline_name'],
                               flight_number=request.args['flight_number'],
                               departure_date=request.args['departure_date'],
                               departure_time=request.args['departure_time'])

    # POST: submit review
    airline_name = request.form['airline_name']
    flight_number = request.form['flight_number']
    departure_date = request.form['departure_date']
    departure_time = request.form['departure_time']
    rating = request.form['rating']
    comment = request.form['comment']

    try:
        cursor = conn.cursor()

        # Check if review already exists (avoid duplicates)
        cursor.execute('''
            SELECT * FROM review
            WHERE airline_name = %s AND flight_number = %s
              AND departure_date = %s AND departure_time = %s
              AND customer_email = %s
        ''', (airline_name, flight_number, departure_date, departure_time, email))

        if cursor.fetchone():
            flash("You have already submitted a review for this flight.", "warning")
            return redirect('/customer_home')

        # Insert new review
        cursor.execute('''
            INSERT INTO review (airline_name, flight_number, departure_date, departure_time, customer_email, rate, comment)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (airline_name, flight_number, departure_date, departure_time, email, rating, comment))

        conn.commit()
        cursor.close()

        flash("Thank you for submitting your review!", "success")
        return redirect('/customer_home')

    except Exception as e:
        conn.rollback()
        print("Error submitting review:", e)
        flash("An error occurred while submitting your review.", "danger")
        return redirect('/customer_home')


@app.route('/purchase', methods=['GET', 'POST'])
def purchase():
    if session.get('user_type') != 'customer':
        return redirect('/')

    if request.method == 'GET':
        airline_name = request.args['airline_name']
        flight_number = request.args['flight_number']
        departure_date = request.args['departure_date']
        departure_time = request.args['departure_time']

        cursor = conn.cursor()

        # Get airplane and base price
        cursor.execute('''
            SELECT airplane_id, airplane_airline_name, base_price
            FROM flight
            WHERE airline_name = %s AND flight_number = %s AND departure_date = %s AND departure_time = %s
        ''', (airline_name, flight_number, departure_date, departure_time))
        flight = cursor.fetchone()

        if not flight:
            return "Flight not found", 404

        airplane_id = flight['airplane_id']
        airplane_airline = flight['airplane_airline_name']
        base_price = flight['base_price']

        # Get seating capacity
        cursor.execute('''
            SELECT seats FROM airplane
            WHERE airplane_id = %s AND airline_name = %s
        ''', (airplane_id, airplane_airline))
        airplane = cursor.fetchone()

        if not airplane:
            return "Airplane not found", 404

        capacity = airplane['seats']

        # Count tickets already sold
        cursor.execute('''
            SELECT COUNT(*) AS count
            FROM ticket
            WHERE airline_name = %s AND flight_number = %s AND departure_date = %s AND departure_time = %s
        ''', (airline_name, flight_number, departure_date, departure_time))
        sold = cursor.fetchone()['count']
        cursor.close()

        # Calculate final price
        demand_ratio = sold / capacity
        final_price = round(base_price * 1.2, 2) if demand_ratio >= 0.6 else round(base_price, 2)

        return render_template('purchase.html',
                            airline_name=airline_name,
                            flight_number=flight_number,
                            departure_date=departure_date,
                            departure_time=departure_time,
                            final_price=final_price)
    # POST method
    email = session['username']
    airline_name = request.form['airline_name']
    flight_number = request.form['flight_number']
    departure_date = request.form['departure_date']
    departure_time = request.form['departure_time']

    try:
        cursor = conn.cursor()

        # Step 1: Get the airplane assigned to this flight
        cursor.execute('''
            SELECT airplane_id, airplane_airline_name
            FROM flight
            WHERE airline_name = %s AND flight_number = %s AND departure_date = %s AND departure_time = %s
        ''', (airline_name, flight_number, departure_date, departure_time))
        flight = cursor.fetchone()

        if not flight:
            return "Flight not found", 404

        airplane_id = flight['airplane_id']
        airplane_airline = flight['airplane_airline_name']

        # Step 2: Get seating capacity
        cursor.execute('''
            SELECT seats FROM airplane
            WHERE airplane_id = %s AND airline_name = %s
        ''', (airplane_id, airplane_airline))
        airplane = cursor.fetchone()

        if not airplane:
            return "Airplane not found", 404

        max_capacity = airplane['seats']

        # Step 3: Count how many tickets already sold
        cursor.execute('''
            SELECT COUNT(*) AS count
            FROM ticket
            WHERE airline_name = %s AND flight_number = %s AND departure_date = %s AND departure_time = %s
        ''', (airline_name, flight_number, departure_date, departure_time))
        sold = cursor.fetchone()['count']

        if sold >= max_capacity:
            return "No more seats available for this flight.", 400
        
        # Step 4: Get base price of the flight
        cursor.execute('''
            SELECT base_price FROM flight
            WHERE airline_name = %s AND flight_number = %s AND departure_date = %s AND departure_time = %s
        ''', (airline_name, flight_number, departure_date, departure_time))
        price_result = cursor.fetchone()

        if not price_result:
            return "Could not retrieve base price.", 500

        base_price = price_result['base_price']

        # Calculate demand ratio
        demand_ratio = sold / max_capacity

        # If 60% or more booked, increase price by 20%
        # Use price from hidden field
        final_price = float(request.form['sold_price'])

        # Step 4: Insert into ticket
        cursor.execute('''
            INSERT INTO ticket (
                airline_name, flight_number, departure_date, departure_time,
                sold_price, card_type, card_number, name_on_card, expiration_date,
                purchase_date, purchase_time
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURDATE(), CURTIME())
        ''', (
            airline_name,
            flight_number,
            departure_date,
            departure_time,
            final_price,
            request.form['card_type'],
            request.form['card_number'],
            request.form['name_on_card'],
            request.form['expiration_date']
        ))

        # Step 5: Get the new ticket_id
        ticket_id = cursor.lastrowid

        # Step 6: Insert into purchase
        cursor.execute('''
            INSERT INTO purchase (ticket_id, customer_email)
            VALUES (%s, %s)
        ''', (ticket_id, email))

        conn.commit()
        cursor.close()
        return render_template("purchase_success.html", ticket_id=ticket_id, airline_name=airline_name,
                       flight_number=flight_number, departure_date=departure_date, departure_time=departure_time)


    except Exception as e:
        conn.rollback()
        print("Purchase error:", e)
        return "Error during purchase", 500



@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_type', None)
    return redirect('/')



if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug=True)
# Import Flask Library
from flask import Flask, render_template, request, session, url_for, redirect, flash
import pymysql.cursors
import hashlib
import traceback #remember to add this library
from datetime import datetime, timedelta, time

# Simulated "current" datetime (e.g., May 10, 2025 at 12:00)
#REFERENCE_DATETIME = datetime(2025, 5, 2, 12, 0, 0)
#REFERENCE_DATETIME = datetime(2015, 5, 10)
REFERENCE_DATETIME= datetime.now()

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
              AND (%s IS NULL OR DATE(departure_date) >= %s)
              AND (%s IS NULL OR DATE(departure_date) <= %s)
            ORDER BY departure_datet ASC
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
              AND departure_date >= NOW()
              AND departure_date <= DATE_ADD(NOW(), INTERVAL 30 DAY)
            ORDER BY departure_date ASC
        '''
        cursor.execute(query, (airline_name,))

    flights = cursor.fetchall()
    cursor.close()
    return render_template('staff_home.html', flights=flights, airline=airline_name)

@app.route('/customer_home', methods=['GET', 'POST'])
def customer_home():
    if session.get('user_type') != 'customer':
        return redirect('/')

    email = session['username']
    cursor = conn.cursor()

    cursor.execute("SELECT customer_name FROM customer WHERE customer_email = %s", (session['username'],))
    name_result = cursor.fetchone()
    customer_name = name_result['customer_name'] if name_result else session['username']


    # Load airport codes for dropdowns if needed later
    cursor.execute("SELECT code FROM airport")
    airport_names = [row['code'] for row in cursor.fetchall()]

    # === Always show purchased flights ===
    my_flights_query = '''
        SELECT f.*, t.ticket_id
        FROM flight f
        JOIN ticket t ON f.airline_name = t.airline_name AND f.flight_number = t.flight_number
                      AND f.departure_date = t.departure_date AND f.departure_time = t.departure_time
        JOIN purchase p ON p.ticket_id = t.ticket_id
        WHERE p.customer_email = %s
    '''
    params = [email]

    # === Handle optional filtering ===
    if request.method == 'POST' and request.form['action'] == 'view_flights':
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

    # === Execute final query ===
    cursor.execute(my_flights_query, tuple(params))
    my_flights = cursor.fetchall()

    # === Add logic for cancellation and reviews ===
    for flight in my_flights:
        # Handle departure_time type (time or timedelta)
        if isinstance(flight['departure_time'], timedelta):
            total_seconds = flight['departure_time'].seconds
            hours, minutes = divmod(total_seconds // 60, 60)
            dep_time = time(hours, minutes)
        else:
            dep_time = flight['departure_time']

        dep_datetime = datetime.combine(flight['departure_date'], dep_time)
        flight['can_cancel'] = (dep_datetime - REFERENCE_DATETIME) > timedelta(hours=24)
        flight['can_review'] = dep_datetime < REFERENCE_DATETIME

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

app.secret_key = 'some key that you will never guess'

if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug=True)


CREATE TABLE airport (
    code CHAR(6) PRIMARY KEY,
    airport_name VARCHAR(30),
    city VARCHAR(30),
    country VARCHAR(30)
);

CREATE TABLE airline (
    airline_name VARCHAR(30) PRIMARY KEY
);

CREATE TABLE airplane (
    airplane_id CHAR(5),
    airline_name VARCHAR(30),
    seats INT CHECK (seats > 0), 
    manufacturing_company VARCHAR(30),
    PRIMARY KEY (airplane_id, airline_name),
    FOREIGN KEY (airline_name) REFERENCES airline(airline_name)
);

CREATE TABLE flight (
    airline_name VARCHAR(30),
    flight_number CHAR(5),
    departure_date DATE, 
    departure_time TIME,
    airplane_id CHAR(5),
    airplane_airline_name VARCHAR(30),
    departure_airport_code CHAR(6),
    arrival_airport_code CHAR(6),
    arrival_date DATE, 
    arrival_time TIME,
    base_price FLOAT CHECK (base_price >= 0),
    status VARCHAR(8),
    PRIMARY KEY (airline_name, flight_number, departure_date, departure_time),
    FOREIGN KEY (airline_name) REFERENCES airline(airline_name),
    FOREIGN KEY (airplane_id, airplane_airline_name) REFERENCES airplane(airplane_id, airline_name),
    FOREIGN KEY (departure_airport_code) REFERENCES airport(code),
    FOREIGN KEY (arrival_airport_code) REFERENCES airport(code)
);

CREATE TABLE ticket (
    ticket_id INT PRIMARY KEY AUTO_INCREMENT,
    airline_name VARCHAR(30),
    flight_number CHAR(5),
    departure_date DATE, 
    departure_time TIME,
    sold_price FLOAT CHECK (sold_price >= 0),
    card_type VARCHAR(6),
    card_number VARCHAR(20),
    name_on_card VARCHAR(30),
    expiration_date DATE,
    purchase_date DATE,
    purchase_time TIME,
    FOREIGN KEY (airline_name, flight_number, departure_date, departure_time) REFERENCES flight(airline_name, flight_number, departure_date, departure_time)
);

CREATE TABLE airline_staff (
    username VARCHAR(20) PRIMARY KEY,
    airline_name VARCHAR(30),
    password VARCHAR(10),
    first_name VARCHAR(10),
    last_name VARCHAR(10),
    date_of_birth DATE,
    FOREIGN KEY (airline_name) REFERENCES airline(airline_name)
);

CREATE TABLE staff_phone_number (
    username VARCHAR(20),
    phone_number VARCHAR(10),
    PRIMARY KEY (username, phone_number),
    FOREIGN KEY (username) REFERENCES airline_staff(username) ON DELETE CASCADE
);

CREATE TABLE staff_email (
    username VARCHAR(20),
    email VARCHAR(30),
    PRIMARY KEY (username, email),
    FOREIGN KEY (username) REFERENCES airline_staff(username) ON DELETE CASCADE
);

CREATE TABLE customer (
    customer_email VARCHAR(30) PRIMARY KEY,
    customer_name VARCHAR(30),
    cust_password VARCHAR(10),
    building_number INT CHECK (building_number > 0),
    street_number VARCHAR(50),
    cust_city VARCHAR(30),
    state VARCHAR(15),
    cust_phone_number VARCHAR(10),
    passport_number VARCHAR(15),
    passport_expiration_date DATE,
    passport_country VARCHAR(30),
    cust_DOB DATE
);

CREATE TABLE purchase (
    ticket_id INT,
    customer_email VARCHAR(30),
    PRIMARY KEY (ticket_id, customer_email),
    FOREIGN KEY (ticket_id) REFERENCES ticket(ticket_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_email) REFERENCES customer(customer_email) ON DELETE CASCADE
);

CREATE TABLE review (
    airline_name VARCHAR(30),
    flight_number CHAR(5),
    departure_date DATE, 
    departure_time TIME,
    customer_email VARCHAR(30),
    rate INT CHECK (rate BETWEEN 1 AND 5),
    comment VARCHAR(1000),
    PRIMARY KEY (customer_email, airline_name, flight_number, departure_date, departure_time),
    FOREIGN KEY (airline_name, flight_number, departure_date, departure_time) REFERENCES flight(airline_name, flight_number, departure_date, departure_time) ON DELETE CASCADE,
    FOREIGN KEY (customer_email) REFERENCES customer(customer_email) ON DELETE CASCADE
);

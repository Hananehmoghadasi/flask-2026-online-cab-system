from flask import Flask, render_template, url_for, redirect, request, flash,session
from models import Users, Driver_location, Drivers, Passengers, Trips, Vehicles, Reviews, Payments, db
from peewee import fn
from geopy.distance import geodesic
import logging
import geopy
from peewee import IntegrityError
from werkzeug.security import (generate_password_hash, check_password_hash)
from functools import wraps

logging.basicConfig(
    level=logging.DEBUG,
    filename='cab.log',
    format='%(message)s - %(filename)s - %(asctime)s - %(levelname)s'
)

def login_required(f):

    @wraps(f)

    def wrapper(*args, **kwargs):

        if 'user_id' not in session:

            return redirect('/login')

        return f(*args, **kwargs)

    return wrapper


def admin_required(f):

    @wraps(f)

    def wrapper(*args, **kwargs):

        if session.get('role') != 'admin':

            flash(
                'Access denied',
                'danger'
            )

            return redirect('/index')

        return f(*args, **kwargs)

    return wrapper


def calculate_distance(lat1, long1, lat2, long2):
    point1 = (lat1, long1)
    point2 = (lat2, long2)
    # فاصله واقعی روی کره زمین رو محاسبه میکنه
    return geodesic(point1, point2).kilometers


def calculate_price(distance_km):
    rate_per_km = 10000
    min_price = 20000
    price = distance_km*rate_per_km
    if price < min_price:
        return int(min_price)
    else:
        return int(price)


app = Flask(__name__)
app.config["SECRET_KEY"] = "taxi-project-2025"


@app.before_request
def before_request():
    db.connect(reuse_if_open=True)


@app.teardown_request
def teardown_request(exc):
    if not db.is_closed():
        db.close()


@app.route("/index")
def index():
    return render_template("index.html")

# مدیریت کاربرا


@app.route("/users")
@login_required
@admin_required
def users():
    users = Users.select()
    return render_template("users.html", users=users)


@app.route('/users/add',
           methods=['GET', 'POST'])
def add_user():

    if request.method == 'POST':

        password = generate_password_hash(
            request.form['password']
        )

        Users.create(
            fullname=request.form['fullname'],
            phone=request.form['phone'],
            password=password,
            role=request.form['role']
        )

        return redirect('/users')

    return render_template(
        'user_form.html'
    )


@app.route("/users/delete/<int:id>")
def delete_user(id):
    user = Users.get_or_none(Users.id == id)

    if user:
        user.delete_instance(recursive=True)

    return redirect("/users")


@app.route('/users/edit/<int:id>',
           methods=['GET', 'POST'])
def edit_user(id):

    user = Users.get_or_none(
        Users.id == id
    )

    if not user:
        return redirect('/users')

    if request.method == 'POST':
        try:
            user.fullname = request.form['fullname']
            user.phone = request.form['phone']

            user.save()

            return redirect('/users')
        except IntegrityError:
            flash('phone already exsits!')

    return render_template(
        'user_form.html',
        user=user
    )


@app.route('/users/search')
def search_users():

    q = request.args.get('q', '')

    users = Users.select().where(
        (Users.fullname.contains(q)) | (Users.phone.contains(q))
    )

    return render_template(
        'users.html',
        users=users
    )

# مدیریت راننده


@app.route('/drivers')
@login_required
@admin_required
def drivers():
    drivers = Drivers.select().join(Users)
    return render_template('drivers.html', drivers=drivers)


@app.route("/drivers/add", methods=["GET", "POST"])
def add_driver():

    if request.method == 'POST':
        user_id = request.form['user_id']
        rating = request.form['rating']
        status = request.form.get('status', 'inactive')

        if not Users.select().where(Users.id == user_id).exists():
            flash('User not found', 'danger')
        else:
            Drivers.create(
                user_id=user_id,
                rating=rating,
                status=status
            )

        return redirect(url_for('drivers'))

    used_users = Drivers.select(Drivers.user)

    users = Users.select().where(
        Users.id.not_in(used_users)
    )

    return render_template(
        'driver_form.html',
        users=users
    )


@app.route("/drivers/delete/<int:id>")
def delete_driver(id):
    driver = Drivers.get_or_none(Drivers.id == id)

    if driver:
        driver.delete_instance(recursive=True)

    return redirect("/drivers")


@app.route('/drivers/edit/<int:id>',
           methods=['GET', 'POST'])
def edit_driver(id):

    driver = Drivers.get_or_none(
        Drivers.id == id
    )

    if not driver:
        return redirect('/drivers')

    if request.method == 'POST':

        driver.rating = float(
            request.form['rating']
        )

        driver.status = request.form['status']

        driver.save()

        flash(
            'Driver updated',
            'success'
        )

        return redirect('/drivers')

    return render_template(
        'driver_form.html',
        driver=driver,
        users=Users.select()
    )


@app.route('/drivers/search')
def search_drivers():

    q = request.args.get('q', '')

    drivers = (
        Drivers
        .select()
        .join(Users)
        .where(
            (Users.fullname.contains(q)) | (Users.phone.contains(q))
        )
    )

    return render_template(
        'drivers.html',
        drivers=drivers
    )
# مدیریت مسافر


@app.route('/passengers')
@login_required
@admin_required
def passengers():
    passengers = Passengers.select().join(Users)
    return render_template('passengers.html', passengers=passengers)


@app.route('/passengers/add', methods=['GET', 'POST'])
def add_passenger():

    if request.method == 'POST':

        user_id = request.form['user_id']

        if Passengers.get_or_none(
            Passengers.user == user_id
        ):
            flash(
                'This user is already a passenger',
                'danger'
            )
            return redirect(
                url_for('add_passenger')
            )

        Passengers.create(
            user_id=user_id,
            credit=request.form['credit'],
            current_lat=request.form['current_lat'],
            current_long=request.form['current_long']
        )

        flash('Passenger added', 'success')
        return redirect(url_for('passengers'))

    used_users = Passengers.select(
        Passengers.user
    )

    users = Users.select().where(
        Users.id.not_in(used_users)
    )

    return render_template(
        'passenger_form.html',
        users=users
    )


@app.route("/passengers/delete/<int:id>")
def delete_passengers(id):
    passenger = Passengers.get_or_none(Passengers.id == id)

    if passenger:
        passenger.delete_instance(recursive=True)

    return redirect("/passengers")


@app.route('/passengers/edit/<int:id>',
           methods=['GET', 'POST'])
def edit_passenger(id):

    passenger = Passengers.get_or_none(
        Passengers.id == id
    )

    if not passenger:
        return redirect('/passengers')

    if request.method == 'POST':

        passenger.credit = float(
            request.form['credit']
        )

        passenger.current_lat = float(
            request.form['current_lat']
        )

        passenger.current_long = float(
            request.form['current_long']
        )

        passenger.save()

        flash(
            'Passenger updated',
            'success'
        )

        return redirect('/passengers')

    return render_template(
        'passenger_form.html',
        passenger=passenger,
        users=Users.select()
    )


@app.route('/passengers/search')
def search_passengers():

    q = request.args.get('q', '')

    passengers = (
        Passengers
        .select()
        .join(Users)
        .where(
            (Users.fullname.contains(q)) | (Users.phone.contains(q))
        )
    )

    return render_template(
        'passengers.html',
        passengers=passengers
    )
# مدیریت ماشین


@app.route('/vehicles')
@login_required
@admin_required
def vehicles():
    vehicles = Vehicles.select().join(Drivers)
    return render_template('vehicles.html', vehicles=vehicles)


@app.route('/vehicles/add', methods=['GET', 'POST'])
def add_vehicle():

    if request.method == 'POST':

        driver_id = request.form['driver_id']

        if Vehicles.get_or_none(
            Vehicles.driver == driver_id
        ):
            flash(
                'This driver is already have a car',
                'danger'
            )
            return redirect(
                url_for('add_vehicle')
            )

        Vehicles.create(
            driver_id=driver_id,
            model=request.form['model'],
            color=request.form['color'],
            plate=request.form['plate']
        )

        flash('vehicle added', 'success')
        return redirect(url_for('vehicles'))

    used_drivers = Vehicles.select(
        Vehicles.driver
    )

    drivers = Drivers.select().where(
        Drivers.id.not_in(used_drivers)
    )

    return render_template(
        'vehicle_form.html',
        drivers=drivers
    )


@app.route("/vehicle/delete/<int:id>")
def delete_vehicles(id):
    vehicle = Vehicles.get_or_none(Vehicles.id == id)

    if vehicle:
        vehicle.delete_instance(recursive=True)

    return redirect("/vehicles")


@app.route('/vehicles/edit/<int:id>',
           methods=['GET', 'POST'])
def edit_vehicle(id):

    vehicle = Vehicles.get_or_none(
        Vehicles.id == id
    )

    if not vehicle:
        return redirect('/vehicles')

    if request.method == 'POST':

        vehicle.model = request.form['model']
        vehicle.color = request.form['color']
        vehicle.plate = request.form['plate']

        vehicle.save()

        flash(
            'Vehicle updated',
            'success'
        )

        return redirect('/vehicles')

    return render_template(
        'vehicle_form.html',
        vehicle=vehicle,
        drivers=Drivers.select()
    )


@app.route('/vehicles/search')
def search_vehicles():

    q = request.args.get('q', '')

    vehicles = (
        Vehicles
        .select()
        .join(Drivers)
        .join(Users)
        .where(
            (Users.fullname.contains(q)) | (Vehicles.plate.contains(q))
        )
    )

    return render_template(
        'vehicles.html',
        vehicles=vehicles
    )
# مدیریت پرداخت


@app.route('/payments')
@login_required
@admin_required
def payments():
    payments = Payments.select().join(Trips)
    return render_template('payments.html', payments=payments)


@app.route('/payments/add', methods=['GET', 'POST'])
def add_payment():

    if request.method == 'POST':

        trip_id = request.form['trip_id']

        if Payments.get_or_none(
            Payments.trip == trip_id
        ):
            flash(
                'This trip is already have a payment',
                'danger'
            )
            return redirect(
                url_for('add_payment')
            )

        Payments.create(
            trip_id=trip_id,
            amount=float(request.form['amount']),
            method=request.form['method'],
            status=request.form['status']
        )

        flash('payment added', 'success')
        return redirect(url_for('payments'))

    used_trips = Payments.select(
        Payments.trip
    )

    trips = Trips.select().where(
        Trips.id.not_in(used_trips)
    )

    return render_template(
        'payment_form.html',
        trips=trips
    )


@app.route("/payment/delete/<int:id>")
def delete_payments(id):
    payment = Payments.get_or_none(Payments.id == id)

    if payment:
        payment.delete_instance(recursive=True)

    return redirect("/payments")


@app.route('/payments/edit/<int:id>',
           methods=['GET', 'POST'])
def edit_payment(id):

    payment = Payments.get_or_none(
        Payments.id == id
    )

    if not payment:
        return redirect('/payments')

    if request.method == 'POST':

        payment.amount = float(request.form['amount'])
        payment.method = request.form['method']
        payment.status = request.form['status']

        payment.save()

        flash(
            'Payment updated',
            'success'
        )

        return redirect('/payments')

    return render_template(
        'payment_form.html',
        payment=payment,
        trips=Trips.select()
    )


@app.route('/payments/search')
def search_payments():

    q = request.args.get('q', '')

    payments = (
        Payments
        .select()
        .join(Trips)
        .where(
            (Payments.method.contains(q)) | (Payments.status.contains(q))
        )
    )

    return render_template(
        'payments.html',
        payments=payments
    )
# مدیریت لوکیشن راننده


@app.route('/driver_locations')
@login_required
@admin_required
def driver_locations():

    locations = (
        Driver_location
        .select()
        .join(Drivers)
    )

    return render_template(
        'driver_locations.html',
        locations=locations
    )


@app.route('/driver_locations/add',
           methods=['GET', 'POST'])
def add_driver_location():

    if request.method == 'POST':

        Driver_location.create(
            driver_id=request.form['driver_id'],
            latitude=float(
                request.form['latitude']
            ),
            longitude=float(
                request.form['longitude']
            )
        )

        flash(
            'Location added',
            'success'
        )

        return redirect(
            url_for('driver_locations')
        )

    drivers = Drivers.select()

    return render_template(
        'driver_location_form.html',
        drivers=drivers
    )


@app.route(
    '/driver_locations/delete/<int:id>'
)
def delete_driver_location(id):

    location = Driver_location.get_or_none(
        Driver_location.id == id
    )

    if location:
        location.delete_instance()

    return redirect(
        url_for('driver_locations')
    )


@app.route('/driver_locations/edit/<int:id>',
           methods=['GET', 'POST'])
def edit_driver_location(id):

    location = Driver_location.get_or_none(
        Driver_location.id == id
    )

    if not location:
        return redirect('/driver_locations')

    if request.method == 'POST':

        location.latitude = float(
            request.form['latitude']
        )

        location.longitude = float(
            request.form['longitude']
        )

        location.save()

        flash(
            'Location updated',
            'success'
        )

        return redirect('/driver_locations')

    return render_template(
        'driver_location_form.html',
        location=location,
        drivers=Drivers.select()
    )


@app.route('/driver_locations/search')
def search_driver_locations():

    q = request.args.get('q', '')

    locations = (
        Driver_location
        .select()
        .join(Drivers)
        .join(Users)
        .where(
            Users.fullname.contains(q)
        )
    )

    return render_template(
        'driver_locations.html',
        locations=locations
    )
# مدیریت نظرات


@app.route('/reviews')
@login_required
@admin_required
def reviews():
    reviews = Reviews.select()
    return render_template('reviews.html', reviews=reviews)


@app.route('/reviews/add', methods=['GET', 'POST'])
def add_review():

    if request.method == 'POST':

        trip_id = request.form['trip_id']
        if Reviews.get_or_none(
            Reviews.trip == trip_id
        ):
            flash(
                'This trip is already have a review',
                'danger'
            )
            return redirect(
                url_for('add_review')
            )

        user_id = request.form['user_id']
        if Reviews.get_or_none(
            Reviews.user == user_id
        ):
            flash(
                'This user is already have a review',
                'danger'
            )
            return redirect(
                url_for('add_review')
            )

        Reviews.create(
            trip_id=trip_id,
            user_id=user_id,
            rating=float(request.form['rating']),
            comment=request.form['comment']
        )

        flash('review added', 'success')
        return redirect(url_for('reviews'))

    used_trips = Reviews.select(
        Reviews.trip
    )

    trips = Trips.select().where(
        Trips.id.not_in(used_trips)
    )
    users = Users.select()

    return render_template(
        'review_form.html',
        trips=trips,
        users=users
    )


@app.route("/review/delete/<int:id>")
def delete_reviews(id):
    review = Reviews.get_or_none(Reviews.id == id)

    if review:
        review.delete_instance(recursive=True)

    return redirect("/reviews")


@app.route('/reviews/edit/<int:id>',
           methods=['GET', 'POST'])
def edit_review(id):

    review = Reviews.get_or_none(
        Reviews.id == id
    )

    if not review:
        return redirect('/reviews')

    if request.method == 'POST':

        review.rating = float(request.form['rating'])
        review.comment = request.form['comment']

        review.save()

        flash(
            'Review updated',
            'success'
        )

        return redirect('/reviews')

    return render_template(
        'review_form.html',
        review=review,
        users=Users.select(),
        trips=Trips.select()
    )


@app.route('/reviews/search')
def search_reviews():

    q = request.args.get('q', '')

    reviews = (
        Reviews
        .select()
        .join(Users)
        .where(
            (Users.fullname.contains(q)) | (Users.phone.contains(q))
        )
    )

    return render_template(
        'reviews.html',
        reviews=reviews
    )

# مدیریت سفرها


@app.route('/trips')
def trips():
    trips = Trips.select()
    return render_template('trips.html', trips=trips)


@app.route('/request_trip', methods=['GET', 'POST'])
def request_trip():
    if request.method == 'POST':
        passenger_id = request.form['passenger_id']
        start_lat = float(request.form['start_lat'])
        start_lon = float(request.form['start_lon'])
        passenger = Passengers.get_or_none(Passengers.id == passenger_id)
        if not passenger:
            flash('Passenger not found', 'danger')
            return redirect(url_for('request_trip'))
        # به‌روزرسانی موقعیت مسافر
        passenger.current_lat = start_lat
        passenger.current_long = start_lon
        passenger.save()
        # یافتن نزدیک‌ترین راننده فعال
        active_drivers = Drivers.select().where(Drivers.status == 'active')
        best_driver = None
        best_dist = float('inf')
        for d in active_drivers:
            last_loc = Driver_location.select().where(Driver_location.driver == d).order_by(
                Driver_location.last_update.desc()).first()
            if last_loc:
                dist = calculate_distance(
                    start_lat, start_lon, last_loc.latitude, last_loc.longitude)
                if dist < best_dist:
                    best_dist = dist
                    best_driver = d
        if not best_driver:
            flash('No active driver nearby', 'danger')
            return redirect(url_for('request_trip'))
        # ایجاد سفر
        trip = Trips.create(driver=best_driver, passenger=passenger,
                            start_lat=start_lat, start_long=start_lon,
                            status='requested')
        best_driver.status = 'busy'
        best_driver.save()
        flash(f'Trip {trip.id} created with driver {best_driver.id}', 'success')
        return redirect(url_for('trips'))
    passengers = Passengers.select()
    return render_template('request_trip.html', passengers=passengers)


@app.route('/complete_trip/<int:trip_id>', methods=['GET', 'POST'])
def complete_trip(trip_id):
    trip = Trips.get_or_none(Trips.id == trip_id)
    if not trip:
        flash('Trip not found', 'danger')
        return redirect(url_for('trips'))
    if request.method == 'POST':
        end_lat = float(request.form['end_lat'])
        end_lon = float(request.form['end_lon'])
        dist = calculate_distance(
            trip.start_lat, trip.start_long, end_lat, end_lon)
        price = calculate_price(dist)
        trip.end_lat = end_lat
        trip.end_long = end_lon
        trip.status = 'completed'
        trip.price = price
        trip.save()
        # آزاد کردن راننده
        driver = trip.driver
        driver.status = 'active'
        driver.save()
        flash(
            f'Trip {trip.id} completed. Distance: {dist:.2f} km, Price: {price} T', 'success')
        return redirect(url_for('trips'))
    return render_template('complete_trip.html', trip=trip)


@app.route('/trips/search')
def search_trips():

    q = request.args.get('q', '').lower()

    trips = []

    for trip in Trips.select():

        driver_name = trip.driver.user.fullname.lower()
        passenger_name = trip.passenger.user.fullname.lower()
        status = trip.status.lower()

        if (
            q in driver_name
            or q in passenger_name
            or q in status
            or q == str(trip.id)
        ):
            trips.append(trip)

    return render_template(
        'trips.html',
        trips=trips
    )

# درآمد


@app.route('/earnings')
@login_required
def earnings():
    total = ((Trips.select(fn.SUM(Trips.price).alias('total')
                           ).where(Trips.status == "completed")).scalar())
    driver_earnings = []
    for d in Drivers.select().join(Users):
        total_driver = ((Trips.select(fn.SUM(Trips.price).alias('total')).where(
            (Trips.status == "completed") & (Trips.driver == d))).scalar())
        if total_driver:
            driver_earnings.append(
                {"name": d.user.fullname, "amount": total_driver})
    return render_template('earnings.html', total=total, driver_earnings=driver_earnings)

# راننده های فعال


@app.route('/active_drivers')
def active_drivers():

    data = []

    for driver in Drivers.select().where(
        Drivers.status == "active"
    ):

        vehicle = Vehicles.get_or_none(
            Vehicles.driver == driver
        )

        location = (
            Driver_location
            .select()
            .where(
                Driver_location.driver == driver
            )
            .order_by(
                Driver_location.last_update.desc()
            )
            .first()
        )

        data.append({
            "driver": driver,
            "vehicle": vehicle,
            "location": location
        })

    return render_template(
        "active_drivers.html",
        data=data
    )


@app.route('/dashboard')
@login_required
@admin_required
def dashboard():

    total_users = Users.select().count()

    total_drivers = Drivers.select().count()

    total_passengers = Passengers.select().count()

    total_trips = Trips.select().count()

    completed_trips = Trips.select().where(
        Trips.status == 'completed'
    ).count()

    total_revenue = (
        Trips.select(
            fn.SUM(Trips.price)
        ).where(
            Trips.status == 'completed'
        ).scalar()
    ) or 0

    return render_template(
        'dashboard.html',
        total_users=total_users,
        total_drivers=total_drivers,
        total_passengers=total_passengers,
        total_trips=total_trips,
        completed_trips=completed_trips,
        total_revenue=total_revenue
    )



@app.route('/login',
           methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        phone = request.form['phone']

        password = request.form['password']

        user = Users.get_or_none(
            Users.phone == phone
        )

        if (
            user and
            check_password_hash(
                user.password,
                password
            )
        ):

            session['user_id'] = user.id

            session['fullname'] = user.fullname

            session['role'] = user.role

            flash(
                'Login successful',
                'success'
            )

            return redirect('/index')

        flash(
            'Invalid phone or password',
            'danger'
        )

    return render_template(
        'login.html'
    )


@app.route('/logout')
def logout():

    session.clear()

    return redirect('/login')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        fullname = request.form['fullname']
        phone = request.form['phone']
        password = generate_password_hash(request.form['password'])
        role = request.form.get('role', 'passenger')  # پیش‌فرض مسافر
        
        # بررسی یکتایی شماره
        if Users.get_or_none(Users.phone == phone):
            flash('این شماره قبلاً ثبت شده است', 'danger')
            return redirect('/signup')
        
        user = Users.create(
            fullname=fullname,
            phone=phone,
            password=password,
            role=role
        )
        
        # اگر نقش مسافر باشد، یک رکورد مسافر هم بساز
        if role == 'passenger':
            Passengers.create(user=user, credit=0)
        elif role == 'driver':
            Drivers.create(user=user, rating=0, status='inactive')
        
        flash('ثبت‌نام موفق. حالا وارد شوید', 'success')
        return redirect('/login')
    
    return render_template('signup.html')


if __name__ == '__main__':
    app.run(debug=True)

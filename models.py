from peewee import SqliteDatabase, Model, IntegerField, CharField, DateTimeField, ForeignKeyField, FloatField, Check
import datetime
from geopy.distance import geodesic
import logging
import geopy

db = SqliteDatabase('cab.db', pragmas={'foreign_keys': 1})


class BaseModel(Model):
    class Meta:
        database = db

class Users(BaseModel):

    fullname = CharField(max_length=40)

    phone = CharField(
        null=True,
        unique=True
    )

    password = CharField()

    role = CharField(
        default='user'
    )

    created_date = DateTimeField(
        default=datetime.datetime.now
    )

    class Meta:
        db_table = 'users'


class Drivers(BaseModel):
    rating = FloatField(default=0.0, constraints=[
                        Check('rating >= 0 and rating <= 5')])
    status = CharField(default='inactive')
    user = ForeignKeyField(Users, backref='drivers',
                           on_delete='CASCADE', unique=True)

    class Meta:
        db_table = 'drivers'


class Passengers(BaseModel):
    credit = FloatField(default=0.0)
    current_lat = FloatField(null=True)
    current_long = FloatField(null=True)
    user = ForeignKeyField(Users, backref='passengers',
                           on_delete='CASCADE', unique=True)

    class Meta:
        db_table = 'passengers'


class Vehicles(BaseModel):
    driver = ForeignKeyField(Drivers, backref='vehicles',
                             on_delete='CASCADE', unique=True)
    model = CharField(max_length=10, null=True)
    color = CharField(max_length=10, null=True)
    plate = CharField(max_length=8, null=True, unique=True)

    class Meta:
        db_table = 'vehicles'


class Driver_location(BaseModel):
    driver = ForeignKeyField(Drivers, backref='locations',
                             on_delete='CASCADE')
    latitude = FloatField(null=True)
    longitude = FloatField(null=True)
    last_update = DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'driver_location'


class Trips(BaseModel):
    driver = ForeignKeyField(Drivers, backref='trips',
                             on_delete='CASCADE')
    passenger = ForeignKeyField(Passengers, backref='trips',
                                on_delete='CASCADE')
    start_lat = FloatField(null=True)
    start_long = FloatField(null=True)
    end_lat = FloatField(null=True)
    end_long = FloatField(null=True)
    status = CharField(default='requested')
    price = FloatField(default=0.0)
    created_date = DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'trips'


class Payments(BaseModel):
    trip = ForeignKeyField(Trips, backref='payments',
                           on_delete='CASCADE')
    amount = FloatField(null=True)
    method = CharField(null=True)
    status = CharField(default='pending')

    class Meta:
        db_table = 'payments'


class Reviews(BaseModel):
    trip = ForeignKeyField(Trips, backref='reviews',
                           on_delete='CASCADE')
    user = ForeignKeyField(Users, backref='reviews',
                           on_delete='CASCADE')
    rating = FloatField(default=0.0, constraints=[
                        Check('rating >= 0 and rating <= 5')])
    comment = CharField(max_length=100)

    class Meta:
        db_table = 'reviews'


db.create_tables([Users, Driver_location, Drivers, Passengers,
                 Trips, Vehicles, Reviews, Payments], safe=True)

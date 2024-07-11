from flask_login import UserMixin
from datetime import datetime
from app import db

from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Table, DateTime, Boolean
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

import re

Base = declarative_base()

theatre_owners_association = Table(
    'theatre_owners',
    Base.metadata,
    Column('theatre_id', Integer, ForeignKey('theatres.id')),
    Column('user_id', Integer, ForeignKey('users.id'))
)

class User(Base, UserMixin, db.Model):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    first_name = Column(String, unique=False, nullable=True)
    last_name = Column(String, unique=False, nullable=True)
    genres = Column(String, nullable=False, default="") # "Action,Adventure,Sci-Fi"
    bio = Column(String, nullable=False, default="")
    profile_picture = Column(String, nullable=False, default="")
    email = Column(String, unique=True, nullable=False)
    roles = relationship('UserRole', back_populates='user')
    bookings = relationship('Booking', back_populates='user')
    
    is_anonymous = False
    
    def get_id(self):
        return str(self.id)
    
    def get_fav_genres(self):
        return self.genres.split(',')
    
    def set_genres(self, genres):
        self.genres = ','.join(genres)
        db.session.commit()
    
    def set_bio(self, bio):
        self.bio = bio
        db.session.commit()
        
    def set_profile_picture(self, profile_picture):
        self.profile_picture = profile_picture
        db.session.commit()
    
    def set_first_name(self, first_name):
        self.first_name = first_name
        db.session.commit()
        
    def set_last_name(self, last_name):
        self.last_name = last_name
        db.session.commit()
        
    def get_roles(self):
        return self.roles
    
    def get_highest_role(self):
        highest_role = 'customer'
        for role in self.roles:
            if role.role == 'superadmin':
                return 'superadmin'
            elif role.role == 'admin':
                highest_role = 'admin'
            elif role.role == 'staff':
                highest_role = 'staff'
        return highest_role
    
    def can_access_dashboard(self):
        return self.get_highest_role() in ['admin', 'staff', 'superadmin']

    def is_superadmin(self):
        return self.get_highest_role() == 'superadmin'
    
    # Returns a list of theatres that the user owns
    # If the user is a superadmin, return all theatres
    def get_owned_theatres(self):
        if self.is_superadmin():
            return Theatre.query.all()
        else:
            return [role.theatre for role in self.roles if role.role == 'admin']
    
    def get_staffed_theatres(self):
        return [role.theatre for role in self.roles if role.role == 'staff']
    
    def is_banned(self):
        for role in self.roles:
            if role.role == 'banned':
                return True
        return False
    
    def set_banned(self, banned):
        if banned:
            self.roles.append(UserRole(role='banned'))
        else:
            for role in self.roles:
                if role.role == 'banned':
                    self.roles.remove(role)
        db.session.commit()
        
    def delete_user(self):
        db.session.delete(self)
        db.session.commit()

class UserRole(Base, db.Model):
    __tablename__ = 'user_roles'

    id = Column(Integer, primary_key=True)
    role = Column(String, nullable=False, default="customer")  # 'customer', 'staff', 'admin', 'superadmin', 'banned'
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    # If null, the user is a superadmin
    theatre_id = Column(Integer, ForeignKey('theatres.id'), nullable=True)
    
    user = relationship('User', back_populates='roles')
    theatre = relationship('Theatre', back_populates='staff')

# ------------------ Theatre ------------------
# HOW IT WORKS:
# 1. A user creates a theatre
# 2. The user is automatically assigned the role 'admin' for the theatre
# 3. The user can then add other users as 'staff' for the theatre
# 4. The user can also add other users as 'admin' for the theatre
# 5. The user can also remove other users from the theatre
# 6. The user can also delete the theatre
# ---------------------------------------------
# HOW THE MODELS WORK:
# 1. A booking is a record of a user purchasing a ticket for a showtime 
# 2. A showtime is a record of a movie being shown at a theatre and contains the start time, end time, price, seats, etc
# 3. A movie is a record of a movie and contains the title, description, genres, etc
# 3.1 A movie can be shown at multiple, distinct theatres (not sharing the same admin)
# 3.2 A movie can have multiple showtimes at multiple theatres
# 4. A theatre owns a list of showtimes, but does not own the movies
# 4.1 A theatre can have multiple movies
# 4.2 A theatre can have multiple showtimes
# 5. A user can be an admin of multiple theatres
# 5.1 A user can be a staff of multiple theatres

class Theatre(Base, db.Model):
    __tablename__ = 'theatres'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String, nullable=True)
    description = Column(String, nullable=True)
    staff = relationship('UserRole', back_populates='theatre')
    # List of showtimes for the theatre
    showtimes = relationship('Showtime', back_populates='theatre')
    
    def set_lat(self, lat):
        self.latitude = lat
        db.session.commit()
    
    def set_long(self, long):
        self.longitude = long
        db.session.commit()
    
    def set_address(self, address):
        self.address = address
        db.session.commit()
    
    # Add movie showtime to theatre
    def add_movie(self, movie):
        self.showtimes.append(movie)
        db.session.commit()
        
    # Get all movies that are being shown at the theatre
    # Goes through all showtimes and gets all the unique movies
    def get_movies(self):
        movies = []
        for showtime in self.showtimes:
            if showtime.movie not in movies:
                movies.append(showtime.movie)
        return movies

# Movie -> Title, Description, Genres, Poster and a list of showtimes
class Movie(Base, db.Model):
    __tablename__ = 'movies'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    genres = Column(String, nullable=False) # "Action,Adventure,Sci-Fi"
    description = Column(String, nullable=False)
    showtimes = relationship('Showtime', back_populates='movie')
    image_url = Column(String, nullable=False)
    language = Column(String, nullable=False)
    movie_format = Column(String, nullable=False)
    
    # Get all theatres that are showing the movie
    # Goes through all showtimes and gets all the unique theatres
    def get_theatres(self):
        theatres = []
        for showtime in self.showtimes:
            if showtime.theatre not in theatres:
                theatres.append(showtime.theatre)
        return theatres
    
    def get_showtimes_for_theatre(self, theatre):
        return [showtime for showtime in self.showtimes if showtime.theatre == theatre]

    def get_genres_string(self):
        # Finds a space before each capital letter and inserts a space
        # e.g. "Action,Adventure,Science Fiction" instead of "Action,Adventure,ScienceFiction"
        formatted_string = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', self.genres)

        # Adds a space after each comma
        # e.g. "Action, Adventure, Science Fiction" instead of "Action,Adventure,Science Fiction"
        formatted_string = formatted_string.replace(',', ', ')
        
        return formatted_string

    def get_genres(self):
        return self.genres.split(',')


class Showtime(Base, db.Model):
    __tablename__ = 'showtimes'

    id = Column(Integer, primary_key=True)
    # The movie that is being shown
    movie_id = Column(Integer, ForeignKey('movies.id'), nullable=False)
    movie = relationship('Movie', back_populates='showtimes')
    # The theatre that is showing the movie
    theatre_id = Column(Integer, ForeignKey('theatres.id'), nullable=False)
    theatre = relationship('Theatre', back_populates='showtimes')
    # Coupons that apply to this showtime
    coupons = relationship('Coupon', back_populates='showtime')
    
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    seat_rows = Column(Integer, nullable=False)
    seat_columns = Column(Integer, nullable=False)
    seats = Column(String, nullable=False) # "0,1,2,3,4,5,6,7,8,9"
    seats_taken = Column(String, nullable=False, default="") # "0,2"
    
    bookings = relationship('Booking', back_populates='showtime')
    
    def get_seats(self):
        return self.seats.split(',')
    
    def get_taken_seats(self):
        return self.seats_taken.split(',')

    def get_available_seats(self):
        return list(set(self.get_seats()) - set(self.get_taken_seats()))
    
    def is_seat_taken(self, seat):
        return seat in self.get_taken_seats()
    
    def set_seat_taken(self, seat):
        self.seats_taken += "," + seat
        db.session.commit()
    
    def get_genres(self):
        return self.movie.genres.split(',')
    
    from datetime import datetime
    
    def get_start_time(self):
        # Convert the start_time string to a datetime object
        try:
            start_time = datetime.strptime(self.start_time, '%Y-%m-%d %H:%M:%S')

        except ValueError:
            start_time = datetime.strptime(self.start_time, '%Y-%m-%dT%H:%M')

        
        return start_time
    
    def get_end_time(self):
        # Convert the start_time string to a datetime object
        try:
            end_time = datetime.strptime(self.end_time, '%Y-%m-%dT%H:%M')
        except ValueError:
            end_time = datetime.strptime(self.end_time, '%Y-%m-%d %H:%M:%S')
        
        return end_time

    def get_duration(self):
        # Convert the start_time and end_time strings to datetime objects
        try:
            start_time = datetime.strptime(self.start_time, '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(self.end_time, '%Y-%m-%dT%H:%M')
        except ValueError:
            start_time = datetime.strptime(self.start_time, '%Y-%m-%d %H:%M:%S')
            end_time = datetime.strptime(self.end_time, '%Y-%m-%d %H:%M:%S')

        # Calculate the duration in seconds
        duration_seconds = (end_time - start_time).total_seconds()

        # Calculate hours and minutes
        hours = int(duration_seconds // 3600)
        minutes = int((duration_seconds % 3600) // 60)

        # Format the duration as HH:MM
        duration_str = f'{hours:01d}:{minutes:02d}'
        
        return duration_str



class Booking(Base, db.Model):
    __tablename__ = 'bookings'

    id = Column(Integer, primary_key=True)
    seats = Column(String, nullable=False) # "0,1,2"
    amount_paid = Column(Float, nullable=False)
    booking_fee = Column(Float, nullable=False)
    transaction_id = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship('User', back_populates='bookings')
    # The showtime of the booking
    showtime_id = Column(Integer, ForeignKey('showtimes.id'), nullable=False)
    showtime = relationship('Showtime', back_populates='bookings')
    confirmation_email = Column(String, nullable=False)
    confirmation_email_sent = Column(Boolean, nullable=False, default=False)
    confirmation_number = Column(String, nullable=True)
    coupon_id = Column(String, nullable= True)

# Many coupons can apply to a single showtime
class Coupon(Base, db.Model):
    __tablename__ = 'coupons'

    id = Column(Integer, primary_key=True)
    code = Column(String, nullable=False)
    discount = Column(Float, nullable=False)
    showtime_id = Column(Integer, ForeignKey('showtimes.id'), nullable=False)
    showtime = relationship('Showtime', back_populates='coupons')
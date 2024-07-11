from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, FloatField, SelectMultipleField, TextAreaField, IntegerField, DateTimeField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from flask import flash
from flask_login import current_user
from app.models import User

from app.models import User, Theatre, UserRole

from app.google_maps_integration import get_lat_long_for_address

class AddUserForm(FlaskForm):
    first_name = StringField('First Name')
    last_name = StringField('Last Name')
    email = StringField('Email',
                             validators=[DataRequired(), Length(min=1, max=20)])
    # Choose the role of the user, options are 'customer', 'staff', 'admin', 'superadmin' using a select field
    role = SelectField('Role', choices=[('customer', 'Customer'), ('staff', 'Staff'), ('admin', 'Admin'), ('superadmin', 'Superadmin')])
    submit = SubmitField('Add User')
    
    # Check if email already exists in the database
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            flash('Email is taken!', 'danger')
            raise ValidationError('That email is taken. Please choose a different one.')

class TheatreForm(FlaskForm):
    name = StringField('Theatre Name', validators=[DataRequired()])
    address = StringField('Address', validators=[DataRequired()])
    latitude = FloatField('Latitude', validators=[DataRequired()])
    longitude = FloatField('Longitude', validators=[DataRequired()])
    theatre_admins = SelectMultipleField('Admins', coerce=int)
    theatre_employees = SelectMultipleField('Employees', coerce=int)

    def populate_theatre_admin_choices(self):
        # Query the database for all the users with the role 'superadmin' or 'admin'
        self.theatre_admins.choices = [(user.id, user.username) for user in User.query.filter(User.roles.any(UserRole.role.in_(['superadmin', 'admin']))).all()]
        
    def populate_theatre_employee_choices(self):
        # Query the database for all the users with the role 'superadmin' or 'staff'
        self.theatre_employees.choices = [(user.id, user.username) for user in User.query.filter(User.roles.any(UserRole.role.in_(['superadmin', 'staff']))).all()]
        
    def validate_address(self, address):
        lat_long = get_lat_long_for_address(address.data)
        if not lat_long:
            raise ValidationError('Invalid address. Please enter a valid address.')
        else:
            self.latitude.data = lat_long[0]
            self.longitude.data = lat_long[1]

class NewMovieForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    genres = StringField('Genres', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    image_url = StringField('Image URL', validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired()])
    seat_rows = IntegerField('Seat Rows', validators=[DataRequired()])
    seat_columns = IntegerField('Seat Columns', validators=[DataRequired()])
    seats = StringField('Seats', validators=[DataRequired()])
    language = StringField('Language', validators=[DataRequired()])
    movie_format = StringField('Movie Format', validators=[DataRequired()])
    theatre_id = SelectField('Theatre', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Create Movie')

# Form for creating a new movie for a particular theatre
class Theatre_NewMovieForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    genres = StringField('Genres', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    image_url = StringField('Image URL', validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired()])
    seat_rows = IntegerField('Seat Rows', validators=[DataRequired()])
    seat_columns = IntegerField('Seat Columns', validators=[DataRequired()])
    seats = StringField('Seats', validators=[DataRequired()])
    language = StringField('Language', validators=[DataRequired()])
    movie_format = StringField('Movie Format', validators=[DataRequired()])
    # Only allow the user to select theatres they are an admin of
    theatre_id = SelectField('Theatre', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Create Movie')
    
    def populate_theatre_choices(self):
        # Query the database for all the theatres the user is an admin of
        self.theatre_id.choices = [(theatre.id, theatre.name) for theatre in Theatre.query.filter(Theatre.staff.any(UserRole.user_id == current_user.id)).all()]
    
    # Validate the user is an admin of the theatre they are trying to add a movie to
    def validate_theatre_id(self, theatre_id):
        theatre = Theatre.query.get(theatre_id.data)
        if not theatre:
            raise ValidationError('Invalid theatre. Please select a valid theatre.')
        elif not theatre.staff.any(UserRole.user_id == current_user.id):
            raise ValidationError('You are not an admin of this theatre. Please select a valid theatre.')

class NewBookingForm(FlaskForm):
    seats = StringField('Seats (comma-separated)', validators=[DataRequired()])
    amount_paid = FloatField('Amount Paid', validators=[DataRequired()])
    booking_fee = FloatField('Booking Fee', validators=[DataRequired()])
    transaction_id = StringField('Transaction ID', validators=[DataRequired()])
    user_id = SelectField('User', coerce=int, validators=[DataRequired()])
    movie_id = SelectField('Movie', coerce=int, validators=[DataRequired()])
    showtime_id = SelectField('Showtime', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Create Booking')
    

class NewShowtimeForm(FlaskForm):
    theatre_id = SelectField('Theatre', coerce=int, validators=[DataRequired()])
    movie_id = SelectField('Movie', coerce=int, validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired()])
    start_time = StringField('Start Time', validators=[DataRequired()])
    end_time = StringField('End Time', validators=[DataRequired()])
    seat_rows = IntegerField('Seat Rows', validators=[DataRequired()])
    seat_columns = IntegerField('Seat Columns', validators=[DataRequired()])
    submit = SubmitField('Create Showtime')

class NewCouponForm(FlaskForm):
    code = StringField('Coupon Code', validators=[DataRequired()])
    discount = FloatField('Discount', validators=[DataRequired()])
    showtime_id = SelectField('Showtimes', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Create Coupon')

class EditProfileForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    username = StringField('Username', )
    biography = TextAreaField('Biography')
    favorite_genres = SelectMultipleField('Favorite Genres', choices = [
    ('action', 'Action'),
    ('comedy', 'Comedy'),
    ('drama', 'Drama'),
    ('adventure', 'Adventure'),
    ('sci-fi', 'Science Fiction'),
    ('horror', 'Horror'),
    ('thriller', 'Thriller'),
    ('romance', 'Romance'),
    ('fantasy', 'Fantasy'),
    ('animation', 'Animation'),
    ('crime', 'Crime'),
    ('family', 'Family'),
    ('mystery', 'Mystery'),
    ('biography', 'Biography'),
    ('history', 'History'),
    ])
    submit = SubmitField('Save Changes')
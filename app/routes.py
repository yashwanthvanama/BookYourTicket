from flask import Blueprint, render_template, url_for, flash, redirect, jsonify, request
from flask_login import login_user, current_user, login_required, logout_user
from flask_mail import Mail, Message
from app.models import User, Movie, Theatre, Booking, UserRole, Showtime, Coupon
from app.forms import AddUserForm, TheatreForm, EditProfileForm, NewMovieForm, NewBookingForm, NewShowtimeForm, NewCouponForm
from app import app, db, oauth, AUTH0_DOMAIN, AUTH0_CLIENT_ID
from werkzeug.security import generate_password_hash, check_password_hash
from libgravatar import Gravatar
from urllib.parse import quote_plus, urlencode
from sqlalchemy import func
import datetime
import plotly.express as px
from collections import Counter

from app.google_maps_integration import get_lat_long_for_address, autocomplete_city, get_distance, get_formatted_address_for_lat_long

import os, stripe, json, qrcode

mail = Mail(app)

version = "N/A"

with open("version.txt") as f:
    version = f.readline()

@app.route("/")
def home():
    # Query the first 10 movies from the database
    return render_template(
        "home.html",
        user=current_user,
        movies=Movie.query.limit(10).all(),
    )


@app.route("/about")
def about():
    return render_template("about.html", user=current_user)

# ----------------------------------------------
# User Authentication routes
# ----------------------------------------------

def get_user_info_from_auth0(token):
    resp = token.get("user_info")
    return resp


@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    user_info = token["userinfo"]
    
    # Check if the user with the same email already exists in the database
    existing_user = User.query.filter_by(email=user_info["email"]).first()
    
    if existing_user:
        # If the user already exists, just log them in
        login_user(existing_user)
        flash("You're now logged in!", "info")
    else:
        # If no user with the same email exists, create a new user and add them to the database
        # Check if the user has a nickname set, if not, use the email as the username
        if "nickname" not in user_info:
            user_info["nickname"] = user_info["email"]
        
        # Check if the user has a first name set, if not, use the nickname as the first name
        if "given_name" not in user_info:
            user_info["given_name"] = user_info["nickname"]
        
        # Check if the user has a last name set, if not, set it to an empty string
        if "family_name" not in user_info:
            user_info["family_name"] = ""
        
        # Check if the user has a profile picture set, if not, use the default Gravatar image
        if "picture" not in user_info:
            user_info["picture"] = Gravatar(user_info["email"]).get_image()
        
        # Check if the nickname is already taken, if so, append a number to the end
        # e.g., John_Doe (taken) -> John_Doe1 (taken) -> John_Doe2 (taken) -> John_Doe3 (not taken)
        while User.query.filter_by(username=user_info["nickname"]).first():
            if user_info["nickname"][-1].isdigit():
                user_info["nickname"] = user_info["nickname"][:-1] + str(int(user_info["nickname"][-1]) + 1)
            else:
                user_info["nickname"] += "1"
        
        user = User(
            username=user_info["nickname"],
            first_name=user_info["given_name"],
            last_name=user_info["family_name"],
            email=user_info["email"],
            profile_picture=user_info["picture"],
        )
        
        # Check if this is the first user registered (zero rows in the users table)
        # Make this user the superuser (you can define your superuser logic here)
        if User.query.count() == 0:
            print("Creating superuser...")
            superadmin_role = UserRole(role='superadmin')
            user.roles.append(superadmin_role)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("You're now logged in!", "info")

    return redirect("/")



@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )


@app.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(
        "https://"
        + AUTH0_DOMAIN
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("home", _external=True),
                "client_id": AUTH0_CLIENT_ID,
            },
            quote_via=quote_plus,
        )
    )

# ----------------------------------------------
# User Profile routes
# ----------------------------------------------

@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", user=current_user, profile=current_user)

# Profile for a specific user, based on their ID
@app.route("/profile/<int:user_id>")
def profile_id(user_id):
    user = User.query.get_or_404(user_id)
    return render_template("profile.html", user=current_user, profile=user)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()  # Initialize the form
    if form.validate_on_submit():
        # Handle form submission and update the user's profile
        # This is where you should update the user's profile in your database
        # Redirect to the user's profile page after updating
        current_user.set_first_name(form.first_name.data)
        current_user.set_last_name(form.last_name.data)
        current_user.set_bio(form.biography.data)
        current_user.set_genres(form.favorite_genres.data)
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('profile'))
    else:
        # Populate the form with the user's current profile information
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.username.data = current_user.username
        form.biography.data = current_user.bio
        form.favorite_genres.data = current_user.genres
        
    return render_template('edit_profile.html', form=form, user=current_user)

# ----------------------------------------------
# User settings
# ----------------------------------------------
@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html", user=current_user, )

# ----------------------------------------------
# Listing all movies
# ----------------------------------------------

@app.route("/movies")
def movies():
    movies = Movie.query.all()
    return render_template("list_movies.html", user=current_user, movies=movies, )

# ----------------------------------------------
# Showtime listing for a specific movie
# ----------------------------------------------
@app.route("/movie/<int:movie_id>")
def view_movie(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    return render_template("movie.html", user=current_user, movie=movie, )

# ----------------------------------------------
# Movie listing for a specific theatre
# ----------------------------------------------
@app.route("/theatre/<int:theatre_id>")
def view_theatre(theatre_id):
    theatre = Theatre.query.get_or_404(theatre_id)
    return render_template("theatre.html", user=current_user, theatre=theatre, )

# ----------------------------------------------
# Listing all theatres
# ----------------------------------------------
@app.route("/theatres")
def theatres():
    theatres = Theatre.query.all()
    return render_template("list_theatres.html", user=current_user, theatres=theatres, )

# ----------------------------------------------
# Listing all of a user's bookings
# ----------------------------------------------
@app.route("/bookings")
@login_required
def bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).all()
    return render_template("bookings.html", user=current_user, bookings=bookings, )

@app.route('/showtime')
def showtime():
    # Get movie_id and theatre_id from query parameters
    movie_id = request.args.get('movie_id')
    theatre_id = request.args.get('theatre_id')

    # Query the database to retrieve the movie and theatre information
    movie = db.session.query(Movie).get(movie_id)
    theatre = db.session.query(Theatre).get(theatre_id)

    if movie and theatre:
        return render_template('showtimes.html', user=current_user, movie=movie, theatre=theatre)
    else:
        # Handle the case where the movie or theatre is not found
        return "Movie or theatre not found", 404


# ----------------------------------------------
# Search routes
# ----------------------------------------------
@app.route("/search")
def search():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    city = request.args.get('city')
    
    # If the lat and lon query parameters are set, use those over the city query parameter
    if lat and lon:
        city = None
        
    # If city is set, get the latitude and longitude for the city
    if city:
        lat_long = get_lat_long_for_address(city)
        if lat_long:
            lat = lat_long[0]
            lon = lat_long[1]
        else:
            flash("City not found", "danger")
            return redirect(url_for('home'))
    
    # If neither lat, lon, or city are set, default to the user's current location
    if not lat and not lon and not city:
        lat = 43.6532
        lon = -79.3832
    
    theatre_name = request.args.get('theatre_name')
    movie_name = request.args.get('movie_name')
    genres = request.args.get('genres')
    search_radius = request.args.get('search_radius')
    
    # If the search radius is not set, default to 10 kilometers
    if not search_radius:
        search_radius = 10
        
    # Get the results from the database
    movies = Movie.query.all()
    results = []
    for movie in movies:
        # Check if the movie title contains the movie name query parameter
        # If the movie name query parameter is not set, or if the movie title contains the movie name query parameter, add the movie to the results
        if not movie_name or movie_name in movie.title:
            # Check if the movie genres contain the genres query parameter
            # If the genres query parameter is not set, or if the movie genres contain the genres query parameter, add the movie to the results
            if not genres or genres in movie.get_genres():
                # Check if the movie theatre is within the search radius of the user
                # If the theatre is within the search radius, add the movie to the results
                
                # Get the theatre by getting the showtimes for a movie and getting the theatre for each showtime
                if movie.showtimes:
                    for showtime in movie.showtimes:
                        theatre = showtime.theatre
                        if theatre:
                            # Get the distance between the user and the theatre
                            distance = get_distance(float(lat), float(lon), float(theatre.latitude), float(theatre.longitude))
                            
                            # If the distance is within the search radius, add the movie to the results
                            if distance <= float(search_radius):
                                # Check if the theatre name contains the theatre name query parameter
                                # If the theatre name query parameter is not set, or if the theatre name contains the theatre name query parameter, add the movie to the results
                                if not theatre_name or theatre_name in theatre.name:
                                    # Add the movie to the results
                                    results.append(movie)
                                    break
    
    return render_template("search.html", user=current_user, lat=lat, lon=lon, movie_name=movie_name, genres=genres, search_radius=search_radius, city=city, results=results)

# ----------------------------------------------
# Search autocomplete route
# ----------------------------------------------
@app.route("/search/autocomplete/movies")
def search_autocomplete_movies():
    results = Movie.query.all()
    return jsonify([result.title for result in results])

# ----------------------------------------------
# Dashboard routes
# ----------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard/dashboard.html", user=current_user, )

# ----------------------------------------------
# System dashboard routes
# ----------------------------------------------
@app.route("/dashboard/system/add-user", methods=['GET', 'POST'])
@login_required
def add_user():
    # Check if the user is a superadmin
    # If not, redirect them to the dashboard
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    form = AddUserForm()

    if form.validate_on_submit():
        # Create a new user object based on the form data
        # Construct a username based off the first and last name
        # Make sure that the first and last name are not empty
        # and that the first letter of each is capitalized
        # and if the username is taken, add a number to the end
        # if the username is still taken, increment the number and repeat.
        # e.g., John Doe -> John_Doe (taken) -> John_Doe1 (taken) -> John_Doe2 (not taken)
        first_name = form.first_name.data.capitalize()
        last_name = form.last_name.data.capitalize()
        username = first_name + "_" + last_name
        while User.query.filter_by(username=username).first():
            if username[-1].isdigit():
                username = username[:-1] + str(int(username[-1]) + 1)
            else:
                username += "1"
                
        # Create a profile picture based on the user's email address
        # If the user has a Gravatar account, use their Gravatar image
        # Otherwise, use the default Gravatar image
        profile_picture = Gravatar(form.email.data).get_image()
        new_user = User(
            username=username,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            profile_picture=profile_picture,
        )
        
        superadmin_role = UserRole(role=form.role.data)
        new_user.roles.append(superadmin_role)

        # Add the new user to the database
        db.session.add(new_user)
        db.session.commit()

        flash('User added successfully!', 'success')
        return redirect(url_for('dashboard'))  # Redirect to your dashboard or another route

    return render_template("dashboard/system/add_user.html", user=current_user,  form=form)

@app.route("/dashboard/system/edit-user/", methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    #TODO: Implement edit user
    # Show a work in progress page
    return "Work in progress"

@app.route("/dashboard/system/view-users")
@login_required
def list_users():
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    return render_template("dashboard/system/list_users.html", user=current_user,  users=users)

@app.route('/dashboard/system/create-theatre', methods=['GET', 'POST'])
def add_theatre():
    form = TheatreForm()
    form.populate_theatre_admin_choices()
    form.populate_theatre_employee_choices()
    
    # Format the address for the theatre from the latitude and longitude
    if form.latitude.data and form.longitude.data:
        form.address.data = get_formatted_address_for_lat_long(form.latitude.data, form.longitude.data)
    
    if form.validate_on_submit():
        theatre = Theatre(
            name=form.name.data,
            latitude=form.latitude.data,
            longitude=form.longitude.data,
            address=form.address.data
        )

        # Add the Admin UserRoles to the theatre
        for user_id in form.theatre_admins.data:
            user = User.query.get(user_id)
            admin_role = UserRole(role='admin')
            admin_role.user = user
            theatre.staff.append(admin_role)       
        
        # Add the Employee UserRoles to the theatre
        for user_id in form.theatre_employees.data:
            user = User.query.get(user_id)
            employee_role = UserRole(role='staff')
            employee_role.user = user
            theatre.staff.append(employee_role)

        db.session.add(theatre)
        db.session.commit()
        
        # Handle success, e.g., redirect or display a success message
        return redirect(url_for('dashboard'))

    return render_template('dashboard/system/add_theatre.html', form=form)

@app.route("/dashboard/system/view-theatres")
@login_required
def list_theatres():
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    theatres = Theatre.query.all()
    return render_template("dashboard/system/list_theatres.html", user=current_user,  theatres=theatres)

@app.route("/dashboard/system/edit-theatre/<int:theatre_id>")
@login_required
def edit_theatre(theatre_id):
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    # Populate the theatre form with the theatre data
    theatre = Theatre.query.get_or_404(theatre_id)
    form = TheatreForm()
    form.name.data = theatre.name
    form.address.data = theatre.address
    form.latitude.data = theatre.latitude
    form.longitude.data = theatre.longitude
    
    # Use the /dashboard/system/edit-theatre.html template
    return render_template('dashboard/system/edit_theatre.html', form=form, theatre=theatre)

    
# Check to see if the user is a superadmin
# If they are, allow them to delete a theatre
# If they are not, redirect them to the list of theatres
@app.route("/dashboard/system/delete-theatre/<int:theatre_id>")
@login_required
def delete_theatre(theatre_id):
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    if current_user.is_superadmin():
        # Delete the theatre
        theatre = Theatre.query.get_or_404(theatre_id)
        db.session.delete(theatre)
        db.session.commit()
        return redirect(url_for('view_theatres'))
    else:
        return redirect(url_for('dashboard'))

# Bookings
@app.route("/dashboard/system/view-bookings")
@login_required
def list_bookings():
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    bookings = Booking.query.all()
    return render_template("dashboard/system/list_bookings.html", user=current_user,  bookings=bookings)

@app.route("/dashboard/system/edit-bookings/<int:booking_id>")
@login_required
def edit_booking(booking_id):
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    # Populate the booking form with the booking data
    booking = Booking.query.get_or_404(booking_id)
    form = NewBookingForm()
    form.seats.data = booking.seats
    form.amount_paid.data = booking.amount_paid
    form.booking_fee.data = booking.booking_fee
    form.transaction_id.data = booking.transaction_id
    form.user_id.data = booking.user_id
    form.movie_id.data = booking.movie_id
    form.showtime_id.data = booking.showtime_id
    
    # Use the /dashboard/system/edit-booking.html template
    return render_template('dashboard/system/edit_booking.html', form=form, booking=booking)

@app.route("/dashboard/system/create-booking", methods=['GET', 'POST'])
@login_required
def add_booking():
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    form = NewBookingForm()
    
    # Populate user options in the form
    form.user_id.choices = [(user.id, user.username) for user in User.query.all()]
    
    # Populate movie options in the form
    form.movie_id.choices = [(movie.id, movie.title) for movie in Movie.query.all()]
    
    # Populate showtime options in the form
    form.showtime_id.choices = [(showtime.id, showtime.start_time) for showtime in Showtime.query.all()]
    
    if form.validate_on_submit():
        # Create a new Booking instance using the form data
        booking = Booking(
            seats=form.seats.data,
            amount_paid=form.amount_paid.data,
            booking_fee=form.booking_fee.data,
            transaction_id=form.transaction_id.data,
            user_id=form.user_id.data,
            movie_id=form.movie_id.data,
            showtime_id=form.showtime_id.data,
            confirmation_email = current_user.email if not(current_user.is_anonymous) else ''
        )
        
        db.session.add(booking)
        db.session.commit()
        
        flash('Booking created successfully!', 'success')
        return redirect(url_for('list_bookings'))
    
    return render_template('/dashboard/system/add_booking.html', form=form)

@app.route("/dashboard/system/delete-booking/<int:booking_id>")
@login_required
def delete_booking(booking_id):
    # Check to see if the user is a superadmin
    # If they are, allow them to delete a booking
    # If they are not, redirect them to the list of bookings
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    # Delete the booking
    booking = Booking.query.get_or_404(booking_id)
    db.session.delete(booking)
    db.session.commit()
    return redirect(url_for('list_bookings'))

@app.route("/dashboard/system/view-booking/<int:booking_id>")
@login_required
def view_booking(booking_id):
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    booking = Booking.query.get_or_404(booking_id)
    return render_template("dashboard/system/view_booking.html", user=current_user,  booking=booking)

# Movies
@app.route("/dashboard/system/create-movie", methods=['GET', 'POST'])
@login_required
def add_movie():
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    form = NewMovieForm()
    
    # Populate theatre options in the form
    form.theatre_id.choices = [(theatre.id, theatre.name) for theatre in Theatre.query.all()]
    
    if form.validate_on_submit():
        # Create a new Movie instance using the form data
        movie = Movie(
            title=form.title.data,
            genres=form.genres.data,
            description=form.description.data,
            image_url=form.image_url.data,
            price=form.price.data,
            seat_rows=form.seat_rows.data,
            seat_columns=form.seat_columns.data,
            seats=form.seats.data,
            language=form.language.data,
            movie_format=form.movie_format.data,
            theatre_id=form.theatre_id.data
        )
        
        db.session.add(movie)
        db.session.commit()
        
        flash('Movie created successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('/dashboard/system/add_movie.html', form=form)

@app.route("/dashboard/system/view-movies")
@login_required
def list_movies():
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    movies = Movie.query.all()
    return render_template("dashboard/system/list_movies.html", user=current_user,  movies=movies)

@app.route("/dashboard/system/delete-movie/<int:movie_id>")
@login_required
def delete_movie(movie_id):
    # Check to see if the user is a superadmin
    # If they are, allow them to delete a movie
    # If they are not, redirect them to the list of movies
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    # Delete the movie
    movie = Movie.query.get_or_404(movie_id)
    db.session.delete(movie)
    db.session.commit()
    return redirect(url_for('list_movies'))

@app.route("/dashboard/system/edit-movie/<int:movie_id>")
@login_required
def edit_movie(movie_id):
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    # Populate the movie form with the movie data
    movie = Movie.query.get_or_404(movie_id)
    form = NewMovieForm()
    form.title.data = movie.title
    form.genres.data = movie.genres
    form.description.data = movie.description
    form.image_url.data = movie.image_url
    form.price.data = movie.price
    
    # Use the /dashboard/system/edit-movie.html template
    return render_template('dashboard/system/edit_movie.html', form=form, movie=movie)

@app.route("/dashboard/system/analytics")
@login_required
def system_analytics():
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    # Return a simple work in progress page
    return "Work in progress"

# Showtimes
@app.route("/dashboard/system/create-showtime", methods=['GET', 'POST'])
@login_required
def add_showtime():
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    form = NewShowtimeForm()
    
    # Populate theatre options in the form
    # Only allow the user to select theatres they are an admin of
    # Superadmins can select any theatre
    form.theatre_id.choices = [(theatre.id, theatre.name) for theatre in Theatre.query.filter(Theatre.staff.any(UserRole.user_id == current_user.id)).all()] if not current_user.is_superadmin() else [(theatre.id, theatre.name) for theatre in Theatre.query.all()]
    
    # Populate movie options in the form
    form.movie_id.choices = [(movie.id, movie.title) for movie in Movie.query.all()]
    
    if form.validate_on_submit():
        # Create a new Showtime instance using the form data
        showtime = Showtime(
            movie_id=form.movie_id.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data
        )
        
        db.session.add(showtime)
        db.session.commit()
        
        flash('Showtime created successfully!', 'success')
        return redirect(url_for('list_showtimes'))
    
    return render_template('/dashboard/system/add_showtime.html', form=form)

@app.route("/dashboard/system/view-showtimes")
@login_required
def list_showtimes():
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    showtimes = Showtime.query.all()
    return render_template("dashboard/system/list_showtimes.html", user=current_user,  showtimes=showtimes)

@app.route("/dashboard/system/edit-showtime/<int:showtime_id>", methods=['GET', 'POST'])
@login_required
def edit_showtime(showtime_id):
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    # Populate the showtime form with the showtime data
    showtime = Showtime.query.get_or_404(showtime_id)
    form = NewShowtimeForm()

    form.movie_id.choices = [(movie.id, movie.title) for movie in Movie.query.all()]    
    
    form.movie_id.data = showtime.movie_id
    form.start_time.data = showtime.start_time
    form.end_time.data = showtime.end_time
    
    # Modify the showtime to have a new movie
    if request.method == 'POST':
        showtime.movie_id = form.movie_id.data
        showtime.start_time = form.start_time.data
        showtime.end_time = form.end_time.data
        db.session.commit()
        flash('Showtime updated successfully!', 'success')
        return redirect(url_for('list_showtimes'))
    
    # Use the /dashboard/system/edit-showtime.html template
    return render_template('dashboard/system/edit_showtime.html', form=form, showtime=showtime)

@app.route("/dashboard/system/delete-showtime/<int:showtime_id>")
@login_required
def delete_showtime(showtime_id):
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    # Check to see if the user is a superadmin
    # If they are, allow them to delete a showtime
    # If they are not, redirect them to the list of showtimes
    if not current_user.is_superadmin():
        return redirect(url_for('list_showtimes'))
    # Delete the showtime
    showtime = Showtime.query.get_or_404(showtime_id)
    db.session.delete(showtime)
    db.session.commit()
    return redirect(url_for('list_showtimes'))

@app.route("/dashboard/system/view-showtime/<int:showtime_id>")
@login_required
def view_showtime(showtime_id):
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    showtime = Showtime.query.get_or_404(showtime_id)
    return render_template("dashboard/system/view_showtime.html", user=current_user,  showtime=showtime)

# Coupons
@app.route("/dashboard/system/create-coupon", methods=['GET', 'POST'])
@login_required
def add_coupon():
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    form = NewCouponForm()

    # Populate movie options in the form
    form.showtime_id.choices = [(showtime.id, showtime.movie.title) for showtime in Showtime.query.all()]

    if form.validate_on_submit():
        # Create a new Coupon instance using the form data
        coupon = Coupon(
            code=form.code.data,
            discount=form.discount.data,
            showtime_id=form.showtime_id.data
        )

        db.session.add(coupon)
        db.session.commit()

        flash('Coupon created successfully!', 'success')
        return redirect(url_for('list_coupons'))

    return render_template('dashboard/system/add_coupon.html', form=form)

@app.route("/dashboard/system/view-coupons")
@login_required
def list_coupons():
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    coupons = Coupon.query.all()
    return render_template("dashboard/system/list_coupons.html", user=current_user,  coupons=coupons)

@app.route("/dashboard/system/edit-coupon/<int:coupon_id>")
@login_required
def edit_coupon(coupon_id):
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    # Populate the coupon form with the coupon data
    coupon = Coupon.query.get_or_404(coupon_id)
    form = NewCouponForm()
    form.code.data = coupon.code
    form.discount.data = coupon.discount
    form.movie_id.data = coupon.movie_id
    
    # Use the /dashboard/system/edit-coupon.html template
    return render_template('dashboard/system/edit_coupon.html', form=form, coupon=coupon)

@app.route("/dashboard/system/delete-coupon/<int:coupon_id>")
@login_required
def delete_coupon(coupon_id):
    if not current_user.is_superadmin():
        flash("You are not a superadmin", "danger")
        return redirect(url_for('dashboard'))
    
    # Check to see if the user is a superadmin
    # If they are, allow them to delete a coupon
    # If they are not, redirect them to the list of coupons
    if not current_user.is_superadmin():
        return redirect(url_for('list_coupons'))
    # Delete the coupon
    coupon = Coupon.query.get_or_404(coupon_id)
    db.session.delete(coupon)
    db.session.commit()
    return redirect(url_for('list_coupons'))

# Delete a user role based off their user id
@app.route("/dashboard/system/delete-user-role/<int:user_id>")
@login_required
def delete_user_role(user_id):
    # Check to see if the user is a superadmin
    # If they are, allow them to delete a user role
    # If they are not, redirect them to the list of users
    if not current_user.is_superadmin():
        return redirect(url_for('list_staff_admin'))
    
    # Delete the user role
    user_role = UserRole.query.get_or_404(user_id)
    db.session.delete(user_role)
    db.session.commit()
    return redirect(url_for('list_staff_admin'))

# ----------------------------------------------
# Theatre dashboard routes
# ----------------------------------------------
@app.route("/dashboard/theatre/list-theatres")
@login_required
def list_theatres_admin():
    # Check if the user is an admin of any theatres
    # If not, redirect them to the dashboard
    if not current_user.get_owned_theatres():
        flash("You are not an admin of any theatres", "danger")
        return redirect(url_for('dashboard'))
    theatres = current_user.get_owned_theatres()
    return render_template("dashboard/theatre/list_theatres.html", user=current_user, theatres=theatres)

# Movies
@app.route("/dashboard/theatre/create-showtime", methods=['GET', 'POST'])
@login_required
def add_showtime_admin():
    # Check if the user is an admin of any theatres
    # If not, redirect them to the dashboard
    if not current_user.get_owned_theatres():
        flash("You are not an admin of any theatres", "danger")
        return redirect(url_for('dashboard'))
    
    form = NewShowtimeForm()
    
    # Populate theatre options in the form
    # Only allow the user to select theatres they are an admin of
    # Superadmins can select any theatre
    form.theatre_id.choices = [(theatre.id, theatre.name) for theatre in Theatre.query.filter(Theatre.staff.any(UserRole.user_id == current_user.id)).all()] if not current_user.is_superadmin() else [(theatre.id, theatre.name) for theatre in Theatre.query.all()]
    
    # Populate movie options in the form
    form.movie_id.choices = [(movie.id, movie.title) for movie in Movie.query.all()]

    if form.validate_on_submit():
            # Calculate the number of seats
        try:
            seats = int(form.seat_rows.data) * int(form.seat_columns.data)
        except:
            # Give a validation error if the user enters invalid seat rows or columns
            flash("Invalid seat rows or columns")
            return render_template('/dashboard/theatre/add_showtime.html', form=form)
        
        # Create a new Showtime instance using the form data
        showtime = Showtime(
            movie_id=form.movie_id.data,
            theatre_id=form.theatre_id.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            price=form.price.data,
            seat_rows=form.seat_rows.data,
            seat_columns=form.seat_columns.data,
            seats=seats,
        )
        
        db.session.add(showtime)
        db.session.commit()
        
        flash('Showtime created successfully!', 'success')
        return redirect(url_for('list_showtimes'))
    
    return render_template('/dashboard/theatre/add_showtime.html', form=form)

@app.route("/dashboard/theatre/view-showtimes")
@login_required
def list_showtimes_admin():
    # Check if the user is an admin of any theatres
    # If not, redirect them to the dashboard
    if not current_user.get_owned_theatres():
        flash("You are not an admin of any theatres", "danger")
        return redirect(url_for('dashboard'))

    showtimes = []
    for theatre in current_user.get_owned_theatres():
        showtimes.append(Showtime.query.filter_by(theatre_id=theatre.id).all())

    return render_template("dashboard/theatre/list_showtimes.html", user=current_user, showtimes=showtimes)

@app.route("/dashboard/theatre/view-movies")
@login_required
def list_movies_admin():
    # Check if the user is an admin of any theatres
    # If not, redirect them to the dashboard
    if not current_user.get_owned_theatres():
        flash("You are not an admin of any theatres", "danger")
        return redirect(url_for('dashboard'))
    
    # Return a simple work in progress page
    return "Work in progress"

@app.route("/dashboard/theatre/edit-movies")
@login_required
def edit_movie_admin():
    # Check if the user is an admin of any theatres
    # If not, redirect them to the dashboard
    if not current_user.get_owned_theatres():
        flash("You are not an admin of any theatres", "danger")
        return redirect(url_for('dashboard'))
    
    # Return a simple work in progress page
    return "Work in progress"

# Booking
@app.route("/dashboard/theatre/view-bookings")
@login_required
def list_bookings_admin():
    # Check if the user is an admin of any theatres
    # If not, redirect them to the dashboard
    if not current_user.get_owned_theatres():
        flash("You are not an admin of any theatres", "danger")
        return redirect(url_for('dashboard'))
    
    bookings = Booking.query.all()
    return render_template("dashboard/theatre/list_bookings.html", user=current_user,  bookings=bookings)

@app.route("/dashboard/theatre/edit-bookings")
@login_required
def edit_booking_admin():
    # Check if the user is an admin of any theatres
    # If not, redirect them to the dashboard
    if not current_user.get_owned_theatres():
        flash("You are not an admin of any theatres", "danger")
        return redirect(url_for('dashboard'))
    
    # Return a simple work in progress page
    return "Work in progress"

@app.route("/dashboard/theatre/create-booking")
@login_required
def create_booking_admin():
    # Check if the user is an admin of any theatres
    # If not, redirect them to the dashboard
    if not current_user.get_owned_theatres():
        flash("You are not an admin of any theatres", "danger")
        return redirect(url_for('dashboard'))
    
    # Return a simple work in progress page
    return "Work in progress"

# Staff
@app.route("/dashboard/theatre/view-staff")
@login_required
def list_staff_admin():
    # Check if the user is an admin of any theatres
    # If not, redirect them to the dashboard
    if not current_user.get_owned_theatres():
        flash("You are not an admin of any theatres", "danger")
        return redirect(url_for('dashboard'))
    
    staff = []
    for theatre in current_user.get_owned_theatres():
        staff.append(UserRole.query.filter_by(theatre_id=theatre.id).all())
    
    # Return a simple work in progress page
    return render_template("dashboard/theatre/list_staff.html", user=current_user, staff=staff)

@app.route("/dashboard/theatre/edit-staff")
@login_required
def edit_staff_admin():
    # Check if the user is an admin of any theatres
    # If not, redirect them to the dashboard
    if not current_user.get_owned_theatres():
        flash("You are not an admin of any theatres", "danger")
        return redirect(url_for('dashboard'))
    
    # Return a simple work in progress page
    return "Work in progress"

@app.route("/dashboard/theatre/create-staff")
@login_required
def add_staff_admin():
    # Check if the user is an admin of any theatres
    # If not, redirect them to the dashboard
    if not current_user.get_owned_theatres():
        flash("You are not an admin of any theatres", "danger")
        return redirect(url_for('dashboard'))
    
    # Return a simple work in progress page
    return "Work in progress"

# Theatre
@app.route("/dashboard/theatre/create-theatre")
@login_required
def create_theatre_admin():
    # Check if the user is an admin of any theatres
    # If not, redirect them to the dashboard
    if not current_user.get_owned_theatres():
        flash("You are not an admin of any theatres", "danger")
        return redirect(url_for('dashboard'))
    
    # Return a simple work in progress page
    return "Work in progress"

@app.route("/dashboard/theatre/edit-theatre")
@login_required
def edit_theatre_admin():
    # Check if the user is an admin of any theatres
    # If not, redirect them to the dashboard
    if not current_user.get_owned_theatres():
        flash("You are not an admin of any theatres", "danger")
        return redirect(url_for('dashboard'))
    
    # Return a simple work in progress page
    return "Work in progress"

@app.route("/dashboard/theatre/list-theatre")
@login_required
def list_theatre_admin():
    # Check if the user is an admin of any theatres
    # If not, redirect them to the dashboard
    if not current_user.get_owned_theatres():
        flash("You are not an admin of any theatres", "danger")
        return redirect(url_for('dashboard'))
    
    return render_template("dashboard/theatre/list_theatres.html", user=current_user, theatres=current_user.get_owned_theatres())

# Analytics
@app.route('/dashboard/system/analytics')
def theatre_analytics_admin():
    # User Statistics
    total_users = User.query.count()
    total_admins = UserRole.query.filter_by(role='admin').count()
    total_staff = UserRole.query.filter_by(role='staff').count()
    total_banned = UserRole.query.filter_by(role='banned').count()

    # Theatre Statistics
    total_theatres = Theatre.query.count()
    total_showtimes = Showtime.query.count()
    total_movies = Movie.query.count()

    # Movie Genres Statistics
    movie_genres = Movie.query.all()
    genre_counts = {}
    for movie in movie_genres:
        genres = movie.genres.split(',')
        for genre in genres:
            genre = genre.strip()
            if genre in genre_counts:
                genre_counts[genre] += 1
            else:
                genre_counts[genre] = 1

    # Showtime Statistics
    avg_showtime_price = Showtime.query.with_entities(func.avg(Showtime.price)).scalar()
    min_showtime_price = Showtime.query.with_entities(func.min(Showtime.price)).scalar()
    max_showtime_price = Showtime.query.with_entities(func.max(Showtime.price)).scalar()
    
    # Calculate the most popular movie genres
    all_genres = []
    for movie in movie_genres:
        genres = movie.genres.split(',')
        all_genres.extend(genres)

    genre_counts = Counter(all_genres)
    popular_genres = dict(genre_counts.most_common(5))
    
    genre_fig = px.bar(x=list(popular_genres.keys()), y=list(popular_genres.values()), labels={'x': 'Genres', 'y': 'Count'})
    genre_fig.update_layout(title='Most Popular Movie Genres')
    genre_chart = genre_fig.to_html(full_html=False)

    return render_template('dashboard/theatre/view_analytics.html', total_users=total_users, total_admins=total_admins,
                           total_staff=total_staff, total_banned=total_banned, total_theatres=total_theatres,
                           total_showtimes=total_showtimes, total_movies=total_movies, genre_chart=genre_chart,
                           avg_showtime_price=avg_showtime_price, min_showtime_price=min_showtime_price,
                           max_showtime_price=max_showtime_price, popular_genres=popular_genres)

# ----------------------------------------------
# Payment routes
# ----------------------------------------------
stripe.api_key = 'sk_test_51OCcWxF26FYMfquJN0RODSF7ypUmO3SInMWUx8p39l3r7EeTjhwmaxRSIKu7iMrDA1PdXkfjoQSO6efaiaB9i1S800ts6Z88oa'

@app.route('/confirmation/<bookingId>')
def confirmation(bookingId):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(request.url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    type(img)
    img_path = os.getcwd() + "/app/static/images/qrcode.png"
    img.save(img_path)
    current_booking = Booking.query.get(bookingId)
    current_show = Showtime.query.get(current_booking.showtime_id)
    current_movie = Movie.query.get(current_show.movie_id)
    current_theater = Theatre.query.get(current_show.theatre_id)
    current_coupon = Coupon.query.get(current_booking.coupon_id)
    no_of_tickets = len(current_booking.seats.split(","))
    sub_total = no_of_tickets*current_show.price
    booking_fee = sub_total*0.1
    discount = sub_total*int(current_coupon.discount)/100 if current_coupon else 0
    total_amount = sub_total + booking_fee - discount
    if not(current_booking.confirmation_email_sent):
        confirmation_url = request.url
        msg = Message('Hello', sender = 'bookyourticket.noreply@gmail.com', recipients = [current_booking.confirmation_email])
        msg.subject = "Booking Confirmation"
        msg.html = """
                     <!DOCTYPE html>
                     <html lang="en">
                     <body>
                     <p> Your booking has been successfull. You can view the details of your booking by visiting this 
                     <a href=""" + confirmation_url + """>link</a>
                     .</p>
                     </body>
                     </html>
                 """
        mail.send(msg)
        current_booking.confirmation_email_sent = True
        current_show.seats_taken = current_show.seats_taken + ',' + current_booking.seats
        try:
            current_booking.transaction_id = request.args['payment_intent']
        except:
            current_booking.transaction_id = ''
        db.session.commit()
    return render_template('confirmation.html',qr_code = url_for('static',filename = 'images/qrcode.png'),user=current_user, movie = current_movie,
                           theatre = current_theater,seats = current_booking.seats, no_of_tickets = no_of_tickets, sub_total = sub_total, 
                           booking_fee = booking_fee, total_amount = total_amount, coupon = current_coupon, discount = discount, bookingId = bookingId, showtime = current_show)

@app.route('/create-payment-intent', methods=['POST'])
def create_payment():
    try:
        data = json.loads(request.data)
        # Create a PaymentIntent with the order amount and currency
        intent = stripe.PaymentIntent.create(
            amount=100,
            currency='usd',
            # In the latest version of the API, specifying the `automatic_payment_methods` parameter is optional because Stripe enables its functionality by default.
            automatic_payment_methods={
                'enabled': True,
            },
        )
        return jsonify({
            'clientSecret': intent['client_secret']
        })
    except Exception as e:
        return jsonify(error=str(e)), 403
    

@app.route('/payment/<showTimeId>/<seats>')
def payment(showTimeId, seats, bookingId = None):
    current_show = db.get_or_404(Showtime,showTimeId)
    current_movie = db.get_or_404(Movie,current_show.movie_id)
    current_theater = db.get_or_404(Theatre,current_show.theatre_id)
    no_of_tickets = len(seats.split(","))
    sub_total = no_of_tickets*current_show.price
    booking_fee = sub_total*0.1
    total_amount = sub_total + booking_fee
    coupons = Coupon.query.filter_by(showtime_id = showTimeId).all()
    if bookingId == None:
        new_booking = Booking(
            user_id = current_user.id if not(current_user.is_anonymous) else 0,
            seats = seats,
            amount_paid = total_amount,
            booking_fee = booking_fee,
            transaction_id = '',
            showtime_id = showTimeId,
            confirmation_email = current_user.email if not(current_user.is_anonymous) else ''
        )
        try:
            db.session.add(new_booking)
            db.session.commit()
        except Exception as e:
                db.session.rollback()  # Rollback changes in case of an error
                flash(
                    "An error occurred during the booking. Please try again later.",
                    "danger",
                )
                print(e)  # Print the error for debugging
                return redirect(url_for("home"))
    else:
        new_booking = Booking.query.get(bookingId)
    
    return render_template('payment.html', user=current_user, movie = current_movie,theatre = current_theater,seats = seats, no_of_tickets = no_of_tickets,
                        sub_total = sub_total, booking_fee = booking_fee, total_amount = total_amount, con_email = new_booking.confirmation_email, 
                        coupons = coupons, booking_id = new_booking.id, showtime = current_show)

@app.route('/update-contact-email/<bookingId>/<email>', methods=['PUT'])
def updateContactEmail(bookingId,email):
    current_booking = Booking.query.get(bookingId)
    print(current_booking)
    if current_booking:
        current_booking.confirmation_email = email
        db.session.commit()
        return {'message': 'email updated successfully'}, 200
    else:
        return {'message': 'Booking or Coupon not found'}, 404
    
@app.route('/update-contact-phone/<bookingId>/<phone>', methods=['PUT'])
def updateContactPhone(bookingId,phone):
    current_booking = Booking.query.get(bookingId)
    print(current_booking)
    if current_booking:
        current_booking.confirmation_number = phone
        db.session.commit()
        return {'message': 'phone updated successfully'}, 200
    else:
        return {'message': 'Booking or Coupon not found'}, 404

@app.route('/apply-coupon/<bookingId>/<couponId>', methods=['PUT'])
def applyCoupon(bookingId, couponId):
    booking = Booking.query.get(bookingId)
    coupon = Coupon.query.get(couponId)
    current_show = Showtime.query.get(booking.showtime_id)
    no_of_tickets = len(booking.seats.split(","))
    sub_total = no_of_tickets*current_show.price
    booking_fee = sub_total*0.1
    discount = sub_total*int(coupon.discount)
    total_amount = sub_total + booking_fee - discount
    if booking and coupon:
        # Update the booking record with the coupon information
        booking.coupon_id = couponId
        booking.amount_paid = total_amount
        db.session.commit()

        return {'message': 'Coupon applied successfully'}, 200
    else:
        return {'message': 'Booking or Coupon not found'}, 404

# ----------------------------------------------
# API routes
# ----------------------------------------------

@app.route('/api/autocomplete/city/<query>')
def autocomplete_city_route(query):
    return jsonify(autocomplete_city(query))

@app.route('/api/autocomplete/movies/<query>')
def autocomplete_movies_route(query):
    results = Movie.query.filter(Movie.title.ilike(f'%{query}%')).all()
    return jsonify([result.title for result in results])

# Get a list of all of the theatres which 
@app.route('/api/autocomplete/theatres/<query>')
def autocomplete_theatres_route(query):
    results = Theatre.query.filter(Theatre.name.ilike(f'%{query}%')).all()
    return jsonify([result.name for result in results])

# Get a list of theatres within a certain radius of a latitude and longitude
@app.route('/api/autocomplete/theatres/<lat>/<long>/<radius>')
def autocomplete_theatres_radius_route(lat, long, radius):
    theatres = Theatre.query.all()
    results = []
    for theatre in theatres:
        if theatre.latitude and theatre.longitude:
            distance = get_distance(float(lat), float(long), theatre.latitude, theatre.longitude)
            if distance <= float(radius):
                results.append(theatre.name)
    return jsonify(results)

@app.route('/api/more-movies', methods=['GET'])
def get_more_movies():
    try:
        page = int(request.args.get('page', 1))
        per_page = 10  # Number of movies to return per page

        # Query the database to fetch movies for the current page
        movies_page = Movie.query.offset((page - 1) * per_page).limit(per_page).all()

        # Serialize movie objects to JSON
        serialized_movies = [
            {
                'id': movie.id,
                'title': movie.title,
                'genres': movie.genres,
                'description': movie.description,
                'image_url': movie.image_url,
                'language': movie.language,
                'movie_format': movie.movie_format
            }
            for movie in movies_page
        ]

        return jsonify(serialized_movies)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/dashboard/theatre/analytics/<theatre_id>')
def theatre_analytics(theatre_id):
    # Theatre's Revenue
    theatre_revenue = 0
    theatre = Theatre.query.get(theatre_id)
    showtimes = Showtime.query.filter_by(theatre_id = theatre_id).all()
    for showtime in showtimes:
        bookings = Booking.query.filter_by(showtime_id = showtime.id).all()
        for booking in bookings:
            theatre_revenue += abs(booking.amount_paid)
    
    # Theatre's Movie Statistics
    movie_genres = []
    for showtime in showtimes:
        movie = Movie.query.get(showtime.movie_id)
        movie_genres.append(movie.get_genres()) # Appends a list of genres for each movie

    # Calculate the most popular movie genres
    all_genres = []
    for genres in movie_genres:
        all_genres.extend(genres)
    genre_counts = Counter(all_genres)
    
    # Make charts for revenue based on the showtime date and the amount paid
    showtime_dates = []
    showtime_revenue = []
    for showtime in showtimes:
        showtime_dates.append(showtime.get_start_time().strftime("%m/%d/%Y"))
        bookings = Booking.query.filter_by(showtime_id = showtime.id).all()
        total_revenue = 0
        for booking in bookings:
            total_revenue += abs(booking.amount_paid)
        showtime_revenue.append(total_revenue)
    
    # Make a chart using plotly
    revenue_chart = px.bar(x=showtime_dates, y=showtime_revenue, labels={'x': 'Date', 'y': 'Revenue'})
    revenue_chart.update_layout(title='Revenue by Date')
    
    return render_template('dashboard/theatre/view_analytics.html', theatre=theatre, theatre_revenue=theatre_revenue, genre_counts=genre_counts, revenue_chart=revenue_chart.to_html(full_html=False))
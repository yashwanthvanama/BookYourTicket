from app import app, db
from app.models import Theatre, Movie, Showtime, Coupon

def populate_database():
    # Create a theatre
    theatre = Theatre(
        name='Example Theatre',
        latitude=37.7749,
        longitude=-122.4194,
        address='123 Main Street',
        description='A great theatre for movies'
    )
    db.session.add(theatre)

    # Create movies
    movies = [
        Movie(
            title='Example Movie1',
            genres='Action,Adventure,Sci-Fi',
            description='This is an example movie description.',
            image_url='mvi.jpeg',
            language='English',
            movie_format='HD'
        ),
        Movie(
            title='Example Movie2',
            genres='Action,Adventure,Sci-Fi',
            description='This is an example movie description.',
            image_url='mvi.jpeg',
            language='English',
            movie_format='HD'
        ),
        Movie(
            title='Example Movie3',
            genres='Action,Adventure,Sci-Fi',
            description='This is an example movie description.',
            image_url='mvi.jpeg',
            language='English',
            movie_format='HD'
        )
    ]
    db.session.add_all(movies)

    # Commit the theatre and movies to the database
    db.session.commit()

    # Create showtimes
    showtimes = [
        Showtime(
            movie_id=1,
            theatre_id=1,
            start_time='2023-01-01 10:00:00',
            end_time='2023-01-01 12:00:00',
            price=10,
            seat_rows=10,
            seat_columns=10,
            seats='0,1,2,3,4,5,6,7,8,9',
            seats_taken='0,2'
        ),
        # Create more showtimes as needed
    ]
    db.session.add_all(showtimes)

    # Commit the showtimes to the database
    db.session.commit()

    # Create coupons
    coupons = [
        Coupon(
            code='Coupon1',
            discount=10,
            showtime_id=1
        ),
        Coupon(
            code='Coupon2',
            discount=15,
            showtime_id=1
        ),
        Coupon(
            code='Coupon3',
            discount=20,
            showtime_id=1
        )
    ]
    db.session.add_all(coupons)

    # Commit the coupons to the database
    db.session.commit()

if __name__ == '__main__':
    # Populate the database
    with app.app_context():
        populate_database()

import csv
from app import app, db
from app.models import Movie

import requests

# Function to download CSV
def download_csv(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text

# Function to add movie data to the database
def add_movies_from_csv(csv_content):
    reader = csv.DictReader(csv_content.splitlines())
    counter = 0
    
    for row in reader:
        if counter == 5000:
            break
        counter += 1
        
        try:
            movie = Movie(
                title=row['Title'],
                description=row['Overview'],
                genres=row['Genre'].replace(" ", ""),  # Remove spaces in the genre string
                image_url=row['Poster_Url'],
                language=row['Original_Language'],
                movie_format="Standard"  # Assuming a default format; update as needed
            )
            db.session.add(movie)
        except Exception as e:
            print(f"Error adding movie {row['Title']}: {str(e)}")
            db.session.rollback()
        db.session.commit()

if __name__ == '__main__':
    # Download the CSV file
    csv_url = 'https://raw.githubusercontent.com/AliQX7/EDA-on-9000-Movies-Dataset/main/mymoviedb.csv'
    csv_data = download_csv(csv_url)
    with app.app_context():
        # Add the movies to the database
        add_movies_from_csv(csv_data)

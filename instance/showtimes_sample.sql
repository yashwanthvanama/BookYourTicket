INSERT INTO theatres (name, latitude, longitude, address, description)
VALUES ('Example Theatre', 37.7749, -122.4194, '123 Main Street', 'A great theatre for movies');
 
INSERT INTO movies (title, genres, description, image_url, language, movie_format)
VALUES ('Example Movie1', 'Action,Adventure,Sci-Fi', 'This is an example movie description.', 'mvi.jpeg', 'English', 'HD');
 
INSERT INTO movies (title, genres, description, image_url, language, movie_format)
VALUES ('Example Movie2', 'Action,Adventure,Sci-Fi', 'This is an example movie description.', 'mvi.jpeg', 'English', 'HD');
 
INSERT INTO movies (title, genres, description, image_url, language, movie_format)
VALUES ('Example Movie3', 'Action,Adventure,Sci-Fi', 'This is an example movie description.', 'mvi.jpeg', 'English', 'HD');
 
INSERT INTO showtimes (movie_id, theatre_id, start_time, end_time, price, seat_rows, seat_columns, seats, seats_taken)
VALUES (1, 1, '2023-01-01 10:00:00', '2023-01-01 12:00:00', 10, 10, 10, '0,1,2,3,4,5,6,7,8,9', '0,2');
 
INSERT INTO showtimes (movie_id, theatre_id, start_time, end_time, price, seat_rows, seat_columns, seats, seats_taken)
VALUES (1, 1, '2023-01-01 13:00:00', '2023-01-01 15:00:00', 10, 10, 10, '0,1,2,3,4,5,6,7,8,9', '0,2');
 
INSERT INTO showtimes (movie_id, theatre_id, start_time, end_time, price, seat_rows, seat_columns, seats, seats_taken)
VALUES (1, 1, '2023-01-01 16:00:00', '2023-01-01 18:00:00', 10, 10, 10, '0,1,2,3,4,5,6,7,8,9', '0,2');
 
INSERT INTO coupons (code, discount, showtime_id)
VALUES ('Coupon1', 10, 1);
 
INSERT INTO coupons (code, discount, showtime_id)
VALUES ('Coupon1', 15, 1);
 
INSERT INTO coupons (code, discount, showtime_id)
VALUES ('Coupon1', 20, 1);
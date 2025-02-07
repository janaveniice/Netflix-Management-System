# DBG4: Netflix Management System

Efficient data management is essential for the Netflix Management System application to be implemented successfully. Our project demonstrated the efficacy of combining relational (MariaDB) and non-relational (MongoDB) databases. MariaDB excelled in handling structured data like user profiles, show details, and watch history, while MongoDB's flexibility accommodated the dynamic nature of reviews and discussions. This hybrid approach enhanced system performance, scalability, and data management. Follow the instructions below to setup the application to run. Ensure both MYSQL and MongoDB are setup. <br>

This project was co-developed by SIT INF2003 G4.

## Ensure the required packages are installed

run `pip install -r requirements.txt`

## Create a netflix database in your MySQL

`CREATE DATABASE netflix`

## Set up your MySQL credentials in models.py and NetflixApp.py (Relational Database)

USER = 'root'<br />
PASSWORD = ''<br />
HOST = ''<br />
DBNAME = 'netflix'

`models.py` : Update lines 8-11<br />
`NetflixApp.py` : Update lines 57-60

## Ensure port is 27017 for MongoDB else update the port (Non-Relational Database)

`NetflixApp.py`: Update line 79, the port number of your Mongo Client

## To run the server

run  `python NetflixApp.py`

## Create an account or login to our test accounts

username: Alice Anderson<br />
password: alicepassword

## Install Tailwindcss (For styling)

1. Install Node.js
2. run `npm i tailwindcss`
3. run `npm run watchcss`

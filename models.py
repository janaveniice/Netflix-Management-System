from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, LargeBinary, Boolean
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()

# Change to your database credentials (password, hostname, dbname)
USER = 'root'
PASSWORD = ''
HOST = ''
DBNAME = 'netflix'

DATABASE_URL = f'mysql+pymysql://{USER}:{PASSWORD}@{HOST}/{DBNAME}'
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

class Cast(Base):
    __tablename__ = 'cast'
    id = Column(Integer, primary_key=True)
    name = Column(String)

class Country(Base):
    __tablename__ = 'countries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)

class Genre(Base):
    __tablename__ = 'genre'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)

class Image(Base):
    __tablename__ = 'images'

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, nullable=False)
    image_url = Column(String(2048), nullable=False, default='No Image')

class Movies(Base):
    __tablename__ = 'movies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    runtime = Column(Integer, nullable=False)
    rating = Column(String(255), nullable=False, default='Not Rated')
    release_year = Column(String(4), nullable=False)
    description = Column(Text, nullable=False)
    image = Column(String(2048), nullable=False, default='No Image')

class MoviesAndTV(Base):
    __tablename__ = 'movies_and_tv'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(1000), nullable=False)

class TVShow(Base):
    __tablename__ = 'tv_shows'

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    season = Column(Integer, nullable=False)
    rating = Column(String(255), nullable=False, default='Not Rated')
    release_year = Column(String(4), nullable=False)
    description = Column(Text, nullable=False)
    image = Column(String(2048), nullable=False, default='No Image')

class TVMoviesCast(Base):
    __tablename__ = 'tv_movies_cast'

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, nullable=False)
    cast_id = Column(Integer, ForeignKey('cast.id'), nullable=False)

    cast = relationship('Cast')

class TVMoviesCountry(Base):
    __tablename__ = 'tv_movies_country'

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, nullable=False)
    country_id = Column(Integer, ForeignKey('countries.id'), nullable=False)

class TVMoviesGenre(Base):
    __tablename__ = 'tv_movies_genre'

    id = Column(Integer, primary_key=True, autoincrement=True)
    show_id = Column(Integer, nullable=False)
    genre_id = Column(Integer, ForeignKey('genre.id'), nullable=False)

class User(Base):
    __tablename__ = 'users'
    
    username = Column(String(255), primary_key=True)
    email = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)
    profile_pic = Column(String(255), nullable=False)

class WatchHistory(Base):
    __tablename__ = 'WatchHistory'
    
    username = Column(String(255), ForeignKey('users.username'), primary_key=True)
    show_id = Column(Integer, primary_key=True)
    like_dislike = Column(Boolean)

class WatchList(Base):
    __tablename__ = 'WatchList'
    
    username = Column(String(255), ForeignKey('users.username'), primary_key=True)
    show_id = Column(Integer, primary_key=True)
    watched = Column(Boolean)
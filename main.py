from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import requests
import os

base_url = os.environ.get('BASE_URL')
img_base_url = os.environ.get('IMG_BASE_URL')

headers = os.environ.get('HEADERS')

# Create the app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY')
Bootstrap5(app)


##CREATE DATABASE
class Base(DeclarativeBase):
    pass


# Connection URL - SQLite, relative to Flask instance path
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///Movies2.db")

# Configure the SQLite database, relative to the app instance folder
db = SQLAlchemy(model_class=Base)

# Initialize the app with the extension
db.init_app(app)


# Define and Create the Model
class Movie(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    ranking: Mapped[int] = mapped_column(Integer, nullable=True)
    review: Mapped[str] = mapped_column(String(250), nullable=True)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)

    # useful for debugging.
    def __repr__(self):
        return f'<Movie {self.title}>'


# Create table schema in the database. Requires application context. (To Be Run only Once)
#with app.app_context():
#    db.create_all()


class RatingForm(FlaskForm):
    rating = StringField(label='Your Rating Out of 10 e.g 7.5', validators=[DataRequired()])
    ranking = StringField(label='Your Ranking', validators=[DataRequired()])
    review = StringField(label='Your Review', validators=[DataRequired()])
    submit = SubmitField(label="Done")


class AddForm(FlaskForm):
    movie_title = StringField(label='Movie Title', validators=[DataRequired()])
    submit = SubmitField(label="Add Movie")


@app.route("/")
def home():

    # ----- make list of movie ratings and sort list by highest values ----- #
    rating_list = []

    for rating in db.session.execute(db.select(Movie.rating)).scalars():
        rating_list.append(rating)
    rating_list.sort(reverse=True)

    # ----- update movie ranking in database ----- #
    rank = 1

    for value in rating_list:
        db.session.execute(db.select(Movie).where(Movie.rating == value)).scalar().ranking = rank
        db.session.commit()
        rank += 1

    # ----- select all movies by movie.ranking ----- #
    result = db.session.execute(db.select(Movie).order_by(Movie.rating))

    # ----- Use .scalars() to get the elements rather than entire rows from the database ----- #
    all_movies = result.scalars().all()
    return render_template("index.html", movies=all_movies)


@app.route("/add", methods=["GET", "POST"])
def add():
    form = AddForm()

    if form.validate_on_submit():
        movie_title = form.movie_title.data
        url = f"{base_url}?query={movie_title}"
        print(url)
        response = requests.get(url, headers=headers)
        data = response.json()["results"]
        return render_template("select.html", options=data)
    return render_template("add.html", form=form)


@app.route("/edit", methods=["GET", "POST"])
def edit():
    form = RatingForm()
    movie_id = request.args.get("id")
    movie = db.get_or_404(Movie, movie_id)

    if form.validate_on_submit():
        movie.rating = float(form.rating.data)
        movie.ranking = float(form.ranking.data)
        movie.review = form.review.data
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("edit.html", movie=movie, form=form)


@app.route("/find", methods=["GET", "POST"])
def find_movie():
    movie_id = request.args.get("id")

    if movie_id:
        movie_api_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
        response = requests.get(movie_api_url, headers=headers)
        data = response.json()

        new_movie = Movie(
            title=data["title"],
            year=data["release_date"].split("-")[0],
            img_url=f"{img_base_url}{data['poster_path']}",
            description=data["overview"]
        )

        db.session.add(new_movie)
        db.session.commit()
        return redirect(url_for("edit", id=new_movie.id))


@app.route("/delete")
def delete():
    movie_id = request.args.get("id")
    movie = db.get_or_404(Movie, movie_id)
    # DELETE RECORD by id
    db.session.delete(movie)
    db.session.commit()
    return redirect(url_for("home"))


if __name__ == '__main__':
    app.run(debug=False)

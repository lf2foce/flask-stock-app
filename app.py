from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float
from flask_marshmallow import Marshmallow
from flask_jwt_extended import JWTManager, jwt_required, create_access_token
import os
from book import books
#graph
from cachetools import cached, TTLCache
import datetime as dt
import pandas as pd
import json
cache = TTLCache(maxsize=100, ttl=60) #load large data


app = Flask(__name__)
app.config["DEBUG"] = True
app.config['JWT_SECRET_KEY'] = 'super-secret'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'planets.db')

db = SQLAlchemy(app)
ma = Marshmallow(app)
jwt = JWTManager(app)

@app.cli.command('db:create')
def db_create():
    db.create_all()
    print("DB created")

@app.cli.command('db:drop')
def db_drop():
    db.drop_all()
    print("DB dropped")

@app.cli.command('db:seed')
def db_seed():
    mercury = Planet(planet_name='Mercury',
                     planet_type='Class D',
                     home_star='Sol',
                     mass=2.258e23,
                     radius=1516,
                     distance=35.98e6)

    venus = Planet(planet_name='Venus',
                         planet_type='Class K',
                         home_star='Sol',
                         mass=4.867e24,
                         radius=3760,
                         distance=67.24e6)

    earth = Planet(planet_name='Earth',
                     planet_type='Class M',
                     home_star='Sol',
                     mass=5.972e24,
                     radius=3959,
                     distance=92.96e6)

    db.session.add(mercury)
    db.session.add(venus)
    db.session.add(earth)

    test_user = User(first_name='William',
                     last_name='Herschel',
                     email='test@test.com',
                     password='P@ssw0rd')

    db.session.add(test_user)
    db.session.commit()
    print('Database seeded!')


@app.route('/')
def index():
  return render_template("index.html", template_books=books)

@app.route("/book/<int:id>")
def book(id):
  return render_template("book.html", template_book=books[id])

@app.route('/api/v1/resources/books/all', methods=['GET'])
def api_all():
    return jsonify(books)

@app.route('/planets', methods=['GET'])
def planets():
    planets_list = Planet.query.all()
    result = planets_schema.dump(planets_list)
    return jsonify(result)

@app.route('/register', methods=['POST'])
def register():
    email = request.form['email']
    test = User.query.filter_by(email=email).first()
    if test:
        return jsonify(message='That email already exists.'), 409
    else:
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        password = request.form['password']
        user = User(first_name=first_name, last_name=last_name, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        return jsonify(message="User created successfully."), 201


@app.route('/login', methods=['POST'])
def login():
    if request.is_json:
        email = request.json['email']
        password = request.json['password']
    else:
        email = request.form['email']
        password = request.form['password']

    test = User.query.filter_by(email=email, password=password).first()
    if test:
        access_token = create_access_token(identity=email)
        return jsonify(message="Login succeeded!", access_token=access_token)
    else:
        return jsonify(message="Bad email or password"), 401


@app.route('/planet_details/<int:planet_id>', methods=["GET"])
def planet_details(planet_id: int):
    planet = Planet.query.filter_by(planet_id=planet_id).first()
    if planet:
        result = planet_schema.dump(planet)
        return jsonify(result)
    else:
        return jsonify(message="That planet does not exist"), 404


@app.route('/add_planet', methods=['POST'])
@jwt_required
def add_planet():
    planet_name = request.form['planet_name']
    test = Planet.query.filter_by(planet_name=planet_name).first()
    if test:
        return jsonify("There is already a planet by that name"), 409
    else:
        planet_type = request.form['planet_type']
        home_star = request.form['home_star']
        mass = float(request.form['mass'])
        radius = float(request.form['radius'])
        distance = float(request.form['distance'])

        new_planet = Planet(planet_name=planet_name,
                            planet_type=planet_type,
                            home_star=home_star,
                            mass=mass,
                            radius=radius,
                            distance=distance)

        db.session.add(new_planet)
        db.session.commit()
        return jsonify(message="You added a planet"), 201



# database models (should be on other file)
class User(db.Model):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True)
    password = Column(String)


class Planet(db.Model):
    __tablename__ = 'planets'
    planet_id = Column(Integer, primary_key=True)
    planet_name = Column(String)
    planet_type = Column(String)
    home_star = Column(String)
    mass = Column(Float)
    radius = Column(Float)
    distance = Column(Float)

class UserSchema(ma.Schema):
    class Meta:
        fields = ('id', 'first_name', 'last_name', 'email', 'password')


class PlanetSchema(ma.Schema):
    class Meta:
        fields = ('planet_id', 'planet_name', 'planet_type', 'home_star', 'mass', 'radius', 'distance')


user_schema = UserSchema()
users_schema = UserSchema(many=True)

planet_schema = PlanetSchema()
planets_schema = PlanetSchema(many=True)


#test plotly

@cached(cache)
def read_data():
    df = pd.read_csv('all_stocks.csv')
    return df

@app.route("/graph")
def graph():
    df = pd.read_csv('vnm.csv').drop(['Open', 'Ticker', 'AdjRatio', 'Liquidity', 'Shares'], axis=1)
    chart_data = df.to_dict(orient='records')
    chart_data = json.dumps(chart_data, indent=2)
    data = {'chart_data': chart_data}
    return render_template("graph.html", data=data)

@app.route('/stocks/<ticker>')
def stock(ticker):
    df = read_data()
    try:
        price = df.loc[ (df['Ticker'] == ticker.upper()) & (df['Date'] == '2020-10-07')].iloc[0]['Adj_Close']
        return "This is the page for the {} ticker, recent price: {}".format(ticker, price)    
    except:
        return "Not valid"

def toDate(dateString): 
    return dt.datetime.strptime(dateString, "%Y-%m-%d").date()

@app.route('/stocks/<ticker>/<string:date>')
def stock_history(ticker,date):
    df = read_data()
    try:
        price = df.loc[ (df['Ticker'] == ticker.upper()) & (df['Date'] < to_date(date)), 'Adj_Close' ]
        chart_data = price.to_dict(orient='records')
        chart_data = json.dumps(chart_data, indent=2)
        return jsonify(chart_data)
    except:
        return "Not valid"        
# Checks to see if the name of the package is the run as the main package.
if __name__ == "__main__":
    # Runs the Flask application only if the main.py file is being run.
    app.run()
    #app.run(host='10.21.184.106',port=5010)
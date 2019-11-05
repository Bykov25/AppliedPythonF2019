#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import Flask, jsonify, abort, make_response, request, g
from schema import valid
from models import Flights, Airports, Aircrafts, LogTable
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, desc, func
import logging
import time
import math


engine = create_engine('sqlite:///database.db')
Session = sessionmaker(bind=engine)

app = Flask(__name__)


logger = logging.getLogger("Logger")
logger.setLevel(logging.INFO)
file = logging.FileHandler("logger")
file.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] - %(name)s - %(message)s"))
logger.addHandler(file)


@app.before_request
def before():
    g.start = time.time()


@app.after_request
def after(response):
    duration_time = time.time() - g.start
    session = Session()
    log = LogTable(data_of_request=time.asctime(),
                   url=request.url,
                   method=request.method,
                   status_code=response.status_code,
                   duration=round(duration_time, 4),
                   json_data=request.json)
    session.add(log)
    session.commit()
    session.close()
    logger.info((f"URL: {request.url}, ") +
                (f"method: {request.method}, ") +
                (f"status code: {response.status_code}, ") +
                (f'duration: {"%.4f" % duration_time} sec'))
    return response


@app.route("/flights", methods=["GET"])
def get_flights():
    session = Session()
    flights = session.query(Flights).all()
    data = []
    for flight in flights:
        data.append(flight.get_data())
    return jsonify({"flights": data}), 200


@app.route("/flights/<int:flight_id>", methods=["GET"])
def get_flight(flight_id):
    session = Session()
    flight = session.query(Flights).filter(Flights.id == flight_id).first()
    if flight:
        return jsonify({"flight": flight.get_data()})
    else:
        abort(404)


@app.errorhandler(404)
def flight_not_found(error):
    return make_response(jsonify({"error": "flight not found"}), 404)


@app.errorhandler(400)
def valid_error(error):
    return make_response(jsonify({"error": "bad request"}), 400)


@app.route("/flights", methods=["POST"])
def add_flight():
    if not valid.validate(request.json):
        abort(400)
    session = Session()
    airport_name = request.json.get("destination_airport")
    aircraft_name = request.json.get("type_of_aircraft")
    airport = session.query(Airports).filter(Airports.airport == airport_name).first()
    if not airport:
        airport = Airports(airport=airport_name)
        session.add(airport)
        session.commit()
    aircraft = session.query(Aircrafts).filter(Aircrafts.aircraft == aircraft_name).first()
    if not aircraft:
        aircraft = Aircrafts(aircraft=aircraft_name)
        session.add(aircraft)
        session.commit()
    flight = Flights(departure_time=request.json.get("departure_time"),
                     arrival_time=request.json.get("arrival_time"),
                     travel_time=request.json.get("travel_time"),
                     destination_airport_id=airport.id,
                     type_of_aircraft_id=aircraft.id)
    session.add(flight)
    session.commit()
    return jsonify({"flight": flight.get_data()}), 201


@app.route("/flights/<int:flight_id>", methods=["DELETE"])
def delete_flight(flight_id):
    session = Session()
    flight = session.query(Flights).filter(Flights.id == flight_id).first()
    if flight:
        session.delete(flight)
        session.commit()
        return jsonify({"result": "flight deleted"}), 200
    else:
        abort(404)


@app.route("/flights/<int:flight_id>", methods=["PUT"])
def update_flight(flight_id):
    if not valid.validate(request.json):
        abort(400)
    session = Session()
    new_dep_time = request.json.get("departure_time")
    new_arr_time = request.json.get("arrival_time")
    new_travel_time = request.json.get("travel_time")
    airport_name = request.json.get("destination_airport")
    aircraft_name = request.json.get("type_of_aircraft")
    airport = session.query(Airports).filter(Airports.airport == airport_name).first()
    if not airport:
        airport = Airports(airport=airport_name)
        session.add(airport)
        session.commit()
    aircraft = session.query(Aircrafts).filter(Aircrafts.aircraft == aircraft_name).first()
    if not aircraft:
        aircraft = Aircrafts(aircraft=aircraft_name)
        session.add(aircraft)
        session.commit()
    session.query(Flights).filter(Flights.id == flight_id).\
        update({Flights.departure_time: new_dep_time,
                Flights.arrival_time: new_arr_time,
                Flights.travel_time: new_travel_time,
                Flights.destination_airport_id: airport.id,
                Flights.type_of_aircraft_id: aircraft.id})
    session.commit()
    flight = session.query(Flights).filter(Flights.id == flight_id).first()
    return jsonify({"flight": flight.get_data()}), 200


@app.route("/flights/sort_by_departure_time", methods=["GET"])
def sort_by_departure_time():
    session = Session()
    flights = session.query(Flights).order_by(Flights.departure_time).all()
    data = []
    for flight in flights:
        data.append(flight.get_data())
    return jsonify({"flihgts": data}), 200


@app.route("/flights/sort_by_arrival_time", methods=["GET"])
def sort_by_arrival_time():
    session = Session()
    flights = session.query(Flights).order_by(Flights.arrival_time).all()
    data = []
    for flight in flights:
        data.append(flight.get_data())
    return jsonify({"flights": data}), 200


@app.route("/flights/filter_airport:<string:destination_airport>", methods=["GET"])
def filter_by_airport(destination_airport):
    session = Session()
    airport = session.query(Airports).filter(Airports.airport == destination_airport).first()
    if airport:
        flights = session.query(Flights).filter(Flights.destination_airport_id == airport.id).all()
        data = []
        for flight in flights:
            data.append(flight.get_data())
        return jsonify({"flights": data}), 200
    abort(404)


@app.route("/flights/filter_aircraft:<string:type_of_aircraft>", methods=["GET"])
def filter_by_aircraft(type_of_aircraft):
    session = Session()
    aircraft = session.query(Aircrafts).filter(Aircrafts.aircraft == type_of_aircraft).first()
    if aircraft:
        flights = session.query(Flights).filter(Flights.type_of_aircraft_id == aircraft.id).all()
        data = []
        for flight in flights:
            data.append(flight.get_data())
        return jsonify({"flights": data}), 200
    abort(404)


@app.route("/flights/metric", methods=["GET"])
def metric():
    session = Session()
    methods = ["GET", "POST", "PUT", "DELETE"]
    metric = {}
    for method in methods:
        cnt = session.query(LogTable).filter(LogTable.method == method).count()
        if cnt:
            method_info = {}
            min_dur = session.query(LogTable.duration).filter(LogTable.method == method).\
                order_by(LogTable.duration).all()[0]
            max_dur = session.query(LogTable.duration).filter(LogTable.method == method).\
                order_by(desc(LogTable.duration)).all()[0]
            avg_dur = session.query(func.avg(LogTable.duration)).filter(LogTable.method == method).first()
            rank = math.floor(((90 * (cnt - 1)) / 100) + 1)
            percentile = session.query(LogTable.duration).filter(LogTable.method == method).\
                order_by(LogTable.duration).limit(rank).first()
            method_info["count_request"] = cnt
            method_info["min_duration"] = min_dur[0]
            method_info["max_duration"] = max_dur[0]
            method_info["avg_duration"] = round(avg_dur[0], 4)
            method_info["percentile"] = percentile[0]
            metric[method] = method_info
    return jsonify({"metric": metric}), 200


if __name__ == "__main__":
    app.run(debug=True)

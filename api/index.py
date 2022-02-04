import logging
import sched
import time
import requests
from flask import Flask, request
from flask_socketio import SocketIO, emit
from datetime import datetime

from api.generator import Generator
from api.reader import Reader
from api.tablebuilder import TableBuilder

# kill a list immediately instead of having to wait (not possible)
# space out events for the time taken to send a bundle to pathling
# test pathling

s = sched.scheduler(time.time)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

reader = Reader()
token = reader.request_token()
gen = Generator(token)


url_transaction = "***REMOVED***/fhir_r4"


@app.route("/resources/<resource_type>")
def find_resource(resource_type=None):
    # define url and GET resource payload
    url_get = f"***REMOVED***/fhir_r4/{resource_type}"
    url_params = request.query_string.decode("ascii")
    if len(url_params) > 1:
        url_get += "?" + url_params
    payload = reader.search_FHIR_data(url_get, token)
    error_msg = ""

    # return with error message if an error occured
    if payload["resourceType"] == "OperationOutcome":
        if payload["issue"][0]["severity"] == "error":
            return {
                "title": "",
                "url": url_get,
                "headers": [],
                "body": [],
                "error": payload["issue"][0]["diagnostics"],
            }

    # build resource table
    tb = TableBuilder(resource_type, payload)
    headers, data = tb.build_table()
    data = data.tolist()
    return {
        "title": resource_type,
        "url": url_get,
        "headers": headers,
        "body": data,
        "error": error_msg,
    }


@socketio.on("start_simulation")
def start_simulation(data):
    list(map(s.cancel, s.queue))
    print("Resource Type:", data["rtype"], "  Duration:", data["duration"])
    gen.set_rtype_and_duration(data["rtype"], data["duration"])
    events = gen.generate_events()
    send_events(events)


@socketio.on("stop_simulation")
def stop_simulation(data):
    list(map(s.cancel, s.queue))
    gen.reset_variables()


@socketio.on("change_endpoint")
def change_endpoint(data):
    global url_transaction
    url_transaction = data

    try:
        r = requests.get(url_transaction + "Patient?_count=1")
    except: 
        emit("endpointStatus", {"url": url_transaction, "status": False})
        return

    emit("endpointStatus", {"url": url_transaction, "status": True})


@socketio.on("estimate_simulation")
def estimate_simulation(data):
    gen.set_rtype_and_duration(data["rtype"], data["duration"])
    events = gen.generate_events()
    num_of_entries = get_num_of_entries(events)
    print(url_transaction)
    #TODO estimate based on number of entries
    # fix table
    # fix aehrc button switcher to showpathling text
    # fix dispatch pathling and disable it
    # use delta instead of append https://docs.delta.io/latest/delta-batch.html#append


def get_num_of_entries(events):
    count = 0
    for event in events:
        for entry in event['resource']['entry']:
            count += 1
    return count


# start timer and send events to FHIR client
def send_events(events):
    get_num_of_entries(events)
    print(url_transaction)

    emit(
        "sendEvents",
        (len(events), calcTimelineDuration(events), getUpcomingEvents(events)),
    )
    start_time = time.time()
    for i, event in enumerate(events):
        upcomingEvent = getUpcomingEvent(events[i + 3]) if i + 3 < len(events) else None

        s.enter(
            event["expectedTime"],
            1,
            send_single_event,
            argument=(event, url_transaction, start_time, i, len(events), upcomingEvent),
        )
    s.run()
    print("Simulation stopped.")
    emit("simulationEnd", True)


# function for sending single event
def send_single_event(event, url, start_time, idx, num_of_events, upcomingEvent):
    start_elapsed = time.time() - start_time
    try:
        r = requests.post(
            url,
            json=event["resource"],
            headers={"Authorization": "Bearer " + token},
            timeout=90,
        )
    except:
        has_error = True
        while has_error:
            print("An error occured, retrying...")
            r = requests.post(
                url,
                json=event["resource"],
                headers={"Authorization": "Bearer " + token},
                timeout=90,
            )
            has_error = False

    completion_elapsed = time.time() - start_time
    # add expected starting time (normed time)
    # add actual finish exection time
    print(f"{idx+1}/{num_of_events}", event["expectedTime"], start_elapsed, completion_elapsed, completion_elapsed-start_elapsed, r.status_code)
    
    emit(
        "postBundle",
        (idx + 1, event["resource"], event["timestamp"], event["expectedTime"], start_elapsed, completion_elapsed, upcomingEvent),
    )

    if r.status_code == 404 or r.status_code == 400 or r.status_code == 412:
        print(r.json(), "\n\n")


def calcTimelineDuration(events):
    last_timestamp = datetime.fromisoformat(events[-1]["timestamp"])
    first_timestamp = datetime.fromisoformat(events[0]["timestamp"])
    return abs((last_timestamp - first_timestamp).total_seconds())


def getUpcomingEvent(event):
    return {
        "id": event["resource"]["entry"][0]["resource"]["id"],
        "expectedTime": event["expectedTime"],
    }


def getUpcomingEvents(events):
    upcoming_events = events[:3] if len(events) >= 3 else events[: len(events)]
    
    return [getUpcomingEvent(event) for event in upcoming_events]


if __name__ == "__main__":
    socketio.run(app)

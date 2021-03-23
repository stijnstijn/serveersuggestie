import collections
import requests
import datetime
import sqlite3
import json
import re


def get_population():
    """
    Get current population of The Netherlands, straight from the CBS

    :return int:  Number of people estimated to be alive in NL
    """
    try:
        cbs_date = re.sub(r'_0([0-9])', '_\\1', datetime.datetime.now().strftime("%Y_%m_%d"))
        cbs_timestamp = int(datetime.datetime.now().timestamp())
        cbs_url = "https://www.cbs.nl/-/media/cbs/Infographics/Bevolkingsteller/%s.json?_=%i" % (
            cbs_date, cbs_timestamp)

        population = requests.get(cbs_url)
        return population.json()[0]

    except Exception as e:
        return None


def get_current_doses():
    """
    Get current doses from the Corona Dashboard

    :return namedtuple:  Named tuple with items 'time' and 'amount', the latter
    a dictionary with amount per vaccine brand and a 'total' key
    """
    dashboard = requests.get("https://coronadashboard.rijksoverheid.nl/")
    api_id = re.findall(r'<script src="/_next/static/([^/]+)/_ssgManifest.js" async="">', dashboard.text)[0]
    api_url = "https://coronadashboard.rijksoverheid.nl/_next/data/%s/landelijk/vaccinaties.json" % api_id
    api_response = requests.get(api_url)

    named_response = collections.namedtuple("Doses", ["time", "amount", "moving_avg"])

    try:
        api_json = api_response.json()
        latest = api_json["pageProps"]["data"]["vaccine_administered_total"]["last_value"]
        vaccines = api_json["pageProps"]["data"]["vaccine_administered_estimate"]["last_value"]
        updated_time = latest["date_of_insertion_unix"]
        vaccines = {"total": latest["estimated"], **{b: vaccines[b] for b in vaccines if "date" not in b and b not in ("total",)}}
        moving_avg = api_json["pageProps"]["data"]["vaccine_administered_rate_moving_average"]["last_value"]["doses_per_day"]

        return named_response(updated_time, vaccines, moving_avg)
    except (KeyError, ValueError):
        return None


def fetch_and_save():
    """
    Fetch latest vaccine data, save to database, return most recent data items

    :return dict:  Dictionary, with dates as keys, and saved data per date
    """
    # prepare database
    db_connection = sqlite3.connect("corona.db")
    db_connection.row_factory = sqlite3.Row
    db = db_connection.cursor()

    db.execute("CREATE TABLE IF NOT EXISTS vaccines (date, population, doses_total, doses_split)")

    today = datetime.datetime.now().strftime("%Y-%m-%d")

    # get latest data
    current = get_current_doses()
    current_population = get_population()
    current_date = datetime.datetime.fromtimestamp(current.time).strftime("%Y-%m-%d")

    latest_record = db.execute("SELECT * FROM vaccines ORDER BY date DESC LIMIT 8").fetchone()

    if not latest_record or current_date > latest_record["date"]:
        db.execute("INSERT INTO vaccines (date, population, doses_total, doses_split, moving_avg) VALUES (?, ?, ?, ?, ?)",
                   (current_date, current_population, current.amount["total"], json.dumps(current.amount), current.moving_avg))
        db_connection.commit()

    recent_data = list(db.execute("SELECT * FROM vaccines ORDER BY date DESC LIMIT 8").fetchall())
    recent_data.reverse()
    result = {}
    previous = None

    for index, row in enumerate(recent_data):
        pct = round(row["doses_total"] / row["population"] * 100, 1)
        result[row["date"]] = {
            **row,
            "pct": pct,
            "pct_increase": round(pct - result[previous]["pct"], 1) if index > 0 else None,
            "doses_increase": (row["doses_total"] - result[previous]["doses_total"]) if index > 0  else None,
            "moving_avg": row["moving_avg"],
            "diff_avg": row["doses_total"] - row["moving_avg"]
        }
        previous = row["date"]

    result = {date: result[date] for date in sorted(result, reverse=True)[:7]}
    return result

import re
import time
import math
import datetime
import irccodes
import json

def format_tweet(meta):
    buffer = ""
    if meta["user"]["verified"]:
        buffer += "✅ "

    timestamp = time.time() - datetime.datetime.strptime(meta["date"], "%Y-%m-%dT%H:%M:%S%z").timestamp()
    buffer += meta["user"]["displayname"]
    buffer = irccodes.bold(buffer)
    buffer += " (@" + meta["user"]["username"] + "): "
    buffer += re.sub(r"\s+", " ", meta["content"].replace("\n", " "))
    if meta.get("retweetedTweet"):
        buffer += " 🔁 "
        buffer += meta.get("retweetedTweet").get("url")
    elif meta.get("quotedTweet"):
        buffer += " ↩️ "
        buffer += meta.get("quotedTweet").get("url")

    buffer += " • "
    buffer += timify_long(timestamp) + " geleden"
    return buffer

def timify_long(number):
    """
    Make a number look like an indication of time

    :param number:  Number to convert. If the number is larger than the current
    UNIX timestamp, decrease by that amount
    :return str: A nice, string, for example `1 month, 3 weeks, 4 hours and 2 minutes`
    """
    number = int(number)
    have_months = False
    have_years = False
    have_weeks = False
    have_days = False
    have_hours = False

    components = []
    if number > time.time():
        number = time.time() - number

    year_length = 365.25 * 86400
    years = math.floor(number / year_length)
    if years:
        have_years = True
        components.append("%i jaar" % years)
        number -= (years * year_length)

    month_length = 30.42 * 86400
    months = math.floor(number / month_length)
    if months:
        have_months = True
        components.append("%i %s" % (months, "maanden" if months != 1 else "maand"))
        number -= (months * month_length)

    week_length = 7 * 86400
    weeks = math.floor(number / week_length)
    if weeks and not have_years:
        have_weeks = True
        components.append("%i %s" % (weeks, "weken" if weeks != 1 else "week"))
        number -= (weeks * week_length)

    day_length = 86400
    days = math.floor(number / day_length)
    if days and not have_years and not have_months:
        have_days = True
        components.append("%i %s" % (days, "dagen" if days != 1 else "dag"))
        number -= (days * day_length)

    hour_length = 3600
    hours = math.floor(number / hour_length)
    if hours and not have_years and not have_months:
        have_hours = True
        components.append("%i uur" % hours)
        number -= (hours * hour_length)

    minute_length = 60
    minutes = math.floor(number / minute_length)
    if minutes and not have_hours and not have_months:
        components.append("%i %s" % (minutes, "minuten" if minutes != 1 else "minuut"))

    if not components:
        components.append("minder dan een minuut")

    last_str = components.pop()
    time_str = ""
    if components:
        time_str = ", ".join(components)
        time_str += " en "

    return time_str + last_str

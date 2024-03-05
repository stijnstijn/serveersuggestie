# start: 8 may 2020 23:16
import subprocess
import requests
import datetime
import irccodes
import sqlite3
import locale
import shlex
import time
import json
import sys
import re
import io

from collections import OrderedDict
from csv import DictReader
from random import shuffle, choice
from helpers import timify_long, format_tweet

def sequence_to_ansi(sequence):
	blocks = ["🤪", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
	sequence = [int(round(value / max(sequence) * (len(blocks) - 2), 0)) for value in sequence]
	return "".join([blocks[int(value) + 1 if value >= 0 else 0] for value in sequence])

def day_local(date):
	date = datetime.datetime.strptime(date, "%Y-%m-%d")
	old_locale = locale.setlocale(locale.LC_ALL)
	locale.setlocale(locale.LC_ALL, "nl_NL.utf8")
	try:
		return date.strftime("%-d %b")
	finally:
		locale.setlocale(locale.LC_ALL, old_locale)

def num_local(num):
	return "{:,}".format(num).replace(",", ".")

def flt_local(num):
	return str(num).replace(".", ",")

def printp(s, *args, **kwargs):
	print(s, *args, **kwargs)

dbconn = sqlite3.connect("tnl.db")
dbconn.row_factory = sqlite3.Row
db = dbconn.cursor()

# prepare or initialise database
db.execute("CREATE TABLE IF NOT EXISTS users (user TEXT, address TEXT)")
db.execute("CREATE TABLE IF NOT EXISTS counters (counter TEXT, address TEXT, count INTEGER DEFAULT 0)")

# parse message parameters
username = sys.argv[1]
address = sys.argv[2]
message = " ".join(sys.argv[3:])

# keep track of people
exists = db.execute("SELECT * FROM users WHERE address = ?", (address,)).fetchone()
if not exists:
	db.execute("INSERT INTO users (user, address) VALUES (?, ?)", (username, address))
else:
	db.execute("UPDATE users SET user = ? WHERE address = ?", (username, address))

# increase counters on detection of a given phrase
counter_triggers = {
	"je moeder": "jemoeder",
	"jemoeder": "jemoeder",
        "jou moeder": "jemoeder",
	"jouw moeder": "jemoeder",
}
for trigger in counter_triggers:
	if trigger in message:
		trigger_id = counter_triggers[trigger]
		exists = db.execute("SELECT * FROM counters WHERE counter = ? AND address = ?", (trigger_id, address)).fetchone()
		if not exists:
			db.execute("INSERT INTO counters (counter, address, count) VALUES (?, ?, ?)", (trigger_id, address, 1))
		else:
			db.execute("UPDATE counters SET count = count + 1 WHERE address = ? AND counter = ?", (address, trigger_id))

dbconn.commit()

# some more advanced commands that can't be processed with just a markov chain
from pathlib import Path
if message.split(" ")[0] == ".glitterplaatje":
	# a glitterplaatje, for you
	bits = message.split(" ")
	urls = [line.strip() for line in open("banks/all-picmix.txt").readlines()]
	shuffle(urls)
	url = urls[0]
	printp("=msg", end="")
	if len(bits) > 1:
		name = re.sub("[^a-zA-Z0-9!@#$%&&*()_+-= ]", "", " ".join(bits[1:]))
		printp("een glitterplaatje voor %s: %s" % (name, url))
	else:
		printp("een glitterplaatje voor jou: %s" % url)

elif message == ".snoeks":
	# an emulation of Frank Snoeks' football commentary
	bank = [line.strip() for line in open("banks/snoeks.txt").readlines()]
	short = []
	long = []
	for item in bank:
		if len(item) < 20:
			short.append(item)
		else:
			long.append(item)

	teams = list(Path("teams/vrouwen").glob("*.txt"))
	teams = [Path("teams/vrouwen/Oranje.txt"), Path("teams/vrouwen/België.txt")]
	shuffle(teams)
	clubs = [line.strip() for line in open("banks/clubs.txt").readlines()]
	shuffle(clubs)
	team1 = teams.pop()
	team2 = teams.pop()
	players1 = [player.strip() for player in team1.open().readlines()]
	players2 = [player.strip() for player in team2.open().readlines()]
	team1 = team1.stem
	team2 = team2.stem
	players = players1.copy()
	players.extend(players2)
	shuffle(players)

	shuffle(long)
	shuffle(short)

	number = choice(range(0,23))
	buffer = ""
	for i in range(0, choice(range(3,12))):
		bteams = [team1, team2]
		if i % 3 == 0:
			bit = long.pop()
		else:
			bit = short.pop()

		while "[team]" in bit:
			team = bteams.pop()
			bit = bit.replace("[team]", team, 1)

		while "[club]" in bit:
			club = clubs.pop()
			bit = bit.replace("[club]", club, 1)

		while "[nummer]" in bit:
			bit = bit.replace("[nummer]", str(choice(range(0,23))), 1)

		while "[speler]" in bit:
			player = players.pop()
			bit = bit.replace("[speler]", player, 1)

		buffer += bit + "... "

	printp("=msg" + buffer)

elif message == ".usd":
	printp("=msg(%s) USD (US Dollar) // $1.00 USD // 0%% change" % username)

elif message == ".eur":
	printp("=msg(%s) EUR (Euro) // €1.00 EUR // 0%% change" % username)

elif message in (".rub", ".rbl"):
	printp("=msg(%s) RUB (Russian Ruble) // ₽1.00 RUB // 0%% change" % username)

elif message == ".scooter":
	message = "🎶 "
	phrases = Path("banks/scooter.txt").read_text().split("\n")
	shuffle(phrases)
	while len(message) < 64:
		message += phrases.pop() + " 🛵 "
	message += phrases.pop() + " 🎶"
	printp("=msg" + message)

elif message.split(" ")[0] in (".maatregel", ".complot", ".drankje", ".wietplan", ".frietplan", ".bijbaan"):
	import openai

	openai.api_key = Path("openapi.key").read_text().strip()
	command = message.split(" ")[0]

	preprompt = "" 
	if command == ".afmaken":
		prompt = " ".join(message.split(" ")[1:])
	elif command == ".bijbaan":
		preprompt = "hierna volgt een bijbaan die een beetje vreemd is, maar wel leuk, en waar je niet zo snel aan zou denken. hij is goed naast je studie te doen."
		prompt = "vandaag komt uit de bijbanencarrousel de volgende bijbaan:"
	elif command == ".maatregel":
		prompt = "vandaag komt uit de maatregelencarrousel de volgende maatregel:"
	elif command == ".wietplan":
		preprompt = "Dit is een verhaal over een wietplan in een parallel universum waarin wiet meer als LSD werkt en een magische en hallucinerende werking heeft. "
		prompt = "Het nieuwe wietplan is bekend gemaakt. Dit houdt in dat"
	elif command == ".frietplan":
		preprompt = "Er is al lang sprake van een frietplan. Een modern, vernieuwend, verrassend algemeen beleid rondom friet. Friet krijgt hierin een zeer belangrijke maatschappelijke rol. "
		prompt = "Het nieuwe frietplan is bekend gemaakt. Dit houdt in dat"
	elif command == ".drankje":
		timestamp = datetime.datetime.now().strftime("%H:%M")
		weekday = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"][datetime.datetime.today().weekday()]
		preprompt = "Voor elk moment is wel een geschikt drankje te bedenken. Geef nu een vervolg op de volgende zin bestaande uit een minder gangbaar drankje en korte uitleg van een paar woorden:  "
		prompt = "Om " + timestamp + " op " + weekday + " is het tijd voor het volgende drankje: "
	else:
		preprompt = "we hebben het hier over complotten die zeer vreemd en esoterisch zijn en weinig betrekking hebben op de actualiteit. weinig mensen kennen deze, zeker niet in de westerse wereld. ik leg uit waarom ze interessant zijn, "
		prompt = "vandaag komt uit de complotcarrousel het volgende complot:"

	response = openai.Completion.create(
		engine="gpt-3.5-turbo-instruct",
		temperature=0.75,
		prompt=preprompt + " " + prompt,
		max_tokens=125,
		top_p=1.0,
		frequency_penalty=0.5,
		presence_penalty=0.0,
		stop=["\n\n\n\n"]
	)

	response = response["choices"][0]["text"].strip().split("\n")[0]

	if not response.strip():
		printp("=msg computer says no")
	else:
		printp("=msg " + prompt.strip() + " " + response.strip())

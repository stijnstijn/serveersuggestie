# start: 8 may 2020 23:16
import requests
import datetime
import sqlite3
import locale
import json
import sys
import re
import io

import vaccins

from collections import OrderedDict
from csv import DictReader
from random import shuffle, choice

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
	print("=msg", end="")
	if len(bits) > 1:
		name = re.sub("[^a-zA-Z0-9!@#$%&&*()_+-= ]", "", " ".join(bits[1:]))
		print("een glitterplaatje voor %s: %s" % (name, url))
	else:
		print("een glitterplaatje voor jou: %s" % url)

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

	teams = list(Path("teams").glob("*.txt"))
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

	print("=msg" + buffer)

elif message == ".corona":
	# generic expression of worry/hope about how NL is coping with corona
	transport = ["trein", "tram", "trolleybus", "watertaxi", "bus", "buurtbus", "stationswachtruimte", "stadsbus"]
	time = ["in de spits", "net voor de spits", "net na de spits", "'s ochtends", "rond de middag", "rond de avond", "vroeg in de ochtend"]
	compliance = ["minder goed dan ik had gehoopt", "totaal niet", "matig", "best slecht", "zeer matig", "redelijk", "best goed", "beter dan ik had gehoopt", "echt heel goed", "uitmuntend"]
	common = ["zo komt het toch wel dichtbij ineens", "zo wordt het niks natuurlijk", "'t is wat allemaal", "ugh", "misschien wordt het nog wel wat", "misschien is er nog hoop", "goed om te zien", "geeft toch een goed gevoel"]

	transport = choice(transport)
	time = choice(time)
	compliance_index = choice(range(0,len(compliance)))
	common_index_start = int(len(common)/2) if compliance_index >= (len(compliance) / 2) else 0
	common_index_end = int(len(common)/2) if common_index_start == 0 else len(common)
	common_index = choice(range(common_index_start, common_index_end))
	compliance = compliance[compliance_index]
	common = common[common_index]

	sentence = "ik zat in de %s %s en mensen hielden zich %s aan de mondkapjesplicht, %s" % (transport, time, compliance, common)
	print("=msg" + sentence)

elif message in (".vaccins", ".vaccin"):
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


	unsorted_vaccines = vaccins.fetch_and_save()
	vaccines = OrderedDict()
	for d in sorted(unsorted_vaccines, reverse=True):
		vaccines[d] = unsorted_vaccines[d]

	latest_data = list(vaccines.values())[0]
	updated_per = day_local(list(vaccines.keys())[0])

	# if we have old data, include it too
	prevbit = ""
	if latest_data["pct_increase"]:
		prev_date = list(vaccines.keys())[1]
		prev_date_fmt = day_local(prev_date)
		prevbit = "; +%s/+%s%% sinds %s" % (num_local(latest_data["doses_increase"]), flt_local(latest_data["pct_increase"]), prev_date_fmt)


	# make a list of all brands of vaccines that have been administered
	message = []
	brandbit = ""
	brand_index = 0
	brands = [brand.replace("_", " ").title().replace("a Z", "aZ") for brand in json.loads(latest_data["doses_split"]).keys() if brand != "total"]
	for brand in brands:
		brandbit += brand
		if brand_index < len(brands) and brand_index == len(brands) - 2:
			brandbit += " en "
		elif brand_index < len(brands) - 1:
			brandbit += ", "

		brand_index += 1

	# finalise message
	message = "💉 Er zijn per %s ~%s vaccins van %s toegediend (%s%% van de bevolking bij 1 dosis pp%s). " % (updated_per,  num_local(latest_data["doses_total"]), brandbit, flt_local(latest_data["pct"]), prevbit)

	# add a slogan for a random brand
	slogans = ["%s. Wat anders?", "Ga nooit de deur uit zonder een shotje %s.", "%s geeft je vleugeltjes!", "%s. Omdat je het waard bent.", "%s - een beetje vreemd, maar wel lekker.", 
		"Je voelt je lekkerder met %s.", "%s, da's pas lekker!", "Heerlijk, helder, %s.", "Je hebt vaccins, en je hebt %s.", "%s. Mannen weten waarom.", "Spuit %s, voel je zeker!", 
		"Een beetje van jezelf, een beetje van %s.", "%s. Er is geen betere.", "%s - het vaccin van wakker Nederland.", "%s. Misschien wel het beste vaccin van Nederland.", 
		"Onbegrijpelijk, %s. Onbegrijpelijk lekker!", "%s - steeds verrassend, altijd voordelig!", "%s - alleen als 'ie ijs- en ijskoud is!", "%s: ik ben toch niet gek?!"]

	# done
	message += choice(slogans) % choice(list(brands))
	print("=msg" + message)

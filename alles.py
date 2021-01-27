# start: 8 may 2020 23:16
import requests
import datetime
import sqlite3
import locale
import sys
import re
import io

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
	# current Dutch vaccination progress
	vaccines = 0
	brands = set()
	max_date = "0000-00-00"
	recency = 0
	per_date = {}

	# get historical vaccine data from this random dude
	# mostly useful for historical data, which coronadashboard doesn't have
	raw_csv = requests.get("https://raw.githubusercontent.com/YorickBleijenberg/COVID_data_RIVM_Netherlands/master/vaccination/people.vaccinated.csv")
	stream = io.StringIO(raw_csv.text)
	reader = DictReader(stream)

	for row in reader:
		row_brands = row["vaccine"].split(",")
		for row_brand in row_brands:
			brands.add(row_brand.strip())
		if row["date"] not in per_date:
			per_date[row["date"]] = 0
		per_date[row["date"]] = max(per_date[row["date"]], int(row["total_vaccinations"]))
		max_date = max(max_date, row["date"])
		recency = max(recency, datetime.datetime.strptime(row["date"], "%Y-%m-%d").timestamp())
		vaccines = max(vaccines, int(row["total_vaccinations"]))

	del per_date[max_date]

	# get most recent data from coronadashboard, which may be more up to date than the csv
	dashboard = requests.get("https://coronadashboard.rijksoverheid.nl/")
	api_id = re.findall(r'<script src="/_next/static/([^/]+)/_ssgManifest.js" async="">', dashboard.text)[0]
	api_response = requests.get("https://coronadashboard.rijksoverheid.nl/_next/data/%s/landelijk/vaccinaties.json" % api_id)
	try:
		api_json = api_response.json()
		vaccines = max(vaccines, int(api_json["pageProps"]["text"]["vaccinaties"]["data"]["sidebar"]["last_value"]["total_vaccinated"]))
		recency = max(recency, int(api_json["pageProps"]["text"]["vaccinaties"]["data"]["sidebar"]["last_value"]["date_unix"]))
	except (KeyError, ValueError):
		pass

	# get population number for netherlands from CBS to calculate how much of 
	# the population has been vaccinated
	try:
		cbs_date = re.sub(r'_0([0-9])', '_\\1', datetime.datetime.now().strftime("%Y_%m_%d"))
		cbs_timestamp = int(datetime.datetime.now().timestamp())
		cbs_url = "https://www.cbs.nl/-/media/cbs/Infographics/Bevolkingsteller/%s.json?_=%i" % (cbs_date, cbs_timestamp)
		population = requests.get(cbs_url)
		population = population.json()[0]
		pct = float(vaccines) / float(population)
		populationbit = "; %s%% van de bevolking" % str(round(pct * 100, 2)).replace(".", ",")
		if per_date:
			prev_value = per_date[sorted(per_date.keys(), reverse=True)[0]]
			prev_pct = float(prev_value) / float(population)
			pct_increase = pct - prev_pct
			populationbit += ", +%s%%" % str(round(pct_increase * 100, 2)).replace(".", ",")
	except Exception as e:
		populationbit = ""


	# format most recent date for which we have data
	old_locale = locale.setlocale(locale.LC_ALL)
	try:
		locale.setlocale(locale.LC_ALL, "nl_NL.utf8")
		updated_per = datetime.datetime.fromtimestamp(recency).strftime("%d %b")
	finally:
		locale.setlocale(locale.LC_ALL, old_locale)

	# if we have data about a previous date, add the change since then
	prevbit = ""
	if per_date:
		prev_date = sorted(per_date.keys(), reverse=True)[0]
		locale.setlocale(locale.LC_ALL, "nl_NL.utf8")
		try:
			prev_date_fmt = re.sub(r'0([0-9])', '\\1', datetime.datetime.strptime(prev_date, "%Y-%m-%d").strftime("%d %b"))
		finally:
			locale.setlocale(locale.LC_ALL, old_locale)
		prev_value = per_date[prev_date]
		difference = "{:,}".format(vaccines - prev_value).replace(",", ".")
		prevbit = " (+%s sinds %s%s)" % (difference, prev_date_fmt, populationbit)


	# make a list of all brands of vaccines that have been administered
	message = []
	brandbit = ""
	brand_index = 0
	for brand in brands:
		brandbit += brand
		if brand_index < len(brands) and brand_index == len(brands) - 2:
			brandbit += " en "
		elif brand_index < len(brands) - 1:
			brandbit += ", "

		brand_index += 1

	# finalise message
	vaccines = "{:,}".format(vaccines).replace(",", ".")
	message = "Er zijn per %s %s vaccins van %s toegediend%s. " % (updated_per, vaccines, brandbit, prevbit)

	# add a slogan for a random brand
	slogans = ["%s. Wat anders?", "Ga nooit de deur uit zonder een shotje %s.", "%s geeft je vleugeltjes!", "%s. Omdat je het waard bent.", "%s - een beetje vreemd, maar wel lekker.", 
		"Je voelt je lekkerder met %s.", "%s, da's pas lekker!", "Heerlijk, helder, %s.", "Je hebt vaccins, en je hebt %s.", "%s. Mannen weten waarom.", "Spuit %s, voel je zeker!", 
		"Een beetje van jezelf, een beetje van %s.", "%s. Er is geen betere.", "%s - het vaccin van wakker Nederland.", "%s. Misschien wel het beste vaccin van Nederland.", 
		"Onbegrijpelijk, %s. Onbegrijpelijk lekker!", "%s - steeds verrassend, altijd voordelig!", "%s - alleen als 'ie ijs- en ijskoud is!", "%s: ik ben toch niet gek?!"]

	# done
	message += choice(slogans) % choice(list(brands))
	print("=msg" + message)

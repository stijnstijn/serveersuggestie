"""
    Copyright (c) 2020 - 2021 Stijn and contributers

    Main repository: https://github.com/stijnstijn/serveersuggestie

    This file is part of serveersuggestie.

    serveersuggestie is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    serveersuggestie is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with serveersuggestie.  If not, see <https://www.gnu.org/licenses/>.
"""
import random
import markovify
import sys
import re

from pathlib import Path

def generate(corpus, pattern=None, default="", max_attempts=50):
	#default 2
	sizes = {
		"asmr.txt": 1,
		"allerhande.txt": 2,
		"bijbel.txt": 3,
		"bijbelstory.txt": 2,
		"allerburu.txt": 1,
		"viva.txt": 2
	}

	suffixes = {
		"bijbel.txt": ["", "Amen."],
		"bijbelburu.txt": ["", "Amen."]
	}

	# default 25
	min_lengths = {
		"allerhande.txt": 65,
		"asmr.txt": 90,
		"vivaaa.txt": 65,
	}

	corpus = re.sub(r"[^0-9a-zA-Z.]*", "", corpus).split(".")[0] + ".txt"
	source = Path(__file__).resolve().parent.joinpath("corpora").joinpath(corpus)
	if not source.exists() or not source.is_file():
		return None

	with source.open(encoding="utf-8") as f:
		text = f.read()

	text_model = markovify.NewlineText(text, state_size=sizes.get(corpus, 2))
	min_for_corpus = min_lengths.get(corpus, 25)

	sentence = None
	retries = 0
	while not sentence:
		sentence = text_model.make_short_sentence(max_chars=500, min_chars=min_for_corpus)
		if pattern and not re.match(pattern, sentence, flags=re.IGNORECASE):
			retries += 1
			if retries < max_attempts:
				sentence = None
				continue
			else:
				return default

	if sentence and corpus in suffixes:
                if sentence[-1] not in [".", "?", "!"]:
                        sentence += random.choice([".", "!"]) + " " + random.choice(suffixes.get(corpus))

	return sentence

if __name__ == "__main__":
	sentence = generate(sys.argv[1])
	if not sentence:
		exit(0)

	print(sentence.strip())

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

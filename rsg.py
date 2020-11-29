from pathlib import Path
from random import choice
from markov import generate

import sys
import re

pattern = re.sub(r"[^ \U0001F300-\U0001F64F\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BFa-zA-Z0-9|\[\]()!@=/?*#$%\\^_&*.,;':\"-+<>-]", "", " ".join(Path("rsg.temp").read_text().strip().split(" ")[1:]), flags=re.UNICODE)
#pattern = " ".join(Path("rsg.temp").read_text().strip().split(" ")[1:])
if pattern != "zelfde":
    Path("rsg.pattern").write_text(pattern)

pattern = Path("rsg.pattern").read_text()

channel = sys.argv[1] if len(sys.argv) > 1 else ""
result = []

userfile = Path("rsg.nicks")
if userfile.exists():
    with userfile.open() as userstream:
        users = [user.strip() for user in userstream.read().split("\n")]
else:
    users = ["gonzobot"]

def get_word_from_bank(file=None, pattern=None, default="", bank=None):
    if bank:
        options = bank
    elif Path(file).exists():
        options = [option.strip() for option in Path(file).open().readlines()]
    else:
        return default

    if pattern:
        options = [option for option in options if re.match(pattern, option, flags=re.IGNORECASE)]
        return choice(options) if options else default
    else:
        return choice(options)


def parse(buffer):
    global channel, users

    replacement = ""
    capitalise = False
    lowercase = False
    all_capitals = False
    if not buffer:
        return ""

    regex = re.search(r"==(.+)$", buffer)
    pattern = None
    if regex:
       buffer = buffer[:len(buffer)-len(regex.group(0))]
       pattern = re.escape(regex.group(1)).replace("\\*", "*").replace("\\?", "?").replace("?", ".").replace("*", ".*")

    if buffer[-1] == "^":
        capitalise = True
        buffer = buffer[:-1]
    elif buffer[-1] == "_":
        lowercase = True
        buffer = buffer[:-1]

    if buffer == buffer.upper() and buffer.upper() != buffer.lower():
        all_capitals = True

    buffer = buffer.lower()
    if "|" in buffer:
        buffer = choice(buffer.split("|"))

    for character in buffer:
        if character == "u":
            replacement += get_word_from_bank(bank=users, pattern=pattern)
        elif character in ("🚖", "🚗", "🚘", "🚙"):
            replacement += get_word_from_bank(file="banks/automerken.txt", pattern=pattern)
        elif character in ("🚲"):
            replacement += get_word_from_bank(file="banks/fietsmerken.txt", pattern=pattern)
        elif character in ("🚂", "🚄", "🚅", "🚞", "🚆", "🚇"):
            replacement += get_word_from_bank(file="banks/treinen.txt", pattern=pattern)
        elif character in ("✈️"):
            replacement += get_word_from_bank(file="banks/vliegtuigen.txt", pattern=pattern)
        elif character in ("🪐"):
            replacement += get_word_from_bank(file="banks/planeten.txt", pattern=pattern)
        elif character == "v":
            replacement += get_word_from_bank(bank=["a","e","i","o","u","y"], pattern=pattern)
        elif character == "c":
            replacement += get_word_from_bank(bank=["b","c","d","f","g","h","j","k","l","m","n","p","q","r","s","t","v","w","x","z"], pattern=pattern)
        elif character == "n":
            noun = get_word_from_bank(file="banks/zelfstnw.txt", pattern=pattern).split("|")
            if len(noun) == 1:
                 replacement += noun[0]
            elif len(noun) == 2:
                 replacement += noun[0]
            else:
                 replacement += noun[0] + noun[1]
        elif character == "e":
            replacement += get_word_from_bank(file="banks/bedrijven.txt", pattern=pattern)
        elif character == "g":
            replacement += get_word_from_bank(file="banks/genres.txt", pattern=pattern)
        elif character == "a":
            replacement += get_word_from_bank(file="banks/bijvnw.txt", pattern=pattern)
        elif character == "s":
            replacement += get_word_from_bank(file="banks/scheldwoorden.txt", pattern=pattern)
        elif character == "p":
            replacement += get_word_from_bank(file="banks/beroemdheden.txt", pattern=pattern)
        elif character in ("l", "🏙", "🌃", "🌆", "🌇"):
            replacement += get_word_from_bank(file="banks/plaatsen.txt", pattern=pattern)
        elif character in ("🏳", "🌍", "🌎", "🌏", "🗺"):
            replacement += get_word_from_bank(file="banks/landen.txt", pattern=pattern)
        elif character == "#":
            nmin = None
            if len(buffer) > 1 and buffer[1] == ":":
                bits = buffer.split(":")[1].split("-")
                if len(bits) == 2:
                    try:
                        nmin = int(bits[0])
                        nmax = int(bits[1])
                        if nmin >= nmax:
                            raise ValueError()
                    except ValueError:
                        nmin = 0
                        nmax = 100
            if not nmin:
                nmin = 0
                nmax = 100
            replacement += str(choice(range(nmin, nmax)))
            break
        elif character == "m" and buffer[1] == ":":
            corpus = buffer.split(":")[1] + ".txt"
            sentence = generate(corpus, pattern=pattern, max_attempts=250)
            if sentence is not None:
                 replacement = sentence
                 break
            else:
                 replacement += character
        else:
            replacement += character

    if lowercase:
        replacement = replacement.lower()

    if capitalise:
        replacement = replacement.title()

    if all_capitals:
        replacement = replacement.upper()

    return replacement

cursor = 0
while True:
    if cursor > len(pattern) - 1:
        break

    character = pattern[cursor]

    if character == "[":
        buffer = ""
        buffer_closed = False
        buffer_cursor = cursor + 1

        while buffer_cursor < len(pattern):
            buffer_character = pattern[buffer_cursor]

            if buffer_character == "]":
                buffer_closed = True
                break

            buffer += buffer_character
            buffer_cursor += 1

        if not buffer_closed:
            print("Unclosed parentheses")
            exit()

        cursor += len(buffer) + 1
        replacement = parse(buffer)
        result.append(replacement)

    else:
        result.append(character)

    cursor += 1

print((" " + "".join(result))[0:500])
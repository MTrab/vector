import json
import os

cwd = os.getcwd()
infile = input("Enter input filename: ")

infile = os.path.join(cwd, infile)

try:
    with open(infile, "r", encoding="UTF-8") as file:
        is_jokes = bool(input("Is this a jokes file? (Y/N) ").lower() in ["y", "yes"])
        min_delay = int(input("Minimuim delay: "))
        max_delay = int(input("Maximum delay: "))
        if not is_jokes:
            dialog_category = input("Dialog category: ")

        outfile = "dialog.json"
        if is_jokes:
            outfile = "jokes.json"

        outfile_input = str(input(f"Output file ({outfile}): "))

        if outfile_input != "" and outfile_input != outfile:
            outfile = outfile_input

        if not is_jokes:
            try:
                with open(outfile, "r", encoding="UTF-8") as readfile:
                    out = json.load(readfile)
            except FileNotFoundError:
                out = {}

            out_obj = {}
            if dialog_category in out:
                out_obj = out[dialog_category]
            else:
                out_obj["min"] = min_delay
                out_obj["max"] = max_delay

            out_obj["sentence"] = []
            while line := file.readline().rstrip():
                out_obj["sentence"].append(line)

            out[dialog_category] = out_obj
        else:
            out = [
                {"min": min_delay, "max": max_delay, "text": line.rstrip()}
                for line in file
            ]

    with open(outfile, "w", encoding="UTF-8") as output:
        output.write(json.dumps(out, indent=4, sort_keys=True))
except FileNotFoundError:
    print(f"The file {infile} was not found!")

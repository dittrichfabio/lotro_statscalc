import os
import re
import sys
import json
import requests
from time import sleep
from bs4 import BeautifulSoup

STATSCALC = os.environ.get('STATSCALC')
VIRTUES_NAMES_URLS = {"Charity": "Charity", "Compassion": "Compassion", "Confidence": "Confidence", "Determination": "Determination_(Virtue)", "Discipline": "Discipline", "Empathy": "Empathy", "Fidelity": "Fidelity", "Fortitude": "Fortitude", "Honesty": "Honesty", "Honour": "Honour", "Idealism": "Idealism", "Innocence": "Innocence", "Justice": "Justice", "Loyalty": "Loyalty", "Mercy": "Mercy", "Patience": "Patience", "Tolerance": "Tolerance", "Valour": "Valour", "Wisdom": "Wisdom", "Wit": "Wit", "Zeal": "Zeal"}
VIRTUES_ESSENCES_STATS_NAME_FIX = {"Agility": "Agility", "Armour Value": "Armour", "Block Rating": "BlockRating", "Critical Defence": "CriticalDefenceRating", "Critical Rating": "CriticalRating", "Evade Rating": "EvadeChanceRating", "Fate": "Fate", "Finesse Rating": "FinesseRating", "in-Combat Morale Regen": "InCombatMoraleRegeneration", "Incoming Healing Rating": "IncomingHealingRating", "Maximum Morale": "Morale", "Maximum Power": "Power", "Might": "Might", "Outgoing Healing Rating": "OutgoingHealingRating", "Parry Rating": "ParryRating", "Physical Mastery Rating": "PhysicalMasteryRating", "Physical Mitigation": "PhysicalMitigationRating", "Resistance Rating": "ResistanceRating", "Tactical Mastery Rating": "TacticalMasteryRating", "Tactical Mitigation": "TacticalMitigationRating", "Vitality": "Vitality", "Will": "Will"}

def get_virtue_stats_from_wiki(delay):
    """
    For each virtue, fetches its lotro-wiki page (based on VIRTUES_NAMES_URLS values).
    Extracts Rank and stats information from the pages.
    Converts page stats to the same format used by the code (based on VIRTUES_STATS_NAME_FIX).
    Saves it under resources/stat_file/virtue_stats.json.
    """
    base_url = "https://lotro-wiki.com/wiki/"
    all_virtue_data = {}

    for virtue in VIRTUES_NAMES_URLS:
        url = base_url + VIRTUES_NAMES_URLS.get(virtue)
        print(f"Fetching {virtue} from {url}")
        response = requests.get(url)
        if not response.ok:
            print(f"Failed to fetch {url}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", class_="altRowsCenter")
        if not table:
            print(f"No virtue stat table found for {virtue}")
            continue

        rows = table.find_all("tr")
        if len(rows) < 3:
            print(f"Not enough rows in virtue table for {virtue}")
            continue

        # Extract the second row's stat names, and get only the first 3 stats (Active bonuses)
        second_header_cells = rows[1].find_all(["th", "td"])
        stat_names = [cell.get_text(strip=True) for cell in second_header_cells[:3]]

        virtue_data = {}
        for row in rows[2:]:  # Skip the two header rows
            cols = row.find_all(["td", "th"])
            if not cols or len(cols) < 4:
                continue

            rank_cell = cols[0].get_text(strip=True)
            if not rank_cell.isdigit():
                continue

            rank = int(rank_cell)
            stats = {}
            for stat_name, cell in zip(stat_names, cols[1:4]):  # First 3 columns after Rank
                value_text = cell.get_text(strip=True)
                value = re.sub(r"[^\d]", "", value_text)
                if value:
                    stats[VIRTUES_ESSENCES_STATS_NAME_FIX[stat_name]] = int(value)

            virtue_data[rank] = stats

        all_virtue_data[virtue] = virtue_data
        sleep(delay)

    with open(os.path.join(STATSCALC, "resources", "stat_files", "virtue_stats.json"), "w") as f:
        json.dump(all_virtue_data, f, indent=2)


def get_essence_stats_from_wiki(delay=5.0):
    url = "https://lotro-wiki.com/wiki/Essences_(Level_141-150)_Index"
    response = requests.get(url)
    if not response.ok:
        print(f"Failed to fetch {url}")
        sys.exit(1)

    STAT_REGEX = re.compile(r"([+-])([0-9,]+) (.*)")
    soup = BeautifulSoup(response.text, "html.parser")
    tables = soup.find_all("table", class_="altRowsPad")
    if not tables:
        print(f"No essences table found.")
        sys.exit(1)

    all_essences_data = {}
    #one table per essence type
    #columns: tier, min level, name, stats
    for table in tables: #for each essence type
        rows = table.find_all("tr")
        for row in rows[1:]: #for each essence in essence type
            essence_stats = {} #TODO: find a way to add essence slot type
            data = row.find_all("td")
            essence_name = data[2].find("span", class_="ajaxttlink").get_text()
            stats_text = data[3].get_text()
            #add two spaces before + or - that is not at the beginning of the string or preceded by a space
            stats_text = re.sub(r'(?<!^)(?<!\s)([+-])', r'  \1', stats_text)
            #split multiple stats by double space
            for stat_text in stats_text.split("  "):
                #try to find regex that matches {sign}{value}{stat_name}
                m = STAT_REGEX.match(stat_text)
                if m: #if matched, fix stat name and add it to this essences' stats
                    stat_name = VIRTUES_ESSENCES_STATS_NAME_FIX[m.groups()[2]]
                    sign = m.groups()[0]
                    stat_value = int(m.groups()[1].replace(",", ""))
                    essence_stats[stat_name] = -1*stat_value if sign == "-" else stat_value
                else: #if not matched, this is a stat that is won't be used for determining the best essences, so include it as "Other"
                    if "Other" in essence_stats:
                        essence_stats["Other"].append(stat_text)
                    else:
                        essence_stats["Other"] = [stat_text]
            all_essences_data[essence_name] = essence_stats

    with open(os.path.join(STATSCALC, "resources", "stat_files", "essences_stats.json"), "w") as f:
        json.dump(all_essences_data, f, indent=2)
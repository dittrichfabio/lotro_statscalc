import os
import json
import click
import itertools
from definitions import *
from functools import partial
from joblib import Parallel, delayed
from lotro_wiki_interface import get_virtue_stats_from_wiki

@click.group()
@click.version_option()
def cli():
    """StatsCalc"""

@cli.command('fetch_virtue_stats')
def fetch_virtue_stat(delay=5.0):
    get_virtue_stats_from_wiki(delay)

@cli.command('fetch_essence_stats')
def fetch_essence_stats(delay=5.0):
    get_virtue_stats_from_wiki(delay)

@cli.command('calculate_stat_percentage')
@click.argument('character_name', required=True)
@click.argument('stat_name', required=True)
@click.argument('stat_value', required=True)
def calculate_stat_percentage(character_name, stat_name, stat_value):
    character = json.load(open(os.path.join(STATSCALC, "resources", "character_files", character_name, "char.json"))) #TODO: not all characters have a char.json
    character_class = character["Class"]
    character_level = character["Level"]
    character_class_stats = CLASSES_STATS[character_class]
    character_armour = character_class_stats["Type"]
    character_stats = character["Stats"]
    extra_stats = character["ExtraStats"]
    computed_stats, overcapped_stats = compute_stat_percentage(stat_name, int(stat_value), character_armour, character_level, extra_stats)

    print(computed_stats)
    print(overcapped_stats)


@cli.command('simulate_equipping_items')
@click.argument('character_name', required=True)
@click.argument('items_file', required=True)
@click.argument('priority', required=False, default="P1", type=click.Choice(["P1", "P2", "P3"]))
def simulate_equipping_items(character_name, items_file, priority):
    items = json.load(open(items_file))
    character = json.load(open(os.path.join(STATSCALC, "resources", "character_files", character_name, "char.json"))) #TODO: not all characters have a char.json
    character_class = character["Class"]
    character_level = character["Level"]
    character_class_stats = CLASSES_STATS[character_class]
    character_armour = character_class_stats["Type"]
    character_stats = character["Stats"]
    extra_stats = character["ExtraStats"]
    #stat_preferences = character["StatPreferences"]
    #if priority == "P1":
    #    stat_priorities = ["P1"]
    #elif priority == "P2":
    #    stat_priorities = ["P1", "P2"]
    #else:
    #    stat_priorities = ["P1", "P2", "P3"]

    #initialize main and secondary stats from character and equip items
    base_stats = equip_items(character_stats, character_class_stats, items)
    print(base_stats)
    #compute percentage of all stats, save information about overcapped stats and adds extra stats
    #computed_stats, overcapped_stats = compute_percentage(base_stats, character_armour, character_level, extra_stats)
    


    # #TODO: change to secondary stats and initialize
    # total_stats = {}
    # for stat in character_stats:
    #     total_stats[stat] = character_stats[stat]

    # #goes over all stats in the character and adds the stats from the items to equip
    # for stat in character_stats:
    #     for item in items:
    #         if stat in item:
    #             total_stats[stat] += item[stat]
    #             if stat in MAIN_STATS: #if the stat is a main stat, add its contribution to secondary stats
    #                 for secondary_stat in character_class_stats[stat]:
    #                     total_stats[secondary_stat] += math.floor(item[stat] * character_class_stats[stat][secondary_stat])

    # for stat in total_stats:
    #     if "Rating" in stat:
    #         if "Mitigation" in stat:
    #             stat_info = STATS_INFO[f"{character_armour}{stat}"]
    #         else:
    #             stat_info = STATS_INFO[f"{stat}"]
    #         stat_percentage = stat.strip("Rating") + "Percentage"
    #         a = stat_info["A"]
    #         b = BRating(bs=stat_info["BStart"], be=stat_info["BEnd"], l=character_level, le=stat_info["LEnd"], ls=stat_info["LStart"])
    #         percentage = round(PfromR(r=total_stats[stat], a=a, b=b), 1)
    #         overcap_percentage = None
    #         overcap_rating = None
    #         if stat_percentage in extra_stats:
    #             percentage += extra_stats[stat_percentage]
    #         if percentage > stat_info["Cap"]:
    #             overcap_percentage = round(percentage - stat_info["Cap"], 1)
    #             percentage = stat_info["Cap"]
    #             rating_for_cap = Rcap(PCap=stat_info["PCap"], a=a, b=b)
    #             overcap_rating = total_stats[stat] - rating_for_cap
    #         if overcap_percentage is not None:
    #             total_stats[stat] = [total_stats[stat], percentage, overcap_rating, overcap_percentage]
    #         else:
    #             total_stats[stat] = [total_stats[stat], percentage]

    # for sp in stat_priorities:
    #     for stat in stat_preferences[sp]:
    #         stat_name = re.sub("Rating$", "", stat)
    #         if type(total_stats[stat]) == list:
    #             r = total_stats[stat][0]
    #             p = total_stats[stat][1]
    #             ocr = None
    #             ocp = None
    #             if len(total_stats[stat]) > 2:
    #                 ocr = total_stats[stat][2]
    #                 ocp = total_stats[stat][3]
    #             if ocr is not None:
    #                 print(f"{stat_name}\t{r} ({p}%) - Overcap {ocr} ({ocp}%)")
    #             else:
    #                 print(f"{stat_name}\t{r} ({p}%)")
    #         else:
    #             v = total_stats[stat]
    #             print(f"{stat_name}\t{v}")
    #     print()


@cli.command('find_best_essences')
@click.argument('character_name', required=True)
@click.argument('items_file', required=True)
@click.argument('priorities_string', required=True)
def find_best_essences(character_name, items_file, priorities_string):
    print(character_name)
    print(items_file)

    priorities = priorities_string.split("|")


@cli.command('find_optimal_essences')
@click.argument('character_name', required=True)
@click.argument('essences_file', required=True)
@click.argument('role', required=True)
@click.option('--algorithm', required=False, default='brute_force', type=click.Choice(['brute_force', 'greedy', 'simulated_annealing', 'ilp']), help='Optimization algorithm to use')
def find_optimal_essences(character_name, essences_file, role, algorithm):
    character = json.load(open(os.path.join(STATSCALC, "resources", "character_files", character_name, f"{role}_stats.json")))
    character_class = character["Class"]
    character_level = character["Level"]
    character_class_stats = CLASSES_STATS[character_class]
    character_armour = character_class_stats["Type"]
    character_stats = character["Stats"]
    level_index = lvl_index(character_level)
    stats_to_print = []

    stat_requirements, stats_to_print, items_to_pick = load_preferred_stats(character_name, role)

    requirements_ratings = get_ratings_for_requirements(stat_requirements, character_level, character_armour) if stat_requirements else {}

    # Prepare essences only
    items_per_type, items_ids, essence_quantity_limits = prepare_essences_only(essences_file, items_to_pick)

    print(items_to_pick, "\n")
    print(items_per_type, "\n")
    print(items_ids, "\n")

    item_types = [i.split('#')[0] for i in items_ids]
    list_of_possibilities = [items_ids[i] for i in items_ids]
    
    stats_rcap = get_all_stats_Rcap(character_level, character_armour)

    # Route to appropriate algorithm
    if algorithm == 'brute_force':
        best_combination, best_combination_value, best_combination_overcapped_stats, best_combination_overcap_value, best_combination_stats = find_optimal_combination_brute_force(
            item_types, items_per_type, items_ids, list_of_possibilities, 
            character_stats, character_class_stats, stats_rcap, requirements_ratings, 
            essence_quantity_limits, stat_requirements, character_level, character_armour
        )
    elif algorithm == 'greedy':
        best_combination, best_combination_value, best_combination_overcapped_stats, best_combination_overcap_value, best_combination_stats = find_optimal_combination_greedy(
            item_types, items_per_type, items_ids, 
            character_stats, character_class_stats, stats_rcap, requirements_ratings,
            essence_quantity_limits, stat_requirements, character_level, character_armour
        )
    elif algorithm == 'simulated_annealing':
        best_combination, best_combination_value, best_combination_overcapped_stats, best_combination_overcap_value, best_combination_stats = find_optimal_combination_simulated_annealing(
            item_types, items_per_type, items_ids,
            character_stats, character_class_stats, stats_rcap, requirements_ratings,
            essence_quantity_limits, stat_requirements, character_level, character_armour
        )
    elif algorithm == 'ilp':
        best_combination, best_combination_value, best_combination_overcapped_stats, best_combination_overcap_value, best_combination_stats = find_optimal_combination_ilp(
            item_types, items_per_type, items_ids,
            character_stats, character_class_stats, stats_rcap, requirements_ratings,
            essence_quantity_limits, stat_requirements, character_level, character_armour
        )

    # Print results
    if best_combination_value > 0:
        total_best_combination_value = 0
        for stat in best_combination_stats:
            total_best_combination_value += best_combination_stats[stat]
        print(f"Found best combination {best_combination} with value {best_combination_value} and overcap {best_combination_overcap_value}. Total combination value: {total_best_combination_value}")
        print("Overcapped stats:")
        for i in best_combination_overcapped_stats:
            print(i, best_combination_overcapped_stats[i])
        print()
        for index, item_type_index in enumerate(best_combination):
            item_type_name = item_types[index]
            item = items_per_type[item_type_name][item_type_index]
            print(item["Name"])
        print()
        for stat in best_combination_stats:
            fstat = RATING2PERCENTAGE_FINAL_STATS.get(stat, stat)
            if fstat != stat:
                stat_info = STATS_INFO.get(get_stats_info_key(fstat, character_armour))
                if stat_info:
                    a = stat_info["A"]
                    b = BRating(bs=stat_info["BStart"][level_index], be=stat_info["BEnd"][level_index], l=character_level, le=stat_info["LEnd"][level_index], ls=stat_info["LStart"][level_index])
                    percentage = PfromR(r=best_combination_stats[stat], a=a, b=b)
                    print(f"{fstat} {round(percentage, 2)}%\n\t{stat} {best_combination_stats[stat]}")
            else:
                if fstat in stats_to_print:
                    print(f"{stat} {best_combination_stats[stat]}")
    else:
        print(f"Couldn't find a combination that satisfies {stat_requirements}.")


@cli.command('compare_items')
@click.argument('character_name', required=True)
@click.argument('items_file', required=True)
@click.argument('priorities_string', required=True)
def compare_items(character_name, items_file, priorities_string):
    print(character_name)
    print(items_file)

    priorities = priorities_string.split("|")


@cli.command('find_optimal_items')
@click.argument('character_name', required=True)
@click.argument('items_file', required=True)
@click.argument('role', required=True)
@click.option('--essences-file', required=False, default=None, help='Path to available essences JSON file')
@click.option('--algorithm', required=False, default='brute_force', type=click.Choice(['brute_force', 'greedy', 'simulated_annealing', 'ilp']), help='Optimization algorithm to use')
def find_optimal_items(character_name, items_file, role, essences_file, algorithm):
    character = json.load(open(os.path.join(STATSCALC, "resources", "character_files", character_name, f"{role}_stats.json")))  #TODO: not all characters have a {role}_stats.json"
    character_class = character["Class"]
    character_level = character["Level"]
    character_class_stats = CLASSES_STATS[character_class]
    character_armour = character_class_stats["Type"]
    character_stats = character["Stats"]
    level_index = lvl_index(character_level)
    #extra_stats = character["ExtraStats"]
    stats_to_print = []

    stat_requirements, stats_to_print, items_to_pick = load_preferred_stats(character_name, role)

    #print(stat_requirements)
    #print(stats_to_print)
    #print(items_to_pick)

    #TODO: redefine how value is computed to have the same value added independent of stat

    #TODO: when loading preferred_stats, make sure that stat actually exist

    #TODO: add a way to define how many of each type we want to equip
    #combination (1, 1, 0, 0, 0, 2) would be invalid if we want 2 0s, 2 1s, 2 2s

    requirements_ratings = get_ratings_for_requirements(stat_requirements, character_level, character_armour) if stat_requirements else {}

    items_per_type, items_ids, essence_quantity_limits = prepare_items(items_file, items_to_pick, essences_file)

    print(items_to_pick, "\n")
    print(items_per_type, "\n")
    print(items_ids, "\n")

    item_types = [i.split('#')[0] for i in items_ids]
    list_of_possibilities = [items_ids[i] for i in items_ids]
    
    stats_rcap = get_all_stats_Rcap(character_level, character_armour)

    # Route to selected algorithm
    if algorithm == 'brute_force':
        best_combination, best_combination_value, best_combination_overcapped_stats, best_combination_overcap_value, best_combination_stats = find_optimal_combination_brute_force(
            item_types, items_per_type, items_ids, list_of_possibilities,
            character_stats, character_class_stats, stats_rcap, requirements_ratings,
            essence_quantity_limits, stat_requirements, character_level, character_armour
        )
    elif algorithm == 'greedy':
        best_combination, best_combination_value, best_combination_overcapped_stats, best_combination_overcap_value, best_combination_stats = find_optimal_combination_greedy(
            item_types, items_per_type, items_ids,
            character_stats, character_class_stats, stats_rcap, requirements_ratings,
            essence_quantity_limits, stat_requirements, character_level, character_armour
        )
    elif algorithm == 'simulated_annealing':
        best_combination, best_combination_value, best_combination_overcapped_stats, best_combination_overcap_value, best_combination_stats = find_optimal_combination_simulated_annealing(
            item_types, items_per_type, items_ids,
            character_stats, character_class_stats, stats_rcap, requirements_ratings,
            essence_quantity_limits, stat_requirements, character_level, character_armour
        )
    elif algorithm == 'ilp':
        best_combination, best_combination_value, best_combination_overcapped_stats, best_combination_overcap_value, best_combination_stats = find_optimal_combination_ilp(
            item_types, items_per_type, items_ids,
            character_stats, character_class_stats, stats_rcap, requirements_ratings,
            essence_quantity_limits, stat_requirements, character_level, character_armour
        )
    else:
        print(f"Unknown algorithm: {algorithm}")
        return
    
    #TODO: print stats increases from base along with each new stat
    #TODO: not all avoidance results not being printed... some rounding differences...
    #TODO: make char.json be a param so that we can use different stat files

    if best_combination_value > 0:
        total_best_combination_value = 0
        for stat in best_combination_stats:
            total_best_combination_value += best_combination_stats[stat]
        print(f"Found best combination {best_combination} with value {best_combination_value} and overcap {best_combination_overcap_value}. Total combination value: {total_best_combination_value}")
        print("Overcapped stats:")
        for i in best_combination_overcapped_stats:
            print(i, best_combination_overcapped_stats[i])
        print()
        for index, item_type_index in enumerate(best_combination):
            item_type_name = item_types[index]
            item = items_per_type[item_type_name][item_type_index]
            print(item["Name"])
        print()
        for stat in best_combination_stats:
            fstat = RATING2PERCENTAGE_FINAL_STATS.get(stat, stat)
            if fstat != stat:
                stat_info = STATS_INFO.get(get_stats_info_key(fstat, character_armour))
                if stat_info:
                    a = stat_info["A"]
                    b = BRating(bs=stat_info["BStart"][level_index], be=stat_info["BEnd"][level_index], l=character_level, le=stat_info["LEnd"][level_index], ls=stat_info["LStart"][level_index])
                    percentage = PfromR(r=best_combination_stats[stat], a=a, b=b)
                    print(f"{fstat} {round(percentage, 2)}%\n\t{stat} {best_combination_stats[stat]}")
            else:
                if fstat in stats_to_print:
                    print(f"{stat} {best_combination_stats[stat]}")
    else:
        print(f"Couldn't find a combination that satisfies {stat_requirements}.")


@cli.command('convert_plugin_data_to_json')
@click.argument('character_name', required=True)
@click.argument('server', required=False)
@click.argument('filename', required=True)
def convert_plugin_data_to_json(character_name, server, filename):
    stats_file = os.path.join(plugin_char_path.format(character_name=character_name, server=server), "Stats.plugindata")
    char_folder = os.path.join(STATSCALC, "stat_files", character_name)
    if not os.path.exists(char_folder):
        os.makedirs(char_folder)

    with open(stats_file, 'r') as f:
        text = f.read()

    matches=STAT.findall(text)
    data = {}
    stats = {}
    for key, value in matches:
        if key in ["Class", "Level"]:
            try:
                data[key] = float(value)
            except ValueError:
                data[key] = value.strip('"')
        else:
            try:
                stats[key] = round(float(value))
            except ValueError:
                stats[key] = value.strip('"')
    for missing_stat, base_stat in TERTIARY_STAT_BASE_MAP.items():
        if missing_stat not in stats and base_stat in stats:
            stats[missing_stat] = stats[base_stat]
    stats = {key: stats[key] for key in sorted(stats, key=lambda x: char_stat_sorting_order.index(x)) if key in char_stat_sorting_order}
    data["Stats"] = stats

    with open(os.path.join(char_folder, filename), 'w') as f:
        json.dump(data, f, indent=4)




@cli.command('stuff')
def stuff():

    r = 14273
    stat = "PhysicalMasteryRating"
    stat_info = STATS_INFO[f"{stat}"]
    character_level = 105
    extra=1.10
    r2 = round(15700.3, -1)

    print(r2)

    #print(stat_info["BStart"], stat_info["BEnd"], character_level, stat_info["LEnd"], stat_info["LStart"])
    b = BRating(bs=stat_info["BStart"], be=stat_info["BEnd"], l=character_level, le=stat_info["LEnd"], ls=stat_info["LStart"])

    print(b)

    print(PfromR(r=r, a=stat_info["A"], b=b))
    print(PfromR(r=r2, a=stat_info["A"], b=b))

#if __name__ == "__main__":
#    character_name = "Cuilrandir"
#    items_file = "stat_files/Cuilrandir/items.json"
#    role = "dps"
#    find_optimal_items(character_name, items_file, role)

if __name__ == "__main__":
    cli()

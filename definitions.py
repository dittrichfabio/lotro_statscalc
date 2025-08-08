import os
import re
import sys
import copy
import json
import math

STAT= re.compile(r'\["(.*?)"] = (.*?)[,\n]')
char_stat_sorting_order = ["Morale", "InCombatMoraleRegeneration", "NonCombatMoraleRegeneration", "Power", "InCombatPowerRegeneration", "NonCombatPowerRegeneration", "Armour", "Might", "Agility", "Vitality", "Will", "Fate", "CriticalRatingMelee", "CriticalRatingRange", "CriticalRatingTactical", "FinesseRating", "PhysicalMasteryRatingMelee", "PhysicalMasteryRatingRange", "TacticalMasteryRating", "OutgoingHealingRating", "ResistanceRating", "CriticalDefenceRating", "IncomingHealingRating", "BlockChanceRating", "PartialBlockChanceRating", "PartialBlockMitigationRating", "ParryChanceRating", "PartialParryChanceRating", "PartialParryMitigationRating", "EvadeChanceRating", "PartialEvadeChanceRating", "PartialEvadeMitigationRating", "PhysicalMitigationRating", "TacticalMitigationRating"]

VIRTUES_NAMES_URLS = {"Charity": "Charity", "Compassion": "Compassion", "Confidence": "Confidence", "Determination": "Determination_(Virtue)", "Discipline": "Discipline", "Empathy": "Empathy", "Fidelity": "Fidelity", "Fortitude": "Fortitude", "Honesty": "Honesty", "Honour": "Honour", "Idealism": "Idealism", "Innocence": "Innocence", "Justice": "Justice", "Loyalty": "Loyalty", "Mercy": "Mercy", "Patience": "Patience", "Tolerance": "Tolerance", "Valour": "Valour", "Wisdom": "Wisdom", "Wit": "Wit", "Zeal": "Zeal"}
VIRTUES_ESSENCES_STATS_NAME_FIX = {"Agility": "Agility", "Armour Value": "Armour", "Block Rating": "BlockRating", "Critical Defence": "CriticalDefenceRating", "Critical Rating": "CriticalRating", "Evade Rating": "EvadeChanceRating", "Fate": "Fate", "Finesse Rating": "FinesseRating", "in-Combat Morale Regen": "InCombatMoraleRegeneration", "Incoming Healing Rating": "IncomingHealingRating", "Maximum Morale": "Morale", "Maximum Power": "Power", "Might": "Might", "Outgoing Healing Rating": "OutgoingHealingRating", "Parry Rating": "ParryRating", "Physical Mastery Rating": "PhysicalMasteryRating", "Physical Mitigation": "PhysicalMitigationRating", "Resistance Rating": "ResistanceRating", "Tactical Mastery Rating": "TacticalMasteryRating", "Tactical Mitigation": "TacticalMitigationRating", "Vitality": "Vitality", "Will": "Will"}

#Plugins data
server = "Angmar"
username = "ddmdarklink"
plugin_char_path = os.path.join("/", "mnt", "c", "Users", "fabio_dittrich", "Documents", "The Lord of the Rings Online", "PluginData", f"{username}", f"{server}", "{character_name}")

#Formulas
BRating = lambda bs, be, l, le, ls: (bs*(le-l)+(l-ls)*be)/(le-ls)
PfromR = lambda r, a, b: r*a/(r+b)
RfromP = lambda p, a, b: p*b/(a-p)
Rcap = lambda PCap, a, b: PCap*b/(a-PCap)
c = lambda PCap, a: PCap/(a-PCap)
Ropt = lambda c, Rcap: (math.sqrt(c+1)-1)/c*Rcap

STATSCALC = os.environ.get('STATSCALC')
STATS_INFO = json.load(open(os.path.join(STATSCALC, "stat_files", "stats_info.json")))
CLASSES_STATS = json.load(open(os.path.join(STATSCALC, "stat_files", "classes.json")))

#main stats that secondary and tertiary stats depend on
MAIN_STATS = ["Armour", "Might", "Agility", "Vitality", "Will", "Fate"]
#secondary stats that are computed from main ones, but can also be found in items
SECONDARY_STATS = ["Morale", "InCombatMoraleRegeneration", "NonCombatMoraleRegeneration", "Power", "InCombatPowerRegeneration", "NonCombatPowerRegeneration", "CriticalRating", "FinesseRating", "PhysicalMasteryRating", "TacticalMasteryRating", "OutgoingHealingRating", "ResistanceRating", "CriticalDefenceRating", "IncomingHealingRating", "BlockChanceRating", "ParryChanceRating", "EvadeChanceRating", "PhysicalMitigationRating", "TacticalMitigationRating"]
#tertiary stats that cannot be found in items and are derived from some secondary stats
TERTIARY_STATS = ["CriticalRatingMelee", "DevastatingRatingMelee", "CriticalMagnitudeRatingMelee", "CriticalRatingRange", "DevastatingRatingRange", "CriticalMagnitudeRatingRange", "CriticalRatingTactical", "DevastatingRatingTactical", "CriticalMagnitudeRatingTactical", "PhysicalMasteryRatingMelee", "PhysicalMasteryRatingRange", "BlockChanceRating", "ParryChanceRating", "EvadeChanceRating", "PartialBlockChanceRating", "PartialParryChanceRating", "PartialEvadeChanceRating", "PartialBlockMitigationRating", "PartialParryMitigationRating", "PartialEvadeMitigationRating"]
#the relationship between secondary and tertiary stats
SECONDARY2TERTIARY_MAPPING = {"CriticalRating": ["CriticalRatingMelee", "CriticalRatingRange", "CriticalRatingTactical"], "PhysicalMasteryRating": ["PhysicalMasteryRatingMelee", "PhysicalMasteryRatingRange"], "BlockChanceRating": ["BlockChanceRating", "PartialBlockChanceRating", "PartialBlockMitigationRating"], "ParryChanceRating": ["ParryChanceRating", "PartialParryChanceRating", "PartialParryMitigationRating"], "EvadeChanceRating": ["EvadeChanceRating", "PartialEvadeChanceRating", "PartialEvadeMitigationRating"]}
#the relationship between tertiary and secondary stats
TERTIARY2SECONDARY_MAPPING = {tstat:stat for stat in SECONDARY2TERTIARY_MAPPING for tstat in SECONDARY2TERTIARY_MAPPING[stat]}
#final stats in form of percentage and the secondary or tertiary stat it is associated to
#FINAL_STATS = ["CriticalHitChanceMelee", "DevastatingHitChanceMelee", "Critical&DevastatingHitMagnitudeMelee", "CriticalHitChanceRange", "DevastatingHitChanceRange", "Critical&DevastatingHitMagnitudeRange", "CriticalHitChanceTactical", "DevastatingHitChanceTactical", "Critical&DevastatingHitMagnitudeTactical", "Finesse", "PhysicalDamageMelee", "PhysicalDamageRange", "TacticalOffenceDamage", "TacticalOutgoingHealing", "Resistance", "CriticalDefence", "IncomingHealing", "BlockChance", "PartialBlockChance", "PartialBlockMitigation", "ParryChance", "PartialParryChance", "PartialParryMitigation", "EvadeChance", "PartialEvadeChance", "PartialEvadeMitigation", "PhysicalMitigation", "TacticalMitigation"]
FINAL_STATS = {"CriticalHitChanceMelee": "CriticalRatingMelee", "DevastatingHitChanceMelee": "DevastatingRatingMelee", "Critical&DevastatingHitMagnitudeMelee": "CriticalMagnitudeRatingMelee", "CriticalHitChanceRange": "CriticalRatingRange", "DevastatingHitChanceRange": "DevastatingRatingRange", "Critical&DevastatingHitMagnitudeRange": "CriticalMagnitudeRatingRange", "CriticalHitChanceTactical": "CriticalRatingTactical", "DevastatingHitChanceTactical": "DevastatingRatingTactical", "Critical&DevastatingHitMagnitudeTactical": "CriticalMagnitudeRatingTactical", "Finesse": "FinesseRating", "PhysicalDamageMelee": "PhysicalMasteryRatingMelee", "PhysicalDamageRange": "PhysicalMasteryRatingRange", "TacticalOffenceDamage": "TacticalMasteryRating", "TacticalOutgoingHealing": "OutgoingHealingRating", "Resistance": "ResistanceRating", "CriticalDefence": "CriticalDefenceRating", "IncomingHealing": "IncomingHealingRating", "BlockChance": "BlockChanceRating", "PartialBlockChance": "PartialBlockChanceRating", "PartialBlockMitigation": "PartialBlockMitigationRating", "ParryChance": "ParryChanceRating", "PartialParryChance": "PartialParryChanceRating", "PartialParryMitigation": "PartialParryMitigationRating", "EvadeChance": "EvadeChanceRating", "PartialEvadeChance": "PartialEvadeChanceRating", "PartialEvadeMitigation": "PartialEvadeMitigationRating", "PhysicalMitigation": "PhysicalMitigationRating", "TacticalMitigation": "TacticalMitigationRating"}
FINAL_STATS.update({stat:"" for stat in MAIN_STATS})
FINAL_STATS.update({"Morale": "", "InCombatMoraleRegeneration": "", "NonCombatMoraleRegeneration": "", "Power": "", "InCombatPowerRegeneration": "", "NonCombatPowerRegeneration": ""})
RATING2PERCENTAGE_FINAL_STATS = {FINAL_STATS[stat]:stat for stat in FINAL_STATS if FINAL_STATS[stat]}
VALID_STATS = list(set(MAIN_STATS+SECONDARY_STATS+list(FINAL_STATS.keys())))
VALID_ITEM_MAX_QUANTITY = {"Boots": 1,  "Chest": 1,  "Gloves": 1,  "Helm": 1,  "Leggings": 1,  "Shoulders": 1,  "Back": 1,  "Ring": 2,  "Earring": 2,  "Bracelet": 2,  "Necklace": 1,  "Pocket": 1, "Essence": 999}
VALID_ITEM_TYPES = list(VALID_ITEM_MAX_QUANTITY.keys())


LEVEL_RANGES = [range(1,50), range(50,60), range(60,65), range(65,75), range(75,85), range(85,95), range(95,100), range(100,105), range(105,106), range(106,115), range(115,116), range(116,120), range(120,121), range(121,130), range(130,131), range(131,140), range(140,141), range(141,150)]

def lvl_index(lvl):
    if lvl == 1:
        return 0
    for i,r in enumerate(LEVEL_RANGES):
        if (lvl-1) in r:
            return i
        
def equip_items(character_stats, character_class_stats, items):
    new_stats = copy.deepcopy(character_stats)
    if "available_items" in items:
        items = items["available_items"]
    for item in items:
        item_stats = item.get("Stats")
        for item_stat in item_stats:
            if item_stat in SECONDARY2TERTIARY_MAPPING:
                for stat in SECONDARY2TERTIARY_MAPPING[item_stat]:
                    new_stats[stat] += item_stats[item_stat]
            else:
                new_stats[item_stat] += item_stats[item_stat]
            if item_stat in MAIN_STATS: #if the stat is a main stat, add its contribution to secondary stats
                for secondary_stat in character_class_stats[item_stat]:
                    new_stats[secondary_stat] += math.floor(item_stats[item_stat] * character_class_stats[item_stat][secondary_stat])
    return new_stats

def compute_percentage(base_stats, character_armour, character_level, extra_stats):
    level_index = lvl_index(character_level)
    computed_stats = {i:0 for i in FINAL_STATS}
    overcapped_stats = {}
    for stat in computed_stats:
        if stat in ["PhysicalMitigation", "TacticalMitigation"]:
            stat_info = STATS_INFO[f"{character_armour}{stat}"]
        else:
            stat_info = STATS_INFO[f"{stat}"]
        a = stat_info["A"]
        b = BRating(bs=stat_info["BStart"][level_index], be=stat_info["BEnd"][level_index], l=character_level, le=stat_info["LEnd"][level_index], ls=stat_info["LStart"][level_index])
        computed_stats[stat] = round(PfromR(r=base_stats[computed_stats[stat]["AssociatedSecondaryStat"]], a=a, b=b), 1)
        if computed_stats[stat] > stat_info["Cap"]:
            overcap_percentage = round(computed_stats[stat] - stat_info["Cap"], 1)
            computed_stats[stat] = stat_info["Cap"]
            rating_for_cap = Rcap(PCap=stat_info["PCap"], a=a, b=b)
            overcap_rating = base_stats[stat] - rating_for_cap
            overcapped_stats[stat] = {"overcap_percentage": overcap_percentage, "overcap_rating": overcap_rating}
        if stat in extra_stats:
            computed_stats[stat] += extra_stats[stat]
    return computed_stats, overcapped_stats

def compute_stat_percentage(stat_name, stat_value, character_armour, character_level, extra_stats):
    level_index = lvl_index(character_level)
    computed_stats = {stat_name:0}
    overcapped_stats = {}
    if stat_name in ["PhysicalMitigation", "TacticalMitigation"]:
        stat_info = STATS_INFO[f"{character_armour}{stat_name}"]
    else:
        stat_info = STATS_INFO[f"{stat_name}"]
    a = stat_info["A"]
    b = BRating(bs=stat_info["BStart"][level_index], be=stat_info["BEnd"][level_index], l=character_level, le=stat_info["LEnd"][level_index], ls=stat_info["LStart"][level_index])
    computed_stats[stat_name] = round(PfromR(r=stat_value, a=a, b=b), 1)
    if computed_stats[stat_name] > stat_info["Cap"]:
        overcap_percentage = round(computed_stats[stat_name] - stat_info["Cap"], 1)
        computed_stats[stat_name] = stat_info["Cap"]
        rating_for_cap = Rcap(PCap=stat_info["PCap"], a=a, b=b)
        overcap_rating = stat_value - rating_for_cap
        overcapped_stats[stat_name] = {"overcap_percentage": overcap_percentage, "overcap_rating": overcap_rating}
    if stat_name in extra_stats:
        computed_stats[stat_name] += extra_stats[stat_name]
    return computed_stats, overcapped_stats

def prepare_items(items_file, items_to_pick):
    items_json = json.load(open(items_file))
    available_items = items_json.get("available_items")

    items_per_type = {}
    for item in items_to_pick:
        if item not in VALID_ITEM_TYPES:
            print(f"Item {item} is invalid. Valid types: {VALID_ITEM_TYPES}. Aborting!")
            sys.exit(1)
        if items_to_pick[item] > VALID_ITEM_MAX_QUANTITY[item]:
            print(f"Item {item} can have a max of {VALID_ITEM_MAX_QUANTITY[item]}, but {items_to_pick[item]} were requested. Aborting!")
            sys.exit(1)

    items_per_type = {i:[] for i in items_to_pick}
    items_ids = {i:[] for i in items_to_pick}
    for item in available_items:
        item_name = item.get("Name", False)
        item_type = item.get("Type", "Unset")
        item_stats = item.get("Stats", False)
        if not item_name:
            print(f"Missing name for item {item}. Aborting!")
            sys.exit(1)
        if item_type not in VALID_ITEM_TYPES:
            print(f"Type {item_type} of {item_name} is not valid. Aborting!")
            sys.exit(1)
        for stat in item_stats:
            if stat not in VALID_STATS:
                print(f"Stat {stat} of {item_name} is not valid. Aborting!")
                sys.exit(1)

        if items_to_pick[item_type] != 0:
            if items_per_type[item_type] == []:
                items_per_type[item_type] = [{"Name": item_name, "Stats": item_stats}]
            else:
                items_per_type[item_type].append({"Name": item_name, "Stats": item_stats})
            if items_ids[item_type] == []:
                items_ids[item_type].append(0)
            else:
                items_ids[item_type].append(items_ids[item_type][-1]+1)
            #items_to_pick[item_type] -= 1
        #    else:
        #        for i in range(1,items_to_pick[item_type]+1):
        #            items_per_type[item_type+f"{i}"] = [{"Name": item_name, "Stats": item_stats}]
        #            items_ids[item_type+f"{i}"] = [0]
        #    else:
        #        for i in range(1,items_to_pick[item_type]+1):
        #            items_per_type[item_type+f"{i}"].append({"Name": item_name, "Stats": item_stats})
        #            items_ids[item_type+f"{i}"].append(items_ids[item_type+f"{i}"][-1]+1)

        # if item_type not in items_per_type:
        #     if items_to_pick[item_type] == 1:
        #         items_per_type[item_type] = [{"Name": item_name, "Stats": item_stats}]
        #         items_ids[item_type] = [0]
        #     else:
        #         for i in range(1,items_to_pick[item_type]+1):
        #             items_per_type[item_type+f"{i}"] = [{"Name": item_name, "Stats": item_stats}]
        #             items_ids[item_type+f"{i}"] = [0]
        # else:
        #     if items_to_pick[item_type] == 1:
        #         items_per_type[item_type].append({"Name": item_name, "Stats": item_stats})
        #         items_ids[item_type].append(items_ids[item_type][-1]+1)
        #     else:
        #         for i in range(1,items_to_pick[item_type]+1):
        #             items_per_type[item_type+f"{i}"].append({"Name": item_name, "Stats": item_stats})
        #             items_ids[item_type+f"{i}"].append(items_ids[item_type+f"{i}"][-1]+1)
    expanded_items_ids = {}
    for item in items_to_pick:
        for i in range(1, items_to_pick[item]+1):
            expanded_items_ids[f"{item}#{i}"] = items_ids[item]

    return items_per_type, expanded_items_ids

def get_all_stats_Rcap(character_level, character_armour):
    level_index = lvl_index(character_level)
    stats_rcap = {}
    for fstat in FINAL_STATS:
        if FINAL_STATS[fstat]:
            if fstat in ["PhysicalMitigation", "TacticalMitigation"]:
                stat_info = STATS_INFO[f"{character_armour}{fstat}"]
            else:
                stat_info = STATS_INFO[f"{fstat}"]
            a = stat_info["A"]
            b = BRating(bs=stat_info["BStart"][level_index], be=stat_info["BEnd"][level_index], l=character_level, le=stat_info["LEnd"][level_index], ls=stat_info["LStart"][level_index])
            stats_rcap[FINAL_STATS[fstat]] = Rcap(PCap=stat_info["PCap"], a=a, b=b)
    return stats_rcap

def get_ratings_for_requirements(stat_requirements, character_level, character_armour):
    requirements_ratings = {}
    level_index = lvl_index(character_level)
    for r in stat_requirements:
        fstat = r.split('=')[0]
        percentage = float(r.split('=')[1]) if len(r.split('=')) == 2 else -1
        if percentage != -1:
            if fstat in ["PhysicalMitigation", "TacticalMitigation"]:
                stat_info = STATS_INFO[f"{character_armour}{fstat}"]
            elif fstat in ["Morale"]:
                requirements_ratings[fstat] = percentage
                continue
            else:
                stat_info = STATS_INFO[f"{fstat}"]
            a = stat_info["A"]
            b = BRating(bs=stat_info["BStart"][level_index], be=stat_info["BEnd"][level_index], l=character_level, le=stat_info["LEnd"][level_index], ls=stat_info["LStart"][level_index])
            requirements_ratings[FINAL_STATS[fstat]] = RfromP(p=percentage, a=a, b=b)
        elif FINAL_STATS[fstat]:
            requirements_ratings[FINAL_STATS[fstat]] = -1
        else:
            requirements_ratings[fstat] = -1
    return requirements_ratings

def define_combination_value(new_stats, requirements_ratings):
    value = 0
    if requirements_ratings:
        if any(new_stats[r] < requirements_ratings[r] for r in requirements_ratings):
            return value
        for r in requirements_ratings:
            value += new_stats[r]
    else:
        for r in new_stats:
            value += new_stats[r]
    return value

def process_combination(combination, item_types, items_per_type, character_stats, character_class_stats, stats_rcap, requirements_ratings, penalize_overcapping):
    #if comb_num % 1000 == 0:
    #    print(comb_num)
    #print(combination)
    combination_items = []
    for index, item_type_index in enumerate(combination):
        item_type_name = item_types[index]
        item = items_per_type[item_type_name][item_type_index]
        #print(item_type_name)
        #print(item)
        #print(item_type_name, item_type_index, item)
        combination_items.append(item)
    #print(combination_items)
    #print(character_stats)
    new_stats = equip_items(character_stats, character_class_stats, combination_items)
    #print(new_stats)
    overcap_value = 0
    overcapped_stats = {}
    for stat in new_stats:
        if stat in stats_rcap:
            if new_stats[stat] > stats_rcap[stat]:
                #print("!!!!")
                #print(stat)
                #print(new_stats[stat])
                #print(stats_rcap[stat])
                secondary_stat = TERTIARY2SECONDARY_MAPPING.get(stat, "use_normal_stat")
                if secondary_stat == "use_normal_stat":
                    overcapped_stats[stat] = (new_stats[stat] - stats_rcap[stat])
                    overcap_value += (new_stats[stat] - stats_rcap[stat])
                elif secondary_stat not in overcapped_stats:
                    overcapped_stats[secondary_stat] = (new_stats[stat] - stats_rcap[stat])
                    overcap_value += (new_stats[stat] - stats_rcap[stat])
                new_stats[stat] = stats_rcap[stat]
    #print(new_stats)
    combination_value = define_combination_value(new_stats, requirements_ratings)
    if penalize_overcapping:
        combination_value -= overcap_value
    #print("=====")
    #print(overcap)
    #print(combination_value)
    return (combination, combination_value, overcapped_stats, overcap_value, new_stats)

def load_preferred_stats(character_name, role):
    preferred_stats_file = os.path.join(STATSCALC, "stat_files", character_name, "preferred_stats.json")
    if not os.path.exists(preferred_stats_file):
        print(f"{preferred_stats_file} does not exist, using all stats for comparing item combinations and printing them all at the end.")
        return VALID_STATS, None
    preferred_stats = json.load(open(preferred_stats_file))
    roles = preferred_stats["roles"]
    if role not in roles:
        print(f"Role {role} is not present in {preferred_stats_file}, using all stats for comparing item combinations and printing them all at the end.")
        return VALID_STATS, None
    
    role_stats = roles[role]
    stat_requirements = role_stats.get("stat_requirements", False)
    stats_to_print = role_stats.get("stats_to_print", False)
    if not stat_requirements:
        print(f"Role {role} does not define 'stat_requirements', using all stats for comparing item combinations.")
        stat_requirements = None
    if not stats_to_print:
        print(f"Role {role} does not define 'stats_to_print', printing all stats at the end.")
        stats_to_print = VALID_STATS
    
    items_to_pick = preferred_stats["items_to_pick"]

    return stat_requirements, stats_to_print, items_to_pick

def expand_item_combinations(items_file):
    pass

def add_item_stats(*dicts):
    result = {}
    for d in dicts:
        for key, value in d.items():
            if key in result:
                result[key] += value
            else:
                result[key] = value
    return result
import os
import re
import sys
import copy
import json
import math
import itertools

STAT= re.compile(r'\["(.*?)"] = (.*?)[,\n]')
char_stat_sorting_order = ["Morale", "InCombatMoraleRegeneration", "NonCombatMoraleRegeneration", "Power", "InCombatPowerRegeneration", "NonCombatPowerRegeneration", "Armour", "Might", "Agility", "Vitality", "Will", "Fate", "CriticalRatingMelee", "CriticalRatingRange", "CriticalRatingTactical", "FinesseRating", "PhysicalMasteryRatingMelee", "PhysicalMasteryRatingRange", "TacticalMasteryRating", "OutgoingHealingRating", "ResistanceRating", "CriticalDefenceRating", "IncomingHealingRating", "BlockChanceRating", "PartialBlockChanceRating", "PartialBlockMitigationRating", "ParryChanceRating", "PartialParryChanceRating", "PartialParryMitigationRating", "EvadeChanceRating", "PartialEvadeChanceRating", "PartialEvadeMitigationRating", "PhysicalMitigationRating", "TacticalMitigationRating"]

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
STATS_INFO = json.load(open(os.path.join(STATSCALC, "resources", "stat_files", "stats_info.json")))
CLASSES_STATS = json.load(open(os.path.join(STATSCALC, "resources", "stat_files", "classes_stats.json")))

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

def prepare_items(items_file, items_to_pick, essences_file=None):
    items_json = json.load(open(items_file))
    available_items = items_json.get("available_items")
    
    # Validate essences file if Essence is in items_to_pick
    if "Essence" in items_to_pick and items_to_pick["Essence"] > 0:
        if essences_file is None:
            print(f"Essence is in items_to_pick but no essences file was provided. Please provide --essences-file argument. Aborting!")
            sys.exit(1)

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
    
    # Load essences if file is provided
    available_essences = []
    if essences_file is not None:
        available_essences = json.load(open(essences_file))
    
    # Process regular items from items.json
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

        if item_type in items_to_pick:
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

    # Process essences from essences file
    essence_quantity_limits = {}
    for essence in available_essences:
        essence_name = essence.get("Name", False)
        essence_type = essence.get("Type", "Unset")
        essence_stats = essence.get("Stats", False)
        quantity_available = essence.get("QuantityAvailable", -1)
        
        if not essence_name:
            print(f"Missing name for essence {essence}. Aborting!")
            sys.exit(1)
        if essence_type != "Essence":
            print(f"Type {essence_type} of {essence_name} is not Essence. Aborting!")
            sys.exit(1)
        for stat in essence_stats:
            if stat not in VALID_STATS:
                print(f"Stat {stat} of {essence_name} is not valid. Aborting!")
                sys.exit(1)
        
        # Track quantity limits for each essence
        essence_quantity_limits[essence_name] = quantity_available
        
        if "Essence" in items_to_pick and items_to_pick["Essence"] != 0:
            if items_per_type["Essence"] == []:
                items_per_type["Essence"] = [{"Name": essence_name, "Stats": essence_stats}]
            else:
                items_per_type["Essence"].append({"Name": essence_name, "Stats": essence_stats})
            if items_ids["Essence"] == []:
                items_ids["Essence"].append(0)
            else:
                items_ids["Essence"].append(items_ids["Essence"][-1]+1)
    
    expanded_items_ids = {}
    for item in items_to_pick:
        for i in range(1, items_to_pick[item]+1):
            expanded_items_ids[f"{item}#{i}"] = items_ids[item]

    return items_per_type, expanded_items_ids, essence_quantity_limits

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

def process_combination(combination, item_types, items_per_type, character_stats, character_class_stats, stats_rcap, requirements_ratings, penalize_overcapping, essence_quantity_limits=None):
    #if comb_num % 1000 == 0:
    #    print(comb_num)
    #print(combination)
    
    # Validate essence quantity limits if provided
    if essence_quantity_limits is not None:
        if not validate_essence_quantities(combination, item_types, items_per_type, essence_quantity_limits):
            return (combination, -1, {}, 0, {})
    
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
    preferred_stats_file = os.path.join(STATSCALC, "resources", "character_files", character_name, "preferred_stats.json")
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

def validate_essence_quantities(combination, item_types, items_per_type, essence_quantity_limits):
    """
    Validate that a combination respects essence quantity limits.
    Returns True if valid, False otherwise.
    """
    essence_counts = {}
    
    for index, item_type_index in enumerate(combination):
        item_type_name = item_types[index]
        if item_type_name == "Essence":
            item = items_per_type[item_type_name][item_type_index]
            essence_name = item["Name"]
            essence_counts[essence_name] = essence_counts.get(essence_name, 0) + 1
            
            # Check if this essence exceeds its quantity limit
            quantity_limit = essence_quantity_limits.get(essence_name, -1)
            if quantity_limit != -1 and essence_counts[essence_name] > quantity_limit:
                return False
    
    return True

def prepare_essences_only(essences_file, items_to_pick):
    """
    Prepare essences only (essence-specific version of prepare_items).
    Returns items_per_type, items_ids, essence_quantity_limits
    """
    available_essences = json.load(open(essences_file))
    
    # Validate that only Essence is in items_to_pick
    if len(items_to_pick) != 1 or "Essence" not in items_to_pick:
        print(f"prepare_essences_only should only be used with Essence items. Found: {items_to_pick}. Aborting!")
        sys.exit(1)
    
    if items_to_pick["Essence"] > VALID_ITEM_MAX_QUANTITY["Essence"]:
        print(f"Essence can have a max of {VALID_ITEM_MAX_QUANTITY['Essence']}, but {items_to_pick['Essence']} were requested. Aborting!")
        sys.exit(1)

    items_per_type = {"Essence": []}
    items_ids = {"Essence": []}
    essence_quantity_limits = {}
    
    for essence in available_essences:
        essence_name = essence.get("Name", False)
        essence_type = essence.get("Type", "Unset")
        essence_stats = essence.get("Stats", False)
        quantity_available = essence.get("QuantityAvailable", -1)
        
        if not essence_name:
            print(f"Missing name for essence {essence}. Aborting!")
            sys.exit(1)
        if essence_type != "Essence":
            print(f"Type {essence_type} of {essence_name} is not Essence. Aborting!")
            sys.exit(1)
        for stat in essence_stats:
            if stat not in VALID_STATS:
                print(f"Stat {stat} of {essence_name} is not valid. Aborting!")
                sys.exit(1)
        
        # Track quantity limits for each essence
        essence_quantity_limits[essence_name] = quantity_available
        
        if items_per_type["Essence"] == []:
            items_per_type["Essence"] = [{"Name": essence_name, "Stats": essence_stats}]
        else:
            items_per_type["Essence"].append({"Name": essence_name, "Stats": essence_stats})
        if items_ids["Essence"] == []:
            items_ids["Essence"].append(0)
        else:
            items_ids["Essence"].append(items_ids["Essence"][-1]+1)
    
    expanded_items_ids = {}
    for i in range(1, items_to_pick["Essence"]+1):
        expanded_items_ids[f"Essence#{i}"] = items_ids["Essence"]

    return items_per_type, expanded_items_ids, essence_quantity_limits

def prune_essences_by_requirements(items_per_type, stat_requirements):
    """
    Prune essences that don't contribute to any required stat.
    Returns filtered items_per_type and mapping of old to new indices.
    """
    if not stat_requirements:
        return items_per_type, {i: i for i in range(len(items_per_type["Essence"]))}
    
    # Extract required stats (both with and without goals)
    required_stats = set()
    for req in stat_requirements:
        stat_name = req.split('=')[0]
        required_stats.add(stat_name)
    
    # Map to secondary stats if needed
    required_secondary_stats = set()
    for stat in required_stats:
        if stat in FINAL_STATS:
            secondary_stat = FINAL_STATS[stat]
            if secondary_stat:
                required_secondary_stats.add(secondary_stat)
        else:
            required_secondary_stats.add(stat)
    
    # Filter essences
    filtered_essences = []
    index_mapping = {}
    new_index = 0
    
    for old_index, essence in enumerate(items_per_type["Essence"]):
        essence_stats = essence["Stats"]
        contributes = False
        
        for stat in essence_stats:
            if stat in required_secondary_stats or stat in required_stats:
                contributes = True
                break
        
        if contributes:
            filtered_essences.append(essence)
            index_mapping[old_index] = new_index
            new_index += 1
    
    return {"Essence": filtered_essences}, index_mapping

def find_optimal_combination_brute_force(item_types, items_per_type, items_ids, list_of_possibilities, 
                                           character_stats, character_class_stats, stats_rcap, requirements_ratings,
                                           essence_quantity_limits, stat_requirements, character_level, character_armour):
    """
    Brute force algorithm with pruning for essence optimization.
    Uses generator to avoid memory explosion.
    Penalizes stats exceeding goal values.
    """
    # Separate stats with goals and without goals
    stats_with_goals = {}
    stats_without_goals = set()
    if stat_requirements:
        for req in stat_requirements:
            if '=' in req:
                stat_name, target = req.split('=')
                stats_with_goals[stat_name] = float(target)
            else:
                stats_without_goals.add(req)
    
    # Prune essences that don't contribute to required stats
    filtered_items_per_type, index_mapping = prune_essences_by_requirements(items_per_type, stat_requirements)
    
    # Update items_ids with new indices
    filtered_items_ids = {}
    for key in items_ids:
        filtered_items_ids[key] = [index_mapping.get(idx, idx) for idx in items_ids[key]]
    
    filtered_list_of_possibilities = [filtered_items_ids[i] for i in filtered_items_ids]
    
    # Use generator instead of list
    all_combinations = itertools.product(*filtered_list_of_possibilities)
    
    penalize_overcapping = True
    best_combination = None
    best_combination_value = -1
    best_combination_overcapped_stats = {}
    best_combination_overcap_value = 0
    best_combination_stats = {}
    
    for combination in all_combinations:
        # Validate essence quantity limits using original items_per_type
        if not validate_essence_quantities(combination, item_types, items_per_type, essence_quantity_limits):
            continue
        
        # Process combination
        result = process_combination(combination, item_types, filtered_items_per_type, 
                                     character_stats, character_class_stats, stats_rcap, 
                                     requirements_ratings, penalize_overcapping, essence_quantity_limits)
        
        base_value = result[1]
        final_stats = result[4]
        
        # Apply penalty for stats exceeding goals
        penalty = 0
        for stat, target in stats_with_goals.items():
            # Map stat name to actual stat name if needed
            actual_stat = stat
            if stat in FINAL_STATS:
                actual_stat = FINAL_STATS[stat]
            
            # Check if this stat is a tertiary stat that needs to be summed from secondary stats
            if actual_stat in TERTIARY2SECONDARY_MAPPING:
                # Sum all secondary stats that contribute to this tertiary stat
                total_value = 0
                for sec_stat, tert_stats in SECONDARY2TERTIARY_MAPPING.items():
                    if actual_stat in tert_stats:
                        total_value += final_stats.get(sec_stat, 0)
                current_value = total_value
            else:
                current_value = final_stats.get(actual_stat, 0)
            
            # For final stats (percentage-based), the target is already in percentage
            # We need to check if the current rating would exceed the target percentage
            # For now, skip penalty for percentage-based stats as the conversion is complex
            # The base value already handles this via requirements_ratings
            if actual_stat not in FINAL_STATS.values():
                # Only apply penalty for non-percentage stats
                if current_value > target:
                    excess = current_value - target
                    penalty += excess * 2  # Moderate penalty for exceeding goal
        
        adjusted_value = base_value - penalty
        
        if adjusted_value > best_combination_value:
            best_combination = result[0]
            best_combination_value = adjusted_value
            best_combination_overcapped_stats = result[2]
            best_combination_overcap_value = result[3]
            best_combination_stats = result[4]
    
    return best_combination, best_combination_value, best_combination_overcapped_stats, best_combination_overcap_value, best_combination_stats

def find_optimal_combination_greedy(item_types, items_per_type, items_ids,
                                     character_stats, character_class_stats, stats_rcap, requirements_ratings,
                                     essence_quantity_limits, stat_requirements, character_level, character_armour):
    """
    Greedy algorithm: pick best essence for each slot sequentially.
    Prioritizes stats with goals, then maximizes non-goal stats.
    Penalizes stats that exceed their goal values.
    """
    # Separate stats with goals and without goals
    stats_with_goals = {}
    stats_without_goals = set()
    
    if stat_requirements:
        for req in stat_requirements:
            if '=' in req:
                stat_name, target = req.split('=')
                stats_with_goals[stat_name] = float(target)
            else:
                stats_without_goals.add(req)
    
    # Calculate current stats
    current_stats = copy.deepcopy(character_stats)
    
    best_combination = []
    essence_counts = {}
    
    # Get number of essence slots
    num_slots = len(item_types)
    
    for slot in range(num_slots):
        best_essence_idx = None
        best_essence_score = -float('inf')
        
        for essence_idx in range(len(items_per_type["Essence"])):
            essence = items_per_type["Essence"][essence_idx]
            essence_name = essence["Name"]
            
            # Check quantity limits
            current_count = essence_counts.get(essence_name, 0)
            quantity_limit = essence_quantity_limits.get(essence_name, -1)
            if quantity_limit != -1 and current_count >= quantity_limit:
                continue
            
            # Calculate score based on contribution to stats with goals
            score = 0
            for stat, value in essence["Stats"].items():
                # Check if this stat matches any goal stat (direct or mapped)
                matched_goal = None
                is_percentage_stat = False
                for goal_stat, target in stats_with_goals.items():
                    actual_goal_stat = goal_stat
                    if goal_stat in FINAL_STATS:
                        actual_goal_stat = FINAL_STATS[goal_stat]
                        is_percentage_stat = True
                    if stat == actual_goal_stat or stat == goal_stat:
                        matched_goal = target
                        break
                
                if matched_goal is not None:
                    # For percentage-based stats, don't apply penalty - let the base value handle it
                    if is_percentage_stat:
                        # Give moderate weight for percentage stats
                        score += value * 1.5
                    else:
                        # Prioritize reaching goals, but penalize going over for rating stats
                        current_value = current_stats.get(stat, 0)
                        target = matched_goal
                        if current_value < target:
                            # Higher score for stats that help reach goals
                            score += value * 2
                        elif current_value + value <= target:
                            # Still beneficial if not exceeding goal
                            score += value * 1.5
                        else:
                            # Penalize going over goal (opportunity cost)
                            excess = (current_value + value) - target
                            score += value - (excess * 2)  # Moderate penalty for excess
                elif stat in stats_without_goals:
                    # Secondary priority
                    score += value
            
            if score > best_essence_score:
                best_essence_score = score
                best_essence_idx = essence_idx
        
        if best_essence_idx is not None:
            best_combination.append(best_essence_idx)
            essence = items_per_type["Essence"][best_essence_idx]
            essence_name = essence["Name"]
            essence_counts[essence_name] = essence_counts.get(essence_name, 0) + 1
            
            # Update current stats
            for stat, value in essence["Stats"].items():
                current_stats[stat] = current_stats.get(stat, 0) + value
    
    # Evaluate the final combination
    result = process_combination(tuple(best_combination), item_types, items_per_type,
                                 character_stats, character_class_stats, stats_rcap,
                                 requirements_ratings, True, essence_quantity_limits)
    
    return result

def find_optimal_combination_simulated_annealing(item_types, items_per_type, items_ids,
                                                   character_stats, character_class_stats, stats_rcap, requirements_ratings,
                                                   essence_quantity_limits, stat_requirements, character_level, character_armour):
    """
    Simulated annealing algorithm for essence optimization.
    Uses custom fitness function that penalizes stats exceeding goal values.
    """
    import random
    import math
    
    # Separate stats with goals and without goals
    stats_with_goals = {}
    stats_without_goals = set()
    if stat_requirements:
        for req in stat_requirements:
            if '=' in req:
                stat_name, target = req.split('=')
                stats_with_goals[stat_name] = float(target)
            else:
                stats_without_goals.add(req)
    
    def custom_fitness(combination):
        """Custom fitness function that penalizes exceeding goal values."""
        # Get base result
        result = process_combination(combination, item_types, items_per_type,
                                     character_stats, character_class_stats, stats_rcap,
                                     requirements_ratings, True, essence_quantity_limits)
        base_value = result[1]
        final_stats = result[4]
        
        # Apply penalty for stats exceeding goals
        penalty = 0
        for stat, target in stats_with_goals.items():
            # Map stat name to actual stat name if needed
            actual_stat = stat
            if stat in FINAL_STATS:
                actual_stat = FINAL_STATS[stat]
            
            # Check if this stat is a tertiary stat that needs to be summed from secondary stats
            if actual_stat in TERTIARY2SECONDARY_MAPPING:
                # Sum all secondary stats that contribute to this tertiary stat
                total_value = 0
                for sec_stat, tert_stats in SECONDARY2TERTIARY_MAPPING.items():
                    if actual_stat in tert_stats:
                        total_value += final_stats.get(sec_stat, 0)
                current_value = total_value
            else:
                current_value = final_stats.get(actual_stat, 0)
            
            # For final stats (percentage-based), the target is already in percentage
            # We need to check if the current rating would exceed the target percentage
            # For now, skip penalty for percentage-based stats as the conversion is complex
            # The base value already handles this via requirements_ratings
            if actual_stat not in FINAL_STATS.values():
                # Only apply penalty for non-percentage stats
                if current_value > target:
                    excess = current_value - target
                    penalty += excess * 2  # Moderate penalty for exceeding goal
        
        return base_value - penalty, result
    
    # Initialize with random combination
    num_slots = len(item_types)
    num_essences = len(items_per_type["Essence"])
    
    current_combination = tuple(random.randint(0, num_essences - 1) for _ in range(num_slots))
    
    # Validate initial combination
    while not validate_essence_quantities(current_combination, item_types, items_per_type, essence_quantity_limits):
        current_combination = tuple(random.randint(0, num_essences - 1) for _ in range(num_slots))
    
    # Evaluate initial combination
    current_value, current_result = custom_fitness(current_combination)
    
    best_combination = current_combination
    best_value = current_value
    best_result = current_result
    
    # Simulated annealing parameters
    initial_temp = 1000.0
    cooling_rate = 0.995
    min_temp = 0.1
    iterations_per_temp = 100
    
    temp = initial_temp
    
    while temp > min_temp:
        for _ in range(iterations_per_temp):
            # Generate neighbor by swapping one essence
            neighbor = list(current_combination)
            swap_idx = random.randint(0, num_slots - 1)
            new_essence_idx = random.randint(0, num_essences - 1)
            neighbor[swap_idx] = new_essence_idx
            neighbor = tuple(neighbor)
            
            # Validate neighbor
            if not validate_essence_quantities(neighbor, item_types, items_per_type, essence_quantity_limits):
                continue
            
            # Evaluate neighbor
            neighbor_value, neighbor_result = custom_fitness(neighbor)
            
            # Accept or reject
            if neighbor_value > current_value:
                current_combination = neighbor
                current_value = neighbor_value
                current_result = neighbor_result
                
                if neighbor_value > best_value:
                    best_combination = neighbor
                    best_value = neighbor_value
                    best_result = neighbor_result
            else:
                delta = neighbor_value - current_value
                probability = math.exp(delta / temp)
                if random.random() < probability:
                    current_combination = neighbor
                    current_value = neighbor_value
                    current_result = neighbor_result
        
        temp *= cooling_rate
    
    return best_result

def find_optimal_combination_ilp(item_types, items_per_type, items_ids,
                                  character_stats, character_class_stats, stats_rcap, requirements_ratings,
                                  essence_quantity_limits, stat_requirements, character_level, character_armour):
    """
    Integer Linear Programming using pulp for essence optimization.
    """
    try:
        import pulp
    except ImportError:
        print("pulp library not found. Please install it with: pip install pulp")
        return None, -1, {}, 0, {}
    
    num_slots = len(item_types)
    num_essences = len(items_per_type["Essence"])
    
    # Create problem
    prob = pulp.LpProblem("EssenceOptimization", pulp.LpMaximize)
    
    # Decision variables: x[i][j] = 1 if essence j is in slot i
    x = pulp.LpVariable.dicts("x", [(i, j) for i in range(num_slots) for j in range(num_essences)], 
                             cat='Binary')
    
    # Constraint: each slot must have exactly one essence
    for i in range(num_slots):
        prob += pulp.lpSum(x[(i, j)] for j in range(num_essences)) == 1
    
    # Constraint: respect quantity limits
    for j, essence in enumerate(items_per_type["Essence"]):
        essence_name = essence["Name"]
        quantity_limit = essence_quantity_limits.get(essence_name, -1)
        if quantity_limit != -1:
            prob += pulp.lpSum(x[(i, j)] for i in range(num_slots)) <= quantity_limit
    
    # Objective: maximize combination value
    # Simplified objective: sum of stat contributions weighted by requirements
    objective = 0
    
    # Get stats with goals (higher weight)
    stats_with_goals = {}
    stats_without_goals = set()
    if stat_requirements:
        for req in stat_requirements:
            if '=' in req:
                stat_name, target = req.split('=')
                stats_with_goals[stat_name] = float(target)
            else:
                stats_without_goals.add(req)
    
    for i in range(num_slots):
        for j, essence in enumerate(items_per_type["Essence"]):
            essence_value = 0
            for stat, value in essence["Stats"].items():
                if stat in stats_with_goals:
                    # Penalize going over goal - simplified for ILP
                    # Since ILP is linear, we use a lower weight for goal stats
                    essence_value += value * 1.2  # Moderate weight for goal stats
                elif stat in stats_without_goals:
                    essence_value += value * 1.5  # Higher weight for non-goal stats (to maximize them)
                else:
                    essence_value += value
            objective += essence_value * x[(i, j)]
    
    prob += objective
    
    # Solve
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    
    if pulp.LpStatus[prob.status] != 'Optimal':
        print("No optimal solution found")
        return None, -1, {}, 0, {}
    
    # Extract solution
    best_combination = []
    for i in range(num_slots):
        for j in range(num_essences):
            if pulp.value(x[(i, j)]) == 1:
                best_combination.append(j)
                break
    
    best_combination = tuple(best_combination)
    
    # Evaluate the solution
    result = process_combination(best_combination, item_types, items_per_type,
                                 character_stats, character_class_stats, stats_rcap,
                                 requirements_ratings, True, essence_quantity_limits)
    
    return result
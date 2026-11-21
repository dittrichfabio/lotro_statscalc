import os
import re
import sys
import copy
import json
import math
import itertools

STAT= re.compile(r'\["(.*?)"] = (.*?)[,\n]')
char_stat_sorting_order = [
    # Primary stats
    "Armour",
    "Morale",
    "InCombatMoraleRegeneration",
    "NonCombatMoraleRegeneration",
    "Power",
    "InCombatPowerRegeneration",
    "NonCombatPowerRegeneration",
    # Main stats
    "Might",
    "Agility",
    "Vitality",
    "Will",
    "Fate",
    # Critical ratings
    "CriticalRatingMelee",
    "CriticalRatingRange",
    "CriticalRatingTactical",
    "DevastatingRatingMelee",
    "DevastatingRatingRange",
    "DevastatingRatingTactical",
    "CriticalMagnitudeRatingMelee",
    "CriticalMagnitudeRatingRange",
    "CriticalMagnitudeRatingTactical",
    # Mastery ratings
    "FinesseRating",
    "PhysicalMasteryRatingMelee",
    "PhysicalMasteryRatingRange",
    "TacticalMasteryRating",
    "OutgoingHealingRating",
    # Defence ratings
    "ResistanceRating",
    "CriticalDefenceRating",
    "IncomingHealingRating",
    # Avoidance ratings
    "BlockChanceRating",
    "PartialBlockChanceRating",
    "PartialBlockMitigationRating",
    "ParryChanceRating",
    "PartialParryChanceRating",
    "PartialParryMitigationRating",
    "EvadeChanceRating",
    "PartialEvadeChanceRating",
    "PartialEvadeMitigationRating",
    # Mitigation ratings
    "PhysicalMitigationRating",
    "TacticalMitigationRating"
]

#Plugins data
DEFAULT_PLUGIN_SERVER = "Angmar"
DEFAULT_PLUGIN_USERNAME = "ddmdarklink"
plugin_char_path = os.path.join("/", "mnt", "c", "Users", "fabio_dittrich", "Documents", "The Lord of the Rings Online", "PluginData", "{username}", "{server}", "{character_name}")

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
VIRTUE_STATS = json.load(open(os.path.join(STATSCALC, "resources", "stat_files", "virtue_stats.json")))

# =============================================================================
# STAT HIERARCHY
# =============================================================================
# Stats are organized in a hierarchy:
# - Main stats: Base attributes that contribute to secondary stats based on class
# - Secondary stats: Can be found on gear, contribute to tertiary stats
# - Tertiary stats: Derived from secondary stats, cannot be found on gear
# - Final stats: Percentage-based values computed from rating stats

# Main stats - these contribute to different stats depending on class
# (Class-specific contributions are defined in classes_stats.json)
MAIN_STATS = ["Might", "Agility", "Vitality", "Will", "Fate"]

# Secondary stats - can be found on gear
SECONDARY_STATS = [
    # Primary stats
    "Armour",
    "Morale",
    "Power",
    # Regeneration stats
    "InCombatMoraleRegeneration",
    "NonCombatMoraleRegeneration",
    "InCombatPowerRegeneration",
    "NonCombatPowerRegeneration",
    # Rating stats
    "CriticalRating",
    "FinesseRating",
    "PhysicalMasteryRating",
    "TacticalMasteryRating",
    "OutgoingHealingRating",
    "ResistanceRating",
    "WoundResistanceRating",
    "FearResistanceRating",
    "DiseaseResistanceRating",
    "PoisonResistanceRating",
    "CriticalDefenceRating",
    "IncomingHealingRating",
    "BlockChanceRating",
    "ParryChanceRating",
    "EvadeChanceRating",
    "PhysicalMitigationRating",
    "TacticalMitigationRating",
]

# Tertiary stats - derived from secondary stats, cannot be found on gear
TERTIARY_STATS = [
    # Critical rating breakdown
    "CriticalRatingMelee",
    "DevastatingRatingMelee",
    "CriticalMagnitudeRatingMelee",
    "CriticalRatingRange",
    "DevastatingRatingRange",
    "CriticalMagnitudeRatingRange",
    "CriticalRatingTactical",
    "DevastatingRatingTactical",
    "CriticalMagnitudeRatingTactical",
    # Physical mastery breakdown
    "PhysicalMasteryRatingMelee",
    "PhysicalMasteryRatingRange",
    # Avoidance breakdown
    "BlockChanceRating",
    "PartialBlockChanceRating",
    "PartialBlockMitigationRating",
    "ParryChanceRating",
    "PartialParryChanceRating",
    "PartialParryMitigationRating",
    "EvadeChanceRating",
    "PartialEvadeChanceRating",
    "PartialEvadeMitigationRating",
    # Resistance breakdown
    "WoundResistanceRating",
    "FearResistanceRating",
    "DiseaseResistanceRating",
    "PoisonResistanceRating"
]

# Mapping from secondary stats to their tertiary stat components
SECONDARY2TERTIARY_MAPPING = {
    "CriticalRating": [
        "CriticalRatingMelee",
        "CriticalRatingRange",
        "CriticalRatingTactical",
        "DevastatingRatingMelee",
        "DevastatingRatingRange",
        "DevastatingRatingTactical",
        "CriticalMagnitudeRatingMelee",
        "CriticalMagnitudeRatingRange",
        "CriticalMagnitudeRatingTactical"
    ],
    "PhysicalMasteryRating": [
        "PhysicalMasteryRatingMelee",
        "PhysicalMasteryRatingRange"
    ],
    "BlockChanceRating": [
        "BlockChanceRating",
        "PartialBlockChanceRating",
        "PartialBlockMitigationRating"
    ],
    "ParryChanceRating": [
        "ParryChanceRating",
        "PartialParryChanceRating",
        "PartialParryMitigationRating"
    ],
    "EvadeChanceRating": [
        "EvadeChanceRating",
        "PartialEvadeChanceRating",
        "PartialEvadeMitigationRating"
    ],
    "ResistanceRating": [
        "ResistanceRating",
        "WoundResistanceRating",
        "FearResistanceRating",
        "DiseaseResistanceRating",
        "PoisonResistanceRating"
    ]
}

# For tertiary stats absent from the character JSON, maps each one to the existing
# stat it should inherit its base value from (same combat-type variant).
TERTIARY_STAT_BASE_MAP = {
    "DevastatingRatingMelee":          "CriticalRatingMelee",
    "CriticalMagnitudeRatingMelee":    "CriticalRatingMelee",
    "DevastatingRatingRange":          "CriticalRatingRange",
    "CriticalMagnitudeRatingRange":    "CriticalRatingRange",
    "DevastatingRatingTactical":       "CriticalRatingTactical",
    "CriticalMagnitudeRatingTactical": "CriticalRatingTactical",
    "PartialBlockChanceRating":        "BlockChanceRating",
    "PartialBlockMitigationRating":    "BlockChanceRating",
    "PartialParryChanceRating":        "ParryChanceRating",
    "PartialParryMitigationRating":    "ParryChanceRating",
    "PartialEvadeChanceRating":        "EvadeChanceRating",
    "PartialEvadeMitigationRating":    "EvadeChanceRating",
    "WoundResistanceRating":           "ResistanceRating",
    "FearResistanceRating":            "ResistanceRating",
    "DiseaseResistanceRating":         "ResistanceRating",
    "PoisonResistanceRating":          "ResistanceRating",
}

# Reverse mapping from tertiary to secondary stats
TERTIARY2SECONDARY_MAPPING = {
    tstat: stat
    for stat in SECONDARY2TERTIARY_MAPPING
    for tstat in SECONDARY2TERTIARY_MAPPING[stat]
}

# Final stats - percentage-based values computed from rating stats
# Maps final stat name to its associated rating stat (empty string if no rating)
FINAL_STATS = {
    # Critical hit chances and magnitudes
    "CriticalHitChanceMelee": "CriticalRatingMelee",
    "DevastatingHitChanceMelee": "DevastatingRatingMelee",
    "Critical&DevastatingHitMagnitudeMelee": "CriticalMagnitudeRatingMelee",
    "CriticalHitChanceRange": "CriticalRatingRange",
    "DevastatingHitChanceRange": "DevastatingRatingRange",
    "Critical&DevastatingHitMagnitudeRange": "CriticalMagnitudeRatingRange",
    "CriticalHitChanceTactical": "CriticalRatingTactical",
    "DevastatingHitChanceTactical": "DevastatingRatingTactical",
    "Critical&DevastatingHitMagnitudeTactical": "CriticalMagnitudeRatingTactical",
    # Finesse
    "Finesse": "FinesseRating",
    # Physical damage
    "PhysicalDamageMelee": "PhysicalMasteryRatingMelee",
    "PhysicalDamageRange": "PhysicalMasteryRatingRange",
    # Tactical offence and healing
    "TacticalOffenceDamage": "TacticalMasteryRating",
    "TacticalOutgoingHealing": "OutgoingHealingRating",
    # Resistance and defence
    "Resistance": "ResistanceRating",
    "WoundResistance":    "WoundResistanceRating",
    "FearResistance":     "FearResistanceRating",
    "DiseaseResistance":  "DiseaseResistanceRating",
    "PoisonResistance":   "PoisonResistanceRating",
    "CriticalDefenceMelee": "CriticalDefenceRating",
    "CriticalDefenceRanged": "CriticalDefenceRating",
    "CriticalDefenceTactical": "CriticalDefenceRating",
    "IncomingHealing": "IncomingHealingRating",
    # Avoidance
    "BlockChance": "BlockChanceRating",
    "PartialBlockChance": "PartialBlockChanceRating",
    "PartialBlockMitigation": "PartialBlockMitigationRating",
    "ParryChance": "ParryChanceRating",
    "PartialParryChance": "PartialParryChanceRating",
    "PartialParryMitigation": "PartialParryMitigationRating",
    "EvadeChance": "EvadeChanceRating",
    "PartialEvadeChance": "PartialEvadeChanceRating",
    "PartialEvadeMitigation": "PartialEvadeMitigationRating",
    # Mitigation
    "PhysicalMitigation": "PhysicalMitigationRating",
    "OrcCraftMitigation": "PhysicalMitigationRating",
    "FellWroughtMitigation": "PhysicalMitigationRating",
    "TacticalMitigation": "TacticalMitigationRating",
    "FireMitigation": "TacticalMitigationRating",
    "LightningMitigation": "TacticalMitigationRating",
    "FrostMitigation": "TacticalMitigationRating",
    "AcidMitigation": "TacticalMitigationRating",
    "ShadowMitigation": "TacticalMitigationRating"
}

# Add main stats and direct stats (no rating conversion)
FINAL_STATS.update({stat: "" for stat in MAIN_STATS})
FINAL_STATS.update({
    "Armour": "",
    "Morale": "",
    "InCombatMoraleRegeneration": "",
    "NonCombatMoraleRegeneration": "",
    "Power": "",
    "InCombatPowerRegeneration": "",
    "NonCombatPowerRegeneration": ""
})

# Reverse mapping from rating to final stats
RATING2PERCENTAGE_FINAL_STATS = {
    FINAL_STATS[stat]: stat
    for stat in FINAL_STATS
    if FINAL_STATS[stat]
}

# All valid stats across all tiers
VALID_STATS = list(set(MAIN_STATS + SECONDARY_STATS + TERTIARY_STATS + list(FINAL_STATS.keys())))
# Valid stats for gear/essence/buff entries (only main and secondary stats can appear on items)
VALID_ITEM_STATS = set(MAIN_STATS + SECONDARY_STATS + list(FINAL_STATS.keys()))
VALID_ITEM_MAX_QUANTITY = {"Boots": 1,  "Chest": 1,  "Gloves": 1,  "Helm": 1,  "Leggings": 1,  "Shoulders": 1,  "Back": 1,  "Ring": 2,  "Earring": 2,  "Bracelet": 2,  "Necklace": 1,  "Pocket": 1, "Essence": 999, "Virtue": 5}
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
    for tertiary_list in SECONDARY2TERTIARY_MAPPING.values():
        for tstat in tertiary_list:
            base_stat = TERTIARY_STAT_BASE_MAP.get(tstat)
            if tstat not in new_stats:
                new_stats[tstat] = new_stats.get(base_stat, 0) if base_stat else 0
            elif base_stat and tstat in SECONDARY_STATS:
                new_stats[tstat] += new_stats.get(base_stat, 0)
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
                    contribution = math.floor(item_stats[item_stat] * character_class_stats[item_stat][secondary_stat])
                    if secondary_stat in SECONDARY2TERTIARY_MAPPING:
                        for tertiary_stat in SECONDARY2TERTIARY_MAPPING[secondary_stat]:
                            new_stats[tertiary_stat] += contribution
                    else:
                        new_stats[secondary_stat] += contribution
            # Convert Armour to mitigation ratings
            if item_stat == "Armour":
                new_stats["PhysicalMitigationRating"] += item_stats[item_stat]
                new_stats["TacticalMitigationRating"] += math.floor(item_stats[item_stat] * 0.2)
    return new_stats

def compute_percentage(base_stats, character_armour, character_level, extra_stats):
    level_index = lvl_index(character_level)
    computed_stats = {i:0 for i in FINAL_STATS}
    overcapped_stats = {}
    for stat in computed_stats:
        stat_info = STATS_INFO[get_stats_info_key(stat, character_armour)]
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
    stat_info = STATS_INFO[get_stats_info_key(stat_name, character_armour)]
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

def prepare_optimization_choices(gear_file, optimization_choices, virtues_items=None):
    gear_json = json.load(open(gear_file))
    available_items = gear_json.get("available_items", [])
    
    # Load essences from separate file or from unified gear file
    available_essences = []
    if "available_essences" in gear_json:
        available_essences = gear_json["available_essences"]
    
    # Validate essences are available if Essence is in items_to_pick
    if "Essence" in optimization_choices and optimization_choices["Essence"] > 0:
        if not available_essences:
            print(f"Essence is in items_to_pick but no essences were found. Aborting!")
            sys.exit(1)

    items_per_type = {}
    for item in optimization_choices:
        if item not in VALID_ITEM_TYPES:
            print(f"Item {item} is invalid. Valid types: {VALID_ITEM_TYPES}. Aborting!")
            sys.exit(1)
        if optimization_choices[item] > VALID_ITEM_MAX_QUANTITY[item]:
            print(f"Item {item} can have a max of {VALID_ITEM_MAX_QUANTITY[item]}, but {optimization_choices[item]} were requested. Aborting!")
            sys.exit(1)

    items_per_type = {i:[] for i in optimization_choices}
    items_ids = {i:[] for i in optimization_choices}
    
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
            if stat not in VALID_ITEM_STATS:
                print(f"Stat '{stat}' of '{item_name}' is not a valid main or secondary stat. Aborting!")
                sys.exit(1)

        if item_type in optimization_choices:
            if optimization_choices[item_type] != 0:
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
            if stat not in VALID_ITEM_STATS:
                print(f"Stat '{stat}' of '{essence_name}' is not a valid main or secondary stat. Aborting!")
                sys.exit(1)
        
        # Track quantity limits for each essence
        essence_quantity_limits[essence_name] = quantity_available
        
        if "Essence" in optimization_choices and optimization_choices["Essence"] != 0:
            if items_per_type["Essence"] == []:
                items_per_type["Essence"] = [{"Name": essence_name, "Stats": essence_stats}]
            else:
                items_per_type["Essence"].append({"Name": essence_name, "Stats": essence_stats})
            if items_ids["Essence"] == []:
                items_ids["Essence"].append(0)
            else:
                items_ids["Essence"].append(items_ids["Essence"][-1]+1)
    
    # Process virtues from virtues_items (if provided)
    if virtues_items is not None:
        for virtue in virtues_items:
            virtue_name = virtue.get("Name", False)
            virtue_type = virtue.get("Type", "Unset")
            virtue_stats = virtue.get("Stats", False)
            quantity_available = virtue.get("QuantityAvailable", -1)
            
            if not virtue_name:
                print(f"Missing name for virtue {virtue}. Aborting!")
                sys.exit(1)
            if virtue_type != "Virtue":
                print(f"Type {virtue_type} of {virtue_name} is not Virtue. Aborting!")
                sys.exit(1)
            for stat in virtue_stats:
                if stat not in VALID_STATS:
                    print(f"Stat {stat} of {virtue_name} is not valid. Aborting!")
                    sys.exit(1)
            
            # Track quantity limits for each virtue (enforce no duplicates)
            essence_quantity_limits[virtue_name] = quantity_available
            
            if "Virtue" in optimization_choices and optimization_choices["Virtue"] != 0:
                if items_per_type["Virtue"] == []:
                    items_per_type["Virtue"] = [{"Name": virtue_name, "Stats": virtue_stats, "Rank": virtue.get("Rank")}]
                else:
                    items_per_type["Virtue"].append({"Name": virtue_name, "Stats": virtue_stats, "Rank": virtue.get("Rank")})
                if items_ids["Virtue"] == []:
                    items_ids["Virtue"].append(0)
                else:
                    items_ids["Virtue"].append(items_ids["Virtue"][-1]+1)
    
    # Validate that each item type in optimization_choices has available items
    for item_type in optimization_choices:
        if optimization_choices[item_type] > 0 and not items_per_type[item_type]:
            print(f"Item type '{item_type}' is in optimization_choices but no available items were found. Aborting!")
            sys.exit(1)
    
    expanded_items_ids = {}
    for item in optimization_choices:
        for i in range(1, optimization_choices[item]+1):
            expanded_items_ids[f"{item}#{i}"] = items_ids[item]

    return items_per_type, expanded_items_ids, essence_quantity_limits

# Maps final stat names that differ from their stats_info.json key to the correct key.
# Stats that share an entry (e.g. all CriticalDefence variants, element mitigations)
# are redirected here; the armour-prefix logic for Mitigation stats is applied after.
STATS_INFO_KEY_OVERRIDES = {
    "CriticalDefenceMelee":    "CriticalDefence",
    "CriticalDefenceRanged":   "CriticalDefence",
    "CriticalDefenceTactical": "CriticalDefence",
    "OrcCraftMitigation":      "PhysicalMitigation",
    "FellWroughtMitigation":   "PhysicalMitigation",
    "FireMitigation":          "TacticalMitigation",
    "LightningMitigation":     "TacticalMitigation",
    "FrostMitigation":         "TacticalMitigation",
    "AcidMitigation":          "TacticalMitigation",
    "ShadowMitigation":        "TacticalMitigation",
    "WoundResistance":         "Resistance",
    "FearResistance":          "Resistance",
    "DiseaseResistance":       "Resistance",
    "PoisonResistance":        "Resistance",
}

def get_stats_info_key(fstat, character_armour):
    key = STATS_INFO_KEY_OVERRIDES.get(fstat, fstat)
    if key in ["PhysicalMitigation", "TacticalMitigation"]:
        return f"{character_armour}{key}"
    return key

def get_all_stats_Rcap(character_level, character_armour):
    level_index = lvl_index(character_level)
    stats_rcap = {}
    for fstat in FINAL_STATS:
        if FINAL_STATS[fstat]:
            stat_info = STATS_INFO[get_stats_info_key(fstat, character_armour)]
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
            if fstat in ["Morale"]:
                target_key, target_value = fstat, percentage
            elif fstat in SECONDARY_STATS:
                if fstat in SECONDARY2TERTIARY_MAPPING:
                    tertiary_examples = SECONDARY2TERTIARY_MAPPING[fstat]
                    print(f"Stat '{fstat}' distributes to multiple tertiary stats and cannot be used as a direct rating requirement. Use a specific tertiary stat instead (e.g. '{tertiary_examples[0]}') or a final stat percentage. Aborting!")
                    sys.exit(1)
                target_key, target_value = fstat, percentage
            elif fstat in TERTIARY_STATS:
                target_key, target_value = fstat, percentage
            else:
                stat_info = STATS_INFO[get_stats_info_key(fstat, character_armour)]
                a = stat_info["A"]
                b = BRating(bs=stat_info["BStart"][level_index], be=stat_info["BEnd"][level_index], l=character_level, le=stat_info["LEnd"][level_index], ls=stat_info["LStart"][level_index])
                target_key, target_value = FINAL_STATS[fstat], RfromP(p=percentage, a=a, b=b)
        elif FINAL_STATS[fstat]:
            target_key, target_value = FINAL_STATS[fstat], -1
        else:
            target_key, target_value = fstat, -1
        if target_key in requirements_ratings and requirements_ratings[target_key] != target_value:
            existing = requirements_ratings[target_key]
            if existing == -1:
                kept = target_value
            elif target_value == -1:
                kept = existing
            else:
                kept = max(existing, target_value)
            print(f"Warning: '{r}' conflicts with a previous requirement — both target '{target_key}'. Keeping higher value: {kept}.")
            requirements_ratings[target_key] = kept
        else:
            requirements_ratings[target_key] = target_value
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
    uncapped_stats = equip_items(character_stats, character_class_stats, combination_items)
    #print(uncapped_stats)
    overcap_value = 0
    overcapped_stats = {}
    new_stats = uncapped_stats.copy()
    for stat in new_stats:
        if stat in stats_rcap:
            effective_cap = max(stats_rcap[stat], requirements_ratings.get(stat, 0))
            secondary = TERTIARY2SECONDARY_MAPPING.get(stat)
            if secondary is not None:
                for sibling in SECONDARY2TERTIARY_MAPPING.get(secondary, []):
                    effective_cap = max(effective_cap, requirements_ratings.get(sibling, 0))
            if new_stats[stat] > effective_cap:
                #print("!!!!")
                #print(stat)
                #print(new_stats[stat])
                #print(stats_rcap[stat])
                secondary_stat = TERTIARY2SECONDARY_MAPPING.get(stat, "use_normal_stat")
                if secondary_stat == "use_normal_stat":
                    overcapped_stats[stat] = (new_stats[stat] - effective_cap)
                    overcap_value += (new_stats[stat] - effective_cap)
                elif secondary_stat not in overcapped_stats:
                    overcapped_stats[secondary_stat] = (new_stats[stat] - effective_cap)
                    overcap_value += (new_stats[stat] - effective_cap)
                new_stats[stat] = effective_cap
    #print(new_stats)
    combination_value = define_combination_value(new_stats, requirements_ratings)
    if penalize_overcapping:
        combination_value -= overcap_value
    #print("=====")
    #print(overcap)
    #print(combination_value)
    return (combination, combination_value, overcapped_stats, overcap_value, new_stats, uncapped_stats)

def resolve_virtue_items(virtues_dict):
    """
    Convert a virtues dict (e.g., {"Honour": 20, "Valour": 18}) to a list of virtue items
    with stats resolved from VIRTUE_STATS. Each virtue is treated as an item with Type="Virtue"
    and QuantityAvailable=1 (no duplicates allowed).
    """
    virtue_items = []
    for virtue_name, rank in virtues_dict.items():
        if virtue_name not in VIRTUE_STATS:
            print(f"Virtue {virtue_name} not found in VIRTUE_STATS. Skipping.")
            continue
        rank_str = str(rank)
        if rank_str not in VIRTUE_STATS[virtue_name]:
            print(f"Rank {rank} not found for virtue {virtue_name}. Skipping.")
            continue
        
        virtue_stats = VIRTUE_STATS[virtue_name][rank_str]
        virtue_items.append({
            "Name": virtue_name,
            "Type": "Virtue",
            "QuantityAvailable": 1,
            "Stats": virtue_stats,
            "Rank": rank
        })
    return virtue_items

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
        stats_to_print = None
    
    optimization_choices = preferred_stats.get("optimization_choices")

    return stat_requirements, stats_to_print, optimization_choices

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

def find_optimal_combination_ilp(item_types, items_per_type, items_ids,
                                  character_stats, character_class_stats, stats_rcap, requirements_ratings,
                                  essence_quantity_limits, stat_requirements, character_level, character_armour):
    """
    Integer Linear Programming using pulp for gear/essence optimization.

    Stat requirements are converted to required ratings via RfromP before this function
    is called (see get_ratings_for_requirements). The optimization is therefore entirely
    linear in rating space — no piecewise approximation is needed.

    Hard constraints enforce minimum ratings from requirements_ratings.
    The objective maximizes capped total ratings (matching the stats_rcap cap logic).
    """
    try:
        import pulp
    except ImportError:
        print("pulp library not found. Please install it with: pip install pulp")
        return None, -1, {}, 0, {}, {}

    # Stats we care about: those in requirements_ratings, or all character stats if none defined
    if requirements_ratings:
        opt_stats = set(requirements_ratings.keys())
    else:
        opt_stats = set(character_stats.keys())

    # Separate virtue slots from gear/essence slots to avoid symmetry issues in ILP
    virtue_slot_indices = [i for i, t in enumerate(item_types) if t == "Virtue"]
    n_virtue_slots = len(virtue_slot_indices)

    # Pre-compute each non-virtue item's contribution to each opt_stat
    slot_item_contrib = []
    for i, t in enumerate(item_types):
        if t == "Virtue":
            slot_item_contrib.append([])
            continue
        item_contribs = []
        for item in items_per_type[t]:
            contrib = {s: 0.0 for s in opt_stats}
            for item_stat, value in item["Stats"].items():
                if item_stat in SECONDARY2TERTIARY_MAPPING:
                    for tertiary_stat in SECONDARY2TERTIARY_MAPPING[item_stat]:
                        if tertiary_stat in contrib:
                            contrib[tertiary_stat] += value
                else:
                    if item_stat in contrib:
                        contrib[item_stat] += value
                if item_stat in MAIN_STATS:
                    for secondary_stat, multiplier in character_class_stats[item_stat].items():
                        if secondary_stat in contrib:
                            contrib[secondary_stat] += math.floor(value * multiplier)
                # Convert Armour to mitigation ratings
                if item_stat == "Armour":
                    if "PhysicalMitigationRating" in contrib:
                        contrib["PhysicalMitigationRating"] += value
                    if "TacticalMitigationRating" in contrib:
                        contrib["TacticalMitigationRating"] += math.floor(value * 0.2)
            item_contribs.append(contrib)
        slot_item_contrib.append(item_contribs)

    # Pre-compute each virtue's contribution to each opt_stat
    virtue_contrib = []
    if n_virtue_slots and "Virtue" in items_per_type:
        for virtue in items_per_type["Virtue"]:
            contrib = {s: 0.0 for s in opt_stats}
            for item_stat, value in virtue["Stats"].items():
                if item_stat in SECONDARY2TERTIARY_MAPPING:
                    for tertiary_stat in SECONDARY2TERTIARY_MAPPING[item_stat]:
                        if tertiary_stat in contrib:
                            contrib[tertiary_stat] += value
                else:
                    if item_stat in contrib:
                        contrib[item_stat] += value
                if item_stat in MAIN_STATS:
                    for secondary_stat, multiplier in character_class_stats[item_stat].items():
                        if secondary_stat in contrib:
                            contrib[secondary_stat] += math.floor(value * multiplier)
                # Convert Armour to mitigation ratings
                if item_stat == "Armour":
                    if "PhysicalMitigationRating" in contrib:
                        contrib["PhysicalMitigationRating"] += value
                    if "TacticalMitigationRating" in contrib:
                        contrib["TacticalMitigationRating"] += math.floor(value * 0.2)
            virtue_contrib.append(contrib)

    prob = pulp.LpProblem("GearOptimization", pulp.LpMaximize)

    # Decision variables: x[(i, j)] = 1 if non-virtue slot i uses item j
    x = {}
    for i, t in enumerate(item_types):
        if t == "Virtue":
            continue
        for j in range(len(items_per_type[t])):
            x[(i, j)] = pulp.LpVariable(f"x_{i}_{j}", cat='Binary')

    # Virtue variables: y[j] = 1 if virtue j is selected (avoids slot symmetry)
    y = {}
    if n_virtue_slots and "Virtue" in items_per_type:
        for j in range(len(items_per_type["Virtue"])):
            y[j] = pulp.LpVariable(f"y_{j}", cat='Binary')

    # Constraint: each non-virtue slot has exactly one item
    for i, t in enumerate(item_types):
        if t == "Virtue":
            continue
        prob += pulp.lpSum(x[(i, j)] for j in range(len(items_per_type[t]))) == 1

    # Constraint: pick exactly n_virtue_slots virtues (replaces per-slot virtue constraints)
    if y:
        prob += pulp.lpSum(y[j] for j in y) == n_virtue_slots

    # Constraint: essence quantity limits
    essence_slots = [i for i, t in enumerate(item_types) if t == "Essence"]
    if essence_slots:
        for j, item in enumerate(items_per_type["Essence"]):
            item_name = item["Name"]
            quantity_limit = essence_quantity_limits.get(item_name, -1)
            if quantity_limit != -1:
                prob += pulp.lpSum(x[(i, j)] for i in essence_slots) <= quantity_limit

    # Compute total rating per stat as an LP affine expression
    total_rating = {}
    for stat in opt_stats:
        base = character_stats.get(stat, 0.0)
        gear_contrib = pulp.lpSum(
            slot_item_contrib[i][j][stat] * x[(i, j)]
            for i, t in enumerate(item_types)
            if t != "Virtue"
            for j in range(len(items_per_type[t]))
        )
        virtue_total = pulp.lpSum(
            virtue_contrib[j][stat] * y[j]
            for j in y
        ) if y else 0
        total_rating[stat] = base + gear_contrib + virtue_total

    # Hard constraints: minimum required ratings
    for stat, req in requirements_ratings.items():
        if req != -1 and stat in total_rating:
            prob += total_rating[stat] >= req

    # Pre-compute maximum possible contribution per stat from all item slots.
    # Used to bound the objective for stats that have no explicit rcap, preventing
    # an unbounded LP relaxation which causes slow B&B convergence.
    max_item_contrib = {stat: 0.0 for stat in opt_stats}
    for i, t in enumerate(item_types):
        if t == "Virtue" or not items_per_type[t]:
            continue
        for stat in opt_stats:
            max_item_contrib[stat] += max(
                slot_item_contrib[i][j].get(stat, 0.0) for j in range(len(items_per_type[t]))
            )
    if y and virtue_contrib:
        for stat in opt_stats:
            top_virtue_contribs = sorted(
                (vc.get(stat, 0.0) for vc in virtue_contrib), reverse=True
            )[:n_virtue_slots]
            max_item_contrib[stat] += sum(top_virtue_contribs)

    # Auxiliary continuous variables for capped totals used in objective.
    # For stats with a hard minimum requirement: cap at the requirement — no benefit to overshoot.
    # For unconstrained stats (req == -1): cap at stats_rcap if available, otherwise cap at the
    # maximum achievable value from items. This keeps the LP relaxation tight and avoids slow B&B.
    cap_var = {}
    for stat in opt_stats:
        req = requirements_ratings.get(stat, -1)
        if req != -1:
            obj_cap = req
        elif stat in stats_rcap:
            obj_cap = stats_rcap[stat]
        else:
            obj_cap = character_stats.get(stat, 0.0) + max_item_contrib[stat]
            print(f"ILP: no rcap for {stat}, using computed cap {obj_cap} (base {character_stats.get(stat, 0.0)} + max items {max_item_contrib[stat]})")

        v = pulp.LpVariable(f"cap_{stat}", lowBound=0)
        prob += v <= total_rating[stat]
        prob += v <= obj_cap
        cap_var[stat] = v

    # Objective: maximise sum of capped ratings for all optimised stats
    prob += pulp.lpSum(cap_var[stat] for stat in opt_stats)

    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    if pulp.LpStatus[prob.status] != 'Optimal':
        print(f"ILP: no optimal solution found (status: {pulp.LpStatus[prob.status]})")
        return None, -1, {}, 0, {}, {}

    # Extract solution: for each slot pick the chosen item index
    # For virtue slots, assign chosen virtues (from y variables) sequentially
    chosen_virtue_indices = []
    if y:
        chosen_virtue_indices = [j for j in y if round(pulp.value(y[j]) or 0) == 1]

    best_combination = []
    virtue_slot_cursor = 0
    for i, t in enumerate(item_types):
        if t == "Virtue":
            chosen = chosen_virtue_indices[virtue_slot_cursor] if virtue_slot_cursor < len(chosen_virtue_indices) else 0
            virtue_slot_cursor += 1
        else:
            chosen = 0
            for j in range(len(items_per_type[t])):
                if round(pulp.value(x[(i, j)]) or 0) == 1:
                    chosen = j
                    break
        best_combination.append(chosen)

    best_combination = tuple(best_combination)

    # Evaluate via process_combination for a consistent result format
    result = process_combination(best_combination, item_types, items_per_type,
                                 character_stats, character_class_stats, stats_rcap,
                                 requirements_ratings, True, essence_quantity_limits)

    return result
# new_definitions.py - Simplified stat hierarchy approach

import os
import re
import sys
import copy
import json
import math

# Constants (unchanged)
STAT = re.compile(r'\["(.*?)"] = (.*?)[,\n]')
char_stat_sorting_order = ["Morale", "InCombatMoraleRegeneration", "NonCombatMoraleRegeneration", "Power", "InCombatPowerRegeneration", "NonCombatPowerRegeneration", "Armour", "Might", "Agility", "Vitality", "Will", "Fate", "CriticalRatingMelee", "CriticalRatingRange", "CriticalRatingTactical", "FinesseRating", "PhysicalMasteryRatingMelee", "PhysicalMasteryRatingRange", "TacticalMasteryRating", "OutgoingHealingRating", "ResistanceRating", "CriticalDefenceRating", "IncomingHealingRating", "BlockChanceRating", "PartialBlockChanceRating", "PartialBlockMitigationRating", "ParryChanceRating", "PartialParryChanceRating", "PartialParryMitigationRating", "EvadeChanceRating", "PartialEvadeChanceRating", "PartialEvadeMitigationRating", "PhysicalMitigationRating", "TacticalMitigationRating"]

server = "Angmar"
username = "ddmdarklink"
plugin_char_path = os.path.join("/", "mnt", "c", "Users", "fabio_dittrich", "Documents", "The Lord of the Rings Online", "PluginData", f"{username}", f"{server}", "{character_name}")

# Formulas (unchanged)
BRating = lambda bs, be, l, le, ls: (bs*(le-l)+(l-ls)*be)/(le-ls)
PfromR = lambda r, a, b: r*a/(r+b)
RfromP = lambda p, a, b: p*b/(a-p)
Rcap = lambda PCap, a, b: PCap*b/(a-PCap)
c = lambda PCap, a: PCap/(a-PCap)
Ropt = lambda c, Rcap: (math.sqrt(c+1)-1)/c*Rcap

STATSCALC = os.environ.get('STATSCALC')
STATS_INFO = json.load(open(os.path.join(STATSCALC, "resources", "stat_files", "stats_info.json")))
CLASSES_STATS = json.load(open(os.path.join(STATSCALC, "resources", "stat_files", "classes_stats.json")))

# SIMPLIFIED STAT HIERARCHY
STAT_HIERARCHY = {
    "main": ["Armour", "Might", "Agility", "Vitality", "Will", "Fate"],
    "secondary": ["Morale", "InCombatMoraleRegeneration", "NonCombatMoraleRegeneration", "Power", "InCombatPowerRegeneration", "NonCombatPowerRegeneration", "CriticalRating", "FinesseRating", "PhysicalMasteryRating", "TacticalMasteryRating", "OutgoingHealingRating", "ResistanceRating", "CriticalDefenceRating", "IncomingHealingRating", "BlockChanceRating", "ParryChanceRating", "EvadeChanceRating", "PhysicalMitigationRating", "TacticalMitigationRating"],
    "tertiary": ["CriticalRatingMelee", "DevastatingRatingMelee", "CriticalMagnitudeRatingMelee", "CriticalRatingRange", "DevastatingRatingRange", "CriticalMagnitudeRatingRange", "CriticalRatingTactical", "DevastatingRatingTactical", "CriticalMagnitudeRatingTactical", "PhysicalMasteryRatingMelee", "PhysicalMasteryRatingRange", "TBlockChanceRating", "TParryChanceRating", "TEvadeChanceRating", "PartialBlockChanceRating", "PartialParryChanceRating", "PartialEvadeChanceRating", "PartialBlockMitigationRating", "PartialParryMitigationRating", "PartialEvadeMitigationRating"],
    "final": {
        "CriticalHitChanceMelee": "CriticalRatingMelee",
        "DevastatingHitChanceMelee": "DevastatingRatingMelee", 
        "Critical&DevastatingHitMagnitudeMelee": "CriticalMagnitudeRatingMelee",
        "CriticalHitChanceRange": "CriticalRatingRange",
        "DevastatingHitChanceRange": "DevastatingRatingRange",
        "Critical&DevastatingHitMagnitudeRange": "CriticalMagnitudeRatingRange",
        "CriticalHitChanceTactical": "CriticalRatingTactical",
        "DevastatingHitChanceTactical": "DevastatingRatingTactical",
        "Critical&DevastatingHitMagnitudeTactical": "CriticalMagnitudeRatingTactical",
        "Finesse": "FinesseRating",
        "PhysicalDamageMelee": "PhysicalMasteryRatingMelee",
        "PhysicalDamageRange": "PhysicalMasteryRatingRange",
        "TacticalOffenceDamage": "TacticalMasteryRating",
        "TacticalOutgoingHealing": "OutgoingHealingRating",
        "Resistance": "ResistanceRating",
        "CriticalDefence": "CriticalDefenceRating",
        "IncomingHealing": "IncomingHealingRating",
        "BlockChance": "TBlockChanceRating",
        "PartialBlockChance": "PartialBlockChanceRating",
        "PartialBlockMitigation": "PartialBlockMitigationRating",
        "ParryChance": "TParryChanceRating",
        "PartialParryChance": "PartialParryChanceRating",
        "PartialParryMitigation": "PartialParryMitigationRating",
        "EvadeChance": "TEvadeChanceRating",
        "PartialEvadeChance": "PartialEvadeChanceRating",
        "PartialEvadeMitigation": "PartialEvadeMitigationRating",
        "PhysicalMitigation": "PhysicalMitigationRating",
        "TacticalMitigation": "TacticalMitigationRating"
    }
}

# Direct stat relationships - replaces multiple mappings
STAT_RELATIONSHIPS = {
    # Secondary -> Tertiary mappings
    "CriticalRating": ["CriticalRatingMelee", "CriticalRatingRange", "CriticalRatingTactical"],
    "PhysicalMasteryRating": ["PhysicalMasteryRatingMelee", "PhysicalMasteryRatingRange"],
    "BlockChanceRating": ["TBlockChanceRating", "PartialBlockChanceRating", "PartialBlockMitigationRating"],
    "ParryChanceRating": ["TParryChanceRating", "PartialParryChanceRating", "PartialParryMitigationRating"],
    "EvadeChanceRating": ["TEvadeChanceRating", "PartialEvadeChanceRating", "PartialEvadeMitigationRating"]
}

# Helper functions for the simplified hierarchy
def get_stat_type(stat_name):
    """Return the type of stat: 'main', 'secondary', 'tertiary', or 'final'"""
    if stat_name in STAT_HIERARCHY["main"]:
        return "main"
    elif stat_name in STAT_HIERARCHY["secondary"]:
        return "secondary"
    elif stat_name in STAT_HIERARCHY["tertiary"]:
        return "tertiary"
    elif stat_name in STAT_HIERARCHY["final"]:
        return "final"
    else:
        return "unknown"

def get_related_stats(stat_name):
    """Get all stats that are related to the given stat"""
    stat_type = get_stat_type(stat_name)
    
    if stat_type == "secondary" and stat_name in STAT_RELATIONSHIPS:
        return STAT_RELATIONSHIPS[stat_name]
    elif stat_type == "final":
        return [STAT_HIERARCHY["final"][stat_name]]
    else:
        return []

def get_parent_stat(stat_name):
    """Get the parent stat that this stat derives from"""
    stat_type = get_stat_type(stat_name)
    
    if stat_type == "final":
        return STAT_HIERARCHY["final"][stat_name]
    elif stat_type == "tertiary":
        # Find which secondary stat this tertiary stat comes from
        for secondary, tertiary_list in STAT_RELATIONSHIPS.items():
            if stat_name in tertiary_list:
                return secondary
    return None

# Simplified constants derived from hierarchy
MAIN_STATS = STAT_HIERARCHY["main"]
SECONDARY_STATS = STAT_HIERARCHY["secondary"]
TERTIARY_STATS = STAT_HIERARCHY["tertiary"]
FINAL_STATS = STAT_HIERARCHY["final"]

# Derived mappings (no need to maintain separately)
def get_secondary_to_tertiary_mapping():
    """Generate secondary to tertiary mapping on demand"""
    return STAT_RELATIONSHIPS

def get_tertiary_to_secondary_mapping():
    """Generate tertiary to secondary mapping on demand"""
    mapping = {}
    for secondary, tertiary_list in STAT_RELATIONSHIPS.items():
        for tertiary in tertiary_list:
            mapping[tertiary] = secondary
    return mapping

def get_rating_to_percentage_mapping():
    """Generate rating to percentage mapping on demand"""
    return {v: k for k, v in FINAL_STATS.items() if v}

# All valid stats
VALID_STATS = (MAIN_STATS + SECONDARY_STATS + TERTIARY_STATS + list(FINAL_STATS.keys()))

# Item validation (unchanged)
VALID_ITEM_MAX_QUANTITY = {"Boots": 1,  "Chest": 1,  "Gloves": 1,  "Helm": 1,  "Leggings": 1,  "Shoulders": 1,  "Back": 1,  "Ring": 2,  "Earring": 2,  "Bracelet": 2,  "Necklace": 1,  "Pocket": 1, "Essence": 999}
VALID_ITEM_TYPES = list(VALID_ITEM_MAX_QUANTITY.keys())

LEVEL_RANGES = [range(1,50), range(50,60), range(60,65), range(65,75), range(75,85), range(85,95), range(95,100), range(100,105), range(105,106), range(106,115), range(115,116), range(116,120), range(120,121), range(121,130), range(130,131), range(131,140), range(140,141), range(141,150)]

def lvl_index(lvl):
    if lvl == 1:
        return 0
    for i,r in enumerate(LEVEL_RANGES):
        if (lvl-1) in r:
            return i

# SIMPLIFIED EQUIP_ITEMS FUNCTION
def equip_items_simplified(character_stats, character_class_stats, items):
    """Simplified version using the new hierarchy"""
    new_stats = copy.deepcopy(character_stats)
    if "available_items" in items:
        items = items["available_items"]
    
    for item in items:
        item_stats = item.get("Stats")
        for item_stat in item_stats:
            stat_type = get_stat_type(item_stat)
            
            # Add the stat directly
            new_stats[item_stat] += item_stats[item_stat]
            
            # Handle main stat contributions to secondary stats
            if stat_type == "main":
                for secondary_stat in character_class_stats[item_stat]:
                    new_stats[secondary_stat] += math.floor(item_stats[item_stat] * character_class_stats[item_stat][secondary_stat])
            
            # Handle secondary stat contributions to tertiary stats
            elif stat_type == "secondary":
                related_tertiary = get_related_stats(item_stat)
                for tertiary_stat in related_tertiary:
                    new_stats[tertiary_stat] += item_stats[item_stat]
    
    return new_stats

# SIMPLIFIED COMPUTE_PERCENTAGE FUNCTION
def compute_percentage_simplified(base_stats, character_armour, character_level, extra_stats):
    """Simplified version using the new hierarchy"""
    level_index = lvl_index(character_level)
    computed_stats = {}
    overcapped_stats = {}
    
    for final_stat, rating_stat in FINAL_STATS.items():
        if not rating_stat:  # Skip main stats and direct stats
            continue
            
        # Get the rating value from base stats
        rating_value = base_stats.get(rating_stat, 0)
        
        # Get stat info
        if final_stat in ["PhysicalMitigation", "TacticalMitigation"]:
            stat_info = STATS_INFO[f"{character_armour}{final_stat}"]
        else:
            stat_info = STATS_INFO[final_stat]
        
        # Calculate percentage
        a = stat_info["A"]
        b = BRating(bs=stat_info["BStart"][level_index], be=stat_info["BEnd"][level_index], 
                   l=character_level, le=stat_info["LEnd"][level_index], ls=stat_info["LStart"][level_index])
        
        percentage = round(PfromR(r=rating_value, a=a, b=b), 1)
        
        # Handle caps
        if percentage > stat_info["Cap"]:
            overcap_percentage = round(percentage - stat_info["Cap"], 1)
            percentage = stat_info["Cap"]
            rating_for_cap = Rcap(PCap=stat_info["PCap"], a=a, b=b)
            overcap_rating = rating_value - rating_for_cap
            overcapped_stats[final_stat] = {
                "overcap_percentage": overcap_percentage, 
                "overcap_rating": overcap_rating
            }
        
        # Add extra stats
        if final_stat in extra_stats:
            percentage += extra_stats[final_stat]
        
        computed_stats[final_stat] = percentage
    
    return computed_stats, overcapped_stats

# Example usage comparison:
"""
OLD APPROACH:
- Need to maintain: MAIN_STATS, SECONDARY_STATS, TERTIARY_STATS
- Need to maintain: SECONDARY2TERTIARY_MAPPING, TERTIARY2SECONDARY_MAPPING  
- Need to maintain: FINAL_STATS (with empty strings as placeholders)
- Need to maintain: RATING2PERCENTAGE_FINAL_STATS
- Complex logic in equip_items checking multiple mappings
- Complex logic in compute_percentage with nested dictionary access

NEW APPROACH:
- Single source of truth: STAT_HIERARCHY
- Single relationship mapping: STAT_RELATIONSHIPS
- Helper functions for navigation
- Clear, linear logic in equip_items and compute_percentage
- No redundant data structures
"""

if __name__ == "__main__":
    # Example usage of compute_percentage_simplified
    
    # Sample character stats (similar to Aeoref character)
    sample_base_stats = {
        "Morale": 8482.901367,
        "InCombatMoraleRegeneration": 645.539989,
        "NonCombatMoraleRegeneration": 6410.39978,
        "Power": 469.583313,
        "InCombatPowerRegeneration": 230.849991,
        "NonCombatPowerRegeneration": 1284.900055,
        "Armour": 570.0,
        "Might": 921.0,
        "Agility": 96.0,
        "Vitality": 882.0,
        "Will": 72.0,
        "Fate": 196.0,
        "CriticalRatingMelee": 4271.166992,
        "CriticalRatingRange": 4271.166992,
        "CriticalRatingTactical": 4271.166992,
        "FinesseRating": 1782.166748,
        "PhysicalMasteryRatingMelee": 6181.291504,
        "PhysicalMasteryRatingRange": 6181.291504,
        "TacticalMasteryRating": 3598.333496,
        "OutgoingHealingRating": 3598.333496,
        "ResistanceRating": 72.0,
        "CriticalDefenceRating": 137.800003,
        "IncomingHealingRating": 532.766663,
        "TBlockChanceRating": 2350.949951,
        "PartialBlockChanceRating": 2350.949951,
        "PartialBlockMitigationRating": 2350.949951,
        "TParryChanceRating": 1283.199951,
        "PartialParryChanceRating": 1283.199951,
        "PartialParryMitigationRating": 1283.199951,
        "TEvadeChanceRating": 330.0,
        "PartialEvadeChanceRating": 330.0,
        "PartialEvadeMitigationRating": 330.0,
        "PhysicalMitigationRating": 1933.333301,
        "TacticalMitigationRating": 1795.300049
    }
    
    # Character details
    character_armour = "Heavy"  # Captain uses Heavy armour
    character_level = 86
    extra_stats = {}  # No extra stats for this example
    
    print("=== Simplified compute_percentage_simplified Example ===")
    print(f"Character Level: {character_level}")
    print(f"Armour Type: {character_armour}")
    print()
    
    # Compute percentages
    computed_stats, overcapped_stats = compute_percentage_simplified(
        sample_base_stats, 
        character_armour, 
        character_level, 
        extra_stats
    )
    
    print("Computed Final Stats (Percentages):")
    for stat_name, percentage in sorted(computed_stats.items()):
        print(f"  {stat_name}: {percentage}%")
    
    if overcapped_stats:
        print("\nOvercapped Stats:")
        for stat_name, overcap_info in overcapped_stats.items():
            print(f"  {stat_name}:")
            print(f"    Overcap Percentage: {overcap_info['overcap_percentage']}%")
            print(f"    Overcap Rating: {overcap_info['overcap_rating']}")
    else:
        print("\nNo stats are overcapped.")
    
    print("\n=== Helper Function Examples ===")
    
    # Test helper functions
    test_stats = ["CriticalRating", "CriticalRatingMelee", "CriticalHitChanceMelee", "Might"]
    
    for stat in test_stats:
        stat_type = get_stat_type(stat)
        related_stats = get_related_stats(stat)
        parent_stat = get_parent_stat(stat)
        
        print(f"\nStat: {stat}")
        print(f"  Type: {stat_type}")
        print(f"  Related Stats: {related_stats}")
        print(f"  Parent Stat: {parent_stat}")

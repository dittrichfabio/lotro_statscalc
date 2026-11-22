import os
import json
import click
import itertools
from definitions import *
from functools import partial
from joblib import Parallel, delayed
from lotro_wiki_interface import get_virtue_stats_from_wiki
from plugindata import load_plugindata
from items_db import ItemDatabase, SLOT_MAP, decode_link_gid, effective_item_level

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


@cli.command('compare_items')
@click.argument('character_name', required=True)
@click.argument('items_file', required=True)
@click.argument('priorities_string', required=True)
def compare_items(character_name, items_file, priorities_string):
    print(character_name)
    print(items_file)

    priorities = priorities_string.split("|")


@cli.command('find_optimal_gear')
@click.argument('character_name', required=True)
@click.argument('gear_file', required=True)
@click.argument('role', required=True)
def find_optimal_gear(character_name, gear_file, role):
    character = json.load(open(os.path.join(STATSCALC, "resources", "character_files", character_name, f"{role}_stats.json")))
    character_class = character["Class"]
    character_level = character["Level"]
    character_class_stats = CLASSES_STATS[character_class]
    character_armour = character_class_stats["Type"]
    character_stats = character["Stats"]
    level_index = lvl_index(character_level)

    stat_requirements, stats_to_print, optimization_choices = load_preferred_stats(character_name, role)

    requirements_ratings = get_ratings_for_requirements(stat_requirements, character_level, character_armour) if stat_requirements else {}

    # Load unified gear file
    gear_json = json.load(open(gear_file))
    available_items = gear_json.get("available_items", [])
    available_essences = gear_json.get("available_essences", [])
    buffs = gear_json.get("buffs", [])

    # Apply active buffs as flat stat additions to character stats
    # Final stats (e.g. WoundResistance) are collected separately as direct % bonuses
    extra_final_stats = {}
    _pure_final_stats = set(FINAL_STATS.keys()) - set(MAIN_STATS) - set(SECONDARY_STATS)
    for buff in buffs:
        buff_name = buff.get("Name", str(buff))
        buff_stats = buff.get("Stats", {})
        for stat in buff_stats:
            if stat not in VALID_ITEM_STATS:
                print(f"Stat '{stat}' of buff '{buff_name}' is not a valid stat. Aborting!")
                sys.exit(1)
        if buff.get("active", False):
            for stat, value in buff_stats.items():
                if stat in _pure_final_stats:
                    extra_final_stats[stat] = extra_final_stats.get(stat, 0) + value
                else:
                    character_stats[stat] = character_stats.get(stat, 0) + value

    # Resolve virtue items from character's available virtues
    virtues_dict = character.get("Virtues", {})
    virtues_items = resolve_virtue_items(virtues_dict) if virtues_dict else None

    # Prepare items with essences and virtues
    items_per_type, items_ids, essence_quantity_limits = prepare_optimization_choices(
        gear_file, optimization_choices, virtues_items=virtues_items
    )

    item_types = [i.split('#')[0] for i in items_ids]
    
    stats_rcap = get_all_stats_Rcap(character_level, character_armour)

    # Use ILP algorithm
    best_combination, best_combination_value, best_combination_overcapped_stats, best_combination_overcap_value, best_combination_stats, best_combination_uncapped_stats = find_optimal_combination_ilp(
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
        # Group and count items by type
        virtue_items = []
        essence_counts = {}
        other_items = []
        
        for index, item_type_index in enumerate(best_combination):
            item_type_name = item_types[index]
            item = items_per_type[item_type_name][item_type_index]
            
            for stat, value in item.get("Stats", {}).items():
                if stat in _pure_final_stats:
                    extra_final_stats[stat] = extra_final_stats.get(stat, 0) + value

            if item_type_name == "Virtue":
                virtue_items.append(item)
            elif item_type_name == "Essence":
                essence_name = item["Name"]
                essence_counts[essence_name] = essence_counts.get(essence_name, 0) + 1
            else:
                other_items.append(item)
        
        # Print virtues with their ranks
        if virtue_items:
            print("Virtues:")
            for virtue in virtue_items:
                rank = virtue.get("Rank", "N/A")
                print(f"  {virtue['Name']} (Rank {rank})")
            print()
        
        # Print essences with counts
        if essence_counts:
            print("Essences:")
            for essence_name, count in essence_counts.items():
                print(f"  {essence_name} x {count}")
            print()
        
        # Print other items
        if other_items:
            print("Gear:")
            for item in other_items:
                print(f"  {item['Name']}")
            print()
        print()

        # Print stats with percentages
        if stats_to_print:
            for fstat in stats_to_print:
                rating_stat = FINAL_STATS.get(fstat, "")
                if rating_stat:
                    stat_info = STATS_INFO.get(get_stats_info_key(fstat, character_armour))
                    if stat_info:
                        a = stat_info["A"]
                        b = BRating(bs=stat_info["BStart"][level_index], be=stat_info["BEnd"][level_index], l=character_level, le=stat_info["LEnd"][level_index], ls=stat_info["LStart"][level_index])
                        capped_value = best_combination_stats.get(rating_stat, 0)
                        uncapped_value = best_combination_uncapped_stats.get(rating_stat, capped_value)
                        base_cap = stats_rcap.get(rating_stat, uncapped_value)
                        penetration = max(0, requirements_ratings.get(rating_stat, 0) - base_cap)
                        secondary_of_r = TERTIARY2SECONDARY_MAPPING.get(rating_stat)
                        if secondary_of_r:
                            for sibling in SECONDARY2TERTIARY_MAPPING.get(secondary_of_r, []):
                                penetration = max(penetration, max(0, requirements_ratings.get(sibling, 0) - base_cap))
                        cap_value = base_cap + penetration
                        percentage = PfromR(r=capped_value - penetration, a=a, b=b) + extra_final_stats.get(fstat, 0)
                        print(f"{fstat}\n\t{round(percentage, 2)}% ({uncapped_value}/{cap_value})")
                else:
                    value = best_combination_stats.get(fstat, 0)
                    print(f"{fstat} {value}")
        else:
            rating_to_finals = {}
            for fstat, rating in FINAL_STATS.items():
                if rating:
                    rating_to_finals.setdefault(rating, []).append(fstat)
            for secondary_stat in SECONDARY_STATS:
                parent = TERTIARY2SECONDARY_MAPPING.get(secondary_stat)
                if parent and parent != secondary_stat:
                    continue
                uncapped_value = best_combination_uncapped_stats.get(secondary_stat)
                stat_for_cap = secondary_stat
                if uncapped_value is None:
                    first_tertiary = next(iter(SECONDARY2TERTIARY_MAPPING.get(secondary_stat, [])), None)
                    uncapped_value = best_combination_uncapped_stats.get(first_tertiary, 0) if first_tertiary else 0
                    stat_for_cap = first_tertiary or secondary_stat
                cap_value = stats_rcap.get(stat_for_cap)
                if cap_value is not None:
                    cap_value = max(cap_value, requirements_ratings.get(secondary_stat, 0))
                    for sibling in SECONDARY2TERTIARY_MAPPING.get(secondary_stat, []):
                        cap_value = max(cap_value, requirements_ratings.get(sibling, 0))
                    print(f"{secondary_stat} {uncapped_value}/{cap_value}")
                else:
                    print(f"{secondary_stat} {uncapped_value}")
                # Print associated final stats indented below
                tertiary_stats = SECONDARY2TERTIARY_MAPPING.get(secondary_stat, [secondary_stat])
                for tstat in tertiary_stats:
                    for fstat in rating_to_finals.get(tstat, []):
                        stat_info = STATS_INFO.get(get_stats_info_key(fstat, character_armour))
                        if stat_info:
                            a = stat_info["A"]
                            b = BRating(bs=stat_info["BStart"][level_index], be=stat_info["BEnd"][level_index], l=character_level, le=stat_info["LEnd"][level_index], ls=stat_info["LStart"][level_index])
                            capped_tvalue = best_combination_stats.get(tstat, 0)
                            uncapped_tvalue = best_combination_uncapped_stats.get(tstat, capped_tvalue)
                            tbase_cap = stats_rcap.get(tstat, uncapped_tvalue)
                            tpenetration = max(0, requirements_ratings.get(tstat, 0) - tbase_cap)
                            secondary_of_t = TERTIARY2SECONDARY_MAPPING.get(tstat)
                            if secondary_of_t:
                                for sibling in SECONDARY2TERTIARY_MAPPING.get(secondary_of_t, []):
                                    tpenetration = max(tpenetration, max(0, requirements_ratings.get(sibling, 0) - tbase_cap))
                            tcap_value = tbase_cap + tpenetration
                            percentage = PfromR(r=capped_tvalue - tpenetration, a=a, b=b) + extra_final_stats.get(fstat, 0)
                            print(f"\t{fstat} {uncapped_tvalue}/{tcap_value} {round(percentage, 2)}%")
    else:
        print(f"Couldn't find a combination that satisfies {stat_requirements}.")


@cli.command('convert_plugin_data_to_json')
@click.argument('character_name', required=True)
@click.argument('server', required=False)
@click.argument('filename', required=True)
@click.option('--username', 'account', default=DEFAULT_PLUGIN_USERNAME,
              help='PluginData account name')
def convert_plugin_data_to_json(character_name, server, filename, account):
    plugin_dir = plugin_char_path.format(
        username=account,
        server=server or DEFAULT_PLUGIN_SERVER,
        character_name=character_name)
    stats_file = os.path.join(plugin_dir, "Stats.plugindata")
    char_folder = os.path.join(STATSCALC, "stat_files", character_name)
    if not os.path.exists(char_folder):
        os.makedirs(char_folder)

    table = load_plugindata(stats_file)

    data = {}
    stats = {}
    for key, value in table.items():
        if key in ["Class", "Level"]:
            try:
                data[key] = float(value)
            except (TypeError, ValueError):
                data[key] = value
        else:
            try:
                stats[key] = round(float(value))
            except (TypeError, ValueError):
                stats[key] = value
    for missing_stat, base_stat in TERTIARY_STAT_BASE_MAP.items():
        if missing_stat not in stats and base_stat in stats:
            stats[missing_stat] = stats[base_stat]
    stats = {key: stats[key] for key in sorted(
        (key for key in stats if key in char_stat_sorting_order),
        key=char_stat_sorting_order.index)}
    data["Stats"] = stats

    with open(os.path.join(char_folder, filename), 'w') as f:
        json.dump(data, f, indent=4)


def _normalize_decoded(value):
    """Cast integral floats from Decoded tables to ints for readable JSON."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        return {k: _normalize_decoded(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_decoded(v) for v in value]
    return value


def _resolve_essences(item_essences, db, db_items, verbose):
    """Resolve Decoded.itemEssences [{GID, Level}] to name + stats entries."""
    if not isinstance(item_essences, list):
        return []
    resolved = []
    for ess in item_essences:
        if not isinstance(ess, dict) or not ess.get("GID"):
            continue
        ess_gid = int(ess["GID"])
        ess_item = db_items.get(ess_gid)
        if ess_item is None:
            if verbose:
                resolved.append({"GID": ess_gid})
            continue
        ess_level = int(ess["Level"]) if ess.get("Level") else effective_item_level(ess_item)
        ess_stats, ess_other = db.resolve_stats(ess_item, ess_level)
        ess_entry = {"Name": ess_item.get("name")}
        if ess_level is not None:
            ess_entry["ItemLevel"] = ess_level
        if ess_stats:
            ess_entry["Stats"] = ess_stats
        if verbose:
            ess_entry["GID"] = ess_gid
            if ess_item.get("quality"):
                ess_entry["Quality"] = ess_item["quality"]
        if ess_other:
            ess_entry["OtherStats"] = ess_other
        resolved.append(ess_entry)
    return resolved


def _shortcut_gid(shortcut_data):
    """Extract the GID half of a quickslot ShortcutData string ("0x<IID>,0x<GID>")."""
    try:
        parts = str(shortcut_data).split(',')
        if len(parts) == 2:
            gid = int(parts[1], 16)
            return gid if gid != 0 else None
    except ValueError:
        pass
    return None


@cli.command('convert_items_to_json')
@click.argument('character_name', required=True)
@click.argument('server', required=False)
@click.argument('filename', required=True)
@click.option('--username', 'account', default=DEFAULT_PLUGIN_USERNAME,
              help='PluginData account name')
@click.option('--verbose', '-v', is_flag=True, default=False,
              help='Include full metadata (GID, Decoded, quality, non-gear and unresolved records)')
def convert_items_to_json(character_name, server, filename, account, verbose):
    """Convert Items.plugindata records into a gear-file-style JSON.

    Each record's itemGID is resolved against the LotroCompanion item DB
    (resources/item_db/items.xml + progressions.xml). Stat progressions are
    interpolated at the item's effective level (Decoded.itemTrueLevel /
    itemLevel when present, else the DB record's level).
    """
    plugin_dir = plugin_char_path.format(
        username=account,
        server=server or DEFAULT_PLUGIN_SERVER,
        character_name=character_name)
    items_file = os.path.join(plugin_dir, "Items.plugindata")
    char_folder = os.path.join(STATSCALC, "stat_files", character_name)
    if not os.path.exists(char_folder):
        os.makedirs(char_folder)

    records = load_plugindata(items_file)
    if isinstance(records, dict):
        records = [records[k] for k in sorted(records)]

    # Resolve GIDs for every record before a single pass over items.xml
    record_gids = []
    for rec in records:
        decoded = rec.get("Decoded") if isinstance(rec.get("Decoded"), dict) else {}
        gid = decoded.get("itemGID")
        if gid is None:
            gid = _shortcut_gid(rec.get("ShortcutData"))
        if gid is None and rec.get("LinkData") and rec.get("Source") != "ChatLinkLI":
            fallback = decode_link_gid(rec["LinkData"])
            if fallback:
                decoded = dict(decoded)
                decoded.update(fallback)
                gid = fallback["itemGID"]
        record_gids.append((decoded, int(gid) if gid else None))

    essence_gids = [
        ess["GID"]
        for decoded, _ in record_gids
        if isinstance(decoded.get("itemEssences"), list)
        for ess in decoded["itemEssences"]
        if isinstance(ess, dict) and ess.get("GID")
    ]

    try:
        db = ItemDatabase()
    except OSError as e:
        print(f"Cannot load item DB: {e}")
        print("Download https://github.com/LotroCompanion/lotro-items-db/raw/master/items.xml "
              "to resources/item_db/items.xml and "
              "https://github.com/LotroCompanion/lotro-data/raw/master/lore/progressions.xml "
              "to resources/item_db/progressions.xml")
        sys.exit(1)
    db_items = db.get_items([gid for _, gid in record_gids] + essence_gids)

    available_items = []
    non_gear_items = []
    unresolved_items = []
    for rec, (decoded, gid) in zip(records, record_gids):
        item = db_items.get(gid) if gid else None
        if item is None:
            entry = {"Name": rec.get("Name")}
            for key in ("Source", "Quality", "Category", "Description", "DecodeError"):
                if rec.get(key) is not None:
                    entry[key] = rec[key]
            if gid:
                entry["GID"] = gid
            if decoded:
                entry["Decoded"] = _normalize_decoded(decoded)
            if rec.get("DecodeError") and rec.get("LinkData"):
                entry["LinkData"] = rec["LinkData"]
            unresolved_items.append(entry)
            continue

        level = effective_item_level(item, decoded)
        stats, other_stats = db.resolve_stats(item, level)
        slot = item.get("slot")
        item_type = SLOT_MAP.get(slot)
        essences = _resolve_essences(
            decoded.get("itemEssences") if decoded else None,
            db, db_items, verbose)

        entry = {"Name": rec.get("Name") or item.get("name")}
        if level is not None:
            entry["ItemLevel"] = level
        entry["Type"] = item_type or slot or item.get("category") or "Unset"
        entry["Stats"] = stats
        if item.get("slots"):
            entry["EssenceSlots"] = int(item["slots"])
            raw_essences = decoded.get("itemEssences") if decoded else None
            entry["UsedEssenceSlots"] = (
                sum(1 for ess in raw_essences if isinstance(ess, dict) and ess.get("GID"))
                if isinstance(raw_essences, list) else 0
            )
        if essences:
            entry["Essences"] = essences
        if other_stats:
            entry["OtherStats"] = other_stats
        if verbose:
            entry["GID"] = gid
            for attr, key in (("minLevel", "MinLevel"), ("quality", "Quality"),
                              ("armourType", "ArmourType"),
                              ("scaling", "Scaling")):
                if item.get(attr) is not None:
                    entry[key] = int(float(item[attr])) if attr in ("minLevel", "slots") else item[attr]
            for weapon_key in ("dps", "minDamage", "maxDamage", "damageType", "weaponType"):
                if item.get(weapon_key) is not None:
                    entry[weapon_key] = item[weapon_key]
            if decoded:
                entry["Decoded"] = _normalize_decoded(decoded)
        if item_type:
            available_items.append(entry)
        else:
            non_gear_items.append(entry)

    output = {"available_items": available_items}
    if verbose:
        output["non_gear_items"] = non_gear_items
        output["unresolved_items"] = unresolved_items
    out_path = os.path.join(char_folder, filename)
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=4, ensure_ascii=False)

    print(f"Wrote {out_path}")
    print(f"  {len(available_items)} gear item(s), "
          f"{len(non_gear_items)} non-gear item(s), "
          f"{len(unresolved_items)} unresolved record(s)")
    for entry in unresolved_items:
        print(f"  unresolved: {entry.get('Name')} "
              f"(GID={entry.get('GID')}, {entry.get('DecodeError') or 'no usable ID'})")
    for entry in non_gear_items:
        print(f"  non-gear: {entry.get('Name')} (Type={entry.get('Type')})")




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

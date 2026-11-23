# LOTRO StatsCalc - Codebase Summary

## Overview
LOTRO StatsCalc is a command-line tool for calculating and optimizing character stats in Lord of the Rings Online (LOTRO). It helps players optimize gear picks by computing stat percentages, finding optimal item combinations, and simulating equipment changes.

## Project Structure

```
lotro_statscalc/
├── src/
│   ├── statscalc.py              # Main CLI entry point
│   ├── definitions.py            # Core definitions and formulas (legacy)
│   ├── new_definitions.py        # Simplified stat hierarchy (new approach)
│   └── lotro_wiki_interface.py  # Web scraping for virtue/essence stats
├── resources/
│   ├── character_files/          # Character-specific data
│   │   ├── {character_name}/
│   │   │   ├── char.json              # Base character stats
│   │   │   ├── {role}_stats.json     # Role-specific stats
│   │   │   ├── preferred_stats.json  # Stat preferences per role
│   │   │   ├── items.json            # Available items
│   │   │   └── available_essences_*.json # Available essences
│   └── stat_files/               # Game data
│       ├── stats_info.json       # Stat caps and formulas
│       ├── classes_stats.json    # Class-specific stat conversions
│       ├── virtue_stats.json     # Virtue rank-to-stat mappings
│       └── essences_stats.json   # Essence stat data
├── tests/
│   └── test_new_definitions.py   # Unit tests for simplified hierarchy
├── setup.py                      # Package configuration
└── stat_files/                   # Additional stat storage
```

## Core Concepts

### Stat Hierarchy
The system uses a 4-tier stat hierarchy:

1. **Main Stats**: Armour, Might, Agility, Vitality, Will, Fate
   - Directly contribute to secondary stats based on class

2. **Secondary Stats**: Morale, Power, CriticalRating, FinesseRating, etc.
   - Can be found on items
   - Contribute to tertiary stats

3. **Tertiary Stats**: CriticalRatingMelee, PhysicalMasteryRatingMelee, etc.
   - Derived from secondary stats
   - Cannot be found directly on items

4. **Final Stats**: CriticalHitChanceMelee, PhysicalDamageMelee, etc.
   - Percentage-based values computed from ratings
   - These are what players actually see in-game

### Rating-to-Percentage Conversion
The game uses a formula to convert ratings to percentages:
```
Percentage = Rating * A / (Rating + B)
```
Where:
- A is a constant for each stat
- B is calculated based on character level using level ranges

### Stat Caps
Each final stat has a cap (e.g., 50% for CriticalHitChance). Stats exceeding the cap are "overcapped" and penalized in optimization.

## CLI Commands

### `fetch_virtue_stats`
Fetches virtue stats from LOTRO-wiki.com and saves to `resources/stat_files/virtue_stats.json`

### `fetch_essence_stats`
Fetches essence stats from LOTRO-wiki.com and saves to `resources/stat_files/essences_stats.json`

### `calculate_stat_percentage`
Calculates the percentage for a given stat value.
```
statscalc calculate_stat_percentage <character_name> <stat_name> <stat_value>
```

### `simulate_equipping_items`
Simulates equipping items and shows resulting stats.
```
statscalc simulate_equipping_items <character_name> <items_file> [priority]
```

### `find_optimal_gear`
Finds the optimal gear combination including items, essences, and virtues.
```
statscalc find_optimal_gear <character_name> <gear_file> [<gear_file> ...] <role> [--essence-mode fixed|free]
```
Multiple gear files can be passed; their `available_items`, `available_essences` and `buffs` sections are concatenated (exact duplicates dropped), so plugin exports can be kept as per-set files. Uses ILP (Integer Linear Programming) algorithm for optimization. Each gear file is a unified JSON containing:
- `available_items`: List of gear pieces (may include `EssenceSlots`, `UsedEssenceSlots` and a resolved `Essences` list from `convert_items_to_json`)
- `available_essences`: List of available essences
- `buffs`: List of consumable buffs (with `active: true/false` flag)

Essence picks are not a fixed count: the optimizer derives how many essences to slot from the open sockets (`EssenceSlots - UsedEssenceSlots`) of whichever gear items are selected, so the count varies per combination. `--essence-mode fixed` (default) treats already-slotted essences as part of the item's stats and only optimizes open sockets; `free` re-optimizes all sockets from the essence pool. Essence optimization is automatic whenever the gear file has `available_essences` and socketed gear — no `optimization_choices` entry needed; `"Essence": 0` explicitly disables it.

Active buffs are applied as flat stat additions to the character's base stats before optimization.
Virtues are resolved from the character's `{role}_stats.json` file (under the `Virtues` field) and optimized as part of the gear selection.

### `convert_plugin_data_to_json`
Converts LOTRO plugin data to JSON format for character stats.
```
statscalc convert_plugin_data_to_json <character_name> [server] <filename> [--username ACCOUNT] [--force]
```
Parses `Stats.plugindata` via `src/plugindata.py` (a hand-rolled Lua-table parser)
and writes `resources/character_files/<character_name>/<filename>`. Existing
files are not overwritten unless `--force` is passed.

### `convert_items_to_json`
Converts `Items.plugindata` records into a gear-file-style JSON.
```
statscalc convert_items_to_json <character_name> [server] <filename> [--username ACCOUNT] [--verbose] [--force]
```
Each record's `itemGID` (from `Decoded`, `ShortcutData`, or a `LinkData`
fallback decode) is resolved against the LotroCompanion item DB in
`resources/item_db/` (`items.xml` + `progressions.xml`, downloaded from
github.com/LotroCompanion — gitignored). Stat progressions are interpolated
at the effective item level (`Decoded.itemTrueLevel`/`itemLevel` if present,
else the DB record's `level`). Writes to
`resources/character_files/<character_name>/<filename>` (no overwrite without
`--force`). `--verbose` adds GID/Decoded/quality metadata plus the
`non_gear_items` and `unresolved_items` sections; the default output is the
slim gear format (`Name`, `ItemLevel`, `Type`, `Stats`, `Essences`,
`OtherStats`, `EssenceSlots`/`UsedEssenceSlots`). Stat values follow game
semantics via `resources/item_db/stats.xml`: INTEGER stats truncate, FLOAT
stats round to display precision, percentage stats scale ×100 and regen
stats ×60.

## Optimization Algorithms

### ILP (Integer Linear Programming)
- Uses `pulp` library (CBC solver)
- Fully implemented with hard constraints and correct objective
- Stat requirements converted to rating space via `RfromP` before solving
- Hard constraints enforce minimum required ratings (`total_rating[stat] >= req`)
- **Objective**: maximise sum of capped ratings
  - For stats **with** a requirement: capped at the requirement rating (no incentive to overshoot)
  - For stats **without** a requirement (e.g. Morale): capped at `stats_rcap` to respect game cap
- Essence quantity limits enforced as linear constraints; essence pick counts are integer variables tied to selected gear's open sockets
- Most efficient for large problems; handles 24+ essence slots in seconds

## Character File Format

### char.json (or {role}_stats.json)
```json
{
    "Class": "Warden",
    "Level": 115.0,
    "Stats": {
        "Morale": 14356.869141,
        "Might": 180.0,
        "Agility": 996.0,
        ...
    },
    "Virtues": {
        "Honour": 20,
        "Valour": 18,
        "Fidelity": 15,
        "Charity": 12,
        "Innocence": 10
    },
    "ExtraStats": {
        "CriticalHitChanceMelee": 7.5
    }
}
```
The `Virtues` field lists available virtues and their current ranks. Stats for each virtue at the given rank are resolved from `resources/stat_files/virtue_stats.json` at runtime.

### preferred_stats.json
```json
{
    "optimization_choices": {
        "Helm": 1,
        "Shoulders": 1,
        "Chest": 1,
        ...
        "Essence": 24,
        "Virtue": 5
    },
    "roles": {
        "tank": {
            "stats_to_print": ["Morale", "Finesse", ...],
            "stat_requirements": ["Morale", "Finesse", ...]
        },
        "dps": {
            "stats_to_print": ["Morale", "CriticalHitChanceMelee", ...],
            "stat_requirements": ["PhysicalDamageMelee=180", ...]
        }
    }
}
```
Note: `optimization_choices` replaces the old `items_to_pick` field (with backward compatibility fallback).

### gear.json (unified gear file)
```json
{
    "available_items": [
        {
            "Name": "Padded Coif of the Expedition's Vanguard",
            "Type": "Helm",
            "Stats": {
                "Armour": 770,
                "Agility": 287,
                "Vitality": 198,
                "PhysicalMasteryRating": 826
            }
        },
        ...
    ],
    "available_essences": [
        {
            "Name": "Major Essence of Might",
            "Type": "Essence",
            "QuantityAvailable": -1,
            "Stats": {
                "Might": 94
            }
        },
        ...
    ],
    "buffs": [
        {
            "Name": "War-speech",
            "active": true,
            "Stats": {
                "TacticalMasteryRating": 500
            }
        }
    ]
}
```
The unified gear file combines items, essences, and buffs in a single JSON. Active buffs are applied as flat stat additions to the character's base stats before optimization.

## Key Functions

### equip_items(character_stats, character_class_stats, items)
Adds item stats to character stats, handling:
- Direct stat additions
- Main stat contributions to secondary stats
- Secondary stat contributions to tertiary stats

### compute_percentage(base_stats, character_armour, character_level, extra_stats)
Converts rating stats to percentage stats, handling:
- Rating-to-percentage conversion
- Stat caps
- Overcap detection and tracking
- Extra stat bonuses

### process_combination(combination, item_types, items_per_type, ...)
Evaluates a single item combination:
- Validates essence quantity limits
- Computes total stats
- Detects overcaps
- Calculates combination value

### load_preferred_stats(character_name, role)
Loads role-specific preferences:
- Stat requirements (with or without goals)
- Stats to print in results
- Items to pick (slots and quantities)

## Recent Changes

### Stat Key Override Map (`definitions.py`)
- Added `STATS_INFO_KEY_OVERRIDES` dict to map specific stat names (e.g. `CriticalDefenceMelee`) to their shared key in `stats_info.json` (e.g. `CriticalDefence`).
- Added `get_stats_info_key(stat, armour)` helper used in all `STATS_INFO` lookups to resolve these mismatches without modifying `stats_info.json`.

### Tertiary Stat Initialization (`definitions.py`)
- Added `TERTIARY_STAT_BASE_MAP`: maps each tertiary stat to the base stat it inherits from (e.g. `DevastatingRatingMelee → CriticalRatingMelee`).
- `equip_items` now pre-initializes any missing tertiary stats from `SECONDARY2TERTIARY_MAPPING` before processing items, using `TERTIARY_STAT_BASE_MAP` to inherit the correct base value (preventing `KeyError`).

### `classes_stats.json` — Added `DevastatingRating*` and `CriticalMagnitudeRating*`
- All 11 classes now include `DevastatingRatingMelee/Range/Tactical` and `CriticalMagnitudeRatingMelee/Range/Tactical` in every main-stat block (`Might`, `Agility`, `Will`, `Fate`).
- Each new entry uses the same multiplier as the corresponding `CriticalRating*` entry, ensuring that main-stat contributions (e.g. Agility → CriticalRatingMelee) also flow equally to Devastating and CritMagnitude variants.

### `convert_plugin_data_to_json` (`statscalc.py`)
- After parsing plugin data, applies `TERTIARY_STAT_BASE_MAP` to fill in any tertiary stats the plugin doesn't export (e.g. `DevastatingRating*` from `CriticalRating*`).
- The sort/filter step now uses `if key in char_stat_sorting_order` to skip unknown keys instead of crashing.
- `char_stat_sorting_order` in `definitions.py` updated to include `DevastatingRating*` and `CriticalMagnitudeRating*` entries.

### ILP Objective Fix — No Over-shooting Requirements (`definitions.py`)
- Previously, the ILP objective maximised `min(rating, stats_rcap)` for all stats, giving incentive to stack a stat well past its requirement (e.g. Finesse ends up at 46% when only 30% was requested).
- **Fix**: for stats with a hard requirement the objective ceiling is now the requirement rating itself. Once the requirement is met there is no further gain, so spare essence slots are redirected to unconstrained stats like Morale.

## Known Issues / TODOs

From code comments:
- Not all characters have a char.json file
- Not all characters have {role}_stats.json files
- Value computation needs redefinition for stat-independent weighting
- Need to validate that stats actually exist when loading preferences
- Need a way to define quantity requirements per item type
- Some avoidance results not being printed due to rounding differences
- char.json should be a parameter to use different stat files
- Stat percentage computation is commented out in simulate_equipping_items

## Simplified Hierarchy (new_definitions.py)

A newer approach that simplifies the stat hierarchy management:
- Single source of truth: `STAT_HIERARCHY`
- Single relationship mapping: `STAT_RELATIONSHIPS`
- Helper functions for navigation: `get_stat_type()`, `get_related_stats()`, `get_parent_stat()`
- Cleaner logic in equip_items and compute_percentage
- No redundant data structures

This is currently being tested in `tests/test_new_definitions.py` but not yet integrated into the main CLI.

## Dependencies

- click: CLI framework
- requests: Web scraping
- beautifulsoup4: HTML parsing
- joblib: Parallel processing (imported but not extensively used)

## Environment Variables

- `STATSCALC`: Must be set to the project root directory

## Plugin Data Path

Plugin data is expected at:
```
/mnt/c/Users/fabio_dittrich/Documents/The Lord of the Rings Online/PluginData/{username}/{server}/{character_name}/
```

Default: username="ddmdarklink", server="Angmar"

## Item Types and Limits

Valid item types and maximum quantities:
- Boots: 1
- Chest: 1
- Gloves: 1
- Helm: 1
- Leggings: 1
- Shoulders: 1
- Back: 1
- Ring: 2
- Earring: 2
- Bracelet: 2
- Necklace: 1
- Pocket: 1
- Essence: 999
- Virtue: 999 (practically limited by available virtues in character file)

## Level Ranges

The game uses discrete level ranges for stat calculations:
- 1-49, 50-59, 60-64, 65-74, 75-84, 85-94, 95-99, 100-104, 105, 106-114, 115, 116-119, 120, 121-129, 130, 131-139, 140, 141-150

Each range has different formula parameters for rating-to-percentage conversion.

import os
import zlib
import math
import bisect
import struct
import xml.etree.ElementTree as ET

from definitions import STATSCALC

ITEM_DB_DIR = os.path.join(STATSCALC, "resources", "item_db")
ITEMS_XML = os.path.join(ITEM_DB_DIR, "items.xml")
PROGRESSIONS_XML = os.path.join(ITEM_DB_DIR, "progressions.xml")
STATS_XML = os.path.join(ITEM_DB_DIR, "stats.xml")

# LotroCompanion items.xml stat name -> StatsCalc stat name.
# Rating stats feed the rating pipeline; *_PERCENTAGE stats map to the
# corresponding final stat (handled as flat % bonuses by find_optimal_gear).
ITEM_STAT_MAP = {
    # main stats
    "MIGHT": "Might",
    "AGILITY": "Agility",
    "VITALITY": "Vitality",
    "WILL": "Will",
    "FATE": "Fate",
    # primary
    "MORALE": "Morale",
    "POWER": "Power",
    "ARMOUR": "Armour",
    "ICMR": "InCombatMoraleRegeneration",
    "OCMR": "NonCombatMoraleRegeneration",
    "ICPR": "InCombatPowerRegeneration",
    "OCPR": "NonCombatPowerRegeneration",
    # ratings
    "CRITICAL_RATING": "CriticalRating",
    "FINESSE": "FinesseRating",
    "PHYSICAL_MASTERY": "PhysicalMasteryRating",
    "TACTICAL_MASTERY": "TacticalMasteryRating",
    "OUTGOING_HEALING": "OutgoingHealingRating",
    "INCOMING_HEALING": "IncomingHealingRating",
    "RESISTANCE": "ResistanceRating",
    "CRITICAL_DEFENCE": "CriticalDefenceRating",
    "BLOCK": "BlockChanceRating",
    "PARRY": "ParryChanceRating",
    "EVADE": "EvadeChanceRating",
    "PHYSICAL_MITIGATION": "PhysicalMitigationRating",
    "TACTICAL_MITIGATION": "TacticalMitigationRating",
    # element mitigations: StatsCalc models all tactical element mits as the
    # shared TacticalMitigationRating (see FINAL_STATS / STATS_INFO_KEY_OVERRIDES)
    "FROST_MITIGATION": "TacticalMitigationRating",
    "FIRE_MITIGATION": "TacticalMitigationRating",
    "LIGHTNING_MITIGATION": "TacticalMitigationRating",
    "ACID_MITIGATION": "TacticalMitigationRating",
    "SHADOW_MITIGATION": "TacticalMitigationRating",
    "ORC_CRAFT_MITIGATION": "PhysicalMitigationRating",
    "FELL_WROUGHT_MITIGATION": "PhysicalMitigationRating",
    # percentage (final stat) modifiers
    "BLOCK_PERCENTAGE": "BlockChance",
    "PARRY_PERCENTAGE": "ParryChance",
    "EVADE_PERCENTAGE": "EvadeChance",
    "PARTIAL_BLOCK_PERCENTAGE": "PartialBlockChance",
    "PARTIAL_BLOCK_MITIGATION_PERCENTAGE": "PartialBlockMitigation",
    "PARTIAL_PARRY_PERCENTAGE": "PartialParryChance",
    "PARTIAL_PARRY_MITIGATION_PERCENTAGE": "PartialParryMitigation",
    "PARTIAL_EVADE_PERCENTAGE": "PartialEvadeChance",
    "PARTIAL_EVADE_MITIGATION_PERCENTAGE": "PartialEvadeMitigation",
    "INCOMING_HEALING_PERCENTAGE": "IncomingHealing",
    "OUTGOING_HEALING_PERCENTAGE": "TacticalOutgoingHealing",
    "CRITICAL_MELEE_PERCENTAGE": "CriticalHitChanceMelee",
    "CRITICAL_RANGED_PERCENTAGE": "CriticalHitChanceRange",
    "CRITICAL_TACTICAL_PERCENTAGE": "CriticalHitChanceTactical",
    "MELEE_DAMAGE_PERCENTAGE": "PhysicalDamageMelee",
    "RANGED_DAMAGE_PERCENTAGE": "PhysicalDamageRange",
    "TACTICAL_DAMAGE_PERCENTAGE": "TacticalOffenceDamage",
    "PHYSICAL_MITIGATION_PERCENTAGE": "PhysicalMitigation",
    "TACTICAL_MITIGATION_PERCENTAGE": "TacticalMitigation",
    "SHADOW_MITIGATION_PERCENTAGE": "ShadowMitigation",
}

# items.xml slot -> StatsCalc item Type
SLOT_MAP = {
    "HEAD": "Helm",
    "SHOULDER": "Shoulders",
    "CHEST": "Chest",
    "HAND": "Gloves",
    "LEGS": "Leggings",
    "FEET": "Boots",
    "BACK": "Back",
    "NECK": "Necklace",
    "WRIST": "Bracelet",
    "LEFT_WRIST": "Bracelet",
    "RIGHT_WRIST": "Bracelet",
    "FINGER": "Ring",
    "LEFT_FINGER": "Ring",
    "RIGHT_FINGER": "Ring",
    "EAR": "Earring",
    "LEFT_EAR": "Earring",
    "RIGHT_EAR": "Earring",
    "POCKET": "Pocket",
}

_ITEM_ATTRS = (
    "key", "name", "level", "minLevel", "slot", "category", "quality",
    "slots", "armourType", "binding", "scaling", "icon",
    "dps", "minDamage", "maxDamage", "damageType", "weaponType",
)

# Regen stats are stored per-second in progressions and displayed/stored
# per-minute (x60) — same convention as StatUtils.fixStatValue upstream.
_REGEN_STATS = {"ICMR", "ICPR", "OCMR", "OCPR"}


def _load_stat_meta(path):
    """Load stats.xml -> {legacyKey: (is_integer, is_percentage, decimals)}.

    Stats without a type attribute are FLOAT; decimals mirrors the
    maxDigitsAbove1 display precision (default 0 -> integer display).
    """
    meta = {}
    if not os.path.exists(path):
        return meta
    for event, elem in ET.iterparse(path, events=('end',)):
        if elem.tag == 'stat':
            key = elem.get('legacyKey')
            if key:
                meta[key] = (
                    elem.get('type') == 'INTEGER',
                    elem.get('isPercentage') == 'true',
                    int(elem.get('maxDigitsAbove1') or 0),
                )
            elem.clear()
    return meta


def _interpolate(points, x):
    """Piecewise-linear interpolation matching upstream LinearInterpolatingProgression:
    None below minX, linear between points, last-slope extrapolation above maxX."""
    if len(points) < 2:
        return points[0][1] if points and x >= points[0][0] else None
    if x < points[0][0]:
        return None
    xs = [p[0] for p in points]
    i = bisect.bisect_left(xs, x)
    if i >= len(points):
        x1, y1 = points[-2]
        x2, y2 = points[-1]
        if x2 == x1:
            return y2
        return y2 + (x - x2) * (y2 - y1) / (x2 - x1)
    x2, y2 = points[i]
    if i == 0 or x2 == x:
        return y2
    x1, y1 = points[i - 1]
    if x2 == x1:
        return y2
    return y1 + (x - x1) * (y2 - y1) / (x2 - x1)


def _round_stat(value, decimals=0):
    """Round half away from zero (Java Math.round semantics) to `decimals`
    places; decimals=0 yields an int."""
    factor = 10 ** decimals
    rounded = math.floor(value * factor + 0.5) / factor
    return int(rounded) if decimals == 0 else rounded


def _parse_range(range_str):
    """'lo-hi' -> (lo, hi); empty bounds are unbounded (None)."""
    lo, _, hi = range_str.partition('-')
    return (float(lo) if lo else None,
            float(hi) if hi else None)


def _load_progressions(path):
    """Load progressions.xml -> {id: ('linear', [(x, y), ...])
    | ('array', [y, ...], min_x)}."""
    progressions = {}
    for event, elem in ET.iterparse(path, events=('end',)):
        if elem.tag == 'linearInterpolationProgression':
            points = sorted(
                (float(p.get('x')), float(p.get('y')))
                for p in elem.findall('point')
            )
            progressions[int(elem.get('identifier'))] = ('linear', points)
            elem.clear()
        elif elem.tag == 'arrayProgression':
            values = []
            for p in elem.findall('point'):
                count = int(p.get('count', 1))
                try:
                    value = float(p.get('y'))
                except (TypeError, ValueError):
                    value = p.get('y')
                values.extend([value] * count)
            min_x = int(elem.get('minX') or 1)
            progressions[int(elem.get('identifier'))] = ('array', values, min_x)
            elem.clear()
    return progressions


def decode_link_gid(link_data):
    """Fallback decoder for the raw LinkData blob.

    Characters are \\u0100-\\u01FF; byte value = ord(c) - 0x100. After an
    8-byte wrapper the payload is zlib/DEFLATE data starting with
    IIDLow(4) IIDHigh(4) GID(4) little-endian. Returns the Decoded-style
    dict on success, None otherwise.
    """
    try:
        raw = bytes(ord(c) - 0x100 for c in link_data)
        payload = raw[8:]
        try:
            inflated = zlib.decompress(payload)
        except zlib.error:
            obj = zlib.decompressobj(-15)
            inflated = obj.decompress(payload)
        iid_low, iid_high, gid = struct.unpack('<III', inflated[:12])
        return {'itemIIDLow': iid_low, 'itemIIDHigh': iid_high, 'itemGID': gid}
    except Exception:
        return None


class ItemDatabase:
    """Resolves itemGID values against the LotroCompanion items/progressions DBs."""

    def __init__(self, items_path=ITEMS_XML, progressions_path=PROGRESSIONS_XML,
                 stats_path=STATS_XML):
        self.items_path = items_path
        self._progressions = _load_progressions(progressions_path)
        self._stat_meta = _load_stat_meta(stats_path)
        self._item_cache = {}

    def get_item(self, gid):
        return self.get_items([gid]).get(int(gid))

    def get_items(self, gids):
        """Single streaming pass over items.xml collecting all wanted GIDs."""
        wanted = {int(g) for g in gids if g is not None}
        result = {}
        missing = wanted - set(self._item_cache)
        if not missing:
            for g in wanted:
                result[g] = self._item_cache[g]
            return result
        for event, elem in ET.iterparse(self.items_path, events=('end',)):
            if elem.tag != 'item':
                continue
            key = int(elem.get('key'))
            if key in missing:
                item = {a: elem.get(a) for a in _ITEM_ATTRS if elem.get(a) is not None}
                stats = []
                stats_elem = elem.find('stats')
                if stats_elem is not None:
                    for s in stats_elem.findall('stat'):
                        stats.append({k: s.get(k) for k in ('name', 'scaling', 'ranged', 'constant', 'value', 'operator') if s.get(k) is not None})
                item['stats'] = stats
                self._item_cache[key] = item
            elem.clear()
            if all(g in self._item_cache for g in wanted):
                break
        for g in wanted:
            result[g] = self._item_cache.get(g)
        return result

    def progression_value(self, progression_id, x):
        prog = self._progressions.get(int(progression_id))
        if prog is None:
            return None
        kind, data = prog[0], prog[1]
        if kind == 'linear':
            return _interpolate(data, x)
        # array progression: index = x - minX, clamped to the last entry
        min_x = prog[2]
        index = int(x) - min_x
        if index < 0:
            return None
        if index >= len(data):
            return data[-1]
        return data[index]

    def _apply_stat_rules(self, name, value, from_progression):
        """Apply upstream StatUtils.fixStatValue scaling and type-aware
        rounding so exported values match what the game displays.

        INTEGER stats truncate; FLOAT stats round to their display
        precision (maxDigitsAbove1, or 2 decimals for percentages).
        """
        meta = self._stat_meta.get(name)
        is_integer, is_percentage, decimals = meta if meta else (False, False, 0)
        if from_progression:
            if is_percentage:
                value *= 100
            if name in _REGEN_STATS:
                value *= 60
        if is_integer:
            return int(value)
        if is_percentage:
            decimals = max(2, decimals)
        return _round_stat(value, decimals)

    def _ranged_value(self, ranged, level):
        """'ranged' may hold comma-separated 'lo-hi:progId' ranges; the
        first range containing the level wins (upstream semantics)."""
        if level is None:
            return None
        for part in ranged.split(','):
            range_part, _, prog_id = part.partition(':')
            if not prog_id:
                continue
            lo, hi = _parse_range(range_part)
            if lo is None and hi is None:
                continue
            if (lo is not None and level < lo) or (hi is not None and level > hi):
                continue
            value = self.progression_value(prog_id, level)
            if isinstance(value, (int, float)):
                return value
        return None

    def resolve_stats(self, item, effective_level):
        """Resolve an item DB record's <stat> entries at the effective level.

        Returns (stats, other_stats): mapped StatsCalc names and raw DB names
        for stats without a mapping.
        """
        stats = {}
        other = {}
        for s in item.get('stats', []):
            name = s['name']
            value = None
            from_progression = False
            if 'ranged' in s:
                value = self._ranged_value(s['ranged'], effective_level)
                from_progression = value is not None
            elif 'scaling' in s:
                if effective_level is not None:
                    value = self.progression_value(s['scaling'], effective_level)
                    from_progression = isinstance(value, (int, float))
            elif 'constant' in s:
                try:
                    value = float(s['constant'])
                except ValueError:
                    continue
            else:
                continue
            if not isinstance(value, (int, float)):
                continue
            value = self._apply_stat_rules(name, float(value), from_progression)
            target = ITEM_STAT_MAP.get(name)
            if target:
                stats[target] = stats.get(target, 0) + value
            else:
                other[name] = other.get(name, 0) + value
        return stats, other


def effective_item_level(item, decoded=None):
    """Effective item level: prefer instance data from the link blob,
    fall back to the DB record's level attribute."""
    if decoded:
        for key in ('itemTrueLevel', 'itemLevel'):
            if decoded.get(key):
                return int(decoded[key])
    if item.get('level'):
        return int(float(item['level']))
    return None

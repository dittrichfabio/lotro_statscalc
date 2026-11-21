import os
import zlib
import bisect
import struct
import xml.etree.ElementTree as ET

from definitions import STATSCALC

ITEM_DB_DIR = os.path.join(STATSCALC, "resources", "item_db")
ITEMS_XML = os.path.join(ITEM_DB_DIR, "items.xml")
PROGRESSIONS_XML = os.path.join(ITEM_DB_DIR, "progressions.xml")

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


def _interpolate(points, x):
    xs = [p[0] for p in points]
    i = bisect.bisect_left(xs, x)
    if i >= len(points):
        return points[-1][1]
    x2, y2 = points[i]
    if x2 == x:
        return y2
    if i == 0:
        return y2
    x1, y1 = points[i - 1]
    if x2 == x1:
        return y2
    return y1 + (x - x1) * (y2 - y1) / (x2 - x1)


def _parse_range(range_str):
    lo, _, hi = range_str.partition('-')
    return (float(lo) if lo else 0.0,
            float(hi) if hi else float('inf'))


def _load_progressions(path):
    """Load progressions.xml -> {id: ('linear', [(x, y), ...]) | ('array', [y, ...])}."""
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
            progressions[int(elem.get('identifier'))] = ('array', values)
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

    def __init__(self, items_path=ITEMS_XML, progressions_path=PROGRESSIONS_XML):
        self.items_path = items_path
        self._progressions = _load_progressions(progressions_path)
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
        kind, data = prog
        if kind == 'linear':
            return _interpolate(data, x)
        # array progression: 1-based index into the expanded table
        index = int(x)
        if index < 1 or index > len(data):
            return None
        return data[index - 1]

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
            if 'ranged' in s:
                range_part, _, prog_id = s['ranged'].partition(':')
                lo, hi = _parse_range(range_part)
                if effective_level is None or not (lo <= effective_level <= hi):
                    continue
                value = self.progression_value(prog_id, effective_level)
                if not isinstance(value, (int, float)):
                    continue
                value = int(value)
            elif 'scaling' in s:
                if effective_level is None:
                    continue
                value = self.progression_value(s['scaling'], effective_level)
                if not isinstance(value, (int, float)):
                    continue
                value = int(value)
            elif 'constant' in s:
                value = float(s['constant'])
                if value.is_integer():
                    value = int(value)
            else:
                continue
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

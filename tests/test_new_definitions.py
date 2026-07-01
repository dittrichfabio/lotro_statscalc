import unittest
import sys
import os

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from new_definitions import (
    compute_percentage_simplified, 
    get_stat_type, 
    get_related_stats, 
    get_parent_stat,
    STAT_HIERARCHY,
    STAT_RELATIONSHIPS
)

class TestNewDefinitions(unittest.TestCase):
    """Test cases for the simplified stat hierarchy functions"""
    
    def setUp(self):
        """Set up test data"""
        # Sample character stats (from Feanari's new_stats2.json)
        self.sample_base_stats = {
            "Morale": 19960,
            "InCombatMoraleRegeneration": 33.6,
            "NonCombatMoraleRegeneration": 376.3,
            "Power": 468,
            "InCombatPowerRegeneration": 5.5,
            "NonCombatPowerRegeneration": 28.6,
            "Armour": 5520,
            "Might": 161,
            "Agility": 424,
            "Vitality": 2790,
            "Will": 2828,
            "Fate": 104,
            "CriticalRatingMelee": 16820,
            "CriticalRatingRange": 16820,
            "CriticalRatingTactical": 16820,
            "FinesseRating": 3939,
            "PhysicalMasteryRatingMelee": 1958,
            "PhysicalMasteryRatingRange": 1958,
            "TacticalMasteryRating": 13779,
            "OutgoingHealingRating": 13779,
            "ResistanceRating": 3380,
            "CriticalDefenceRating": 1094,
            "IncomingHealingRating": 410,
            "TBlockChanceRating": 0,
            "PartialBlockChanceRating": 0,
            "PartialBlockMitigationRating": 0,
            "TParryChanceRating": 164,
            "PartialParryChanceRating": 164,
            "PartialParryMitigationRating": 164,
            "TEvadeChanceRating": 6081,
            "PartialEvadeChanceRating": 6081,
            "PartialEvadeMitigationRating": 6081,
            "PhysicalMitigationRating": 8656,
            "TacticalMitigationRating": 5473
        }
        
        # Character details
        self.character_armour = "Light"  # LoreMaster uses Light armour
        self.character_level = 100
        self.extra_stats = {}  # No extra stats for this test
        
        # Expected computed stats (from actual run of compute_percentage_simplified)
        self.expected_computed_stats = {
            # offensive stats
            "CriticalHitChanceMelee": 25.0,
            "CriticalHitChanceRange": 25.0,
            "CriticalHitChanceTactical": 25.0,
            "DevastatingHitChanceMelee": 9.6,
            "DevastatingHitChanceRange": 9.6,
            "DevastatingHitChanceTactical": 9.6,
            "Critical&DevastatingHitMagnitudeMelee": 53.4,
            "Critical&DevastatingHitMagnitudeRange": 53.4,
            "Critical&DevastatingHitMagnitudeTactical": 53.4,
            "Finesse": 26.8,
            "PhysicalDamageMelee": 40.4,
            "PhysicalDamageRange": 40.4,
            "TacticalOffenceDamage": 210.0,
            "TacticalOutgoingHealing": 52.8,
            # defensive stats
            "Resistance": 16.6,
            "CriticalDefence": 13.7,
            "IncomingHealing": 1.7,
            "BlockChance": 0,
            "PartialBlockChance": 0,
            "PartialBlockMitigation": 0,
            "ParryChance": 1.4,
            "PartialParryChance": 0.4,
            "PartialParryMitigation": 0.6,
            "EvadeChance": 9.8,
            "PartialEvadeChance": 12.0,
            "PartialEvadeMitigation": 16.9,
            "PhysicalMitigation": 37.0,
            "TacticalMitigation": 34.4,
        }
        
        # Expected no overcapped stats for this character
        self.expected_overcapped_stats = {}
    
    def test_compute_percentage_simplified(self):
        """Test compute_percentage_simplified produces expected results"""
        computed_stats, overcapped_stats = compute_percentage_simplified(
            self.sample_base_stats, 
            self.character_armour, 
            self.character_level, 
            self.extra_stats
        )
        
        # Test computed stats match expected values (within floating point precision)
        for stat_name, expected_percentage in self.expected_computed_stats.items():
            self.assertIn(stat_name, computed_stats, f"Stat {stat_name} should be in computed stats")
            actual_percentage = computed_stats[stat_name]
            self.assertAlmostEqual(
                actual_percentage, 
                expected_percentage, 
                places=1, 
                msg=f"Stat {stat_name}: expected {expected_percentage}%, got {actual_percentage}%"
            )
        
        # Test no overcapped stats
        self.assertEqual(overcapped_stats, self.expected_overcapped_stats, 
                        "Should have no overcapped stats")
    
    def test_helper_functions(self):
        """Test the helper functions work correctly"""
        # Test get_stat_type
        self.assertEqual(get_stat_type("CriticalRating"), "secondary")
        self.assertEqual(get_stat_type("CriticalRatingMelee"), "tertiary")
        self.assertEqual(get_stat_type("CriticalHitChanceMelee"), "final")
        self.assertEqual(get_stat_type("Might"), "main")
        self.assertEqual(get_stat_type("NonExistentStat"), "unknown")
        
        # Test get_related_stats
        self.assertEqual(get_related_stats("CriticalRating"), 
                        ["CriticalRatingMelee", "CriticalRatingRange", "CriticalRatingTactical"])
        self.assertEqual(get_related_stats("CriticalRatingMelee"), [])
        self.assertEqual(get_related_stats("CriticalHitChanceMelee"), ["CriticalRatingMelee"])
        self.assertEqual(get_related_stats("Might"), [])
        self.assertEqual(get_related_stats("BlockChanceRating"), 
                        ["TBlockChanceRating", "PartialBlockChanceRating", "PartialBlockMitigationRating"])
        self.assertEqual(get_related_stats("TBlockChanceRating"), [])
        
        # Test get_parent_stat
        self.assertEqual(get_parent_stat("CriticalHitChanceMelee"), "CriticalRatingMelee")
        self.assertEqual(get_parent_stat("CriticalRatingMelee"), "CriticalRating")
        self.assertIsNone(get_parent_stat("CriticalRating"))
        self.assertIsNone(get_parent_stat("Might"))
        self.assertEqual(get_parent_stat("BlockChance"), "TBlockChanceRating")
        self.assertEqual(get_parent_stat("TBlockChanceRating"), "BlockChanceRating")
    
    def test_stat_hierarchy_structure(self):
        """Test that the stat hierarchy is properly structured"""
        # Test that all expected stat types exist
        self.assertIn("main", STAT_HIERARCHY)
        self.assertIn("secondary", STAT_HIERARCHY)
        self.assertIn("tertiary", STAT_HIERARCHY)
        self.assertIn("final", STAT_HIERARCHY)
        
        # Test that main stats are properly categorized
        for stat in STAT_HIERARCHY["main"]:
            self.assertEqual(get_stat_type(stat), "main")
        
        # Test that secondary stats are properly categorized
        for stat in STAT_HIERARCHY["secondary"]:
            self.assertEqual(get_stat_type(stat), "secondary")
        
        # Test that tertiary stats are properly categorized
        for stat in STAT_HIERARCHY["tertiary"]:
            self.assertEqual(get_stat_type(stat), "tertiary")
        
        # Test that final stats are properly categorized
        for stat in STAT_HIERARCHY["final"]:
            self.assertEqual(get_stat_type(stat), "final")
    
    def test_stat_relationships(self):
        """Test that stat relationships are properly defined"""
        # Test that all secondary stats in relationships exist in secondary hierarchy
        for secondary_stat in STAT_RELATIONSHIPS:
            self.assertIn(secondary_stat, STAT_HIERARCHY["secondary"])
        
        # Test that all tertiary stats in relationships exist in tertiary hierarchy
        for secondary_stat, tertiary_list in STAT_RELATIONSHIPS.items():
            for tertiary_stat in tertiary_list:
                self.assertIn(tertiary_stat, STAT_HIERARCHY["tertiary"])

if __name__ == '__main__':
    unittest.main()

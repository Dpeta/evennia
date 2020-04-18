#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit test module for Trait classes.

"""

from copy import copy
from anything import Something
from mock import MagicMock, patch
from django.test import TestCase
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest
from evennia.contrib import traits


class _MockObj:
    def __init__(self):
        self.attributes = MagicMock()
        self.attributes.get = self.get
        self.attributes.add = self.add
        self.dbstore = {}
        self.category = "traits"

    def get(self, key, category=None):
        assert category == self.category
        return self.dbstore.get(key)

    def add(self, key, value, category=None):
        assert category == self.category
        self.dbstore[key] = value

# we want to test the base traits too
_TEST_TRAIT_CLASS_PATHS = [
    "evennia.contrib.traits.Trait",
    "evennia.contrib.traits.NumericTrait",
    "evennia.contrib.traits.StaticTrait",
    "evennia.contrib.traits.CounterTrait",
    "evennia.contrib.traits.GaugeTrait",
]

class _TraitHandlerBase(TestCase):
    "Base for trait tests"
    @patch("evennia.contrib.traits._TRAIT_CLASS_PATHS", new=_TEST_TRAIT_CLASS_PATHS)
    def setUp(self):
        self.obj = _MockObj()
        self.traithandler = traits.TraitHandler(self.obj)
        self.obj.traits = self.traithandler

    def _get_dbstore(self, key):
        return self.obj.dbstore['traits'][key]


class TraitHandlerTest(_TraitHandlerBase):
    """Testing for TraitHandler"""

    def setUp(self):
        super().setUp()
        self.traithandler.add(
            "test1",
            name="Test1",
            trait_type='trait'
        )
        self.traithandler.add(
            "test2",
            name="Test2",
            trait_type='trait',
            value=["foo", {"1": [1, 2, 3]}, 4],
        )

    def test_add_trait(self):
        self.assertEqual(
            self._get_dbstore("test1"),
            {"name": "Test1",
             "trait_type": 'trait',
             "value": None,
            }
        )
        self.assertEqual(
            self._get_dbstore("test2"),
            {"name": "Test2",
             "trait_type": 'trait',
             "value": ["foo", {"1": [1, 2, 3]}, 4],
            }
        )
        self.assertEqual(len(self.traithandler), 2)

    def test_cache(self):
        """
        Cache should not be set until first get
        """
        self.assertEqual(len(self.traithandler._cache), 0)
        self.traithandler.all  # does not affect cache
        self.assertEqual(len(self.traithandler._cache), 0)
        self.traithandler.test1
        self.assertEqual(len(self.traithandler._cache), 1)
        self.traithandler.test2
        self.assertEqual(len(self.traithandler._cache), 2)

    def test_setting(self):
        "Don't allow setting stuff on traithandler"
        with self.assertRaises(traits.TraitException):
            self.traithandler.foo = "bar"
        with self.assertRaises(traits.TraitException):
            self.traithandler["foo"] = "bar"

    def test_getting(self):
        "Test we are getting data from the dbstore"
        self.assertEqual(
            self.traithandler.test1._data,
            {"name": "Test1", "trait_type": "trait",
             "value": None}
        )
        self.assertEqual(
            self.traithandler._cache, Something
        )
        self.assertEqual(
            self.traithandler.test2._data,
            {"name": "Test2", "trait_type": "trait",
             "value": ["foo", {"1": [1, 2, 3]}, 4]}
        )
        self.assertEqual(
            self.traithandler._cache, Something
        )
        self.assertFalse(self.traithandler.get("foo"))
        self.assertFalse(self.traithandler.bar)

    def test_all(self):
        "Test all method"
        self.assertEqual(self.traithandler.all, ["test1", "test2"])

    def test_remove(self):
        "Test remove method"
        self.traithandler.remove("test2")
        self.assertEqual(len(self.traithandler), 1)
        self.assertTrue(bool(self.traithandler.get("test1")))  # this populates cache
        self.assertEqual(len(self.traithandler._cache), 1)
        with self.assertRaises(traits.TraitException):
            self.traithandler.remove("foo")

    def test_clear(self):
        "Test clear method"
        self.traithandler.clear()
        self.assertEqual(len(self.traithandler), 0)

    def test_trait_db_connection(self):
        "Test that updating a trait property actually updates value in db"
        trait = self.traithandler.test1
        self.assertEqual(trait.value, None)
        trait.value = 10
        self.assertEqual(trait.value, 10)
        self.assertEqual(
            self.obj.attributes.get("traits", category="traits")['test1']['value'],
            10
        )
        trait.value = 20
        self.assertEqual(trait.value, 20)
        self.assertEqual(
            self.obj.attributes.get("traits", category="traits")['test1']['value'],
            20
        )
        del trait.value
        self.assertEqual(
            self.obj.attributes.get("traits", category="traits")['test1']['value'],
            None
        )


class TraitTest(_TraitHandlerBase):
    """
    Test the base Trait class
    """

    def setUp(self):
        super().setUp()
        self.traithandler.add(
            "test1",
            name="Test1",
            trait_type="trait",
            value="value",
            extra_val1="xvalue1",
            extra_val2="xvalue2",
        )
        self.trait = self.traithandler.get("test1")

    def test_init(self):
        self.assertEqual(
            self.trait._data,
            {"name": "Test1",
             "trait_type": "trait",
             "value": "value",
             "extra_val1": "xvalue1",
             "extra_val2": "xvalue2"
            }
        )

    def test_validate_input__valid(self):
        """Test valid validation input"""
        # all data supplied, and extras
        dat = {
           "name": "Test",
           "trait_type": "trait",
           "value": 10,
           "extra_val": 1000
        }
        expected = copy(dat)  # we must break link or return === dat always
        self.assertEqual(expected, traits.Trait.validate_input(dat))

        # don't supply value, should get default
        dat = {
           "name": "Test",
           "trait_type": "trait",
           # missing value
           "extra_val": 1000
        }
        expected = copy(dat)
        expected["value"] = traits.Trait.data_keys['value']
        self.assertEqual(expected, traits.Trait.validate_input(dat))

        # make sure extra values are cleaned if trait accepts no extras
        dat = {
           "name": "Test",
           "trait_type": "trait",
           "value": 10,
           "extra_val1": 1000,
           "extra_val2": "xvalue"
        }
        expected = copy(dat)
        expected.pop("extra_val1")
        expected.pop("extra_val2")
        with patch.object(traits.Trait, "allow_extra_properties", False):
            self.assertEqual(expected, traits.Trait.validate_input(dat))

    def test_validate_input__fail(self):
        """Test failing validation"""
        dat = {
           # missing name
           "trait_type": "trait",
           "value": 10,
           "extra_val": 1000
        }
        with self.assertRaises(traits.TraitException):
            traits.Trait.validate_input(dat)

        # make value a required key
        mock_data_keys = {
            "value": traits.MandatoryTraitKey
        }
        with patch.object(traits.Trait, "data_keys", mock_data_keys):
            dat = {
               "name": "Trait",
               "trait_type": "trait",
               # missing value, now mandatory
               "extra_val": 1000
            }
            with self.assertRaises(traits.TraitException):
                traits.Trait.validate_input(dat)

    def test_trait_getset(self):
        """Get-set-del operations on trait"""
        self.assertEqual(self.trait.name, "Test1")
        self.assertEqual(self.trait['name'], "Test1")
        self.assertEqual(self.trait.value, "value")
        self.assertEqual(self.trait['value'], "value")
        self.assertEqual(self.trait.extra_val1, "xvalue1" )
        self.assertEqual(self.trait['extra_val2'], "xvalue2")

        self.trait.value = 20
        self.assertEqual(self.trait['value'], 20)
        self.trait['value'] = 20
        self.assertEqual(self.trait.value, 20)
        self.trait.extra_val1 = 100
        self.assertEqual(self.trait.extra_val1, 100)
        # additional properties
        self.trait.foo = "bar"
        self.assertEqual(self.trait.foo, "bar")

        del self.trait.foo
        with self.assertRaises(KeyError):
            self.trait['foo']
        with self.assertRaises(AttributeError):
            self.trait.foo
        del self.trait.extra_val1
        with self.assertRaises(AttributeError):
            self.trait.extra_val1
        del self.trait.value
        # fall back to default
        self.assertTrue(self.trait.value == traits.Trait.data_keys["value"])

    def test_repr(self):
        self.assertEqual(repr(self.trait), Something)
        self.assertEqual(str(self.trait), Something)


class TestTraitNumeric(_TraitHandlerBase):

    def test_trait__numeric(self):
        self.traithandler.add(
            "test2",
            name="Test2",
            trait_type='numeric',
        )
        self.assertEqual(
            self._get_dbstore("test2"),
            {"name": "Test2",
             "trait_type": 'numeric',
             "base": 0,
            }
        )




    def test_trait__static(self):
        self.traithandler.add(
            "test3",
            name="Test3",
            trait_type='static'
        )
        self.assertEqual(
            self._get_dbstore("test3"),
            {"name": "Test3",
             "trait_type": 'static',
             "base": 0,
             "mod": 0,
            }
        )

    def test_trait__counter(self):
        self.traithandler.add(
            "test4",
            name="Test4",
            trait_type='counter'
        )
        self.assertEqual(
            self._get_dbstore("test4"),
            {"name": "Test4",
             "trait_type": 'counter',
             "base": 0,
             "mod": 0,
             "current": 0,
             "max_value": None,
             "min_value": None,
            }
        )

    def test_trait__gauge(self):
        self.traithandler.add(
            "test5",
            name="Test5",
            trait_type='gauge'
        )
        self.assertEqual(
            self._get_dbstore("test5"),
            {"name": "Test5",
             "trait_type": 'gauge',
             "base": 0,
             "mod": 0,
             "current": 0,
             "max_value": None,
             "min_value": None,
            }
        )

#
#
# class TraitTestCase(TestCase):
#     """Test case for basic Trait functionality."""
#     def setUp(self):
#         # direct instantiation for testing only; use TraitHandler in production
#         self.trait = TraitStatic({
#             'trait_type': 'static',
#             'name': 'Strength',
#             'base': 8,
#             'mod': 0,
#         })
#
#     def tearDown(self):
#         self.trait = None
#
#     def check_trait(self, base=None, mod=None, actual=None):
#         """helper; allows one-line checking of `Trait` properties"""
#         if base is not None: self.assertEqual(self.trait.base, base)
#         if mod is not None: self.assertEqual(self.trait.mod, mod)
#         if actual is not None: self.assertEqual(self.trait.actual, actual)
#
#     def test_initial_state(self):
#         """`Trait` fixture object properties are as expected"""
#         self.assertEqual(self.trait.name, 'Strength')
#         self.check_trait(8, 0, 8)
#
#     def test_change_base(self):
#         """changes to `base` are reflected in `actual`"""
#         self.trait.base += 1
#         self.check_trait(9, 0, 9)
#
#     def test_change_mod(self):
#         """changes to `mod` are reflected in `actual`"""
#         self.trait.mod = 1
#         self.check_trait(8, 1, 9)
#
#     def test_reset_mod(self):
#         """`reset_mod()` function zeroes out `mod`"""
#         self.mod = 1
#         self.trait.reset_mod()
#         self.check_trait(8, 0, 8)
#
#
# class TraitExtraPropsTestCase(TestCase):
#     """Test case for Trait extra properties functionality."""
#     def setUp(self):
#         # direct instantiation for testing only; use TraitHandler in production
#         self.trait = Trait({
#             'type': 'static',
#             'name': 'Strength',
#             'base': 8,
#             'mod': 0,
#             'extra': {'preloaded': True},
#         })
#
#     def tearDown(self):
#         self.trait = None
#
#     def test_extra_props_get(self):
#         """test that extra properties are gettable"""
#         # access via getattr
#         self.assertTrue(self.trait.preloaded)
#         # access via getitem
#         self.assertTrue(self.trait['preloaded'])
#
#     def test_extra_props_set(self):
#         """test that extra properties are settable"""
#         # set via setattr
#         self.trait.skill_points = 2
#         self.assertIn('skill_points', self.trait.extra)
#         # set via setitem
#         self.trait['skill_points'] = 2
#         self.assertIn('skill_points', self.trait.extra)
#
#     def test_extra_props_del(self):
#         """test that extra properties are deletable"""
#         # delete via delattr
#         del self.trait.preloaded
#         self.assertNotIn('preloaded', self.trait.extra)
#         with self.assertRaises(AttributeError):
#              x = self.trait.preloaded
#         # delete via delitem
#         del self.trait['preloaded']
#         self.assertNotIn('preloaded', self.trait.extra)
#         with self.assertRaises(KeyError):
#              x = self.trait['preloaded']
#
# class TraitOperatorsTestCase(TestCase):
#     """Test case for numeric magic method implementations."""
#     def setUp(self):
#         # direct instantiation for testing only; use TraitHandler in production
#         self.st = Trait({
#             'name': 'Strength',
#             'type': 'static',
#             'base': 8,
#         })
#         self.at = Trait({
#             'name': 'Attack',
#             'type': 'static',
#             'base': 4,
#         })
#
#     def tearDown(self):
#         self.st, self.at = None, None
#
#     def test_pos_shortcut(self):
#         """overridden unary + operator returns `actual` property"""
#         self.assertIn(type(+self.st), (float, int))
#         self.assertEqual(+self.st, self.st.actual)
#         self.assertEqual(+self.st, 8)
#
#     def test_add_traits(self):
#         """test addition of `Trait` objects"""
#         # two Trait objects
#         self.assertEqual(self.st + self.at, 12)
#         # Trait and numeric
#         self.assertEqual(self.st + 1, 9)
#         self.assertEqual(1 + self.st, 9)
#
#     def test_sub_traits(self):
#         """test subtraction of `Trait` objects"""
#         # two Trait objects
#         self.assertEqual(self.st - self.at, 4)
#         # Trait and numeric
#         self.assertEqual(self.st - 1, 7)
#         self.assertEqual(10 - self.st, 2)
#
#     def test_mul_traits(self):
#         """test multiplication of `Trait` objects"""
#         # between two Traits
#         self.assertEqual(self.st * self.at, 32)
#         # between Trait and numeric
#         self.assertEqual(self.at * 4, 16)
#         self.assertEqual(4 * self.at, 16)
#
#     def test_floordiv(self):
#         """test floor division of `Trait` objects"""
#         # between two Traits
#         self.assertEqual(self.st // self.at, 2)
#         # between Trait and numeric
#         self.assertEqual(self.st // 2, 4)
#         self.assertEqual(18 // self.st, 2)
#
#     def test_comparisons_traits(self):
#         """test equality comparison between `Trait` objects"""
#         self.assertNotEqual(self.st, self.at)
#         self.assertLess(self.at, self.st)
#         self.assertLessEqual(self.at, self.st)
#         self.assertGreater(self.st, self.at)
#         self.assertGreaterEqual(self.st, self.at)
#         # make st.actual = at.actual by modding at
#         self.at.mod = 4
#         self.assertEqual(self.st, self.at)
#         self.assertGreaterEqual(self.st, self.at)
#         self.assertLessEqual(self.st, self.at)
#
#     def test_comparisons_numeric(self):
#         """equality comparisons between `Trait` and numeric"""
#         self.assertEqual(self.st, 8)
#         self.assertEqual(8, self.st)
#         self.assertNotEqual(self.st, 0)
#         self.assertNotEqual(0, self.st)
#         self.assertLess(self.st, 10)
#         self.assertLess(0, self.st)
#         self.assertLessEqual(self.st, 8)
#         self.assertLessEqual(8, self.st)
#         self.assertLessEqual(self.st, 10)
#         self.assertLessEqual(0, self.st)
#         self.assertGreater(self.st, 0)
#         self.assertGreater(10, self.st)
#         self.assertGreaterEqual(self.st, 8)
#         self.assertGreaterEqual(8, self.st)
#         self.assertGreaterEqual(self.st, 0)
#         self.assertGreaterEqual(10, self.st)
#
#
# class CounterTraitTestCase(TestCase):
#     """Test case for counter trait functionality."""
#     def setUp(self):
#         # direct instantiation for testing only; use TraitHandler in production
#         self.trait = Trait({
#             'type': 'counter',
#             'name': 'Bonus/Penalty',
#             'base': 0,
#             'mod': 0,
#             'min': -3,
#             'max': 3,
#         })
#
#     def tearDown(self):
#         self.trait = None
#
#     def check_trait(self, base=None, mod=None, current=None,
#                     actual=None, min=None, max=None,):
#         """helper; allows one-line checking of Trait properties"""
#         if base is not None: self.assertEqual(self.trait.base, base)
#         if mod is not None: self.assertEqual(self.trait.mod, mod)
#         if current is not None: self.assertEqual(self.trait.current, current)
#         if actual is not None: self.assertEqual(self.trait.actual, actual)
#         if min is not None: self.assertEqual(self.trait.min, min)
#         if max is not None: self.assertEqual(self.trait.max, max)
#
#     def test_initial_state(self):
#         """fixture object properties are as expected"""
#         self.assertEqual(self.trait.name, 'Bonus/Penalty')
#         self.check_trait(0, 0, 0, 0, -3, 3)
#
#     def test_upper_bound(self):
#         """`current` may not be set above `max` when `max` is numeric"""
#         self.trait.current = 5
#         self.check_trait(0, 0, 3, 3, -3, 3)
#
#     def test_upper_unbound(self):
#         """`current` may be set very high when `max` is None"""
#         self.trait.max = None
#         self.trait.current = 10000000
#         self.check_trait(0, 0, 10000000, 10000000, -3, None)
#
#     def test_lower_bound(self):
#         """`current` may not be set below `min` when `min` is numeric"""
#         self.trait.current = -5
#         self.check_trait(0, 0, -3, -3, -3, 3)
#
#     def test_lower_unbound(self):
#         """`current` may be set very low when `min` is None"""
#         self.trait.min = None
#         self.trait.current = -10000000
#         self.check_trait(0, 0, -10000000, -10000000, None, 3)
#
#     def test_mod(self):
#         """confirm `mod` functionality mid-range"""
#         self.trait.mod = 2
#         self.check_trait(0, 2, 0, 2, -3, 3)
#
#     def test_mod_upper_bound(self):
#         """`actual` is constrained even if `current`+`mod` exceed `max`"""
#         self.trait.current = 2
#         self.trait.mod = 4
#         self.check_trait(0, 4, 2, 3, -3, 3)
#
#     def test_mod_lower_bound(self):
#         """`actual` is constrained even if `current`+`mod` exceeds `min`"""
#         self.trait.current = -2
#         self.trait.mod = -4
#         self.check_trait(0, -4, -2, -3, -3, 3)
#
#     def test_no_max_below_base(self):
#         """`max` may not be set below `base`"""
#         self.trait.max = -1
#         self.check_trait(0, 0, 0, 0, -3, 0)
#
#     def test_no_base_above_max(self):
#         """`base` may not be set above `max`"""
#         self.trait.base = 5
#         self.check_trait(3, 0, 3, 3, -3, 3)
#
#     def test_no_min_above_base(self):
#         """`min` may not be set above `base`"""
#         self.trait.min = 1
#         self.check_trait(0, 0, 0, 0, 0, 3)
#
#     def test_no_base_below_min(self):
#         """`base` may not be set below `min`"""
#         self.trait.base = -5
#         self.check_trait(-3, 0, -3, -3, -3, 3)
#
#     def test_reset_counter(self):
#         """`reset_to_base()` method sets `current` = `base`"""
#         self.trait.current = 2
#         self.check_trait(0, 0, 2, 2, -3, 3)
#         self.trait.reset_counter()
#         self.check_trait(0, 0, 0, 0, -3, 3)
#
#     def test_percent_divzero(self):
#         """confirm `percent()`functionality when unbounded and `base`=0"""
#         self.trait.min = self.trait.max = None
#         self.check_trait(0, 0, 0, 0, None, None)
#         self.assertEqual(self.trait.percent(), '100.0%')
#         self.trait.current = 20
#         self.check_trait(0, 0, 20, 20, None, None)
#         self.assertEqual(self.trait.percent(), '100.0%')
#
#
# class GaugeTraitTestCase(TestCase):
#     """Test case for `GaugeTrait` functionality"""
#     def setUp(self):
#         # direct instantiation for testing only; use TraitHandler in production
#         self.trait = Trait({
#             'name': 'HP',
#             'type': 'gauge',
#             'base': 10,
#             'mod': 0,
#             'min': 0,
#             'max': 'base'
#         })
#
#     def tearDown(self):
#         self.trait = None
#
#     def check_trait(self, base=None, mod=None, current=None,
#                     actual=None, min=None, max=None,):
#         """helper; allows one-line checking of Trait properties"""
#         if base is not None: self.assertEqual(self.trait.base, base)
#         if mod is not None: self.assertEqual(self.trait.mod, mod)
#         if current is not None: self.assertEqual(self.trait.current, current)
#         if actual is not None: self.assertEqual(self.trait.actual, actual)
#         if min is not None: self.assertEqual(self.trait.min, min)
#         if max is not None: self.assertEqual(self.trait.max, max)
#
#     def test_initial_state(self):
#         """fixture object properties are as expected"""
#         self.assertEqual(self.trait.name, 'HP')
#         self.check_trait(10, 0, 10, 10, 0, 10)
#
#     def test_change_base(self):
#         """test that changing base property is not constrained when `max`='base'"""
#         self.trait.base = 20
#         self.check_trait(20, 0, 20, 20, 0, 20)
#
#     def test_buff_full(self):
#         """increasing `mod` increases `current`"""
#         self.trait.mod = 2
#         self.check_trait(10, 2, 12, 12, 0, 12)
#         self.trait.reset_mod()
#         self.check_trait(10, 0, 10, 10, 0, 10)
#         self.trait.current = 5
#         self.trait.mod = 2
#         self.check_trait(10, 2, 7, 7, 0, 12)
#
#     def test_debuff_full(self):
#         """decreasing `mod` decreases `current` if it would be above `max`"""
#         self.trait.mod = -2
#         self.check_trait(10, -2, 8, 8, 0, 8)
#         self.trait.reset_mod()
#         self.trait.current = 5
#         self.trait.mod = -2
#         self.check_trait(10, -2, 5, 5, 0, 8)
#
#     def test_fill_max_base(self):
#         """`overfill()` method functionality with default `max`=`base` config"""
#         self.trait.current = 5
#         self.check_trait(10, 0, 5, 5, 0, 10)
#         self.trait.fill_gauge()
#         self.check_trait(10, 0, 10, 10, 0, 10)
#
#     def test_fill_max_static(self):
#         """`overfill()` method functionality with static number `max` config"""
#         self.trait.max = 20
#         self.trait.current = 5
#         self.check_trait(10, 0, 5, 5, 0, 20)
#         self.trait.fill_gauge()
#         self.check_trait(10, 0, 15, 15, 0, 20) # can exceed `mod`+`base`
#         self.trait.fill_gauge()
#         self.check_trait(10, 0, 20, 20, 0, 20) # but not `max`
#
#     def test_fill_max_unbounded(self):
#         """`overfill()` method functionality with unbounded `max` config"""
#         self.trait.max = None
#         self.trait.current = 5
#         self.trait.mod = 2
#         self.check_trait(10, 2, 7, 7, 0, None)
#         self.trait.fill_gauge()
#         self.check_trait(10, 2, 19, 19, 0, None)
#
#     def test_percent_base(self):
#         """`percent()` method functionality with `max`=`base`"""
#         self.trait.base = 100
#         self.trait.current = 69
#         self.check_trait(100, 0, 69, 69, 0, 100)
#         self.assertEqual(self.trait.percent(), '69.0%')
#
#     def test_percent_static(self):
#         """`percent()` method functionality with static number `max` config."""
#         self.trait.base = 30
#         self.trait.mod += 3
#         self.trait.max = 99
#         self.check_trait(30, 3, 33, 33, 0, 99)
#         self.assertEqual(self.trait.percent(), '33.3%')
#
#     def test_percent_unbounded(self):
#         """`percent()` method functionality with unbounded `max` config."""
#         self.trait.base = 50
#         self.trait.max = None
#         self.trait.current = 75
#         self.check_trait(50, 0, 75, 75, 0, None)
#         self.assertEqual(self.trait.percent(), '150.0%')
#
#
# class TraitFactoryTestCase(EvenniaTest):
#     """Test case for the TraitHandler class."""
#     def setUp(self):
#         super(TraitFactoryTestCase, self).setUp()
#         self.traits = TraitHandler(self.char1)
#
#     def test_add_get(self):
#         """test adding and getting Traits via TraitHandler"""
#         self.traits.add(
#             key='str', name='Strength', type='static')
#
#         t = self.traits.get('str')
#         self.assertIsInstance(t, Trait)
#         self.assertEqual(t.name, "Strength")
#         self.assertEqual(t._type, "static")
#
#     def test_len_remove(self):
#         """test response to len() and removing Traits from TraitHandler"""
#         self.traits.add(
#             key='str', name='Strength', type='static')
#
#         self.assertEqual(len(self.traits), 1)
#         self.traits.remove('str')
#         self.assertEqual(len(self.traits), 0)
#
#     def test_all_clear(self):
#         """test `all` property and clear function on TraitHandler"""
#         self.traits.add(
#             key='str', name='Strength', type='static')
#         self.traits.add(
#             key='bonus', name='Bonus', type='counter')
#         self.traits.add(
#             key='hp', name='HP', type='gauge')
#
#         self.assertEqual(frozenset(self.traits.all),
#                          frozenset(['str', 'bonus', 'hp']))
#         self.assertEqual(len(self.traits), 3)
#         self.traits.clear()
#         self.assertEqual(len(self.traits), 0)
#
#     def test_alternate_access(self):
#         """test `Trait` access by attribute and dict item syntax"""
#         self.traits.add(
#             key='str', name='Strength', type='static')
#
#         # as attribute
#         self.assertIsInstance(self.traits.str, Trait)
#         self.assertEqual(self.traits.str.name, 'Strength')
#         # as dict key
#         self.assertIsInstance(self.traits['str'], Trait)
#         self.assertEqual(self.traits['str'].name, 'Strength')
#
#     def test_assignment_error(self):
#         """ensure attempting to assign to a Trait key on a TraitHandler fails."""
#         with self.assertRaises(TraitException):
#             self.traits.str = 5
#         with self.assertRaises(TraitException):
#             self.traits['str'] = 5
#
#     def test_defaults_static(self):
#         """check defaults for static trait optional parameters in config"""
#         self.traits.add(
#             key='str', name='Strength', type='static')
#
#         st = self.traits.str
#         self.assertEqual(st._type, 'static')
#         self.assertEqual(st.base, 0)
#         self.assertEqual(st.mod, 0)
#         self.assertEqual(st.current, 0)
#         self.assertEqual(st.actual, 0)
#         with self.assertRaises(AttributeError):
#             x = st.min
#         with self.assertRaises(AttributeError):
#             x = st.max
#
#     def test_defaults_counter(self):
#         """check defaults for counter trait optional parameters in config"""
#         self.traits.add(
#             key='bonus', name='Bonus', type='counter')
#
#         bo = self.traits.bonus
#         self.assertEqual(bo._type, 'counter')
#         self.assertEqual(bo.base, 0)
#         self.assertEqual(bo.mod, 0)
#         self.assertIs(bo.min, None)
#         self.assertIs(bo.max, None)
#         self.assertEqual(bo.extra, [])
#
#     def test_defaults_gauge(self):
#         """check defaults for gauge trait optional parameters in config"""
#         self.traits.add(
#             key='hp', name='HP', type='gauge')
#
#         hp = self.traits.hp
#         self.assertEqual(hp._type, 'gauge')
#         self.assertEqual(hp.name, 'HP')
#         self.assertEqual(hp.base, 0)
#         self.assertEqual(hp.mod, 0)
#         self.assertEqual(hp.current, 0)
#         self.assertEqual(hp.min, 0)
#         self.assertEqual(hp.max, 0)
#         self.assertEqual(hp.extra, [])
#
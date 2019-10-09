from __future__ import print_function
# Copyright 2018 - Sean Donovan
# AtlanticWave/SDX Project

import unittest
import logging
import os
from localctlr.LCRuleManager import *
from shared.SDXControllerConnectionManagerConnection import SDXMessageInstallRule, SDXMessageRemoveRule


class InitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.logger = logging.getLogger(cls.__name__)
        formatter = logging.Formatter('%(asctime)s %(name)-12s: %(thread)s %(levelname)-8s %(message)s')
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(formatter)
        cls.logger.setLevel(logging.DEBUG)
        cls.logger.handlers = []
        cls.logger.addHandler(console)
        cls.logger.debug("Beginning %s:%s" % (os.path.basename(__file__),
                                              cls.__name__))

        import sys
        cls.logger.debug("BEGIN %s" % cls.__name__)
        cls.logger.debug("sys.path: %s" % sys.path)
        
    def test_singleton(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        firstManager = LCRuleManager()
        secondManager = LCRuleManager()

        print(">>>>>>>>>>>> %s" % (firstManager is secondManager))
        self.failUnless(firstManager is secondManager)

    def test_init_fields(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        m = LCRuleManager("lcrulemanagertest.db")
        # if this doesn't blow up, we should be good.
        #FIXME: how to verify the DB is good?

class AddRuleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.logger = logging.getLogger(cls.__name__)
        formatter = logging.Formatter('%(asctime)s %(name)-12s: %(thread)s %(levelname)-8s %(message)s')
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(formatter)
        cls.logger.setLevel(logging.DEBUG)
        cls.logger.handlers = []
        cls.logger.addHandler(console)

        cls.logger.debug("Beginning %s:%s" % (os.path.basename(__file__),
                                              cls.__name__))

    def test_good_add_rules(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        m = LCRuleManager()
        rule = "FAKE RULE"
        cookie = 1
        switch_id = 10
        status = RULE_STATUS_INSTALLING
        m.add_rule(cookie, switch_id, rule, status)
        # We'll test that we can get the rule in a bit.

    def test_add_bad_status(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        m = LCRuleManager()
        rule = "FAKE RULE"
        cookie = 2
        switch_id = 10
        status = "NOT A REAL STATUS"
        self.failUnlessRaises(LCRuleManagerTypeError,
                              m.add_rule, cookie, switch_id, rule, status)

    def test_duplicate_add(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        m = LCRuleManager()
        rule = "FAKE RULE"
        cookie = 3
        switch_id = 10
        status = RULE_STATUS_INSTALLING
        m.add_rule(cookie, switch_id, rule, status)

        self.failUnlessRaises(LCRuleManagerValidationError,
                              m.add_rule, cookie, switch_id, rule, status)
    #FIXME: Should there be other check here?

    
class GetRuleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.logger = logging.getLogger(cls.__class__.__name__)
        formatter = logging.Formatter('%(asctime)s %(name)-12s: %(thread)s %(levelname)-8s %(message)s')
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(formatter)
        cls.logger.setLevel(logging.DEBUG)
        cls.logger.handlers = []
        cls.logger.addHandler(console)

        cls.logger.debug("Beginning %s:%s" % (os.path.basename(__file__),
                                              cls.__name__))

    def test_get_known_rule(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        # Add rule, then get it to confirm that it was correct.
        m = LCRuleManager()
        rule1 = "FAKE RULE"
        cookie1 = 11
        switch_id1 = 10
        status1 = RULE_STATUS_INSTALLING
        m.add_rule(cookie1, switch_id1, rule1, status1)

        getrules = m.get_rules(cookie1, switch_id1)
        self.failUnlessEqual(rule1, getrules[0])

        rule2 = "TOTALLY REAL RULE"
        cookie2 = 12
        switch_id2 = 20
        status2 = RULE_STATUS_INSTALLING
        m.add_rule(cookie2, switch_id2, rule2, status2)
        getrules = m.get_rules(cookie1, switch_id1)
        print(">>>>>>>>>", getrules)
        
        self.failUnlessEqual(rule1, getrules[0])
        getrules = m.get_rules(cookie2, switch_id2)
        print(">>>>>>>>>", getrules)
        self.failUnlessEqual(rule2, getrules[0])

    def test_get_unknown_rule(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        # Try to get a rule that doesn't exist, should return none
        m = LCRuleManager()
        rule1 = "FAKE RULE"
        cookie1 = 13
        switch_id1 = 10
        status1 = RULE_STATUS_INSTALLING
        m.add_rule(cookie1, switch_id1, rule1, status1)


        rule2 = "TOTALLY REAL RULE"
        cookie2 = 14
        switch_id2 = 20
        status2 = RULE_STATUS_INSTALLING
        # NOT ADDING THIS ONE!
        #m.add_rule(cookie2, rule2, status2)

        getrules = m.get_rules(cookie1, switch_id1)
        self.failUnlessEqual(rule1, getrules[0])
        getrules = m.get_rules(cookie2, switch_id2)
        self.failUnlessEqual([], getrules)

    def test_get_rule_full_tuple(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        #FIXME
        pass
    

class FindRuleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.logger = logging.getLogger(cls.__class__.__name__)
        formatter = logging.Formatter('%(asctime)s %(name)-12s: %(thread)s %(levelname)-8s %(message)s')
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(formatter)
        cls.logger.setLevel(logging.DEBUG)
        cls.logger.handlers = []
        cls.logger.addHandler(console)

        cls.logger.debug("Beginning %s:%s" % (os.path.basename(__file__),
                                              cls.__name__))

    def test_find_all_empty_rules(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        # Immediately check for rules
        m = LCRuleManager()
        m.__init__()
        rules = m._find_rules()
        self.failUnlessEqual([], rules)

    def test_find_all_rules(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        m = LCRuleManager()
        m.__init__()
        rule1 = "FAKE RULE"
        cookie1 = 21
        switch_id1 = 10
        status1 = RULE_STATUS_INSTALLING
        m.add_rule(cookie1, switch_id1, rule1, status1)

        rule2 = "TOTALLY REAL RULE"
        cookie2 = 22
        switch_id2 = 20
        status2 = RULE_STATUS_INSTALLING
        m.add_rule(cookie2, switch_id2, rule2, status2)

        rules = m._find_rules()
        print(">>>> rules: %s" % rules)
        self.failUnlessEqual(len(rules), 2)

    def test_find_filtered_cookie_rules(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        m = LCRuleManager()
        m.__init__()
        rule1 = "FAKE RULE"
        cookie1 = 23
        switch_id1 = 10
        status1 = RULE_STATUS_INSTALLING
        m.add_rule(cookie1, switch_id1, rule1, status1)

        rule2 = "TOTALLY REAL RULE"
        cookie2 = 24
        switch_id2 = 20
        status2 = RULE_STATUS_INSTALLING
        m.add_rule(cookie2, switch_id2, rule2, status2)

        rules = m._find_rules({'cookie':23})
        self.failUnlessEqual(len(rules), 1)

    def test_find_filtered_status_rules(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        m = LCRuleManager()
        m.__init__()
        rule1 = "FAKE RULE"
        cookie1 = 25
        switch_id1 = 10
        status1 = RULE_STATUS_INSTALLING
        m.add_rule(cookie1, switch_id1, rule1, status1)

        rule2 = "TOTALLY REAL RULE"
        cookie2 = 26
        switch_id2 = 20
        status2 = RULE_STATUS_ACTIVE
        m.add_rule(cookie2, switch_id2, rule2, status2)

        rules = m._find_rules({'status':RULE_STATUS_ACTIVE})
        self.failUnlessEqual(len(rules), 1)


    def test_find_filtered_rule_rules(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        #FIXME: This is impractical right now, so not going to test it.
        pass
    
    

class ChangeStatusTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.logger = logging.getLogger(cls.__class__.__name__)
        formatter = logging.Formatter('%(asctime)s %(name)-12s: %(thread)s %(levelname)-8s %(message)s')
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(formatter)
        cls.logger.setLevel(logging.DEBUG)
        cls.logger.handlers = []
        cls.logger.addHandler(console)

        cls.logger.debug("Beginning %s:%s" % (os.path.basename(__file__),
                                              cls.__name__))

    def test_good_status_change(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        m = LCRuleManager()
        m.__init__()
        rule1 = "FAKE RULE"
        cookie1 = 31
        switch_id1 = 10
        status1 = RULE_STATUS_INSTALLING
        m.add_rule(cookie1, switch_id1, rule1, status1)

        rules = m.get_rules(cookie1, switch_id1, True)
        self.failIfEqual(rules, [])
        for rule in rules:
            print("$$$$$$ %s" % str(rule))
            (pre_cookie, pre_switch_id, pre_rule, pre_status) = rule
            self.failUnlessEqual(pre_status, status1)

        status2 = RULE_STATUS_ACTIVE
        m.set_status(cookie1, switch_id1, status2)

        rules = m.get_rules(cookie1, switch_id1, True)

        self.failUnlessEqual(len(rules), 1)
        self.failIfEqual(rules, [])
        for rule in rules:
            (post_cookie, post_switch_id, post_rule, post_status) = rule
            self.failUnlessEqual(post_status, status2)
        self.failIfEqual(status1, status2)

    def test_invalid_status_change(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        m = LCRuleManager()
        m.__init__()
        rule1 = "FAKE RULE"
        cookie1 = 32
        switch_id1 = 10
        status1 = RULE_STATUS_INSTALLING
        m.add_rule(cookie1, switch_id1, rule1, status1)

        rules = m.get_rules(cookie1, switch_id1, True)
        self.failIfEqual(rules, [])
        for rule in rules:
            (pre_cookie, pre_switch_id, pre_rule, pre_status) = rule
            self.failUnlessEqual(pre_status, status1)

        status2 = "FAKE STATUS!"
        self.failUnlessRaises(LCRuleManagerValidationError,
                              m.set_status, cookie1, switch_id1, status2)
    

class RemoveRuleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.logger = logging.getLogger(cls.__class__.__name__)
        formatter = logging.Formatter('%(asctime)s %(name)-12s: %(thread)s %(levelname)-8s %(message)s')
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(formatter)
        cls.logger.setLevel(logging.DEBUG)
        cls.logger.handlers = []
        cls.logger.addHandler(console)

        cls.logger.debug("Beginning %s:%s" % (os.path.basename(__file__),
                                              cls.__name__))

    def test_remove_known_rule(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        m = LCRuleManager()
        m.__init__()
        rule1 = "FAKE RULE"
        cookie1 = 41
        switch_id1 = 10
        status1 = RULE_STATUS_INSTALLING
        m.add_rule(cookie1, switch_id1, rule1, status1)

        pre_rule = m.get_rules(cookie1, switch_id1)
        self.failUnlessEqual(pre_rule, [rule1])

        m.rm_rule(cookie1, switch_id1)
        post_rule = m.get_rules(cookie1, switch_id1)
        self.failUnlessEqual(post_rule, [])
    
    def test_remove_unknown_rule(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        m = LCRuleManager()
        m.__init__()
        cookie1 = 42
        switch_id1 = 10
        self.failUnlessRaises(LCRuleManagerDeletionError,
                              m.rm_rule, cookie1, switch_id1)

    def test_duplicate_remove_rule(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        m = LCRuleManager()
        m.__init__()
        rule1 = "FAKE RULE"
        cookie1 = 43
        switch_id1 = 10
        status1 = RULE_STATUS_INSTALLING
        m.add_rule(cookie1, switch_id1, rule1, status1)

        pre_rule = m.get_rules(cookie1, switch_id1)
        self.failUnlessEqual(pre_rule, [rule1])

        m.rm_rule(cookie1, switch_id1)
        post_rule = m.get_rules(cookie1, switch_id1)
        self.failUnlessEqual(post_rule, [])

        self.failUnlessRaises(LCRuleManagerDeletionError,
                              m.rm_rule, cookie1, switch_id1)
    
        


class InitialRulesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.logger = logging.getLogger(cls.__class__.__name__)
        formatter = logging.Formatter('%(asctime)s %(name)-12s: %(thread)s %(levelname)-8s %(message)s')
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(formatter)
        cls.logger.setLevel(logging.DEBUG)
        cls.logger.handlers = []
        cls.logger.addHandler(console)

        cls.logger.debug("Beginning %s:%s" % (os.path.basename(__file__),
                                              cls.__name__))

    def test_add_initial_rule(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        # Make sure it doesn't blow up
        m = LCRuleManager()
        m.__init__()
        cookie1 = 51
        switch_id1 = 10
        rule1 = SDXMessageInstallRule("Fake Rule")
        m.add_initial_rule(rule1, cookie1, switch_id1)
    
    def test_add_initial_rule_in_db(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        # With empty DB, add initial rule, then call initial rules complete
        # Verify that rule was added
        m = LCRuleManager()
        m.__init__()
        cookie1 = 52
        switch_id1 = 10
        rule1 = SDXMessageInstallRule("FAKE RULE")
        status1 = RULE_STATUS_INSTALLING
        m.add_initial_rule(rule1, cookie1, switch_id1)

        (del_list, add_list) = m.initial_rules_complete()
        m.clear_initial_rules()
        print("  ^^^^ add_list: %s" % add_list)
        print("  ^^^^ del_list: %s" % del_list)

        #for (r, c, sw) in add_list:
        for rule in add_list:
            (r,c,sw) = rule
            print(" ^^^^ ASDF       %s:%s:%s" % (r, c, sw))
            s = RULE_STATUS_INSTALLING
            m.add_rule(c, sw, r, s)
        for (r, c, sw) in del_list:
            m.rm_rule(c, sw)

        rules = m.get_rules(cookie1, switch_id1, True)
        self.failIfEqual(rules, [])
        for rule in rules:
            (c, sw, r, s) = rule
            self.failUnlessEqual(r, rule1)

    def test_initial_rule_rm_rule(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        # Add two rules, add only one of them as an initial rule, call
        # initial rules complete, confirm that one still exists and the other is
        # removed.
        m = LCRuleManager()
        m.__init__()
        rule1 = "FAKE RULE"
        cookie1 = 53
        switch_id1 = 10
        status1 = RULE_STATUS_INSTALLING
        m.add_rule(cookie1, switch_id1, rule1, status1)

        rules = m.get_rules(cookie1, switch_id1, True)
        self.failIfEqual(rules, [])
        print("    ^&^&^&^&^ %s" % rules)
        for rule in rules:
            (c,sw,r,s) = rule
            self.failUnlessEqual(rule1, r)

        rule2 = "TOTALLY REAL RULE"
        cookie2 = 54
        switch_id2 = 20
        status2 = RULE_STATUS_INSTALLING
        m.add_rule(cookie2, switch_id2, rule2, status2)

        rules = m.get_rules(cookie1, switch_id1, True)
        self.failIfEqual(rules, [])
        for rule in rules:
            (c,sw,r,s) = rule
            print("  $$$$ RULE: %s:%s:%s" % (c, sw, r))
        for rule in rules:
            (c,sw,r,s) = rule
            self.failUnlessEqual(rule1, r)
        rules = m.get_rules(cookie2, switch_id2, True)
        self.failIfEqual(rules, [])
        for rule in rules:
            (c,sw,r,s) = rule
            print("  $$$$ RULE: %s:%s:%s" % (c, sw, r))
        for rule in rules:
            (c,sw,r,s) = rule
            self.failUnlessEqual(rule2, r)

        m.add_initial_rule(SDXMessageInstallRule(rule1), cookie1, switch_id1)
        
        (del_list, add_list) = m.initial_rules_complete()
        m.clear_initial_rules()
        for (r, c, sw) in add_list:
            s = RULE_STATUS_INSTALLING
            m.add_rule(c, sw, r, s)
        for (r, c, sw) in del_list:
            m.rm_rule(c, sw)


        rules = m.get_rules(cookie1, switch_id1, True)
        self.failIfEqual(rules, [])
        for rule in rules:
            (c, sw, r, s) = rule
            self.failUnlessEqual(r, rule1)

        rules = m.get_rules(cookie2, switch_id2, True)
        self.failUnlessEqual([], rules)
        

    def test_initial_rule_twice_rule(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        # Empty DB, add rule with initial_rules, remove same rule so DB's empty
        # again, add a different initial_rule, confirm that only the second
        # initial rule is added 
        m = LCRuleManager()
        m.__init__()
        rule1 = "FAKE RULE"
        cookie1 = 55
        switch_id1 = 10
        status1 = RULE_STATUS_INSTALLING

        rule2 = "TOTALLY REAL RULE"
        cookie2 = 56
        switch_id2 = 20
        status2 = RULE_STATUS_INSTALLING

        m.add_initial_rule(SDXMessageInstallRule(rule1), cookie1, switch_id1)

        (del_list, add_list) = m.initial_rules_complete()
        m.clear_initial_rules()
        for (r, c, sw) in add_list:
            s = RULE_STATUS_INSTALLING
            m.add_rule(c, sw, r, s)
        for (r, c, sw) in del_list:
            m.rm_rule(c, sw)


        rules = m._find_rules()
        self.failUnlessEqual(1, len(rules))
        rules = m.get_rules(cookie1, switch_id1, True)
        self.failIfEqual(rules, [])
        for rule in rules:
            (c, sw, r, s) = rule
            self.assertEqual(rule1, r.data['rule'])
        rules = m.get_rules(cookie2, switch_id2)
        self.failUnlessEqual(rules, [])


        m.rm_rule(cookie1, switch_id1)

        rules = m._find_rules()
        self.failUnlessEqual(0, len(rules)) #empty
        
        m.add_initial_rule(SDXMessageInstallRule(rule2), cookie2, switch_id2)

        (del_list, add_list) = m.initial_rules_complete()
        m.clear_initial_rules()
        for (r, c, sw) in add_list:
            s = RULE_STATUS_INSTALLING
            m.add_rule(c, sw, r, s)
        for (r, c, sw) in del_list:
            m.rm_rule(c, sw)

        rules = m._find_rules()
        print("((((((((RULES %s" %rules)
        self.failUnlessEqual(1, len(rules))
        rules = m.get_rules(cookie1, switch_id1)
        self.failUnlessEqual([], rules)

        rules = m.get_rules(cookie2, switch_id2, True)
        self.failIfEqual(rules, [])
        for rule in rules:
            (c,sw,r,s) = rule
            self.failUnlessEqual(rule2, r.data['rule'])

if __name__ == '__main__':
    unittest.main()

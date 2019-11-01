# Copyright 2016 - Sean Donovan
# AtlanticWave/SDX Project


# Unit tests for the AuthenticationInspector class

import unittest
import threading
#import mock
import os

from sdxctlr.AuthenticationInspector import *


class SingletonTest(unittest.TestCase):
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
        firstInspector = AuthenticationInspector()
        secondInspector = AuthenticationInspector()
        self.failUnless(firstInspector is secondInspector)

class AddingUsers(unittest.TestCase):
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
        
    def test_add_single_user(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        user = "john"
        credentials = "pa$$word"
        
        ai = AuthenticationInspector()
        ai.add_user(user, credentials)
        self.failUnless(ai.is_authenticated(user, credentials))

    def test_add_many_users(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        user1 = "natasha"
        credentials1 = "moose"
        user2 = "boris"
        credentials2 = "squirrel"
        userlist = ((user1, credentials1),
                    (user2, credentials2))
        ai = AuthenticationInspector()
        ai.add_users(userlist)
        self.failUnless(ai.is_authenticated(user1, credentials1))
        self.failUnless(ai.is_authenticated(user2, credentials2))


    def test_overwrite_user(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        user = "bob"
        credentials1 = "qwerty"
        credentials2 = "asdf"

        ai = AuthenticationInspector()
        ai.add_user(user, credentials1)
        self.failUnless(ai.is_authenticated(user, credentials1))

        # Change password
        ai.add_user(user, credentials2)
        self.failUnless(ai.is_authenticated(user, credentials2))
        self.failUnlessEqual(ai.is_authenticated(user, credentials1),
                             False)

class NonUserTest(unittest.TestCase):
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
        
    def test_non_user(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        user = "badname"
        credentials = "badnamepw"
        ai = AuthenticationInspector()
        self.failUnlessEqual(ai.is_authenticated(user, credentials),
                             False)

    def test_bad_password(self):
        self.logger.warning("BEGIN %s" % (self.id()))
        user = "james"
        credentials = "beard"
        badcredentials = "moustache"

        ai = AuthenticationInspector()
        ai.add_user(user, credentials)
        self.failUnless(ai.is_authenticated(user, credentials))
        self.failUnlessEqual(ai.is_authenticated(user, badcredentials),
                             False)


if __name__ == '__main__':
    unittest.main()

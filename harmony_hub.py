#!/usr/bin/env python3
"""
This is the Harmony Hub NodeServer for ISY and Polyglot v2 written in Python2/3
by JimBo jimboca3@gmail.com
"""

import polyinterface
import sys

LOGGER = polyinterface.LOGGER

# Harmony Hub Main Controller
from harmony_hub_nodes import HarmonyController

if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('HarmonyHub')
        """
        Instantiates the Interface to Polyglot.
        """
        polyglot.start()
        """
        Starts MQTT and connects to Polyglot.
        """
        control = HarmonyController(polyglot)
        """
        Creates the Controller Node and passes in the Interface
        """
        control.runForever()
        """
        Sits around and does nothing forever, keeping your program running.
        """
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
        """
        Catch SIGTERM or Control-C and exit cleanly.
        """

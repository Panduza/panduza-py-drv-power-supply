# adapted from https://github.com/fdmysterious/python-lab-control/blob/master/instr/ql335p.py

import logging
import io
import time
import re

import time
from hamcrest import empty
import serial
from loguru import logger
from panduza_platform import MetaDriverPsu

import functools

class DriverQL335P(MetaDriverPsu):
    
    def __init__(self):
        super().__init__()

    def config(self):
        """ FROM MetaDriver
        """

        return {
            "compatible": "psu_ql335p",
            "info": { "type": "psu", "version": "1.0" },
            "settings": {
                "serial_port" : "Serial port on which the power supply is connected"
            }
        }

    def setup(self, tree):
        """ FROM MetaDriver
        """
        # Initialize variables
        self.supported_settings = self.api_settings.copy()

        self.api_attributes["volts"]["max"] = 30
        self.api_attributes["volts"]["scale"] = 0.01

        self.api_attributes["amps"]["max"] = 5
        self.api_attributes["amps"]["scale"] = 0.001
        
        self.api_attributes["model_name"] = "QL335P"

        if "serial_port" not in tree["settings"]:
            logger.error("Setting serial_port is mandatory for this driver")
            return False

        self.serial_port = tree["settings"]["serial_port"]

        self.dev               = serial.serial_for_url(self.serial_port, do_not_open=True)
        self.dev.baudrate      = 19200
        self.dev.bytesize      = serial.EIGHTBITS
        self.dev.parity        = serial.PARITY_NONE
        self.dev.stopbits      = serial.STOPBITS_ONE
        self.dev.rtscts        = False

        self.dev.timeout       = 10
        self.dev.write_timeout = 10

        # https://stackoverflow.com/questions/10222788/line-buffered-serial-input
        self.io                = io.TextIOWrapper(
            self.dev,
            encoding       = "ascii",
            newline        = None,
            line_buffering = False
        )
        self.io._CHUNK_SIZE= 1

        self.tree_settings = tree["settings"].copy()

        # Register commands
        self.psu_register_command("state", self.__set_state)
        self.psu_register_command("volts", self.__set_volts)
        self.psu_register_command("amps", self.__set_amps)

        for key in self.tree_settings.copy():
            if key not in self.supported_settings:
                logger.warning("Driver ql335p does not support setting " + key + " and will ignore it.")
                self.remove_setting(self.supported_settings, key)
            else:
                self.supported_settings[key] = self.tree_settings[key]

        self.api_attributes["settings"] = self.supported_settings

    ###########################################################################
    ###########################################################################

    def on_start(self):
        self.dev.open()
        super().on_start()
        pass

    ###########################################################################
    ###########################################################################
        
    def loop(self):
        """ FROM MetaDriver
        """
        return False

    ###########################################################################
    ###########################################################################

    def __write(self, *cmds):
        # Append new line terminator to all commands
        txt = "".join( map(lambda x: f"{x}\r\n", cmds) )

        self.log.debug(f"TX: {txt!r}")
        self.io.write(txt)
        self.io.flush()

    ###########################################################################
    ###########################################################################

    def __set_state(self, payload): # set psu output on or off
        """
        """
        req = self.payload_to_dict(payload)
        req_state = req["state"]
        # Update enable
        self.state = req_state
        if self.state == "on":
            cmd = True
        elif self.state == "off":
            cmd = False

        self.__write(f"OP1 {int(cmd)}")
        self.psu_push_attribute("state", self.state)
        logger.info(f"new state :" + str(payload))


    def __set_volts(self, payload):
        req = self.payload_to_dict(payload)
        self.api_attributes["volts"]["value"] = req["volts"]
        print(req["volts"])
        volts = req["volts"]
        
        self.__write(f"V1 {volts:.3f}")

        self.psu_push_attribute("volts", self.api_attributes["volts"])
        logger.info(f"new volts :" + str(payload))


    def __set_amps(self, payload):
        req = self.payload_to_dict(payload)
        self.api_attributes["amps"]["value"] = req["amps"]
        print(req["amps"])
        amps = req["amps"]
        self.__write(f"I1 {amps:.3f}")

        self.psu_push_attribute("amps", self.api_attributes["amps"])
        logger.info(f"new amps :" + str(payload))

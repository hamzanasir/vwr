#!/usr/bin/env python
"""Python driver for [VWR circulating baths]
(https://us.vwr.com/store/catalog/product.jsp?catalog_number=89203-002).

Distributed under the GNU General Public License v2
Copyright (C) 2015 NuMat Technologies
"""
import socket
from threading import Timer


class CirculatingBath(object):
    """Python driver for [VWR circulating baths](https://us.vwr.com/store/
    catalog/product.jsp?catalog_number=89203-002).

    This class communicates with the circulating bath over UDP sockets.
    """
    max_delay = 60
    initial_delay = 1
    factor = 2

    def __init__(self, address, password=100, timeout=None):
        """Opens ports to communicate with the circulating bath.

        Args:
            address: The IP address of the device
            password: The password next to "Unlock" in the user interface
                settings. Default 100.
            timeout: Max time to wait for response, in seconds. Default None
                (blocking).
        """
        self.address = address
        self.password = password
        self.timeout = timeout
        self.connected = False
        self.delay = self.initial_delay
        self._reconnect()

    def _connect(self):
        """Connects to the device using two UDP raw sockets.

        The interface is bizarre in that the device expects requests on
        port 1024, but replies on port 1026. To get around, we use two
        separate sockets and handle blocking with the `self.waiting` boolean.
        """
        self.sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listener.bind(('', 1026))
        self.waiting = False
        if self.timeout:
            self.listener.settimeout(self.timeout)
        self.get_setpoint()  # dummy request to check if bath is connected
        self.connected = True
        self.delay = self.initial_delay

    def _reconnect(self):
        """Reconnects on decay to the bath"""
        try:
            self._connect()
        except socket.timeout:
            self.delay = min(self.delay * self.factor, self.max_delay)
            Timer(self.delay, self._reconnect).start()

    def turn_on(self):
        """Turns the circulating bath on.

        Returns:
            True if successful, else False.
        """
        self.listener.settimeout(5)
        self._send('SO1P{}'.format(self.password))
        response = self._receive()
        self.listener.settimeout(self.timeout)
        return (response == '!')

    def turn_off(self):
        """Turns the circulating bath off.

        Note that turning the bath off takes multiple seconds before a response
        is sent. Be careful when using this method with a set timeout.

        Returns:
            True if successful, else False.
        """
        self.listener.settimeout(5)
        self._send('SO0P{}'.format(self.password))
        response = self._receive()
        self.listener.settimeout(self.timeout)
        return (response == '!')

    def check_fault(self):
        """Checks for faults with the bath

        Returns:
            True if faulty, else False
        """
        self._send('RF')
        response = self._receive()
        return (response == '1')

    def get(self):
        """Gets the setpoint and internal temperature."""
        response = {'setpoint': self.get_setpoint(),
                    'actual': self.get_internal_temperature(),
                    'pump': self.get_pump_speed(),
                    'on': self.get_operating_status(),
                    'fault': self.check_fault(),
                    'connected': True}
        if self.connected and all(v is not None for v in response.values()):
            return response
        else:
            return {'connected': False}

    def get_setpoint(self):
        """Gets the setpoint temperature."""
        self._send('RS')
        response = self._receive()
        return float(response) if response else None

    def get_temperature_units(self):
        """Gets the temperature units, e.g. C or F."""
        self._send('RU')
        return self._receive()

    def get_internal_temperature(self):
        """Gets the temperature inside the bath."""
        self._send('RT')
        response = self._receive()
        return float(response) if response else None

    def get_external_temperature(self):
        """If connected, get the temperature of the external thermocouple."""
        self._send('RR')
        return self._receive()

    def get_operating_status(self):
        """Returns a boolean indicating if bath is operating."""
        self._send('RO')
        response = self._receive()
        return bool(int(response)) if response else None

    def get_pump_speed(self):
        """Returns pump speed as an integer indicating percent, 5-100."""
        self._send('RM')
        response = self._receive()
        return int(response) if response else None

    def set_setpoint(self, setpoint):
        """Sets setpoint temperature.

        Args:
            setpoint: Setpoint temperature, in machine units, as a float.
        Returns:
            True if successful, else False.
        """
        self._send('SS{:.2f}P{:d}'.format(setpoint, self.password))
        return (self._receive() == '!')

    def set_pump_speed(self, speed):
        """Sets pump speed.

        Args:
            setpoint: Pump speed as an integer, 5-100. Will be rounded to
                nearest 5.
        Returns:
            True if successful, else False.
        """
        rounded_speed = int(5 * round(speed / 5))
        self._send('SM{:d}P{:d}'.format(rounded_speed, self.password))
        return (self._receive() == '!')

    def close(self):
        """Closes the listening port."""
        self.listener.close()

    def _send(self, message):
        """Selds a message to the circulating bath."""
        if self.waiting or not self.connected:
            Timer(1, self._send, [message]).start()
        else:
            self.waiting = True
            try:
                self.sender.sendto((message + '\r').encode('utf-8'),
                                   (self.address, 1024))
            except socket.timeout:
                if self.connected:
                    self.connected = False
                    self._reconnect()
                self.waiting = False

    def _receive(self):
        """Receives messages from the circulating bath."""
        try:
            message, _ = self.listener.recvfrom(512)
            response = message.decode('utf-8').strip()
        except socket.timeout:
            response = None
            if self.connected:
                self.connected = False
                self._reconnect()
                return None
        self.waiting = False
        return response

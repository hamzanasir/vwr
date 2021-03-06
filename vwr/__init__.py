#!/usr/bin/env python
"""Python driver, command-line tool, and web server for [VWR circulating baths]
(https://us.vwr.com/store/catalog/product.jsp?catalog_number=89203-002).

Distributed under the GNU General Public License v2
Copyright (C) 2015 NuMat Technologies
"""
import argparse
import socket
import sys
import webbrowser
from vwr import server
from vwr.driver import CirculatingBath


def command_line():
    """Command-line interface to driver. Run with `vwr`."""
    parser = argparse.ArgumentParser(description="Control a VWR circulating "
                                     "bath from a web site.")
    parser.add_argument("address", help="The IP address of the bath.")
    parser.add_argument("--require-login", "-l", action="store_true",
                        help="Redirects users to a password login screen.")
    parser.add_argument("--set-password", "-p", action="store_true",
                        help="Start a dialog to set the password of the "
                        "website login page.")
    parser.add_argument("--set-temperature", "-t", default=None, type=float,
                        help="Sets the bath temperature.")
    parser.add_argument("--port", default=50000, type=int, help="The "
                        "port on which to run the web server. Default 50000.")
    parser.add_argument("--unlock-code", "-u", default=100, type=int,
                        help="The code opposite the 'Unlock' option on the "
                        "VWR circulating bath. Default 100.")
    args = parser.parse_args()

    bath = CirculatingBath(args.address, password=args.unlock_code)

    if args.set_password:
        server.set_password()

    try:
        setpoint = bath.get_setpoint()
        actual = bath.get_internal_temperature()
        units = bath.get_temperature_units()
        print(("Current state: {setpoint:.2f} {units} "
              "setpoint, {actual:.2f} {units} actual").format(**locals()))
    except socket.timeout:
        sys.stderr.write("Could not connect to VWR circulating bath"
                         ". Is it running at {}?\n".format(args.address))
        bath.close()
        sys.exit(0)

    if args.set_temperature:
        success = bath.set_setpoint(args.set_temperature)
        if success:
            print(("Successfully set temperature to {setpoint:.2f}"
                  " {units}.").format(setpoint=args.set_temperature,
                                      units=units))
        else:
            sys.stderr.write("Failed to set temperature.")

    print("Running server at http://localhost:{}/".format(args.port))
    webbrowser.open("http://localhost:{}/".format(args.port), new=2)
    try:
        server.run_server(bath, port=args.port,
                          require_login=args.require_login)
    finally:
        bath.close()


if __name__ == "__main__":
    command_line()

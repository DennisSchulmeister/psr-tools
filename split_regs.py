#! /usr/bin/env python
#encoding=utf-8
# psr-tools: split_regs (http://www.patk.org)
# Copyright (C) 2011  Dennis Schulmeister <dennis@patk.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse, os, sys
import psr9000.regbank as regbank

if __name__ == "__main__":
    cmd_parser = argparse.ArgumentParser(
        prog        = "psr-tools: split_regs",
        version     = "0.2",
        description = "Simple tool to rearrange PSR-9000 registrations"
    )

    cmd_parser.add_argument(
        "-s", "--split",
        action  = "store_true",
        default = False,
        help    = "Read backup and print registration map",
    )

    cmd_parser.add_argument(
        "-c", "--create",
        action  = "store_true",
        default = False,
        help    = "Read backup and registration map in order to create new backup",
    )

    cmd_parser.add_argument(
        "-i", "--input",
        help    = "Name of old user data backup",
    )

    cmd_parser.add_argument(
        "-o", "--output",
        help    = "Name of new user data backup",
    )

    cmd_parser.add_argument(
        "-m", "--map",
        help    = "Map file. Default is to read StdIn / write StdOut"
    )

    cmd_arguments = cmd_parser.parse_args()

    if not cmd_arguments.split and not cmd_arguments.create:
        sys.exit("Specify either --split or --create")
    elif not cmd_arguments.input:
        sys.exit("Missing --input option is always required")
    elif cmd_arguments.create and not cmd_arguments.output:
        sys.exit("Missing --output option is required in create mode")
    elif cmd_arguments.input == cmd_arguments.output:
        sys.exit("Input must be different from output")
    elif not os.path.exists(cmd_arguments.input):
        sys.exit("Input directory does not exit")
    elif not os.path.isdir(cmd_arguments.input):
        sys.exit("Input file is no directory")
    elif not os.path.exists(os.path.join(cmd_arguments.input, "Regist.reg")):
        sys.exit("No registrations found inside input directory")
    elif cmd_arguments.output and os.path.exists(cmd_arguments.output):
        sys.exit("Output directory already exits")

    banks = regbank.read_banks(cmd_arguments.input)

    if cmd_arguments.split:
        if cmd_arguments.map and os.path.exists(cmd_arguments.map):
            sys.exit("Map file already exists")

        if cmd_arguments.map:
            map_file = open(cmd_arguments.map, "w")
        else:
            map_file = sys.stdout

        regbank.write_registration_map(banks, map_file)

        if cmd_arguments.map:
            map_file.close()
    elif cmd_arguments.create:
        if cmd_arguments.map and not os.path.exists(cmd_arguments.map):
            sys.exit("Map file does not exist")

        if cmd_arguments.map:
            map_file = open(cmd_arguments.map, "r")
        else:
            map_file = sys.stdin

        registration_map = regbank.read_registration_map(map_file)
        new_banks = regbank.rearrange_registrations(banks, registration_map)
        regbank.write_banks(new_banks, cmd_arguments.output)

        if cmd_arguments.map:
            map_file.close()
    else:
        sys.exit("Abort due to unknown operation mode!")

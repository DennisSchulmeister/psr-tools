#! /usr/bin/env python
#encoding=utf-8
# psr-tools: patch_regs (http://www.patk.org)
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

def patch_banks(banks, start, new_bytes):
    '''
    Takes an list of registration banks as created by read_banks(), an integer
    offset and a bytes object. All non-empty registrations in all banks are
    patched accordingly.
    '''
    start = start - 32
    end = start + len(new_bytes)

    for bank in banks:
        for registration in bank["registrations"]:
            if registration["empty"]:
                continue

            for new_byte in new_bytes:
                registration["data"] = registration["data"][:start] \
                                     + new_bytes + registration["data"][end:]

if __name__ == "__main__":
    cmd_parser = argparse.ArgumentParser(
        prog        = "psr-tools: patch_regs",
        version     = "0.1",
        description = "Simple tool to patch PSR-9000 registrations"
    )

    cmd_parser.add_argument(
        "-i", "--input",
        metavar = "input",
        help    = "Name of old user data backup",
    )

    cmd_parser.add_argument(
        "-o", "--output",
        metavar = "output",
        help    = "Name of new user data backup",
    )

    cmd_parser.add_argument(
        "-s", "--seek",
        metavar = "seek",
        type    = int,
        help    = "Seek position inside each registration",
    )

    cmd_parser.add_argument(
        "-b", "--bytes",
        metavar = "bytes",
        help    = "Hex-string with bytes to be written (e.g. 310f)",
    )

    cmd_arguments = cmd_parser.parse_args()

    if not cmd_arguments.input:
        sys.exit("Missing --input option is always required")
    elif not cmd_arguments.output:
        sys.exit("Missing --output option is always required")
    elif not os.path.exists(cmd_arguments.input):
        sys.exit("Input directory does not exit")
    elif not os.path.isdir(cmd_arguments.input):
        sys.exit("Input file is no directory")
    elif not os.path.exists(os.path.join(cmd_arguments.input, "Regist.reg")):
        sys.exit("No registrations found inside input directory")
    elif cmd_arguments.seek < 32:
        sys.exit("Seek position must be greater than 32 bytes to skip registration header")
    elif not cmd_arguments.bytes:
        sys.exit("Missing --bytes option is always required")

    if cmd_arguments.input == cmd_arguments.output:
        sys.stderr.write("WARNING: Input directory is the same as output directory\n")

    banks = regbank.read_banks(cmd_arguments.input)
    patch_banks(banks, cmd_arguments.seek, bytearray.fromhex(cmd_arguments.bytes))
    regbank.write_banks(banks, cmd_arguments.output)

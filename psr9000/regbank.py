#! /usr/bin/env python
#encoding=utf-8
# psr-tools: psr-9000 registration bank library (http://www.patk.org)
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

import os, struct

def filter_string(string):
    '''
    Cuts a C-string so that it doesn't contain \x00-bytes anymore.
    '''
    length = string.find("\x00")

    if length < 0:
        return string.rstrip()
    elif length == 0:
        return ""
    else:
        return string[:length].rstrip()

def read_banks(input_dir):
    '''
    Reads in registrations and returns a list of all banks with contained
    registrations. The list is of following format:

    [
        {
            "number": 1,
            "name": "Bank 1",
            "position": 12345,
            "size": 432,
            "registrations": [
                {
                    "number": 1,
                    "empty": False,
                    "name": "Registration 1",
                    "size": 321,
                    "head": b"0x... 0x...",
                    "data": b"0x... 0x...",
                },
                ...
            ]
        },
        ...
    ]

    Missing banks or registrations are considered empty. Therefor a bank is
    not required to have exactly eight registrations. The head field contains
    the complete registration header including the name, as it has been read
    from the file (32 bytes).

    Raises a ValueError if the binary registration file cannot be parsed.
    '''
    banks = []
    registration_file = open(os.path.join(input_dir, "Regist.reg"), "rb")
    magic_bytes = registration_file.read(4)

    if not magic_bytes == "\xd0\x06\x00\x00":
        raise ValueError("Unknown registration format: %s" % magic_bytes)

    registration_file.seek(0)

    for i in range(64):
        index_entry = registration_file.read(48)

        if len(index_entry) < 48:
            raise ValueError("Aborting due to truncated data file")

        bank_size, bank_position, bank_number, bank_name = struct.unpack("> 16x l l B 16s 6x x", index_entry)
        bank_name = filter_string(bank_name)

        if not bank_size:
            continue

        banks.append({
            "number": bank_number,
            "name": bank_name,
            "position": bank_position,
            "size": bank_size,
            "registrations": []
        })

    for bank in banks:
        offset = 48
        registration_file.seek(bank["position"] + offset)

        while offset < bank["size"]:
            reg_head = registration_file.read(32)
            reg_id, reg_size, reg_name = struct.unpack("> 6s l 6x 16s", reg_head)

            reg_name = filter_string(reg_name)
            reg_number = int(reg_id[3:])
            reg_data = registration_file.read(reg_size - 22)
            reg_empty = reg_head[11] == b"\x00"

            offset += len(reg_head) + len(reg_data)

            bank["registrations"].append({
                "number": reg_number,
                "empty": reg_empty,
                "name": reg_name,
                "size": reg_size,
                "head": reg_head,
                "data": reg_data,
            })

    registration_file.close()
    return banks

def write_registration_map(banks, map_file):
    '''
    Takes a list of registrations as created by read_banks() and a data stream
    where a textual map of all registration banks is printed. The output format
    is rather simple:

    01|N|Bank Name
    01|1|Registration 1
    01|2|Registration 20
    01|3|Registration 3
    01|4|Registration 4
    01|5|Registration 5
    01|6|
    01|7|Registration 7
    01|8|Registration 8

    02|N|Bank Name
    02|1|Registration 1
    02|2|Registration 2
    ...

    Bank numbers are printed as decimals and only existing non-empty banks
    are printed. Empty registrations have no name.
    '''
    for bank in banks:
        bank_number = bank["number"] + 1

        if bank_number < 10:
            bank_number = "0" + str(bank_number)
        else:
            bank_number = str(bank_number)[:2]

        map_file.write("%s|N|%s\n" % (bank_number, bank["name"]))

        index = -1
        for registration in bank["registrations"]:
            index += 1

            while index < registration["number"]:
                map_file.write("%s|%s|\n" % (bank_number, index + 1))
                index += 1

            map_file.write("%s|%s|%s\n" % (bank_number, registration["number"] + 1, registration["name"]))

        while index < 7:
            map_file.write("%s|%s|\n" % (bank_number, index + 1))
            index += 1

        map_file.write("\n")

def read_registration_map(map_file):
    '''
    Reads a textual registration map as created by write_registration_map()
    and modified by the user. Every registration without a name is considered
    to be empty. Bank number -1 means "next bank". -2 means to skip one bank,
    -3 means to skip two banks and so on.

    A list like the following is returned:

    [
        {
            "number": 1,
            "name": "Bank name",
            "registrations": [
                {
                    "empty": False,
                    "bank": 23,
                    "registration": 3,
                    "name": "Registration name",
                },
                ...
            ]
        },
        ...
    ]

    Empty registrations only have the "empty" field set to True. The other
    fields are not present, then.

    The user is allowed to change the number of a bank at the first line
    of each bank. She is also allowed to change bank and registration names.
    The other fields must remain untouched as they describe where a registration
    comes from.

    Raises a ValueError if the map file contains syntax errors.
    '''
    registration_map = []
    current_bank = {}
    bank_number = -1

    def syntax_error(msg, line):
        raise ValueError("Syntax error in map file\n%s\n%s" % (msg, line))

    def append_current_bank():
        if bank_number < 0:
            return

        if "registrations" in current_bank:
            current_bank["registrations"] = current_bank["registrations"][:8]
            missing_registrations =  8 - len(current_bank["registrations"])

            for i in range(missing_registrations):
                current_bank["registrations"].append({"empty": True})

        registration_map.append(current_bank)

    for line in map_file:
        line = line.strip()

        if not line:
            continue

        fields = line.split("|")

        if len(fields) != 3:
            syntax_error("Expected 3 fields but got %s" % len(fields), line)

        fields[0] = fields[0].strip()
        fields[1] = fields[1].strip()
        fields[2] = fields[2]

        if fields[0]:
            try:
                fields[0] = int(fields[0])
            except ValueError as err:
                syntax_error(err.message, line)

        if fields[1] == "N":
            append_current_bank()

            if fields[0] < 0:
                bank_number += (fields[0] * -1)
            else:
                bank_number = fields[0] - 1

            current_bank = {
                "number": bank_number,
                "name": fields[2],
                "registrations": [],
            }
        else:
            if bank_number < 0:
                syntax_error("Registrations without bank found", line)

            if not fields[2]:
                current_bank["registrations"].append({"empty": True})
            else:
                current_bank["registrations"].append({
                    "empty": False,
                    "bank": fields[0] - 1,
                    "registration": int(fields[1]) - 1,
                    "name": fields[2],
                })

    append_current_bank()
    return registration_map

def rearrange_registrations(banks, registration_map):
    '''
    Takes a bank list as createy by read_banks() and a registration map as
    created by read_registration_map() in order to create a new bank list.
    Raises a KeyError if a registration or bank cannot be found.
    '''
    new_banks = []
    bank_position = 0x0C10

    for map_bank in registration_map:
        current_bank = {
            "number": map_bank["number"],
            "name": map_bank["name"],
            "position": bank_position,
            "size": 48,
            "registrations": []
        }

        reg_number = -1

        for map_registration in map_bank["registrations"]:
            reg_number += 1
            reg_empty = True
            reg_name = ""
            reg_size = 0
            reg_head = b""
            reg_data = b""

            if map_registration["empty"]:
                current_bank["size"] += 583
            else:
                found_bank = None
                found_registration = None

                for bank in banks:
                    if bank["number"] == map_registration["bank"]:
                        found_bank = bank
                        break

                if not found_bank:
                    raise KeyError("Couldn't find bank number %s'" % map_registration["bank"])

                for registration in found_bank["registrations"]:
                    if registration["number"] == map_registration["registration"]:
                        found_registration = registration
                        break

                if not found_registration:
                    raise KeyError("Couldn't find registration %s in bank %s'" % (map_registration["registration"], map_registration["bank"]))

                reg_name = map_registration["name"]
                reg_size = found_registration["size"]
                reg_head = found_registration["head"]
                reg_data = found_registration["data"]
                reg_empty = found_registration["empty"]

                current_bank["size"] += reg_size + 10

            current_bank["registrations"].append({
                "number": reg_number,
                "empty": reg_empty,
                "name": reg_name,
                "size": reg_size,
                "head": reg_head,
                "data": reg_data,
            })


        bank_position += current_bank["size"]
        new_banks.append(current_bank)

    return new_banks

def write_banks(banks, output_dir):
    '''
    Writes the given list of registration banks to the output directory. The
    output directory will be a valid user data backup. This function ignores
    the header field from the registration list.
    '''
    already_exists = os.path.exists(output_dir)

    if not already_exists:
        os.mkdir(output_dir)

    registration_file = open(os.path.join(output_dir, "Regist.reg"), "wb")
    bank_files = []
    amount = 0

    for bank in banks:
        amount += 1

        if amount == 1:
            registration_file.write("\xd0\x06" + 14 * "\x00")
            first_bank = False
        else:
            registration_file.write(16 * "\x00")

        if bank["number"] < 16:
            hex_number = "0" + hex(bank["number"])[2:]
        else:
            hex_number = hex(bank["number"])[2:4]

        long_name = bank["name"] + ((16 - len(bank["name"])) * " ") + "%s.reg" % (hex_number.upper())
        index_bytes = struct.pack("> l l B 22s x", bank["size"], bank["position"], bank["number"], long_name)
        registration_file.write(index_bytes)
        bank_files.append(long_name)

    while amount < 64:
        amount += 1
        registration_file.write(48 * "\x00")

    registration_file.write(16 * "\x00")

    for bank in banks:
        bank_bytes = struct.pack("> 16s 32s", bank["name"], "PSR-9000PREGIST Ver1.00         ")
        registration_file.write(bank_bytes)

        for registration in bank["registrations"]:
            registration_file.write("REG00" + str(registration["number"]))

            if not registration["empty"] and registration["name"]:
                registration_file.write(struct.pack("> l", registration["size"]))
                registration_file.write("\x08\x01\x00\x00\x00\x00")
                registration_file.write(struct.pack("16s", registration["name"]))
                registration_file.write(registration["data"])
            else:
                registration_file.write(struct.pack("> l", 573))
                registration_file.write(573 * "\x00")

    registration_file.close()

    if not already_exists:
        config_file = open(os.path.join(output_dir, "USERFILE.INI"), "wb")
        config_file.write("[TITLE]\r\n")
        config_file.write("9000Pro USERFILE.INI\r\n")
        config_file.write("YAMAHA Corporation\r\n")
        config_file.write("[DISK NO]\r\n")
        config_file.write("DISK000\r\n")
        config_file.write("[INSTRUMENT]\r\n")
        config_file.write("9000Pro\r\n")
        config_file.write("[VERSION]\r\n")
        config_file.write("Ver2.06\r\n")
        config_file.write("[TOTAL USER DATA SIZE]\r\n")
        config_file.write("%sKB\r\n" % os.stat(os.path.join(output_dir, "Regist.reg")).st_size)
        config_file.write("[REGISTRATION]\r\n")
        config_file.write("TOTAL FILE NUM:%s\r\n" % len(bank_files))

        index = 0

        for bank_file in bank_files:
            index += 1
            config_file.write("%s = %s\r\n" % (index, bank_file))

        config_file.write("[DATAEND]\r\n")
        config_file.close()

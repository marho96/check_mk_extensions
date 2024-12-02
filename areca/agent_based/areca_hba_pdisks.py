#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# +------------------------------------------------------------------+
#
# This file is an addon for Check_MK.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.


# hddEnclosure01Slots:
#.1.3.6.1.4.1.18928.1.2.3.2.4.1.1.1 = 1
#.1.3.6.1.4.1.18928.1.2.3.2.4.1.1.20 = 20
# hddEnclosure01Desc:
#.1.3.6.1.4.1.18928.1.2.3.2.4.1.2.1 = "SLOT 01"
# hddEnclosure01Name:
#.1.3.6.1.4.1.18928.1.2.3.2.4.1.3.20 = "WDC WD30EFRX-68AX9N0                    "
# hddEnclosure01Serial:
#.1.3.6.1.4.1.18928.1.2.3.2.4.1.4.20 = "1234567            "
# hddEnclosure01FirmVer:
#.1.3.6.1.4.1.18928.1.2.3.2.4.1.5.20 = "CC1H    "
# hddEnclosure01Capacity:
#.1.3.6.1.4.1.18928.1.2.3.2.4.1.6.1 = 0
#.1.3.6.1.4.1.18928.1.2.3.2.4.1.6.20 = 3000600
# hddEnclosure01Type:
#.1.3.6.1.4.1.18928.1.2.3.2.4.1.7.1 = 0
#.1.3.6.1.4.1.18928.1.2.3.2.4.1.7.20 = 1
#  hddEnclosure01State:
#.1.3.6.1.4.1.18928.1.2.3.2.4.1.8.1 = "Empty Slot"
#.1.3.6.1.4.1.18928.1.2.3.2.4.1.8.20 = "RaidSet Member"

# How to grok:
#.1.3.6.1.4.1.18928.1.2.3.E.4.1.F.D
#                         |     | |
#                         |     | +---enc disk id
#                         |     +-----field
#                         +-------enclosure

max_enclosures = 8

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    startswith,
)
from cmk.agent_based.v2.render import bytes

def parse_areca_hba_pdisks(string_table):
    section = {}
    slot_type = {
        "1": "SATA",
        "2": "SAS",
    }
    for encl in range(max_enclosures):
        installed, desc = string_table[encl * 2][0]
        if installed == "1":
            section[encl + 1] = {
                "name": desc,
                "slots": {},
            }
            for id, desc, name, serial, firmver, capacity, typ, state in string_table[encl * 2 + 1]:
                if state != "Empty Slot":
                    section[encl + 1]["slots"][int(id)] = {
                        "desc": desc,
                        "name": name,
                        "serial": serial,
                        "firmver": firmver,
                        "capacity": int(capacity) * 1024 *1024,
                        "type": slot_type.get(typ),
                        "state": state,
                    }
    return section

def discover_areca_hba_pdisks(section) -> DiscoveryResult:
    for encl in section.keys():
        for slot in section[encl]["slots"].keys():
            yield Service(item="%d/%02d" % (encl, slot))

def check_areca_hba_pdisks(item, section) -> CheckResult:
    encl, slot = list(map(int, item.split("/")))
    if encl in section:
        if slot in section[encl]["slots"]:
            data = section[encl]["slots"][slot]
            yield Result(state=State.OK, summary="%s %s %s (%s)" % (data["name"], data["serial"], data["firmver"], bytes(data["capacity"])))
            if data["state"] == "Failed":
                yield Result(state=State.CRIT, summary="failed")

snmp_sections = []
for encl in range(1, max_enclosures + 1):
    snmp_sections.append(SNMPTree(
        base = f".1.3.6.1.4.1.18928.1.2.3.{encl}",
        oids = [
            "1.0", # ARECA-SNMP-MIB::hddEnclosureNNInstalled
            "2.0", # ARECA-SNMP-MIB::hddEnclosureNNDescription
        ],
    ))
    snmp_sections.append(SNMPTree(
        base = f".1.3.6.1.4.1.18928.1.2.3.{encl}.4.1",
        oids = [
            "1", # ARECA-SNMP-MIB::hddEnclosureNNSlots
            "2", # ARECA-SNMP-MIB::hddEnclosureNNDesc
            "3", # ARECA-SNMP-MIB::hddEnclosureNNName
            "4", # ARECA-SNMP-MIB::hddEnclosureNNSerial
            "5", # ARECA-SNMP-MIB::hddEnclosureNNFirmVer
            "6", # ARECA-SNMP-MIB::hddEnclosureNNCapacity
            "7", # ARECA-SNMP-MIB::hddEnclosureNNType
            "8", # ARECA-SNMP-MIB::hddEnclosureNNState
        ],
    ))

snmp_section_areca_hba_pdisks = SNMPSection(
    name = "areca_hba_pdisks",
    parse_function = parse_areca_hba_pdisks,
    detect = startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.18928.1"),
    fetch = snmp_sections,
)

check_plugin_areca_hba_pdisks = CheckPlugin(
    name = "areca_hba_pdisks",
    sections = ["areca_hba_pdisks"],
    service_name = "PDisk Enc/Sl %s",
    discovery_function = discover_areca_hba_pdisks,
    check_function = check_areca_hba_pdisks,
)
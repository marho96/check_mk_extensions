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


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    startswith,
)


def parse_areca_hba_raidsets(string_table):
    section = {}
    for id, name, state, members in string_table:
        section[id] = {
            "name": name,
            "state": state,
            "members": members,
        }
    return section

def discover_areca_hba_raidsets(section) -> DiscoveryResult:
    for id in section.keys():
        yield Service(item=id)

def check_areca_hba_raidsets(item, section) -> CheckResult:
    if item in section:
        data = section[item]
        if data["state"] == "Normal":
            state = State.OK
        elif data["state"] == "Rebuilding":
            state = State.WARN
        elif data["state"] in ["Degraded", "Offline"]:
            state = State.CRIT
        else:
            state = State.UNKNOWN
        yield Result(
            state=state,
            summary="%s is %s, members: %s" % (data["name"], data["state"], data["members"])
        )

snmp_section_areca_hba_raidsets = SimpleSNMPSection(
    name="areca_hba_raidsets",
    parse_function=parse_areca_hba_raidsets,
    detect = startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.18928.1"),
    fetch = SNMPTree(
        base=".1.3.6.1.4.1.18928.1.2.4.1.1",
        oids=[ 
            "1", # ARECA-SNMP-MIB::raidNumber
            "2", # ARECA-SNMP-MIB::raidName
            "4", # ARECA-SNMP-MIB::raidState
            "8", # ARECA-SNMP-MIB::raidMemberDiskChannels
        ],
    ),
)

check_plugin_areca_hba_raidsets = CheckPlugin(
    name="areca_hba_raidsets",
    sections=["areca_hba_raidsets"],
    service_name="Raid set %s",
    discovery_function=discover_areca_hba_raidsets,
    check_function=check_areca_hba_raidsets,
)
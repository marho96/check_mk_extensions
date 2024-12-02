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

# Fans

#.1.3.6.1.4.1.18928.1.2.2.1.9.1.1.1 = INTEGER: 1
#.1.3.6.1.4.1.18928.1.2.2.1.9.1.2.1 = STRING: "CPU Fan"
#.1.3.6.1.4.1.18928.1.2.2.1.9.1.3.1 = INTEGER: 0

# snmp_info  : oid(".1.3.6.1.4.1.18928.1.2.2.1.9.1"), [ "1", "2", "3" ]

from cmk.plugins.lib.fan import check_fan

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
)

def areca_fan_name(desc):
    return desc.split()[0]

def parse_areca_hba_fans(string_table):
    section = {}
    for desc, speed in string_table:
        speed = int(speed)
        if speed > 0:
            section[areca_fan_name(desc)] = speed
    return section

def discover_areca_hba_fans(section) -> DiscoveryResult:
    for name in section.keys():
        yield Service(item=name)

def check_areca_hba_fans(item, params, section) -> CheckResult:
    if item in section:
        yield from check_fan(section[item], params)

snmp_section_areca_hba_fans = SimpleSNMPSection(
    name = "areca_hba_fans",
    parse_function = parse_areca_hba_fans,
    detect = startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.18928.1"),
    fetch = SNMPTree(
        base = ".1.3.6.1.4.1.18928.1.2.2.1.9.1",
        oids = [
            "2", # hwControllerBoardFanDesc
            "3", # hwControllerBoardFanSpeed
        ]
    )
)

check_plugin_areca_hba_fans = CheckPlugin(
    name = "areca_hba_fans",
    sections = ["areca_hba_fans"],
    service_name = "Fan %s",
    discovery_function = discover_areca_hba_fans,
    check_function = check_areca_hba_fans,
    check_default_parameters = {
        "output_metrics": True,
    },
    check_ruleset_name = "hw_fans",
)
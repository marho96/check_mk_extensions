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


# Temperature

#.1.3.6.1.4.1.18928.1.2.2.1.10.1.1.1 = INTEGER: 1
#.1.3.6.1.4.1.18928.1.2.2.1.10.1.1.2 = INTEGER: 2
#.1.3.6.1.4.1.18928.1.2.2.1.10.1.2.1 = STRING: "CPU Temperature"
#.1.3.6.1.4.1.18928.1.2.2.1.10.1.2.2 = STRING: "Controller Temp."
#.1.3.6.1.4.1.18928.1.2.2.1.10.1.3.1 = INTEGER: 80
#.1.3.6.1.4.1.18928.1.2.2.1.10.1.3.2 = INTEGER: 35

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
from cmk.plugins.lib import temperature


def parse_areca_hba_temp(string_table):
    section = {}
    for name, temp in string_table:
        newname = []
        for namepart in name.split():
            if "temp" not in namepart.lower():
                newname.append(namepart)
        section[" ".join(newname)] = int(temp)
    return section

def discover_areca_hba_temp(section) -> DiscoveryResult:
    for name in section.keys():
        yield Service(item=name)

def check_areca_hba_temp(item, params, section) -> CheckResult:
    if item in section:
        temp = section[item]
        yield from temperature.check_temperature(temp, params)

snmp_section_areca_hba_temp = SimpleSNMPSection(
    name="areca_hba_temp",
    parse_function=parse_areca_hba_temp,
    detect = startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.18928.1"),
    fetch = SNMPTree(
        base=".1.3.6.1.4.1.18928.1.2.2.1.10.1",
        oids=[
            "2", # ARECA-SNMP-MIB::hwControllerBoardTempDesc
            "3", # ARECA-SNMP-MIB::hwControllerBoardTempValue
        ],
    ),
)

check_plugin_areca_hba_temp = CheckPlugin(
    name="areca_hba_temp",
    sections=["areca_hba_temp"],
    service_name="Temperature %s",
    discovery_function=discover_areca_hba_temp,
    check_function=check_areca_hba_temp,
    check_default_parameters={},
    check_ruleset_name="temperature",
)
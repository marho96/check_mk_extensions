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
# The official homepage for this check is at http://bitbucket.org/darkfader
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

from cmk.utils import debug
from pprint import pprint # type: ignore

def parse_areca_hba_ldisks(string_table):
    section = {}
    for vsf_id, vsf_name, vsf_rsf, vsf_size, vsf_state, vsf_rbld in string_table:
        section[vsf_id] = {
            "name": vsf_name,
            "rsf": vsf_rsf,
            "size": int(vsf_size) / 1024.0,
            "state": vsf_state,
            "rbld": int(vsf_rbld) / 10.0,
        }
    if debug.enabled():
        pprint(string_table)
        pprint(section)
    return section

def discover_areca_hba_ldisks(section) -> DiscoveryResult:
    for id in section.keys():
        yield Service(item=id)

def check_areca_hba_ldisks(item, section) -> CheckResult:
    if item in section:
        vsf = section[item]
        state = State.UNKNOWN
        msg = "%s is %s" % (vsf["name"], vsf["state"].lower())
        if vsf["state"] == "Normal":
            state = State.OK
        elif vsf["state"] == "Rebuilding":
            state = State.WARN
            reb_gb = vsf["size"] * vsf["rbld"] / 100.0
            msg += " - %d%% (%d/%d GB) done" % (vsf["rbld"], reb_gb, vsf["size"])
        elif vsf["state"] == "Degraded":
            state = State.WARN
        else:
            msg += " - Unhandled state"
        yield Result(state=state, summary=msg)

snmp_section_areca_hba_ldisks = SimpleSNMPSection(
    name = "areca_hba_ldisks",
    parse_function = parse_areca_hba_ldisks,
    detect = startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.18928.1"),
    # detect = lambda oid: True,
    fetch = SNMPTree(
        base = ".1.3.6.1.4.1.18928.1.2.5.1.1",
        oids = [
            "1", # ARECA-SNMP-MIB::volNumber
            "2", # ARECA-SNMP-MIB::volName
            "3", # ARECA-SNMP-MIB::volRaidName
            "4", # ARECA-SNMP-MIB::volCapacity
            "5", # ARECA-SNMP-MIB::volState
            "6", # ARECA-SNMP-MIB::volProgress
        ],
    ),
)

check_plugin_areca_hba_ldisks = CheckPlugin(
    name = "areca_hba_ldisks",
    sections = ["areca_hba_ldisks"],
    service_name = "Volume set %s",
    discovery_function = discover_areca_hba_ldisks,
    check_function = check_areca_hba_ldisks,
)
#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-

# (c) 2017 Heinlein Support GmbH
#          Robert Sander <r.sander@heinlein-support.de>

#
# This is free software;  you can redistribute it and/or modify it
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
    Service,
    Result,
    SimpleSNMPSection,
    SNMPTree,
    State,
    all_of,
    contains,
    exists,
)


def parse_dell_sc_cache(string_table):
    section = {}
    for line in string_table:
        section[line[0]] = {
            'status': int(line[1]),
            'name': line[2],
            'battery_status': int(line[3]),
            'battery_expiry': line[4],
        }
    return section

def discover_dell_sc_cache(section) -> DiscoveryResult:
    for id in section.keys():
        yield Service(item=id)

def check_dell_sc_cache(item, section) -> CheckResult:
    state = {
        1  : ('up', State.OK),
        2  : ('down', State.CRIT),
        3  : ('degraded', State.WARN),
    }
    batt = {
        0  : 'no battery',
        1  : 'normal',
        2  : 'expiration pending',
        3  : 'expired',
    }

    if item in section:
        data = section[item]
        cache_state = state.get(data['status'], ('unknown', State.UNKNOWN))

        yield Result(state=cache_state[1], summary="%s, Battery Expiration: %s (%s), State is %s" % (
            data['name'],
            data['battery_expiry'],
            batt.get(data['battery_status'], data['battery_status']),
            cache_state[0])
        )


check_plugin_dell_sc_cache = CheckPlugin(
    name="dell_sc_cache",
    sections = [ "dell_sc_cache" ],
    service_name="Dell SC Cache %s",
    discovery_function=discover_dell_sc_cache,
    check_function=check_dell_sc_cache,
)


snmp_section_dell_sc_cache = SimpleSNMPSection(
    name = "dell_sc_cache",
    parse_function = parse_dell_sc_cache,
    detect = all_of(
        contains(".1.3.6.1.2.1.1.1.0", "compellent"),
        exists(".1.3.6.1.4.1.674.11000.2000.500.1.2.1.0"),
    ),
    fetch = SNMPTree(
      base = '.1.3.6.1.4.1.674.11000.2000.500.1.2.28.1',
      oids = [
        '2',    # scCacheNbr
        '3',    # scCacheStatus
        '4',    # scCacheName
        '5',    # scCacheBatStat
        '6',    # scCacheBatExpr
      ],
    )
)

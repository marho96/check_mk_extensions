#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-

# (c) 2024 Heinlein Support GmbH
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

from .agent_based_api.v1 import (
    contains,
    get_value_store,
    register,
    render,
    HostLabel,
    Result,
    Service,
    SNMPTree,
    State,
)
from .agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    HostLabelGenerator,
)
from .utils.temperature import (
    TempParamDict,
    check_temperature,
)
from cmk.plugins.lib.fan import check_fan
from cmk.plugins.lib.elphase import check_elphase

_map_component_status = {
    -1: (State.UNKNOWN, "not present"),
     0: (State.OK, "ok"),
     1: (State.WARN, "warning"),
     2: (State.CRIT, "error"),
     3: (State.CRIT, "fatal error"),
}

_map_node_oper_status = {
    0: (State.UNKNOWN, "unknown"),
    1: (State.OK, "online"),
    2: (State.WARN, "going online"),
    3: (State.OK, "locked online"),
    4: (State.WARN, "going locked online"),
    5: (State.CRIT, "offline"),
    6: (State.CRIT, "going offline"),
    7: (State.CRIT, "locked offline"),
    8: (State.CRIT, "going locked offline"),
    9: (State.OK, "standby"),
    10: (State.WARN, "going standby"),
}

def _check_component_status(device_status):
    status = _map_component_status.get(device_status, (3, 'Unknown status: %d' % device_status))
    yield Result(state=status[0], summary="Device state is %s" % status[1])


#   .--Temperatures--------------------------------------------------------.
#   |   _____                                   _                          |
#   |  |_   _|__ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___  ___    |
#   |    | |/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \/ __|   |
#   |    | |  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/\__ \   |
#   |    |_|\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___||___/   |
#   |                     |_|                                              |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'
#.
    
def parse_forcepoint_firewall_temperature(string_table):
    section = {}
    for line in string_table:
        section[line[0]] = {
            'temp': int(line[1]),
            'status': int(line[2]),
        }
    return section

register.snmp_section(
    name="forcepoint_firewall_temperature",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.47565.1.1"),
    parse_function=parse_forcepoint_firewall_temperature,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.47565.1.1.1.16.1",
        oids=[
            '2', # fwHwTemperatureName
            '3', # fwHwTemperature
            '4', # fwHwTemperatureStatus
        ]
    ),
)

def discover_forcepoint_firewall_temperature(section) -> DiscoveryResult:
    for tempname in section:
        yield Service(item=tempname)

def check_forcepoint_firewall_temperature(item: str, params: TempParamDict, section) -> CheckResult:
    if item in section:
        yield from check_temperature(
            section[item]['temp'],
            params,
            value_store=get_value_store(),
            unique_name=f"forcepoint_firewall.temperature.{item}",
        )
        yield from _check_component_status(section[item]['status'])

register.check_plugin(
    name='forcepoint_firewall_temperature',
    service_name="Temperature %s",
    discovery_function=discover_forcepoint_firewall_temperature,
    check_function=check_forcepoint_firewall_temperature,
    check_ruleset_name='temperature',
    check_default_parameters={},
)


#   .--PSUs----------------------------------------------------------------.
#   |                        ____  ____  _   _                             |
#   |                       |  _ \/ ___|| | | |___                         |
#   |                       | |_) \___ \| | | / __|                        |
#   |                       |  __/ ___) | |_| \__ \                        |
#   |                       |_|   |____/ \___/|___/                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'
#.

def parse_forcepoint_firewall_psu(string_table):
    section = {}
    for line in string_table:
        section[line[0]] = {
            'status': int(line[1]),
        }
    return section

register.snmp_section(
    name="forcepoint_firewall_psu",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.47565.1.1"),
    parse_function=parse_forcepoint_firewall_psu,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.47565.1.1.1.17.1",
        oids=[
            '2', # fwPsuName
            '3', # fwPsuStatus
        ]
    ),
)

def discover_forcepoint_firewall_psu(section) -> DiscoveryResult:
    for psuname in section:
        yield Service(item=psuname)

def check_forcepoint_firewall_psu(item: str, section) -> CheckResult:
    if item in section:
        yield from _check_component_status(section[item]['status'])

register.check_plugin(
    name='forcepoint_firewall_psu',
    service_name="PSU %s",
    discovery_function=discover_forcepoint_firewall_psu,
    check_function=check_forcepoint_firewall_psu,
)


#   .--Fans----------------------------------------------------------------.
#   |                         _____                                        |
#   |                        |  ___|_ _ _ __  ___                          |
#   |                        | |_ / _` | '_ \/ __|                         |
#   |                        |  _| (_| | | | \__ \                         |
#   |                        |_|  \__,_|_| |_|___/                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'
#.

def parse_forcepoint_firewall_fan(string_table):
    section = {}
    for line in string_table:
        section[line[0]] = {
            'rpm': int(line[1]),
            'status': int(line[2]),
        }
    return section

register.snmp_section(
    name="forcepoint_firewall_fan",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.47565.1.1"),
    parse_function=parse_forcepoint_firewall_fan,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.47565.1.1.1.18.1",
        oids=[
            '2', # fwFanName
            '3', # fwFan
            '4', # fwFanStatus
        ]
    ),
)

def discover_forcepoint_firewall_fan(section) -> DiscoveryResult:
    for fanname in section:
        yield Service(item=fanname)

def check_forcepoint_firewall_fan(item: str, params, section) -> CheckResult:
    if item in section:
        yield from check_fan(section[item]['rpm'], params)
        yield from _check_component_status(section[item]['status'])

register.check_plugin(
    name='forcepoint_firewall_fan',
    service_name="Fan %s",
    discovery_function=discover_forcepoint_firewall_fan,
    check_function=check_forcepoint_firewall_fan,
    check_ruleset_name="hw_fans",
    check_default_parameters={
        "output_metrics": True,
    },
)


#   .--Voltages------------------------------------------------------------.
#   |              __     __    _ _                                        |
#   |              \ \   / /__ | | |_ __ _  __ _  ___  ___                 |
#   |               \ \ / / _ \| | __/ _` |/ _` |/ _ \/ __|                |
#   |                \ V / (_) | | || (_| | (_| |  __/\__ \                |
#   |                 \_/ \___/|_|\__\__,_|\__, |\___||___/                |
#   |                                      |___/                           |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'
#.

def parse_forcepoint_firewall_voltage(string_table):
    section = {}
    for line in string_table:
        status = _map_component_status.get(int(line[2]), (3, 'Unknown status: %s' % line[2]))
        section[line[0]] = {
            'voltage': float(line[1]) / 1000.0,
            'device_state': status,
        }
    return section

register.snmp_section(
    name="forcepoint_firewall_voltage",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.47565.1.1"),
    parse_function=parse_forcepoint_firewall_voltage,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.47565.1.1.1.20.1",
        oids=[
            '2', # fwVoltageName
            '3', # fwVoltage
            '4', # fwVoltageStatus
        ]
    ),
)

def discover_forcepoint_firewall_voltage(section) -> DiscoveryResult:
    for voltagename in section:
        yield Service(item=voltagename)

def check_forcepoint_firewall_voltage(item: str, params, section) -> CheckResult:
    if item in section:
        yield from check_elphase(item, params, section)

register.check_plugin(
    name='forcepoint_firewall_voltage',
    service_name="Voltage %s",
    discovery_function=discover_forcepoint_firewall_voltage,
    check_function=check_forcepoint_firewall_voltage,
    check_ruleset_name='el_inphase',
    check_default_parameters={},
)


#   .--Cluster Status------------------------------------------------------.
#   |     ____ _           _              ____  _        _                 |
#   |    / ___| |_   _ ___| |_ ___ _ __  / ___|| |_ __ _| |_ _   _ ___     |
#   |   | |   | | | | / __| __/ _ \ '__| \___ \| __/ _` | __| | | / __|    |
#   |   | |___| | |_| \__ \ ||  __/ |     ___) | || (_| | |_| |_| \__ \    |
#   |    \____|_|\__,_|___/\__\___|_|    |____/ \__\__,_|\__|\__,_|___/    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'
#.

def parse_forcepoint_firewall_cluster_status(string_table):
    section = {}
    if len(string_table) == 1 and len(string_table[0]) == 6:
        line = string_table[0]
        section = {
            'Cluster ID': int(line[0]),
            'Member ID': int(line[1]),
            'Node Operational State': _map_node_oper_status.get(int(line[2]), (State.UNKNOWN, "Unknown state %s" % line[2])),
            'Appliance Model': line[3],
            'POS Code': line[4],
            'Serial': line[5],
        }
    return section

def host_label_forcepoint_firewall_cluster_status(section) -> HostLabelGenerator:
    if section:
        yield HostLabel('forcepoint/clusterid', str(section['Cluster ID']))
        yield HostLabel('forcepoint/model', section['Appliance Model'])

register.snmp_section(
    name="forcepoint_firewall_cluster_status",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.47565.1.1"),
    parse_function=parse_forcepoint_firewall_cluster_status,
    host_label_function=host_label_forcepoint_firewall_cluster_status,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.47565.1.1.1.19",
        oids=[
            '1.0',  # nodeClusterId
            '2.0',  # nodeMemberId
            '3.0',  # nodeOperState
            '9.0',  # nodeApplianceModel
            '10.0', # nodePosCode
            '13.0', # nodeHardwareSerialNumber
        ]
    ),
)

def discover_forcepoint_firewall_cluster_status(section) -> DiscoveryResult:
    if section:
        yield Service()
    
def check_forcepoint_firewall_cluster_status(section) -> CheckResult:
    for key, value in section.items():
        if isinstance(value, tuple):
            yield Result(state=value[0], summary='%s: %s' % ( key, value[1]))
        else:
            yield Result(state=State.OK, summary='%s: %s' % ( key, value))
    
register.check_plugin(
    name='forcepoint_firewall_cluster_status',
    service_name="ForcePoint Cluster Status",
    discovery_function=discover_forcepoint_firewall_cluster_status,
    check_function=check_forcepoint_firewall_cluster_status,
)

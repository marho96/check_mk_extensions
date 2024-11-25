#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-

#
# (C) 2023 Heinlein Support GmbH - License: GNU General Public License v2
# Robert Sander <r.sander@heinlein-support.de>
#

import sys
import os
import argparse # type: ignore
import checkmkapi
import requests
import json
from datetime import date # type: ignore
from pprint import pprint # type: ignore

apifeiertage = 'https://openholidaysapi.org/'

#
# defaults
#
countries = ["de", "at", "lu"]
default_country = "de"
language = "DE"

def convert_name(name):
    umlaute = {
        'ä': 'ae',
        'ö': 'oe',
        'ü': 'ue',
        'Ä': 'Ae',
        'Ö': 'Oe',
        'Ü': 'Ue',
        'ß': 'ss',
    }
    for umlaut, ersatz in umlaute.items():
        name = name.replace(umlaut, ersatz)
    return name

states = {}
states_orig = {}
state_choices = set()
for country in countries:
    states[country] = {}
    states_orig[country] = {}
    resp = requests.get(apifeiertage + 'Subdivisions', params = {"countryIsoCode": country.upper()})
    for region in resp.json():
        use_region = False
        for category in region.get("category", []):
            if category.get("language") == "EN" and category.get("text") in ["state", "federal state"]:
                use_region = True
                break
        if use_region:
            longname = region.get("shortName")
            name = longname.lower()
            for name_info in region.get("name", []):
                if name_info.get("language") == language:
                    longname = name_info.get("text", longname)
            name_convert = convert_name(name)
            states[country][name] = {"name": longname, "ascii": name_convert}
            states_orig[country][name_convert] = name
            state_choices.add(name)

always = [{'day': 'all', 'time_ranges': [{'start': '00:00', 'end': '24:00'}]}]

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--url', help='URL to Check_MK site')
parser.add_argument('-u', '--username', help='name of the automation user')
parser.add_argument('-p', '--password', help='secret of the automation user')
parser.add_argument('-c', '--config-file', help='config file (JSON)',
                    default=os.path.join(os.environ.get('OMD_ROOT'), 'etc', 'holidays'))
parser.add_argument('-D', '--debug', action='store_true')
subparsers = parser.add_subparsers(title='available commands', help='call "subcommand --help" for more information')
delete_timeperiod = subparsers.add_parser('delete', help='delete timeperiod')
delete_timeperiod.set_defaults(func='delete_timeperiod')
delete_timeperiod.add_argument('name', help='name of timeperiod')
delete_old = subparsers.add_parser('delete_old', help='delete old holiday timeperiods')
delete_old.set_defaults(func='delete_old')
dump_timeperiods = subparsers.add_parser('dump_timeperiods', help='dump timeperiods')
dump_timeperiods.set_defaults(func='dump_timeperiods')
dump_regions = subparsers.add_parser('dump_regions', help='show avaliable regions')
dump_regions.set_defaults(func='dump_regions')
add_holidays = subparsers.add_parser('add_holidays', help='add timeperiod from %s' % apifeiertage)
add_holidays.set_defaults(func='add_holidays')
add_holidays.add_argument('-a', '--all-states', action='store_true', help='Nur bundesweite Feiertage')
add_holidays.add_argument('-l', '--country', choices=countries, default=default_country, help='Land (default=de)')
add_holidays.add_argument('-s', '--state', choices=list(state_choices), help='Bundesland')
add_holidays.add_argument('-y', '--year')
add_holidays.add_argument('-Y', '--current-year', action='store_true')
add_holidays.add_argument('-e', '--exclude-in-default', action='store_true', help='Exclude in passender Standard-Timeperiod')
add_holidays.add_argument('-E', '--exclude-in', help='Exclude in anderer Timeperiod')
add_region = subparsers.add_parser('add_region', help='add a new region to the configuration (base timeperiods and tag)')
add_region.set_defaults(func='add_region')
add_region.add_argument('-l', '--country', choices=countries, default=default_country, help='Land')
add_region.add_argument('-s', '--state', choices=list(state_choices), help='Bundesland', required=True)
add_auto_holidays = subparsers.add_parser('add_auto_holidays', help='add timeperiods from %s for all regions' % apifeiertage)
add_auto_holidays.set_defaults(func='add_auto_holidays')
add_auto_holidays.add_argument('-y', '--year')
add_auto_holidays.add_argument('-Y', '--current-year', action='store_true')
cleanup = subparsers.add_parser('cleanup', help='remove timeperiods and tag group. Use with caution!')
cleanup.set_defaults(func='cleanup')

def exclude_in_timeperiod(name, exclude_in_tp):
    etp, etag = cmk.get_timeperiod(exclude_in_tp)

    if args.debug:
        pprint(etp)
        pprint(etag)

    exclude = etp['extensions']['exclude']
    exclude.append(name)

    if args.debug:
        pprint(exclude)

    cmk.edit_timeperiod(exclude_in_tp, etag, exclude=exclude)

def add_holiday_timeperiod(country=default_country, state=None, all_states=False, current_year=False, set_year=None, exclude_in_default=True, exclude_in=None):
    params = {"languageIsoCode": language, "countryIsoCode": country.upper()}
    name = config['timeperiods']['holidays']['name'] + '_'
    alias = config['timeperiods']['holidays']['title'] + ' '
    year = None
    if current_year:
        year = str(date.today().year)
    elif set_year:
        year = set_year
    if year:
        params['validFrom'] = f"{year}-01-01"
        params['validTo'] = f"{year}-12-31"
        name += year
        alias += year    
    name += "_" + country
    alias += " " + country.upper()
    if all_states:
        name += '_national'
        alias += ' national'
    elif state:
        params['subdivisionCode'] = "%s-%s" % (country.upper(), state.upper())
        name += '_%s' % states[country][state]["ascii"]
        alias += ' %s' % states[country][state]["name"]

    if args.debug:
        pprint(params)

    if 'validFrom' not in params and 'subdivisonCode' not in params:
        print('Please give at least a year or a state.\n')
        add_holidays.print_help()
        sys.exit(1)
        
    resp = requests.get(apifeiertage + "PublicHolidays", params=params)
    if resp.content:
        try:
            data = resp.json()
        except json.decoder.JSONDecodeError:
            data = resp.content
    else:
        data = {}
    if resp.status_code >= 400:
        sys.stderr.write("%r\n" % data)
    
    if args.debug:
        print("data = ")
        pprint(data)

    exceptions = []
    for feiertag in data:
        if all_states:
            if feiertag["nationwide"]:
                exceptions.append({
                    'date': feiertag['startDate'],
                    'time_ranges': [ { 'start': '00:00:00', 'end': '24:00:00' } ]
                })
        else:
            exceptions.append({
                'date': feiertag['startDate'],
                'time_ranges': [ { 'start': '00:00:00', 'end': '24:00:00' } ]
            })

    if args.debug:
        print("name =")
        pprint(name)
        print("alias =")
        pprint(alias)
        print("exceptions =")
        pprint(exceptions)

    if exceptions:
        tp, etag = cmk.create_timeperiod(name, alias, [], exceptions=exceptions)

        if args.debug:
            pprint(tp)

        if exclude_in_default:
            exclude_in_timeperiod(name, config['timeperiods']['workhours']['name'] + "_" + country + "_" + states[country][state]["ascii"])
                
        if exclude_in:
            exclude_in_timeperiod(name, exclude_in)

args = parser.parse_args()
if 'func' not in args:
    parser.print_help()
    sys.exit(1)
if args.debug:
    pprint(args)

config = json.load(open(args.config_file))

if args.debug:
    pprint(config)

cmk = checkmkapi.CMKRESTAPI(args.url, args.username, args.password)

if args.func == 'dump_timeperiods':
    pprint(cmk.get_timeperiods()[0])

if args.func == 'dump_regions':
    pprint(states)
    pprint(states_orig)

if args.func == 'delete_timeperiod':
    cmk.delete_timeperiod(args.name, '*')
    cmk.activate()

if args.func == 'delete_old':
    tps, etag = cmk.get_timeperiods()

    to_delete = []
    thisyear = str(date.today().year)

    if args.debug:
        print(f"Removing each timeperiod starting with \"{config['timeperiods']['holidays']['name']}_\" up to but not including {thisyear}")

    tps, etag = cmk.get_timeperiods()

    for tp in tps['value']:
        if tp['id'].startswith(config['timeperiods']['holidays']['name'] + '_'):
            year = tp['id'].split('_')[1]
            if year < thisyear:
                to_delete.append(tp['id'])

    for tp in tps['value']:
        excludes = tp['extensions'].get('exclude', [])
        changes = False
        for td in to_delete:
            if td in excludes:
                if args.debug:
                    print(f"Removing {td} from {tp['id']}")
                excludes.remove(td)
                changes = True
        if changes:
            te, etag = cmk.get_timeperiod(tp['id'])
            cmk.edit_timeperiod(tp['id'], etag, exclude=excludes)
    for td in to_delete:
        if args.debug:
            print(f"Removing {td}")
        cmk.delete_timeperiod(td, '*')
    if to_delete:
        cmk.activate()

if args.func == 'add_holidays':
    add_holiday_timeperiod(args.country, args.state, args.all_states, args.current_year, args.year, args.exclude_in_default, args.exclude_in)
    cmk.activate()

if args.func == "add_region":
    workhoursname = '%s_%s_%s' % ( config['timeperiods']['workhours']['name'],
                                   args.country,
                                   states[args.country][args.state]["ascii"] )
    tp, etag = cmk.create_timeperiod(workhoursname,
                                     '%s %s %s' % ( config['timeperiods']['workhours']['title'],
                                                    args.country.upper(),
                                                    states[args.country][args.state]["name"] ),
                                     config['workdays'])
    if args.debug:
        pprint(tp)
        
    tp, etag = cmk.create_timeperiod('%s_%s_%s' % ( config['timeperiods']['oncall']['name'],
                                                    args.country,
                                                    states[args.country][args.state]["ascii"] ),
                                     '%s %s %s' % ( config['timeperiods']['oncall']['title'],
                                                    args.country.upper(),
                                                    states[args.country][args.state]["name"] ),
                                     always,
                                     exclude=[workhoursname])
    if args.debug:
        pprint(tp)

    tg = None
    try:
        tg, etag = cmk.get_host_tag_group(config['taggroup']['name'])
    except:
        pass

    tag = {
        'id': "%s_%s_%s" % (config['taggroup']['name'], args.country, states[args.country][args.state]["ascii"]),
        'title': "%s %s %s" % (config['taggroup']['title'], args.country.upper(), states[args.country][args.state]["name"])
    }

    if not tg:
        tg, etag = cmk.create_host_tag_group(
            config['taggroup']['name'],
            config['taggroup']['title'],
            [
                {'title': config['taggroup']['empty_title']},
                tag,
            ],
            topic = config['taggroup'].get('topic'),
            help = config['taggroup'].get('help')
        )
    else:
        tags = tg['extensions']['tags']

        tags.append(tag)

        cmk.edit_host_tag_group(config['taggroup']['name'], etag, tags=tags)

    nrs, etag = cmk.get_notification_rules()

    if args.debug:
        pprint(nrs)

    # for nr in nrs['value']:
        
    cmk.activate()
    
if args.func == 'add_auto_holidays':
    tps, etag = cmk.get_timeperiods()
    changes = False
    for tp in tps['value']:
        if tp['id'].startswith(config['timeperiods']['workhours']['name']):
            if args.debug:
                print(f"found {tp['id']}")
            _, country, state = tp['id'].split('_')
            add_holiday_timeperiod(country=country, state=states_orig[country][state], current_year=args.current_year, set_year=args.year)
            changes = True
    if changes:
        cmk.activate()

if args.func == "cleanup":
    tps, etag = cmk.get_timeperiods()

    if args.debug:
        pprint(tps)

    changes = False
        
    for typ in ['oncall', 'workhours', 'holidays']:
        # order is important
        for tp in tps['value']:
            if tp['id'].startswith(config['timeperiods'][typ]['name']):
                if args.debug:
                    print(f"removing {tp['id']}")
                cmk.delete_timeperiod(tp['id'], '*')
                changes = True

    try:
        cmk.delete_host_tag_group(config['taggroup']['name'])
        if args.debug:
            print(f"remove host tag group {config['taggroup']['name']}")
        changes = True
    except:
        pass
    
    if changes:
        cmk.activate()

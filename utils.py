#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals

import os
import json
from datetime import timedelta

import arrow
import pandas as pd


def date_range(start, end):
    delta = end - start
    res = []
    for i in range(delta.days + 1):
        d = start + timedelta(days=i)
        res.append(d.strftime('%Y-%m-%d'))
    return res


def get_metadata(day, name, data_dir='data'):
    with open(os.path.join(data_dir, name, 'index.json'), 'r') as f:
        dates = json.load(f)

    dates['start'] = map(arrow.get, dates['start'])
    dates['end'] = map(arrow.get, dates['end'])

    start = filter(lambda t: day >= t, dates['start'])
    if len(start) > 1:
        start = start[-1]
    else:
        start = start[0]

    end = filter(lambda t: day <= t, dates['end'])[0]

    start_str = start.strftime('%Y%m%d')
    end_str = end.strftime('%Y%m%d')

    print('Get {} from {} to {}'.format(name, start_str, end_str))
    fpath = '{}_{}_{}.csv.gz'.format(name, start_str, end_str)
    return pd.read_csv(os.path.join(data_dir, name, fpath), compression='gzip')
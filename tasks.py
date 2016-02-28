from __future__ import print_function

import boto3
import arrow
import pandas as pd

import process


GITHUB_URL = 'https://raw.githubusercontent.com/scascketta/CapMetrics/master/data/vehicle_positions/{}.csv'


def process_day_to_s3(day, bucket, key):
    print('Processing', day)

    url = GITHUB_URL.format(day)
    print('Downloading from:', url)
    df = pd.read_csv(url)

    day_t = arrow.get(day)
    stops = process.get_metadata(day_t, 'stops')
    schedule = process.get_metadata(day_t, 'schedule')

    positions = process.process_day(df, stops, schedule)

    output_path = '{}_processed.csv'.format(day)
    positions.to_csv(output_path, index=False)

    s3_client = boto3.client('s3')
    s3_client.upload_file(output_path, bucket, key)

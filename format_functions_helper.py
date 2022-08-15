from datetime import datetime
import json
import pandas as pd
import pytz
import teavault_api
import os
import math

def tick_from_eth_basis_to_usdt(tick):
    tick = int(tick)
    price = ((1.0001) ** (-tick)) * 10 ** 12
    return price

#1622592380

#date = datetime.fromtimestamp(1622592380,gmt_0_timezone).strftime('%Y-%m-%d %H:%M:%S')

def usdt_to_tick_eth_basis(eth_in_usdt):
    price = round(math.log(1/eth_in_usdt*(10**12),1.0001))
    return price

gmt_0_timezone = pytz.timezone('UTC')
taipei = pytz.timezone('Asia/Taipei')

def timestamp_to_date_taipei(time_stamp):
    date = datetime.fromtimestamp(time_stamp, taipei).strftime('%Y-%m-%d %H:%M:%S')

    return date

def timestamp_to_date(time_stamp):
    date = datetime.fromtimestamp(time_stamp, gmt_0_timezone).strftime('%Y-%m-%d %H:%M:%S')

    return date


def usdt_formatted(usdt):
    usdt = float(usdt)
    usdt_formatted = usdt * (10 ** -6)

    return usdt_formatted

def usdt_formatted_in_m(usdt):
    # 10**06 = original usdt amount, 10**-12 for Million
    usdt = float(usdt)
    usdt_format_in_m = usdt * (10 ** -12)

    return int(usdt_format_in_m)

def eth_formatted(eth):
    eth = float(eth)
    eth_formatted = eth * (10 ** -18)

    return eth_formatted

def timestamp_fit_simulator( timestamp):
    timestamp = timestamp

    return timestamp

#save_file( data=API_return_output_json, document_directory= './data/simulator_result/', file_name = 'test' , file_type='.json')

def save_file(data, document_directory = '', file_name ='', output_file_type='.csv'):

    file_path = document_directory + file_name + output_file_type

    if output_file_type == '.csv':
        data.to_csv(file_path)
    elif output_file_type == '.json':
        with open(file_path, 'w') as file_object:  # open the file in write mode
            simulator_input = json.dump(data, file_object)
        file_object.close()
    else:
        return "not predefined file type, can't process"
    print("file saved in:" + str(file_path))

    return file_path

def filter_raw_event( input_raw_event,  output_file_path ='./data/processed_event/processed_event.csv'):

    df = input_raw_event[['timestamp', 'amount0', 'amount1', 'event', 'tick']]
    df = df[df['event'] == 'Swap']
    df[['USDC']] = df[['amount0']].applymap(lambda x: usdt_formatted(x))
    df[['ETH']] = df[['amount1']].applymap(lambda x: eth_formatted(x))
    df['ETH/USDC'] = df['tick'].map(lambda x: tick_from_eth_basis_to_usdt(x))
    df['date'] = df['timestamp'].map(lambda x: timestamp_to_date(x))
    df = df[['timestamp', 'date', 'USDC', 'ETH', 'ETH/USDC', 'tick']]

    delete_file( input_file_path = output_file_path)

    df.to_csv(output_file_path)
    message = "output_event saved in: " + str(output_file_path)
    print(message)

    return df


def delete_file(input_file_path ="./data/raw_price_bounds/current_price_bounds.csv", ):
    try:
        os.remove(input_file_path)
        print("Successfully  deleting file ", input_file_path)


    except:
        print("Error while deleting file ", input_file_path)

    return


def get_start_time_end_time_in_stamp( previous_hours_to_check = 12 ):

    # get end_time -> current
    now = datetime.now()
    print(now)
    end_time_stamp = int(datetime.timestamp(now))

    # get start_time -> current -  hours
    start_time_stamp = end_time_stamp - 3600 * previous_hours_to_check

    return start_time_stamp, end_time_stamp


def get_raw_events_from_api(start_time_timestamp, end_time_timestamp):
    # per hour = 3600 timestamp
    raw_event_string = teavault_api.get_raw_events(start_time=str(start_time_timestamp),
                                                   end_time=str(end_time_timestamp))
    raw_event = raw_event_string['data']
    print("num of raw events: " + str(len(raw_event)))
    raw_events_df = pd.DataFrame(raw_event)

    return raw_events_df

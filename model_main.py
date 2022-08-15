import teavault_api
from datetime import datetime
from importlib import reload
import pandas as pd
import format_functions_helper as format
reload(teavault_api)
reload(format)
# import rpy2.robjects as robjects
import os
import json
import logging
from pathlib import Path
import sys
import time


#####################################################################
# set variables to use
#####################################################################

uni_token_0_addr =  "0x82af49447d8a07e3bd95bd0d56f35241523fbab1"
uni_token_1_addr = "0xff970a61a04b1ca14834a43f5de4533ebddb5cc8"
uni_pool_fee_for_add_remove_liquidity = 500
uni_pool_fee_for_swap = 500

deadline_in_stamp = '1666424790'
# when add liquidity from vault to uniswap, save some value
# for token0 = 0.1%, usdc = 1%%
add_liquidity_token_0_reserve_ratio = 0.80
add_liquidity_token_1_reserve_ratio = 0.80
token_0_symbol, token_1_symbol = 'WETH', 'USDC'
reserve_swap_size_percent = 0.8
# teavault_api.equation_transfer_sqrt_price_token_0_based_on_token_1(sqrt_price_token_0)

# if use l1 event to create price bounds, place to l2, neeed to reverse bounds
l2_to_l1_flag = True
fix_start_time_stamp = 1638086400

# Sunday, November 28, 2021 8:00:00 AM
fix_start_time_stamp_2 = 1640419210
#December 25, 2021 8:00:10 AM
#####################################################################
# set multiple teavault address
#####################################################################

#teavault_address_test_net = ''
teavault_address_main_net = ""

#####################################################################
# check working directory
#####################################################################

# Import the os moduleimportos# Print the current working directory
print("Current working directory:{0}".format(os.getcwd()))

# Change the current working directory
#os.chdir('/Users/laalberta/Documents/')
# Print the current working directory
print("Current working directory:{0}".format(os.getcwd()))


############################################################
# create error logging file
############################################################

logging.basicConfig(filename='./data/error_records.log', filemode='a', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' ,datefmt='%d-%b-%y %H:%M')

############################################################
# Get raw event file from api
############################################################
# November 15, 2021 8: 00:00 AM below
#fix_start_time_stamp = 1636963200
# Sunday, November 28, 2021 8:00:00 AM
fix_start_time_stamp = 1638086400
# pull events data from previous hours till current time
start_time_stamp, flexible_end_time_stamp = format.get_start_time_end_time_in_stamp( previous_hours_to_check = 120)

record_start_time_stamp = fix_start_time_stamp
record_end_time_stamp = flexible_end_time_stamp

try:
    raw_events_df = format.get_raw_events_from_api(start_time_timestamp = fix_start_time_stamp , end_time_timestamp = flexible_end_time_stamp)

except:
    logging.error('raw events api failed to load')

#####################################################################
# processed raw event file (filter on swap events only)
#####################################################################
###  saved only last 110 event for prediction used #######

filter_events_df = format.filter_raw_event( input_raw_event = raw_events_df,  output_file_path ='./data/processed_event/processed_event.csv')

#####################################################################
# run R code and create output price_bounds file
#####################################################################

### only saved last 110 event for prediction used #######

format.delete_file(input_file_path = './data/raw_price_bounds/current_price_bounds.csv', )

###############################################
# create dynamic price bounds
###############################################
# input:  ./data/processed/processed_events.csv ( last 120 rows)
# output: ./data/raw_price_bounds/current_price_bounds.csv (latest 10 rows of price bounds)
##############################################

#r_source = robjects.r['source']
#r_source('./R_model/dynamic_model_wide.R')
#r_source('./R_model/dynamic_model_wide.R')
os.system('R -f ./R_model/dynamic_model_wide.R')


#####################################################################
# run R code and create output price_bounds file
#####################################################################


price_record = pd.read_csv('./data/raw_price_bounds/current_price_bounds.csv')
current_upper_bound, current_lower_bound = price_record['upper_bound'].iloc[-1], price_record ['lower_bound'].iloc[-1]

# model_previous_price_record = pd.read_csv('./data/previous_price_bounds/previous_price_bounds.csv')
# previous_upper_bound , previous_lower_bound = model_previous_price_record['upper_bound'].iloc[-1],  model_previous_price_record['lower_bound'].iloc[-1]

#####################################################################
# reverse l2_l1_price bounds
#####################################################################
if l2_to_l1_flag is True:
   current_upper_bound, current_lower_bound = teavault_api.l2_to_l1_flag_reverse(current_upper_bound, current_lower_bound )

#####################################################################
# compare previous price bounds and current one to decide if change new position on uniswap
#####################################################################

position_info = teavault_api.get_uniswap_current_position_list()
if len(position_info['positions']) != 0:
    previous_upper_bound = int(position_info['positions'][0]['tickUpper'])
    previous_lower_bound = int(position_info['positions'][0]['tickLower'])
else:
    previous_upper_bound = 0
    previous_lower_bound = 0

print("current bounds:", current_upper_bound, current_lower_bound)
print("previous bounds:", previous_upper_bound, previous_lower_bound)

###########################################################################
# calculate uniswap current pool token0/token1 price and transfer to tick
###########################################################################

current_pool_addr = teavault_api.get_uniswap_pool_address(  token_0 = uni_token_0_addr, token_1 = uni_token_1_addr, fee= uni_pool_fee_for_add_remove_liquidity)
current_pool_addr = current_pool_addr['address']

sqrt_price_token_0 = int(teavault_api.get_uniswap_pool_current_price( current_pool_addr) ['sqrtPriceX96'])

# equation need to set as variable

uni_pool_price_token_0_based_on_token_1 = teavault_api.equation_transfer_sqrt_price_token_0_based_on_token_1(sqrt_price_token_0)

tick_eth_in_usdt_curret_pool_price = format.usdt_to_tick_eth_basis( uni_pool_price_token_0_based_on_token_1 )

tick_eth_in_usdt_curret_pool_price_l2_format  = -(tick_eth_in_usdt_curret_pool_price)


######################################################
#  update price bounds for next session to compare
######################################################
record_end_time_taipei = format.timestamp_to_date_taipei(record_end_time_stamp)

df = pd.DataFrame({
    'event_start_timestamp': [record_start_time_stamp],
    'event_end_timestamp': [record_end_time_stamp],
    'ETH.USDC': [uni_pool_price_token_0_based_on_token_1],
    'lower_bound': [current_lower_bound],
    'upper_bound': [current_upper_bound],
    'taipei_time_end_time_stamp': [record_end_time_taipei]
})

output_file_path = './data/processed_event/' + str(record_start_time_stamp) + "_" + str(
    record_end_time_stamp) + "_bounds_changed_events.csv"
filter_events_df.to_csv(output_file_path)
df.to_csv('./data/previous_price_bounds/previous_price_bounds_updated_every_record.csv', mode='a', index=False, header=False)



#####################################################################
# compare previous price bounds and current one to decide if change new position on uniswap
#####################################################################

print("current price:", tick_eth_in_usdt_curret_pool_price_l2_format)

upper_changed = abs(current_upper_bound - previous_upper_bound)
lower_changed = abs(current_lower_bound - previous_lower_bound)
total_changed = upper_changed + lower_changed


if total_changed >= 960:
    #if tick_eth_in_usdt_curret_pool_price_l2_format not in range(previous_lower_bound, previous_upper_bound):

        #if (current_upper_bound != previous_upper_bound) or (current_lower_bound != previous_lower_bound):
    #if tick_eth_in_usdt_curret_pool_price_l2_format not in range( previous_lower_bound, previous_upper_bound):



        ############################################
        # get uniswap current position
        # #########################################


        position_info = teavault_api.get_uniswap_current_position_list()
        if len(position_info['positions']) != 0:
            uni_pool_fee, uni_position_tick_lower,  uni_position_tick_upper,  uni_position_token_0_addr, uni_position_token_1_addr,uni_position_liquidity  = position_info['positions'][0]['fee'], position_info['positions'][0]['tickLower'],position_info['positions'][0]['tickUpper'],position_info['positions'][0]['token0Address'],position_info['positions'][0]['token1Address'], position_info['positions'][0]['liquidity']
            tokensOwed0, tokensOwed1 = int(position_info['positions'][0]['tokensOwed0']), int(position_info['positions'][0]['tokensOwed1'])

            print("current uniswap positions:")
            print(position_info)

            initiate_remove_position = True

            if (tokensOwed0 > 0 or tokensOwed1 >0):
                initiate_collect_uni_position = True
            else:
                initiate_collect_uni_position = False

        else:
            print("no position on uniswap at the moment! ")
            initiate_remove_position = False
            initiate_collect_uni_position = False

        ######################################################################################
        # if account has position on uniswap: remove deployed position and collect tokens back
        ######################################################################################
        if initiate_remove_position is True:

            if int(uni_position_liquidity) > 0:
                remove_txID = teavault_api.remove_liquidity_on_uniswap(
                     token_0_addr = uni_position_token_0_addr , token_1_addr=uni_position_token_1_addr ,
                    fee = uni_pool_fee_for_add_remove_liquidity, tickLower = uni_position_tick_lower , tickUpper = uni_position_tick_upper ,
                    liquidity =uni_position_liquidity, amount_0_min = 0, amount_1_min = 0,deadline = deadline_in_stamp
                    )

                try:
                    if teavault_api.check_if_contract_is_deployed(remove_txID['TxID']) is True:
                        print("remove position on uniswap done! ")
                        pass

                except:
                    response = "when remove position: " + str(remove_txID)
                    teavault_api.slack_trading_monitor(input_text=response)
                    logging.error(response)
                    print(response)
                    #sys.exit(1)
            else:
                print("do not remove position")

            ##################################################
            # if current position's collct token > 0 then initiate collect earned token from uniswap back to vault action
            ##################################################

        if initiate_collect_uni_position is True:

            collect_txID = teavault_api.collect_tokens_from_uniswap_to_vault(

                token_0_addr = uni_position_token_0_addr , token_1_addr=uni_position_token_1_addr ,
                fee = uni_pool_fee, tickLower = uni_position_tick_lower , tickUpper = uni_position_tick_upper ,
                desired_amount_0_callback=999999999999999999999, desired_amount_1_callback=999999999999999999999
                )


            try:
                if teavault_api.check_if_contract_is_deployed(collect_txID['TxID']) is True:
                    print("collect owed tokens on uniswap done! ")
                pass

            except:

                response = "when collect token:" + str(collect_txID)
                teavault_api.slack_trading_monitor(input_text= response)
                logging.error(response)
                print(response)
                sys.exit(1)

        else:
            print("no need to collect token ")

         ##################################################
        # calculate uniswap current pool token0/token1 price
        ##################################################


        current_pool_addr = teavault_api.get_uniswap_pool_address(

            token_0 = uni_token_0_addr, token_1 = uni_token_1_addr,
            fee= uni_pool_fee_for_add_remove_liquidity
            )
        current_pool_addr = current_pool_addr['address']

        sqrt_price_token_0 = int(teavault_api.get_uniswap_pool_current_price( current_pool_addr) ['sqrtPriceX96'])

        # equation need to set as variable

        uni_pool_price_token_0_based_on_token_1 = teavault_api.equation_transfer_sqrt_price_token_0_based_on_token_1(sqrt_price_token_0)



        ##################################################
        # get quote from uniswap pool token0/token1 ratio
        ##################################################
        # ratio = token0 / token1 (in USDC/ETH pool means per USDT equals how many ETH)
        # ratio = 1 => token0:token1 = 1:0
        # ratio = 0 => token0:token1 = 0:1
        ##################################################

        #format.tick_from_eth_basis_to_usdt(193200)
        # token0/token1 ratio base token need to be flexible
        # the purpose of setting liquidity is just to get a ratio of token0/token1, not to use it for swap
        liquidity = 1000000000000000
        token_0_token_1_amount = teavault_api.get_quote_from_uniswap_pool_token_ratio(current_pool_addr, current_lower_bound, current_upper_bound, liquidity)

        amount_0_formatted = format.eth_formatted(token_0_token_1_amount['amount0'])
        amount_1_formatted = format.usdt_formatted(token_0_token_1_amount['amount1'])


        amount_0_size, amount_1_size = amount_0_formatted, amount_1_formatted

        #amount_0_size, amount_1_size = int(token_0_token_1_amount['amount0']), int(token_0_token_1_amount['amount1'])

        # add another situation
        if  (amount_0_size > 0) and (amount_1_size == 0):
            token_0_1_ratio = 1

        elif  (amount_0_size == 00) and (amount_1_size > 0):
            token_0_1_ratio = 0
        else:
            token_0_1_ratio = amount_0_size/amount_1_size


        #################################################################
        # get vault total value based on current uniswap pool price
        ##################################################################

        # vault info
        vault_info = teavault_api.get_vault_balance_list()

        vault_token_0, vault_token_1 = vault_info['tokens'][0], vault_info['tokens'][1]
        vault_token_0_addr = vault_token_0['address']
        vault_token_1_addr = vault_token_1['address']

        current_token_0_balance_in_vault = teavault_api.get_vault_token_value( vault_token_0, token_0_symbol= token_0_symbol, token_1_symbol= token_1_symbol)
        current_token_1_balance_in_vault = teavault_api.get_vault_token_value( vault_token_1, token_0_symbol= token_0_symbol, token_1_symbol=token_1_symbol)

        # get vault total value based on uniswap pool price
        vault_total_value_based_on_token1_unit = current_token_0_balance_in_vault[token_0_symbol] * uni_pool_price_token_0_based_on_token_1 + current_token_1_balance_in_vault[token_1_symbol]


        ##########################################################################
        # estimate how much needed to bet on token0 and token1 size for next round
        ##########################################################################
        # note:
        # use uniswap price, uniswap estiamte ratio between token_a/token_b and
        # vault_total_value to estimate actaul size needed for token_a,token_b from vault
        ##########################################################################

        ##################################################
        # ratio = 1 => token0:token1 = 1:0
        # ratio = 0 => token0:token1 = 0:1
        ##################################################
        vault_estimated_size_to_match_uniswap_ratio = {}

        if token_0_1_ratio ==1:

            token_0_actual_size_based_on_token1 = vault_total_value_based_on_token1_unit / uni_pool_price_token_0_based_on_token_1
            vault_estimated_size_to_match_uniswap_ratio[token_0_symbol] = token_0_actual_size_based_on_token1
            vault_estimated_size_to_match_uniswap_ratio[token_1_symbol] = 0

        elif token_0_1_ratio ==0:

            vault_estimated_size_to_match_uniswap_ratio[token_0_symbol] = 0
            vault_estimated_size_to_match_uniswap_ratio[token_1_symbol] = vault_total_value_based_on_token1_unit

        else:
            # 1ETH needs 2000 USDT to match on uniswap => total value of this = 1ETH * (ETH/USDT price_from_uniswap) + 2000 USDT
            per_eth_with_usdt_bet_size = 1/token_0_1_ratio
            total_value_from_per_eth_need_how_much_usdt = per_eth_with_usdt_bet_size + 1* uni_pool_price_token_0_based_on_token_1

            # bet_ratio calculate the actual size of token0 and token1 you need from your vault to match uniswap quote ratio
            # ex) 1 ETH needs 2000 USDT on uniswap, and your vault value is 100K
            # based on this info, what is the actual size of eth and usdt you need to match that ratio based on your total vault value

            bet_ratio = vault_total_value_based_on_token1_unit / total_value_from_per_eth_need_how_much_usdt
            eth_actual_size = bet_ratio * 1
            usdt_actual_size = bet_ratio * per_eth_with_usdt_bet_size

            vault_estimated_size_to_match_uniswap_ratio[token_0_symbol] = eth_actual_size
            vault_estimated_size_to_match_uniswap_ratio[token_1_symbol] = usdt_actual_size

        print( "amount of token0/token1 size to bet based on current vault value: " + str(vault_estimated_size_to_match_uniswap_ratio))


        ##########################################################################
        # calculate swap amount needed  ( current vault value vs estimated vault value )
        ##########################################################################
        # token_0: ETH , toekn_1: USDC
        # output sample:
        # {'ETH': 15, 'USDC': 30000}
        ##########################################################################


        # if token_1_current_size - token1_estimate_size >0: need to swap all toke1 in vault to token 0
        # if token_1_current_size - token1_estimate_size <0: need to swap all token 0 in vault to token1

        swap_amount_needed_between_actual_vault_and_estimated_bet_size_token_1_based = current_token_1_balance_in_vault[token_1_symbol] - vault_estimated_size_to_match_uniswap_ratio[token_1_symbol]
        # make sure still save some amount of vaule from each token when swapping
        bet_swap_amount_needed_between_actual_vault_and_estimated_bet_size_token_1_based = swap_amount_needed_between_actual_vault_and_estimated_bet_size_token_1_based * ( 1 - reserve_swap_size_percent)

        ##########################################################################
        # based on which token need to swap and amount, perform swap action
        ##########################################################################

        if bet_swap_amount_needed_between_actual_vault_and_estimated_bet_size_token_1_based  !=0:
            initiate_swap_amount_in_vault = True

        else:
            initiate_swap_amount_in_vault = False


        # switch token_1 to token_0
        if (initiate_swap_amount_in_vault is True and bet_swap_amount_needed_between_actual_vault_and_estimated_bet_size_token_1_based >0 ):

            decimal_bet_swap_amount_needed_between_actual_vault_and_estimated_bet_size = int(bet_swap_amount_needed_between_actual_vault_and_estimated_bet_size_token_1_based * 10**(vault_token_1['decimal']))

            swap_txID = teavault_api.swap_amount_between_tokens_in_vault_match_input_amount(

                                token_input_for_swap_addr = vault_token_1_addr  ,
                                token_output_for_swap_addr = vault_token_0_addr ,
                                fee = uni_pool_fee_for_swap, desired_input_amount = decimal_bet_swap_amount_needed_between_actual_vault_and_estimated_bet_size ,
                                desired_min_output_amount = 0, sqrt_price_input_to_output = 0, deadline = deadline_in_stamp
                                )

            try:
                if teavault_api.check_if_contract_is_deployed(swap_txID ['TxID']) is True:
                    print(" swap tokens to meet current uniswap pool ratio done!")
                pass

            except:
                response = "when swap token: " + str(swap_txID)
                teavault_api.slack_trading_monitor(input_text=response)
                logging.error(response)
                print(response)
                #sys.exit(1)

        # switch token_0 to token_1
        elif (initiate_swap_amount_in_vault is True and bet_swap_amount_needed_between_actual_vault_and_estimated_bet_size_token_1_based <0 ):

            # eth in usdt
            swap_amount_needed_in_token_0_based = swap_amount_needed_between_actual_vault_and_estimated_bet_size_token_1_based / uni_pool_price_token_0_based_on_token_1

            decimal_bet_swap_amount_needed_in_token_0_based = abs( int(swap_amount_needed_in_token_0_based * 10 **(vault_token_0['decimal'])) )

            swap_txID = teavault_api.swap_amount_between_tokens_in_vault_match_input_amount(

                    token_input_for_swap_addr = vault_token_0_addr  , token_output_for_swap_addr = vault_token_1_addr ,
                    fee = uni_pool_fee_for_swap, desired_input_amount = decimal_bet_swap_amount_needed_in_token_0_based ,
                    desired_min_output_amount = 0, sqrt_price_input_to_output = 0, deadline = deadline_in_stamp)

            try:
                if teavault_api.check_if_contract_is_deployed(swap_txID ['TxID']) is True:
                    print(" swap tokens to meet current uniswap pool ratio done!")
                    pass
            except:
                response = "when swap token:" + str(swap_txID)
                teavault_api.slack_trading_monitor(input_text=response)
                logging.error(response)
                print(response)
                sys.exit(1)


        else:
            print("no action performed when swap")

        ################################################
        # update vault balance info
        ################################################

        # vault info
        vault_info = teavault_api.get_vault_balance_list()

        vault_token_0, vault_token_1 = vault_info['tokens'][0], vault_info['tokens'][1]

        current_token_0_balance_in_vault = teavault_api.get_vault_token_value( vault_token_0, token_0_symbol= token_0_symbol, token_1_symbol= token_1_symbol)
        current_token_1_balance_in_vault = teavault_api.get_vault_token_value( vault_token_1, token_0_symbol= token_0_symbol, token_1_symbol= token_1_symbol)


        bet_decimal_current_token_0_balance_in_vault = int( ( current_token_0_balance_in_vault[token_0_symbol] *( 1- add_liquidity_token_0_reserve_ratio )) * (10 ** (vault_token_0['decimal']))  )

        if bet_decimal_current_token_0_balance_in_vault < 0 : bet_decimal_current_token_0_balance_in_vault = 0

        bet_decimal_current_token_1_balance_in_vault = int ( ( current_token_1_balance_in_vault[token_1_symbol]  * ( 1- add_liquidity_token_1_reserve_ratio ) )* (10 ** (vault_token_1['decimal'])) )
        if bet_decimal_current_token_1_balance_in_vault <0 : bet_decimal_current_token_1_balance_in_vault = 0

        #########################################################
        # check if there is any current uniswap position
        #########################################################

        position_info = teavault_api.get_uniswap_current_position_list()
        if len(position_info['positions']) != 0:

            initiate_add_uni_position = False
        else:

            if (bet_decimal_current_token_1_balance_in_vault > 0 or bet_decimal_current_token_0_balance_in_vault > 0):
                print("no position on uniswap at the moment! ")
                initiate_add_uni_position = True



        #########################################################
        # add liquidity on uniswap based on updated vault info
        #########################################################
        if initiate_add_uni_position is True:

            add_txID = teavault_api.add_liquidity_on_uniswap(

                token_0_addr = uni_token_0_addr, token_1_addr = uni_token_1_addr,
                fee= uni_pool_fee_for_add_remove_liquidity,
                tickLower= current_lower_bound, tickUpper = current_upper_bound,
                desired_amount_0_bet_size = bet_decimal_current_token_0_balance_in_vault,
                desired_amount_1_bet_size = bet_decimal_current_token_1_balance_in_vault,
                amount_0_min=0, amount_1_min=0,
                deadline= deadline_in_stamp

                )

            try:
                if teavault_api.check_if_contract_is_deployed(add_txID['TxID']) is True:
                    print("add liquidty from vault to uniswap done!")
                    pass
            except:
                response = "when add liquidity:" + str(add_txID)
                teavault_api.slack_trading_monitor(input_text=response)
                logging.error(response)
                print(response)

                sys.exit(1)

    ######################################################
        #  update price bounds for next session to compare
        ######################################################


        df = pd.DataFrame({
                           'start_timestamp': [record_start_time_stamp],
                            'end_timestamp': [record_end_time_stamp],
                           'ETH.USDC': [uni_pool_price_token_0_based_on_token_1],
                           'lower_bound': [current_lower_bound],
                           'upper_bound': [current_upper_bound],
                           })

        output_file_path = './data/processed_event/' + str(record_start_time_stamp) + "_" + str(record_end_time_stamp) + "_bounds_changed_events.csv"
        filter_events_df.to_csv( output_file_path)
        df.to_csv('./data/previous_price_bounds/previous_price_bounds_updated_changed_price_bounds.csv', mode='a', index=False, header=False)


else:
    print("no need to change price bounds")
    pass


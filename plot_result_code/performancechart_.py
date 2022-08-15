import os
import numpy as np
from bokeh.plotting import figure, show, output_file
from bokeh.models import Range1d, CrosshairTool, Span
from bokeh.layouts import gridplot


def plot(ledger):

    df_ledger = ledger.df_ledger()
    trade_info = ledger.trade_info
    config_settings = ledger.config_settings

    df_ledger = df_ledger.loc[(df_ledger["event"] != "add") | (df_ledger["event"] != "remove")]

    base_token = config_settings.base_token.name
    if base_token == config_settings.token_0.name:
        target_token = config_settings.token_1.name
    elif base_token == config_settings.token_1.name:
        target_token = config_settings.token_0.name

    all_datetime_range = np.array(df_ledger["datetime"], dtype=np.datetime64)

    xdr = Range1d(start=all_datetime_range[0], end=all_datetime_range[-1])
    tools = ('undo', 'box_zoom', "wheel_zoom", "reset", "pan", 'crosshair', 'save')

    # P_Position_Change(fees/LP)
    P_PC = figure(title="Position Change", x_axis_type="datetime", x_axis_label="time",
                  y_axis_label=f"{base_token}(%)",
                  height=250, sizing_mode="stretch_width", x_range=xdr, tools=tools)

    pc_set = {"time": [], "lp_pnl": [], "fees":[], "IL":[]}
    for i in trade_info.values():
        time = i["end_datetime"]
        lp_pnl = i["LP_PNL(%)"]
        fees = i["fees(%)"]
        IL = -i["IL(%)"]
        pc_set["time"].append(time)
        pc_set["lp_pnl"].append(lp_pnl)
        pc_set["fees"].append(fees)
        pc_set["IL"].append(IL)

    x_t = pc_set["time"]
    y_fees = pc_set["fees"]
    y_IL = pc_set["IL"]

    P_PC.circle(x_t, y_fees, legend_label="Fees", color="#73C6B6", size=5)
    P_PC.circle(x_t, y_IL, legend_label="IL", color="#A569BD", size=5)

    h_line = Span(location=0, dimension='width', line_color='#17202A', line_dash='dashed', line_width=1)
    P_PC.add_layout(h_line)
    P_PC.legend.click_policy = "hide"

    # P_kline
    y_price = df_ledger["price"]
    P_kline = figure(title="Price & Range", x_axis_label="time", x_axis_type="datetime",
                     y_axis_label=f"{target_token}/{base_token}", height=300, sizing_mode="stretch_width",
                     tools=tools, x_range=xdr)
    P_kline.line(all_datetime_range, y_price, legend_label="price", color="#515A5A", line_width=1.5)

    range_set = [[i["start_datetime"], i["end_datetime"],i["lower_price"], i["upper_price"]] for i in trade_info.values()]
    for i in range_set:
        x_t = [i[0], i[1]]
        y_lower = [i[2], i[2]]
        y_upper = [i[3], i[3]]
        P_kline.line(x_t, y_lower, legend_label="lower", color="#2980B9", line_width=1.5)
        P_kline.line(x_t, y_upper, legend_label="upper", color="#2980B9", line_width=1.5)

    # entry exit price
    entry_exit_set = {"datetime": [], "price":[]}
    for i in trade_info.values():
        start = i["start_datetime"]
        end = i["end_datetime"]
        entry_price = i["entry_price"]
        exit_price = i["exit_price"]
        entry_exit_set["datetime"].append(start)
        entry_exit_set["price"].append(entry_price)
        entry_exit_set["datetime"].append(end)
        entry_exit_set["price"].append(exit_price)

    x_t = entry_exit_set["datetime"]
    y_p = entry_exit_set["price"]
    P_kline.circle(x_t, y_p, legend_label='change', color="#F5B041", size=3)

    # P_acount
    y_fees = df_ledger["cum_fee(%)"]
    y_amm_pnl = df_ledger["amm_pnl(%)"]
    y_lp_pnl = df_ledger["lp_cum_pnl(%)"]

    first_timestamp = df_ledger.loc[df_ledger['event'] == 'add'].iloc[0]['timestamp']
    df_2 = df_ledger.loc[df_ledger.timestamp >= first_timestamp]
    list_1 = [0] * len(df_ledger.loc[df_ledger.timestamp < first_timestamp])
    list_2 = (100 * (df_2['price'] / df_2['price'].values[0] - 1)).tolist()
    list_3 = (100 * 0.5 * (df_2['price'] / df_2['price'].values[0] - 1)).tolist()
    y_100_holder = list_1 + list_2
    y_50_holder = list_1 + list_3

    P_account = figure(title="AMM Performance", x_axis_label="time", y_axis_label=f"{base_token}(%)",
                       height=250, sizing_mode="stretch_width", tools=tools, x_range=xdr)
    P_account.line(all_datetime_range, y_fees, legend_label="Earned Fees", color="#16A085", line_width=1.5)
    P_account.line(all_datetime_range, y_amm_pnl, legend_label="AMM PNL", color="#34495E", line_width=1.5)
    P_account.line(all_datetime_range, y_lp_pnl, legend_label="LP PNL", color="#E74C3C", line_width=1.5)
    P_account.line(all_datetime_range, y_50_holder, legend_label="50% Holder PNL", color="#F5B041", line_width=1.5)
    P_account.line(all_datetime_range, y_100_holder, legend_label="100% Holder PNL", color="#AF7AC5", line_width=1.5)
    h_line = Span(location=0, dimension='width', line_color='#17202A', line_dash='dashed', line_width=1)
    P_account.add_layout(h_line)
    P_account.legend.click_policy = "hide"

    plots = [P_PC, P_kline, P_account]

    # crosshair
    crosshair = CrosshairTool(dimensions="height")
    for i in plots:
        i.add_tools(crosshair)

    # set output file
    output_file(os.path.join(config_settings.report_folder, 'performance_chart.html'))

    # put together
    grid = gridplot(plots, toolbar_location='right', ncols=1)
    show(grid)

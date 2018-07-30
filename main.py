import abcFinance
import abce
from firm import Firm
from people import People
from bank import Bank
import pandas as pd
import plotly.offline as offline
import plotly.graph_objs as go

params = dict(
    population=5000,
    people_money=200000,
    num_firms=50,
    num_banks=5,
    firm_money=1800,

    num_days=1000,

    l=0.5,  # constant from CS equation
    num_days_buffer=10,  # number of days worth of wages a firm will keep after giving profits
    phi_upper=12,  # phi_upper * demand gives upper bound to inventory
    phi_lower=2,
    excess=2,  # if number of workers offered to work for firm exceeds 110% of ideal number, decrease wage
    wage_increment=0.1,
    price_increment=0.1,
    worker_increment=0.1,
    productivity=1,
    wage_acceptance=1,
    cash_reserves=500)

simulation = abce.Simulation(name='economy', processes=1)
# initiate banks first
group_of_banks = simulation.build_agents(Bank, "bank", number=params["num_banks"], **params)
group_of_firms = simulation.build_agents(Firm, "firm", number=params["num_firms"], **params)
people = simulation.build_agents(People, "people", number=1, **params)

(people + group_of_firms).open_bank_acc()
group_of_banks.credit_depositors()

all_agents = group_of_firms + group_of_banks + people

for r in range(params["num_days"]):
    simulation.time = r

    group_of_firms.panel_log(variables=['wage', 'ideal_num_workers'],
                             goods=['workers'])
    print("test")
    people.create_labor()

    # LOANS:
    group_of_banks.determine_interest()
    group_of_banks.send_interest_rates()
    group_of_firms.request_loan()
    group_of_banks.open_new_acc()
    group_of_banks.close_accounts()
    group_of_banks.grant_loans()

    vacancies_list = list(group_of_firms.publish_vacencies())

    people.send_workers(vacancies_list)

    group_of_firms.production()
    group_of_firms.pay_workers()

    # LOANS
    group_of_firms.loan_repayment()

    group_of_firms.send_prices()
    people.get_prices()
    demand = people.buy_goods()

    group_of_firms.sell_goods()
    group_of_firms.pay_dividends()

    group_of_firms.determine_bounds(demand=list(demand)[0])
    (group_of_firms + people).print_possessions()
    group_of_firms.determine_wage()
    group_of_firms.expand_or_change_price()
    (people + group_of_firms).destroy_unused_labor()
    people.consumption()
    all_agents.check_for_lost_messages()
    people.adjust_accounts()
    group_of_banks.book_end_of_period()


all_agents.print_balance_statement()


#all_agents.print_balance_statement()


print('done')

#simulation.graph()
path = simulation.path
simulation.finalize()


def GraphFn(graphing_variable, agent):
    """
    function that takes in graphing variable as parameter and the produces a
    graph using plotly
    """
    df = pd.read_csv(path + "/panel_" + agent + ".csv")

    print("start graph fn")
    x_data = [[] for _ in range(params["num_" + agent + "s"])]
    y_data = [[] for _ in range(params["num_" + agent + "s"])]

    for i in range(len(df)):
        name = df["name"][i]
        number = int(name[4:])
        x_data[number].append(df["round"][i])
        y_data[number].append(df[graphing_variable][i])

    data = []

    for i in range(params["num_" + agent + "s"]):
        data.append(go.Scatter(x=x_data[i],
                               y=y_data[i],
                               mode="lines"))

    layout = go.Layout(
        title="A graph of " + graphing_variable,
        xaxis=dict(title="round"),
        yaxis=dict(title=graphing_variable)
    )
    fig = go.Figure(data=data, layout=layout)
    offline.plot(fig, filename=graphing_variable + ".html")
    print("end graph fn")


def GraphFn_People(graphing_variable, agent):
    """
    function that takes in graphing variable as parameter and the produces a
    graph using plotly
    """
    df = pd.read_csv(path + "/panel_" + agent + ".csv")

    print("start graph fn")
    x_data = [[]]
    y_data = [[]]

    for i in range(len(df)):
        name = df["name"][i]
        number = int(name[4:])
        x_data[number].append(df["round"][i])
        y_data[number].append(df[graphing_variable][i])

    data = []

    data.append(go.Scatter(x=x_data[0],
                           y=y_data[0],
                           mode="lines"))

GraphFn("wage", "firm")
GraphFn("workers", "firm")
GraphFn("ideal_num_workers", "firm")
GraphFn("num_loans", "firm")


"""
Currently no where near the lower bound of cash/loan ratio, as we have one day
loans and when we call the "determine_interest" fn. there are no outstanding 
loans and therefore a 1:1 ratio.
Should we adjust ideal_num_workers, so that the value can be above what can be
afforded so then we can encourage loans to fulfill that value. Currently we just 
set the variable to a value that can be afforded.
"""

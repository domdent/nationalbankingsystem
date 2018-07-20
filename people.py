import abce
import abcFinance
import random


class People(abcFinance.Agent):

    """
    People:
    - Represents the total american population
    - Gains units of labour equal to their population at the start of each day
    - Destroys all excess labour at the end of each day
    - Buys produce from firms
        - Demand is decided by C-D utility function
        - If they can't afford to meet their demand, they buy as much produce ss possible
    - Offers to sell labour to every firm at the start of each day
        - Maximum labour offered is proportional to firm wages
        - Sends a message to the firm each round telling the firm their offer
        - If they have less labour than the maximum labour offered, they will sell ll their labour
        - Otherwise, they will sell the maximum
    """

    def init(self, people_money, population, l, num_firms, wage_acceptance, num_banks, **_):
        self.name = "people"
        self.population = population
        self.create('money', people_money)
        self.produce = 0
        self.num_firms = num_firms
        self.price_dict = {}
        self.l = l
        self.wage_acceptance = wage_acceptance
        self.accounts.make_stock_accounts(["goods"])
        self.accounts.make_flow_accounts(["consumption_expenses", "labour_value"])
        self.num_banks = num_banks
        # split deposits across banks
        split_amount = float(self["money"]) / num_banks
        for i in range(self.num_banks):
            bank_id = "bank" + str(i) + "_deposit"
            self.accounts.make_stock_accounts([bank_id])
            self.accounts.book(debit=[(bank_id, split_amount)], credit=[("equity", split_amount)])

    def open_bank_acc(self):
        # for each bank send "deposit" so they can add it to their credit
        # look into using autobook
        for i in range(self.num_banks):
            bank_ID = "bank" + str(i)
            amount = self.accounts[bank_ID + "_deposit"].get_balance()[1]
            self.send_envelope(bank_ID, "deposit", amount)

    def create_labor(self):
        """
        creates labour to add to the people's inventory
        """
        self.create('workers', self.population)

    def destroy_unused_labor(self):
        """
        destroys all labour
        """
        self.destroy('workers')

    def consumption(self):
        self.log("consumption", self["produce"])
        self.destroy("produce")

    def find_q(self):
        """
        returns the parameter q as defined in the C-D utility function
        """
        L = self.l
        q = 0
        for id in range(self.num_firms):
            q += self.price_dict[('firm', id)] ** (L / (L - 1))
        q = float(q) ** ((L - 1) / L)
        return q

    def buy_goods(self):
        """
        Calculates the demand from each firm and makes buy offers for produce of this amount at this value, or as much
        as the people can afford

        Args:   q, l parameters as defined in the C-D utility function
                firm_price = the price the firm is selling the goods for
                firm_id = the number of the firm the people are trading with
        """
        q = self.find_q()
        self.log('q', q)

        demand_list = []
        l = self.l

        I = self.not_reserved('money')
        for firm in range(self.num_firms):  # fix systematic advantage for 0 firm
            firm_price = float(self.price_dict['firm', firm])
            demand = (I / q) * (q / firm_price) ** (1 / (1 - l))
            self.buy(('firm', firm), good='produce', quantity=demand, price=firm_price)
            # Book keeping code:
            bank_acc = "bank" + str(random.randint(0, self.num_banks - 1))
            self.book(debit=[("goods", 100)], credit=[(bank_acc + "_deposit", 100)])
            self.send_envelope(('firm', firm), "account", bank_acc)

            demand_list.append(demand)
        self.log('total_demand', sum(demand_list))
        return demand_list

    def send_workers(self, vacancies_list):
        """
        Calculates the supply of employees for each firm, gives this amount of labour, or as much labour as possible
        to each firm

        Args:   sum_wages = the sum of the wages offered from every firm
                firm_wage = the wage the firm is offering
                firm_id = the number of the firm the people are trading with
        """
        wages = [vacancy["wage"] for vacancy in vacancies_list]

        max_wage = max(wages)

        distances = [1 - ((max_wage - wage) / max_wage) ** self.wage_acceptance for wage in wages]

        norm = sum(distances)

        for vacancies, dist in zip(vacancies_list, distances):
            firm = vacancies["name"]
            willing_workers = self.population / norm * dist
            if vacancies["number"] <= willing_workers:
                self.send(firm, 'max_employees', willing_workers)
                self.give(firm, good='workers', quantity=vacancies["number"])
            else:
                self.give(firm, good='workers', quantity=willing_workers)

    def print_possessions(self):
        """
        prints possessions and logs money of a person agent
        """
        print('    ' + self.group + str(dict(self.possessions())))
        self.log("money", self["money"])
        self.log("workers", self["workers"])

    def getvalue(self):
        """
        returns the value of money owned by a person agent
        """
        return self["money"]

    def getvaluegoods(self):
        """
        returns the amount of produce owned by the person agent
        """
        return self["produce"]

    def get_prices(self):
        """
        reads the messages from the firms and creates a price list
        """
        price_msg = self.get_messages("price")
        for msg in price_msg:
            self.price_dict[msg.sender] = msg.content
        return self.price_dict

    def create_income(self):
        """
        Needs to recieve message about payment and account accordingly
        :return:
        """
        messages = self.get_messages("wage_payment")

        for msg in messages:
            msg_sender = msg.sender
            wage_payment = msg.content
            if len(msg_sender) > 1 and type(msg_sender) == tuple:
                msg_sender = msg_sender[0] + str(msg_sender[1])

        for i in range(self.num_banks):
            bank_acc = "bank" + str(i)
            self.book(debit=[(bank_acc + "_deposit", (100 * self.population)/self.num_banks)],
                      credit=[("labour_value", (100 * self.population)/self.num_banks)])
        for i in range(self.num_banks):
            bank_acc = "bank" + str(i)
            self.send_envelope(bank_acc, "wage", (100 * self.population)/self.num_banks)





import abcFinance
import random

class Bank(abcFinance.Agent):
    """
    Bank
    """

    def init(self, cash_reserves, num_firms, **_):
        """
        """
        self.name = "bank" + str(self.id)

        self.accounts.make_stock_accounts(["cash", "Equity"])
        self.accounts.make_flow_accounts(["interest_income"])
        self.book(debit=[("cash", cash_reserves)],
                  credit=[("Equity", cash_reserves)])
        self.create("cash", cash_reserves)
        self.num_firms = num_firms
        self.interest = random.uniform(0.01, 0.05)  # between 1% and 5%
        self.account_list = []
        self.ratio = 0

    def credit_depositors(self):
        """

        """
        messages = self.get_messages("deposit")
        for msg in messages:
            sender = msg.sender
            amount = msg.content
            if len(sender) > 1 and type(sender) == tuple:
                sender = sender[0] + str(sender[1])
            self.account_list.append(sender + "_deposit")
            self.accounts.make_stock_accounts([(sender + "_deposit")])
            self.book(debit=[("cash", amount)],
                      credit=[(sender + "_deposit", amount)])

    def send_interest_rates(self):
        """

        """
        for i in range(self.num_firms):
            firm_id = "firm" + str(i)
            self.send_envelope(firm_id, "interest", self.interest)

    def determine_interest(self):
        """
        See how much of cash/deposit limit (1:10) is full
        """
        cash = self.accounts["cash"].get_balance()[1]
        deposits = 0
        for account in self.account_list:
            deposits += self.accounts[account].get_balance()[1]

        self.ratio = deposits / cash

        # ratio between 3-8 is good
        if self.ratio > 8:
            if self.ratio > 9:
                self.interest *= 0.9
            else:
                self.interest *= 0.95
        if self.ratio < 3:
            self.interest *= 1.1 + ((3 - self.ratio) / 50)
        # interest has to be at least 0.1 %
        self.interest = max(self.interest, 0.001)

    def open_new_acc(self):
        messages = self.get_messages("account")
        for msg in messages:
            sender = msg.sender
            amount = msg.content
            if len(sender) > 1 and type(sender) == tuple:
                sender = sender[0] + str(sender[1])
            self.accounts.make_stock_accounts([(sender + "_deposit")])
            self.book(debit=[("cash", amount)],
                      credit=[(sender + "_deposit", amount)])
            self.account_list.append(sender + "_deposit")

    def close_accounts(self):
        messages = self.get_messages("close")
        for msg in messages:
            firm_id = msg.content
            for i in range(len(self.account_list)):
                if firm_id == self.account_list[i]:
                    del self.account_list[i]

    def grant_loans(self):
        """
        look at loan and grant
        """
        loan_limit = 10 - self.ratio
        cash = self.accounts["cash"].get_balance()[1]
        loan_limit *= cash
        scaling = 1

        # find out total loans requested for scalling
        messages = self.get_messages("loan")
        total_loans_requested = 0
        for msg in messages:
            total_loans_requested += msg.content
        if total_loans_requested > loan_limit:
            scaling = loan_limit / total_loans_requested

        # actually book loans in
        for msg in messages:
            sender = msg.sender
            if len(sender) > 1 and type(sender) == tuple:
                sender = sender[0] + str(sender[1])
            amount = msg.content
            self.book(debit=[(sender + "_loan", amount * scaling)],
                      credit=[(sender + "_deposit", amount * scaling)])
            self.send(sender, "abce_forceexecute", ("_autobook", dict(
                debit=[(self.firm_id_deposit, amount * scaling)],
                credit=[("loan_liabilities", amount * scaling)])))
            loan = [amount * scaling, self.interest]
            self.send_envelope(sender, "loan_details", loan)




    def print_balance_statement(self):
        print(self.name)
       # self.print_profit_and_loss()
       # self.book_end_of_period()
        self.print_balance_sheet()

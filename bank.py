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
        self.book(debit=[("cash", cash_reserves)],
                  credit=[("Equity", cash_reserves)])
        self.create("cash", cash_reserves)
        self.num_firms = num_firms
        self.interest = random.uniform(1, 5)

    def credit_depositors(self):
        """

        """
        messages = self.get_messages("deposit")
        for msg in messages:
            sender = msg.sender
            amount = msg.content
            if len(sender) > 1 and type(sender) == tuple:
                sender = sender[0] + str(sender[1])
            self.accounts.make_stock_accounts([(sender + "_deposit")])
            self.book(debit=[("cash", amount)],
                      credit=[(sender + "_deposit", amount)])

    def print_balance_statement(self):
        print(self.name)
        self.print_profit_and_loss()
        self.book_end_of_period()
        self.print_balance_sheet()

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
        for i in range(self.num_firms):
            firm_deposit = self.accounts["firm" + str(i) + "_deposit"].get_balance()[1]
            deposits += firm_deposit
        deposits += self.accounts["people_deposit"].get_balance()[1]

        ratio = deposits / cash

        # ratio between 2-8 is good
        if ratio > 8:
            self.interest *= 0.95

        if ratio < 3:
            self.interest = (3 - ratio) 







#   def grant_loans(self):














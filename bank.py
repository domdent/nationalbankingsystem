import abcFinance

class Bank(abcFinance.Agent):
    """
    Bank
    """

    def init(self, cash_reserves, **_):
        """
        """
        self.name = "bank" + str(self.id)

        self.accounts.make_stock_accounts(["cash", "Equity"])
        self.book(debit=[("cash", cash_reserves)],
                  credit=[("Equity", cash_reserves)])
        self.create("cash", cash_reserves)

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

import abcFinance
import abce

class Bank(abcFinance.Agent):
    """
    Bank
    """

    def init(self, cash_reserves):
        """

        """
        self.name = "bank" + str(self.id)
        self.accounts.make_stock_accounts(["cash", "Equity", "customer_assets"])
        self.book(debit=[("cash", cash_reserves)], credit=[("Equity", cash_reserves)])
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
            self.accounts.make_liability_accounts([(sender + "_deposit")])
            self.book(debit=[("customer_assets", amount)], credit=[(sender + "_deposit", amount)])

    def move_deposits(self):
        """
        Need to move across deposits between banks or same banks when deposits are
        exchanged between account holders
        """
        # credit buyer deposit
        # debit seller deposit
        withdraw_amount = []
        withdraw_account = []
        messages = self.get_messages("amount")
        for msg in messages:
            withdraw_amount.append(msg.content)
        messages = self.get_messages("withdraw")
        for msg in messages:
            withdraw_account.append(msg.content)
        for i in range(len(withdraw_amount)):
            self.book(debit=[(withdraw_account[i] + "_deposit", withdraw_amount[i])],
                      credit=[("customer_assets", withdraw_amount[i])])

        messages = self.get_messages("deposit")
        deposit_account = []
        deposit_amount = []
        for msg in messages:
            sender = msg.sender
            deposit_amount.append(msg.content)
            if len(sender) > 1 and type(sender) == tuple:
                sender = sender[0] + str(sender[1])
            deposit_account.append(sender)
        for i in range(len(deposit_account)):
            self.book(debit=[("customer_assets", deposit_amount[i])],
                      credit=[(deposit_account[i] + "_deposit", deposit_amount[i])])

    def credit_income(self):
        messages = self.get_messages("wage")
        for msg in messages:
            sender = msg.sender
            amount = msg.content
            if len(sender) > 1 and type(sender) == tuple:
                sender = sender[0] + str(sender[1])
            self.book(debit=[("customer_assets", amount)], credit=[(sender + "_deposit", amount)])



    def print_possessions(self):
        """

        """
        self.log("cash", self["cash"])

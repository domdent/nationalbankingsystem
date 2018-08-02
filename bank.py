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

        self.accounts.make_stock_accounts(["gov_bonds", "bank_notes" + str(self.id)])
        self.accounts.make_flow_accounts(["interest_income", "profits"])
        self.book(debit=[("gov_bonds", cash_reserves)],
                  credit=[(self.accounts.residual_account_name, cash_reserves)])
        self.create("gov_bonds", cash_reserves)
        self.num_firms = num_firms
        self.interest = random.uniform(0.01, 0.05)  # between 1% and 5%
        self.account_list = []
        self.ratio = 0
        self.cash_reserves = cash_reserves

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
            self.book(debit=[("equity", amount)],
                      credit=[(sender + "_deposit", amount)])
            self.book(debit=[(sender + "_deposit", amount)],
                      credit=[("bank_notes" + str(self.id), amount)])
            if msg.sender != "people":
                self.send(msg.sender, "abcEconomics_forceexecute", ("_autobook", dict(
                    debit=[("bank_notes" + str(self.id), amount)],
                    credit=[(sender + "_deposit", amount)])))
            else:
                self.send("people", "abcEconomics_forceexecute", ("_autobook", dict(
                    debit=[("bank_notes" + str(self.id), amount)],
                    credit=[(self.name + "_deposit", amount)])))

    def send_interest_rates(self):
        """

        """
        print(self.name, self.interest)
        for i in range(self.num_firms):
            firm_id = ("firm", i)
            self.send_envelope(firm_id, "interest", self.interest)

    def determine_interest(self):
        """
        See how much of cash/deposit limit (1:10) is full
        """
        cash = self.accounts["gov_bonds"].get_balance()[1]
        deposits = 0
        for account in self.account_list:
            deposits += self.accounts[account].get_balance()[1]
        bank_notes = self.accounts["bank_notes" + str(self.id)].get_balance()[1]

        self.ratio = (deposits + 10 * bank_notes) / cash

        # ratio between 3-8 is good
        if self.ratio > 8:
            if self.ratio > 9:
                self.interest *= 1.15
            else:
                self.interest *= 1.05
        if self.ratio < 3:
            self.interest *= 0.9 - ((3 - self.ratio) / 50)
        # interest has to be at least 0.1 %
        self.interest = max(self.interest, 0.000001)

    def open_new_acc(self):
        messages = self.get_messages("account")
        for msg in messages:
            sender = msg.sender
            oldbank, amount = msg.content
            if len(sender) > 1 and type(sender) == tuple:
                sender = sender[0] + str(sender[1])
            print(oldbank)

            try:
                self.accounts.make_stock_accounts([sender + "_deposit"])
            except AssertionError:
                pass

            try:
                self.accounts.make_stock_accounts([oldbank + "_deposit"])
            except AssertionError:
                pass
            self.book(debit=[(oldbank + "_deposit", amount)],
                      credit=[(sender + "_deposit", amount)])
            self.account_list.append(sender + "_deposit")

    def close_accounts(self):
        messages = self.get_messages("close")
        for msg in messages:
            new_bank, balance = msg.content
            firm_id = msg.sender[0] + str(msg.sender[1])
            count = 0
            loop = True
            while loop == True:
                if str(firm_id + "_deposit") == str(self.account_list[count]):
                    del self.account_list[count]
                    loop = False
                count += 1
            try:
                self.accounts.make_stock_accounts([new_bank + "_deposit"])
            except AssertionError:
                pass
            self.accounts.book(debit=[(firm_id + "_deposit", balance)],
                               credit=[(new_bank + "_deposit", balance)])

    def grant_loans(self):
        """
        look at loan and grant
        """
        loan_limit = 10 - self.ratio
        cash = self.accounts["gov_bonds"].get_balance()[1]
        loan_limit *= cash
        scaling = 1

        # find out total loans requested for scalling
        messages = self.get_messages("loan")
        total_loans_requested = 0
        for msg in messages:
            total_loans_requested += msg.content
        if total_loans_requested > loan_limit and total_loans_requested != 0:
            scaling = loan_limit / total_loans_requested

        # actually book loans in
        for msg in messages:
            sender = msg.sender
            sender_list = msg.sender
            if len(sender) > 1 and type(sender) == tuple:
                sender = sender[0] + str(sender[1])
            amount = msg.content
            try:
                self.book(debit=[(sender + "_loan", amount * scaling)],
                          credit=[(sender + "_deposit", amount * scaling)])
            except KeyError:
                self.accounts.make_stock_accounts([sender + "_loan"])
                self.book(debit=[(sender + "_loan", amount * scaling)],
                          credit=[(sender + "_deposit", amount * scaling)])
            self.send(sender_list, "abcEconomics_forceexecute", ("_autobook", dict(
                debit=[(sender + "_deposit", amount * scaling)],
                credit=[("loan_liabilities", amount * scaling)])))
            loan = [amount * scaling, self.interest]
            self.send_envelope(sender_list, "loan_details", loan)

    def give_profits(self):
        equity = self.accounts[self.accounts.residual_account_name].get_balance()[1]
        if equity > self.cash_reserves:
            amount = equity - self.cash_reserves
            self.book(debit=[(self.accounts.residual_account_name, amount)],
                      credit=[("people_deposit", amount)])
            self.send("people", "abcEconomics_forceexecute", ("_autobook", dict(
                debit=[(self.name + "_deposit", amount)],
                credit=[("bank_profits", amount)])))


    def print_balance_statement(self):
        print(self.name)
       # self.print_profit_and_loss()
       # self.book_end_of_period()
        self.print_balance_sheet()

    def grant_bank_notes(self):
        """
        ratio is determined by the "determine_interest" Fn. so that must be
        called before this
        """
        messages = self.get_messages("bank_notes")

        for msg in messages:
            sender = msg.sender
            if len(sender) > 1 and type(sender) == tuple:
                sender = sender[0] + str(sender[1])
            sender_list = msg.sender
            amount = msg.content
            current_bank_notes = self.accounts["bank_notes" + str(self.id)].get_balance()[1]
            gov_bonds = self.accounts["gov_bonds"].get_balance()[1]
            if (amount / gov_bonds) + self.ratio <= 10:
                # if granting the bank notes doesn't go over the ratio of 10
                # book bank notes
                self.book(debit=[(sender + "_deposit", amount)],
                          credit=[("bank_notes" + str(self.id), amount)])
                self.create("bank_notes" + str(self.id), amount)
                self.send(sender_list, "abcEconomics_forceexecute", ("_autobook", dict(
                    debit=[("bank_notes" + str(self.id), amount)],
                    credit=[(sender + "_deposit", amount)])))
                self.give(sender_list, "bank_notes" + str(self.id), amount)
            else:
                print("NEED TO GET BANK NOTES FROM OTHER BANKS!!")
                pass
                # have to get bank notes from other banks...
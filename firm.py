import abcFinance
import random


class Firm(abcFinance.Agent):
    """
    Firm:
    - employs workers each round
    - offers wage based on if they found workers at the previous wage level
        - increases wage when they didn't find enough workers in previous round
        - decreases wage when they did find enough workers in previous x rounds
    - has an inventory of goods with upper and lower bounds on ideal amount
        - hires workers when they have a lower than ideal amount of inventory
        - fires workers when they have higher than ideal amount of inventory
    - prices, based on high and lower bounds
        - if inventory is low and price isn't above upper bound, increase price
        with a probability p
        - if inventory is high and price isn't below lower bound, lower price with
        a probability p
    - pay workers
    - pay left over profits to workers
    """
    def init(self, firm_money, wage_increment, price_increment, worker_increment,
             phi_upper, phi_lower, excess, num_days_buffer, productivity, num_firms,
             num_banks, population,  **_):
        """
        initializes starting characteristics
        """
        self.last_round_money = firm_money
        self.wage_increment = wage_increment
        self.price_increment = price_increment
        self.phi_upper = phi_upper
        self.phi_lower = phi_lower
        self.excess = excess
        self.num_days_buffer = num_days_buffer
        self.productivity = productivity
        self.worker_increment = worker_increment
        self.ideal_num_workers = population / num_firms * 0.5
        self.price = 20
        self.wage = 10
        self.upper_inv = 0
        self.lower_inv = 0
        self.upper_price = 0
        self.lower_price = 0
        self.profit = self.profit_1 = 0
        self.last_action = (None, None)
        # accounting
        self.num_banks = num_banks
        amount = firm_money / num_banks
        for i in range(self.num_banks):
            self.accounts.make_asset_accounts(["bank_notes" + str(i)])
        bank_id = str(random.randint(0, num_banks - 1))
        self.housebank = "bank" + str(bank_id)
        self.create("bank_notes" + str(self.housebank[4:]), firm_money)
        self.firm_id_deposit = ("firm" + str(self.id) + "_deposit")
        self.accounts.make_stock_accounts(["wages_owed"])
        self.accounts.make_asset_accounts([self.firm_id_deposit, "goods"])

        self.accounts.make_flow_accounts(["capitalized_production", "wage_expenses",
                                          "sales_revenue", "cost_of_goods_sold",
                                          "dividend_expenses", "interest_expenses"])
        self.accounts.book(debit=[(self.firm_id_deposit, firm_money)],
                           credit=[("equity", firm_money)])
        self.demand = 0
        self.opened_loan_account = False
        self.own_loan = False
        self.create("workers", 0)
        self.num_loans = 0
        self.waiting_for_bank_notes = False
        self.outstanding_payment = 0
        self.outstanding_dividends = False


    def open_bank_acc(self):
        # sends message to open bank account
        balance = self.accounts["firm" + str(self.id) + "_deposit"].get_balance()[1]
        self.send_envelope(self.housebank, "deposit", balance)


    def production(self):
        """
        produces goods to add to inventory based on number of workers and productivity
        """
        before = self["produce"]
        self.create("produce", self.productivity * self["workers"])
        # books at current wage price
        goods_value = self.productivity * self["workers"] * self.wage
        self.accounts.book(debit=[("goods", goods_value), ("wage_expenses", goods_value)],
                           credit=[("wages_owed", goods_value), ("capitalized_production", goods_value)])
        self.log("production", self["produce"] - before)

    def determine_wage(self):
        """
        determines if the wage will be altered or not
        if the ideal number of workers wasn't satisfied then raises the wage
        if the number of workers offered exceeded 110% of the ideal number then lower the wage
        """
        total_bank_notes = 0
        for i in range(self.num_banks):
            total_bank_notes += self["bank_notes" + str(i)]
        self.log("notes", total_bank_notes)

        messages = self.get_messages("max_employees")
        if self.ideal_num_workers > self['workers']:
            self.wage += random.uniform(0, self.wage_increment * self.wage)

        elif self.ideal_num_workers == self['workers']:
            max_employees = messages[0]
            if max_employees > self.excess * self.ideal_num_workers:
                self.wage -= random.uniform(0, self.wage_increment * self.wage)
                if self.wage < 0:
                    self.wage = 0
        else:
            raise Exception()

    def determine_bounds(self, demand):
        """
        determines the bound on the prices and inventory amounts

        Args:
            demand: number of units of goods demanded by people from firm
        """
        self.upper_inv = self.phi_upper * list(demand)[self.id]
        self.lower_inv = self.phi_lower * list(demand)[self.id]
        self.log('upper_inv', self.upper_inv)
        self.log('lower_inv', self.lower_inv)
        self.log('demand', list(demand)[self.id])

    def pay_dividends(self):
        total_bank_notes = 0
        for i in range(self.num_banks):
            total_bank_notes += self.accounts["bank_notes" + str(i)].get_balance()[1]
        deposits = self.accounts[self.firm_id_deposit].get_balance()[1]

        self.profits = total_bank_notes + deposits - self.last_round_money
        dividends = max(0, self.profits)
        self.last_round_money = total_bank_notes
        if dividends - deposits < 0:
            # give deposits
            # accounting
            self.accounts.book(debit=[("dividend_expenses", dividends)],
                               credit=[(self.firm_id_deposit, dividends)])
            self.send(self.housebank, "abcEconomics_forceexecute", ("_autobook", dict(
                debit=[(self.firm_id_deposit, dividends)],
                credit=[("people_deposit", dividends)])))
            self.send("people", "abcEconomics_forceexecute", ("_autobook", dict(
                debit=[(self.housebank + "_deposit", dividends)],
                credit=[("salary_income", dividends)])))

        elif dividends - deposits - total_bank_notes < 0:
            # give deposits
            self.outstanding_dividends = True
            self.accounts.book(debit=[("dividend_expenses", deposits)],
                               credit=[(self.firm_id_deposit, deposits)])
            self.send(self.housebank, "abcEconomics_forceexecute", ("_autobook", dict(
                debit=[(self.firm_id_deposit, deposits)],
                credit=[("people_deposit", deposits)])))
            self.send("people", "abcEconomics_forceexecute", ("_autobook", dict(
                debit=[(self.housebank + "_deposit", deposits)],
                credit=[("salary_income", deposits)])))
            # need to give in bank notes for deposits
            amount = dividends - deposits
            housebank_notes = self["bank_notes" + str(self.housebank[4:])]
            if amount < housebank_notes:
                self.send_envelope(self.housebank, "deposit", (amount, str(self.housebank[4:])))
                self.give(self.housebank, "bank_notes" + str(self.housebank[4:]), amount)
            else:
                self.send_envelope(self.housebank, "deposit", (housebank_notes, str(self.housebank[4:])))
                self.give(self.housebank, "bank_notes" + str(self.housebank[4:]), housebank_notes)

                # sends off for all housebank notes that agent can
                # now needs to proportionally send off for the required amount from other banks
                amount -= housebank_notes
                total_bank_notes -= housebank_notes
                # make proportionality dictionary:
                bank_note_dict = {}
                for i in range(self.num_banks):
                    balance = self["bank_notes" + str(i)]
                    bank_note_dict[i] = balance / total_bank_notes

                for i in range(self.num_banks):
                    self.send_envelope(self.housebank, "deposit", (amount * bank_note_dict[i], str(i)))
                    self.give(self.housebank, "bank_notes" + str(i), amount * bank_note_dict[i])
                    # needs to be processed in bank agent
                    # then call up second dividend function for payment
        else:
            print("ERROR: dividends - deposits - total_bank_notes is greater than 0!")


    def pay_remaining_dividends(self):
        # all deposits need to be sent
        if self.outstanding_dividends == True:
            deposits = self.accounts[self.firm_id_deposit].get_balance()[1]
            self.accounts.book(debit=[("dividend_expenses", deposits)],
                               credit=[(self.firm_id_deposit, deposits)])
            self.send(self.housebank, "abcEconomics_forceexecute", ("_autobook", dict(
                debit=[(self.firm_id_deposit, deposits)],
                credit=[("people_deposit", deposits)])))
            self.send("people", "abcEconomics_forceexecute", ("_autobook", dict(
                debit=[(self.housebank + "_deposit", deposits)],
                credit=[("salary_income", deposits)])))
            self.outstanding_dividends = False



    def expand_or_change_price(self):
        profitable = self.profit >= self.profit_1

        total_bank_notes = 0
        for i in range(self.num_banks):
            total_bank_notes += self["bank_notes" + str(i)]

        if self['produce'] > self.upper_inv:
            if not profitable or random.random() < 0.1  or self.last_action[1] != '-':
                self.last_action = random.choice([('ideal_num_workers', '-'),
                                                  ('price', '-')])
            if self.last_action != ('price', '-'):
                self.ideal_num_workers -= random.uniform(0, self.worker_increment * self.ideal_num_workers)
            elif self.last_action != ('ideal_num_workers', '-'):
                self.price -= random.uniform(0, self.price_increment * self.price)
            else:
                raise

        elif self['produce'] < self.lower_inv:
            if not profitable or random.random() < 0.1 or self.last_action[1] != '+':
                self.last_action = random.choice([('ideal_num_workers', '+'),
                                                  ('price', '+')])
            if self.last_action != ('price', '+'):
                if self['workers'] >= self.ideal_num_workers:
                    self.ideal_num_workers += random.uniform(0, self.worker_increment * self.ideal_num_workers)
                    if self.ideal_num_workers > total_bank_notes / self.wage:
                        pass # IS SOMETHING MEANT TO BE HERE???
            elif self.last_action != ('ideal_num_workers', '+'):
                self.price += random.uniform(0, self.price_increment * self.price)
            else:
                raise
        else:
            self.last_action = (None, None)

        self.price = max(self.wage, self.price)
        self.ideal_num_workers = max(0, self.ideal_num_workers)
        self.log('price', self.price)

    def sell_goods(self):
        """
        sells the goods to the employees
        """
        for offer in self.get_offers("produce"):
            self.demand = offer.quantity
            bank_notes = offer.currency
            if offer.price >= self.price and self["produce"] >= offer.quantity:
                # accounting
                sale_value = offer.price * offer.quantity
                goods_value = self.accounts["goods"].get_balance()[1]
                ave_unit_cost = goods_value / self["produce"]
                cost = ave_unit_cost * offer.quantity
                self.accounts.book(debit=[(bank_notes, sale_value),
                                          ("cost_of_goods_sold", cost)],
                                   credit=[("sales_revenue", sale_value),
                                           ("goods", cost)])
                self.send("people", "abcEconomics_forceexecute", ("_autobook", dict(
                    debit=[("goods", sale_value)],
                    credit=[(bank_notes, sale_value)])))
                self.accept(offer)
                self.log('sales', offer.quantity)

            elif offer.price >= self.price and self["produce"] < offer.quantity:
                # accounting
                sale_value = offer.price * self["produce"]
                goods_value = self.accounts["goods"].get_balance()[1]
                cost = goods_value
                self.accounts.book(debit=[(bank_notes, sale_value),
                                          ("cost_of_goods_sold", cost)],
                                   credit=[("sales_revenue", sale_value),
                                           ("goods", cost)])
                self.send("people", "abcEconomics_forceexecute", ("_autobook", dict(
                    debit=[("goods", sale_value)],
                    credit=[(bank_notes, sale_value)])))

                self.accept(offer, quantity=self["produce"])
                self.log('sales', self["produce"])

            elif offer.price < self.price:
                self.reject(offer)
                self.log('sales', 0)

    def pay_workers(self):
        """
        pays the workers
        if the salary owed is greater than owned money:
        gives out all money and reduces wage by 1 unit
        should edit this and take out loan for payments
        """
        salary = self.accounts["wages_owed"].get_balance()[1]

        total_bank_notes = 0
        for i in range(self.num_banks):
            total_bank_notes += self["bank_notes" + str(i)]

        # give bank notes
        # accounting
        # payment is in bank notes
        paid = 0
        c = list(range(0, self.num_banks))
        randomised_order = random.sample(c, self.num_banks)
        for i in randomised_order:
            if paid == salary:
                break
            note = "bank_notes" + str(i)
            balance = self[note]

            if salary - paid - balance < 0:
                # just send salary - paid worth of i bank notes
                self.give("people", note, quantity=salary - paid)
                self.accounts.book(debit=[("wages_owed", salary - paid)],
                                   credit=[(note, salary - paid)])
                self.send("people", "abcEconomics_forceexecute", ("_autobook", dict(
                    debit=[(note, salary - paid)],
                    credit=[("salary_income", salary - paid)])))
                paid = salary

            elif salary - paid - balance > 0:
                # just send balance worth of i bank notes
                self.give("people", note, quantity=balance)
                self.accounts.book(debit=[("wages_owed", balance)],
                                   credit=[(note, balance)])
                self.send("people", "abcEconomics_forceexecute", ("_autobook", dict(
                    debit=[(note, balance)],
                    credit=[("salary_income", balance)])))
                paid += balance

        if paid != salary:
            # they haven't been able to pay the workers
            # need to now either transfer deposits into bank notes
            # or take out a loan?
            deposit_balance = self.accounts[self.firm_id_deposit].get_balance()[1]
            if deposit_balance > salary - paid:
                # need to transfer deposit into bank notes for payment
                amount = salary - paid
                self.send_envelope(self.housebank, "bank_notes", amount)
                self.waiting_for_bank_notes = True
                self.outstanding_payment = amount
            elif salary - paid - deposit_balance > 0:
                print("ERROR: outstanding payment, see Fn. pay_workers in firm")
        self.salary = salary

    def pay_workers_bank_notes(self):
        if self.waiting_for_bank_notes == True:
            amount = self.outstanding_payment
            self.outstanding_payment = 0
            note = "bank_notes" + self.housebank[4:]
            self.accounts.book(debit=[("wages_owed", amount)],
                               credit=[(note, amount)])
            self.send("people", "abcEconomics_forceexecute", ("_autobook", dict(
                debit=[(note, amount)],
                credit=[("salary_income", amount)])))
            self.give("people", note, quantity=amount)
            self.waiting_for_bank_notes = False


    def getvalue_ideal_num_workers(self):
        return (self.name, self.ideal_num_workers)

    def getvalue_wage(self):
        return self.wage

    def publish_vacencies(self):

        total_bank_notes = 0
        for i in range(self.num_banks):
            total_bank_notes += self["bank_notes" + str(i)]

        if self.ideal_num_workers > total_bank_notes / self.wage:
            self.ideal_num_workers = total_bank_notes / self.wage
        return {"name": self.name, "number": self.ideal_num_workers, "wage": self.wage}

    def send_prices(self):
        self.send_envelope('people', 'price', self.price)
        return self.price

    def print_possessions(self):
        """
        prints possessions and logs money of a person agent
        """
        total_bank_notes = 0
        for i in range(self.num_banks):
            total_bank_notes += self["bank_notes" + str(i)]
        self.log("total_bank_notes", total_bank_notes)
        self.log("produce", self["produce"])
        self.log("workers", self["workers"])

    def destroy_unused_labor(self):
        """
        """
        self.destroy('workers')
        self.log('tot_wage_bill', self.salary)


    def print_balance_statement(self):
        print(self.name)
     #   self.print_profit_and_loss()
      #  self.book_end_of_period()
        self.print_balance_sheet()

    def request_loan(self):
        """
        request a loan
        """
        balance = self.accounts["firm" + str(self.id) + "_deposit"].get_balance()[1]
        total_bank_notes = 0
        for i in range(self.num_banks):
            total_bank_notes += self["bank_notes" + str(i)]
        balance += total_bank_notes

        # get all interest rates from banks
        interest = [[] for _ in range(self.num_banks)]
        messages = self.get_messages("interest")
        count = 0
        housebank_rate = 0
        loan = 0

        for msg in messages:
            if msg.sender == self.housebank:
                housebank_rate = msg.content
            interest[count].append(msg.sender)
            interest[count].append(msg.content)
            count += 1

        interest.sort(key=lambda x: float(x[1]))

        # chance of changing bank for better interest rate on loan if demand condition satisfied:
        if interest[0][0] != self.housebank and self.demand > balance / self.wage:
            prob_change = (housebank_rate - interest[0][1]) / housebank_rate
            if random.uniform(0, 1) < prob_change:
                # Fn. that does accounting statements and sends new bank a request
                self.move_banks(interest[0][0])
                housebank_rate = interest[0][1]

        # request loan
        if self.demand > balance / self.wage and housebank_rate < (self.price / self.wage) - 1:
            loan = self.demand * self.wage - balance
            if loan > 0:
                self.num_loans += 1
                if self.opened_loan_account == False:
                    self.accounts.make_stock_accounts(["loan_liabilities"])
                    self.opened_loan_account = True
                self.send_envelope(self.housebank, "loan", loan)
                self.own_loan = True

    def move_banks(self, new_bank):
        """
        moves across deposits from accounts that the people agent owns
        in personal booking statements and bank's booking statements
        """
        balance = self.accounts["firm" + str(self.id) + "_deposit"].get_balance()[1]
        self.send_envelope(self.housebank, "close", (new_bank, balance))
        # open account at new bank
        self.send_envelope(new_bank, "account", (self.housebank, balance))
        self.housebank = new_bank
        # needs to be recieved at bank's end and accounted for

    def loan_repayment(self):
        """

        """
        self.log("num_loans", self.num_loans)
        if self.own_loan == True:
            messages = self.get_messages("loan_details")
            for msg in messages:
                # loan is list with given loan amount [0] and interest [1]
                loan = msg.content
                amount = loan[0]
                interest_payment = loan[1]*loan[0]
                self.accounts.book(debit=[("interest_expenses", interest_payment)],
                                   credit=[(self.firm_id_deposit, interest_payment)])
                self.accounts.book(debit=[("loan_liabilities", amount)],
                                   credit=[(self.firm_id_deposit, amount)])
                self.send(self.housebank, "abcEconomics_forceexecute", ("_autobook", dict(
                              debit=[(self.firm_id_deposit, interest_payment)],
                              credit=[("interest_income", interest_payment)])))
                self.send(self.housebank, "abcEconomics_forceexecute", ("_autobook", dict(
                              debit=[(self.firm_id_deposit, amount)],
                              credit=[("firm" + str(self.id) + "_loan", amount)])))
                self.own_loan = False

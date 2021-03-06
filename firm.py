import abce
import random


class Firm(abce.Agent):
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
             phi_upper, phi_lower, excess, num_days_buffer, productivity, num_firms, population,  **_):
        """
        initializes starting characteristics
        """
        self.create("money", firm_money)
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

    def production(self):
        """
        produces goods to add to inventory based on number of workers and productivity
        """
        before = self["produce"]
        self.create("produce", self.productivity * self["workers"])
        self.log("production", self["produce"] - before)

    def determine_wage(self):
        """
        determines if the wage will be altered or not
        if the ideal number of workers wasn't satisfied then raises the wage
        if the number of workers offered exceeded 110% of the ideal number then lower the wage
        """
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
        #self.log('demand', list(demand)[self.id])

    def determine_profits(self):
        self.profit_1 = self.profit
        self.profit = self['money'] - self.last_round_money + self.dividends
        self.last_round_money = self['money']

    def expand_or_change_price(self):
        profitable = self.profit >= self.profit_1

        if self['produce'] > self.upper_inv:
            if not profitable or random.random() < 0.1  or self.last_action[1] != '-':
                self.last_action = random.choice([('ideal_num_workers', '-'),
                                                  ('price', '-')])
            if self.last_action != ('price', '-'):
                self.ideal_num_workers -= random.uniform(0, self.worker_increment * self.ideal_num_workers)
            elif self.last_action != ('ideal_num_workers', '-'):
                self.price -= random.uniform(0, self.price_increment * self.price)
            else:
                raise Exception()

        elif self['produce'] < self.lower_inv:
            if not profitable or random.random() < 0.1 or self.last_action[1] != '+':
                self.last_action = random.choice([('ideal_num_workers', '+'),
                                                  ('price', '+')])
            if self.last_action != ('price', '+'):
                if self['workers'] >= self.ideal_num_workers:
                    self.ideal_num_workers += random.uniform(0, self.worker_increment * self.ideal_num_workers)
            elif self.last_action != ('ideal_num_workers', '+'):
                self.price += random.uniform(0, self.price_increment * self.price)
            else:
                raise Exception()
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
            if offer.price >= self.price and self["produce"] >= offer.quantity:
                self.accept(offer)
                self.log('sales', offer.quantity)
            elif offer.price >= self.price and self["produce"] < offer.quantity:
                self.log('sales', self["produce"])
                self.accept(offer, quantity=self["produce"])
            elif offer.price < self.price:
                self.reject(offer)
                self.log('sales', 0)
            else:
                raise Exception()

    def pay_workers(self):
        """
        pays the workers
        if the salary owed is greater than owned money:
        gives out all money and reduces wage by 1 unit
        """
        salary = self.wage * self['workers']
        if salary > self["money"]:
            salary = self["money"]
            self.wage -= self.wage_increment
            self.wage = max(0, self.wage)
        self.give("people", "money", quantity=salary)
        self.salary = salary

    def pay_dividents(self):
        """
        pays workers/bosses (same agent) the extra profits
        """
        buffer = self.num_days_buffer * self.wage * self.ideal_num_workers
        dividends = self["money"] - buffer
        if dividends > 0:
            self.give("people", "money", quantity=dividends)

        self.log('dividends', max(0, dividends))
        self.dividends = dividends

    def getvalue_ideal_num_workers(self):
        return (self.name, self.ideal_num_workers)

    def getvalue_wage(self):
        return self.wage

    def publish_vacancies(self):
        return {"name": self.name, "number": self.ideal_num_workers, "wage": self.wage}

    def send_prices(self):
        self.send_envelope('people', 'price', self.price)
        self.send_envelope('farmers', 'price', self.price)
        return self.price

    def print_possessions(self):
        """
        prints possessions and logs money of a person agent
        """
        self.log("money", self["money"])
        self.log("produce", self["produce"])
        self.log("workers", self["workers"])
        self.log("firm_wage", self.wage)

    def destroy_unused_labor(self):
        """
        """
        self.destroy('workers')
        self.log('wage_share', self.salary / (self.salary + self.dividends))
        self.log('tot_wage_bill', self.salary)

"""
Figure out who owns how much to whom, and generate minimal amount of transfers between people to settle balances
"""

import argparse
import csv
import heapq
import logging
from decimal import Decimal
from numbers import Number
from typing import Callable, Sequence
from typing import TypeVar

T = TypeVar("T")

# see here https://stackoverflow.com/a/38537983
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
info = logging.info


class PrioFuncHeap:
    """
    Heap data struct for easily accessing smallest element. Supports an optional prio_func which allows for deriving
    priority from heap entries for added flexibility.

    Based on this: https://docs.python.org/3/library/heapq.html

    Motivated by wanting encapsulation in a class, heap functionality without changing underlying data and more
    flexible sorting
    """

    data: list = None
    # don't want implicit 'self' argument here, thus staticmethod
    prio_func: Callable[[T], Number] = staticmethod(lambda x: x)

    def __init__(
        self, data: Sequence[T], prio_func: Callable[[T], Number] = None
    ) -> None:
        if prio_func is not None:
            self.prio_func = prio_func
        self.data = [(self.prio_func(item), item) for item in data]
        heapq.heapify(self.data)

    def push(self, item: T) -> None:
        """
        put item on heap based on priority calculated by prio_func(item).
        :param item:
        :return: None
        """
        heapq.heappush(self.data, (self.prio_func(item), item))

    def pop(self) -> T:
        """
        remove lowest-priority item from heap and return it, where priority is determined by prio_func(item)
        :return: item with lowest priority
        """
        prio, item = heapq.heappop(self.data)
        return item

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self) -> T:
        while len(self.data) > 0:
            yield self.pop()


def resolve_transfers(balances: dict):
    """
    given a balance for each person, determine who should transfer whom how much money. positive balance = person
    should receive money from the group, mutatis mutandis for negative. greedily tries to find minimum amount of
    transfers necessary to balance accounts under the constraint that people with positive balance should never have
    to transfer money to others, given that they already gave some advance to the group
    :param balances: {person: balance} dict
    :return: list of transactions to be carried out, list of remaining unbalanced debts, same for credit
    """

    credit_recs = [
        (balance, person) for person, balance in balances.items() if balance > 0
    ]
    # highest balance = lowest priority for this heap
    credit_heap: PrioFuncHeap = PrioFuncHeap(credit_recs, lambda rec: -1 * rec[0])

    # make debts positive amounts, no need to track sign after splitting balances by pos/neg
    debt_recs = [
        (-1 * balance, person) for person, balance in balances.items() if balance < 0
    ]
    # highest balance = lowest priority for this heap
    debt_heap: PrioFuncHeap = PrioFuncHeap(debt_recs, lambda rec: -1 * rec[0])

    transactions: list = []
    while len(credit_heap) > 0 and len(debt_heap) > 0:
        debt, debtor = debt_heap.pop()
        credit, creditor = credit_heap.pop()

        # don't transfer more than debtor owes/creditor is owed
        transaction_amount: Decimal = min(debt, credit)
        transactions.append(
            {"sender": debtor, "receiver": creditor, "amount": transaction_amount}
        )

        remaining_credit = credit - transaction_amount
        if remaining_credit > 0:
            # creditor is still owed money
            credit_heap.push((remaining_credit, creditor))

        remaining_debt = debt - transaction_amount
        if remaining_debt > 0:
            # debtor still owes money
            debt_heap.push((remaining_debt, debtor))

    unbalanced_debt = list(debt_heap)
    unbalanced_credit = list(credit_heap)
    return transactions, unbalanced_debt, unbalanced_credit


def calculate_balances(records):
    """
    calculate balances
    balances -> for each transaction on record, figure out how much each debtor owes to sponsor
    easiest to also include sponsor as (implicitly) one of the debtors, as that person also has to pay fraction of
    overall price
    thus: each person involved in transaction has to pay (amount / nr_all_people_involved), subtract this from balance
    and at the same time, sponsor gets amount paid added to their balance
    :param records: iterable of dicts listing amounts paid as well as who paid (creditor) and who needs to pay back (
    debtors)
    :return: {person: balance} dict, where positive balance = group owes this person money, negative balance = person
    needs to pay money to group
    """
    balances = dict()
    for rec in records:
        sponsor = rec["sponsor"]
        debtors = rec["debtors"]
        amount = rec["amount"]
        all_people: list = [sponsor] + debtors

        # sponsor gets credited with amount paid
        prev_balance_spons = balances.get(sponsor, Decimal("0.00"))
        balances[sponsor] = prev_balance_spons + amount

        # everyone involved in the transaction gets charged with amount owed
        owed = amount / len(all_people)
        for person in all_people:
            prev_balance = balances.get(person, Decimal("0.00"))
            # rounding to full cents
            balances[person] = (prev_balance - owed).quantize(Decimal("0.01"))
    return balances


def load_records(records_file: str) -> list:
    """
    read expense records from `records_file` and parse into list of dicts. does some value conversions along the way
    :param records_file:
    :return:
    """
    with open(records_file, "r", newline="") as f:
        reader = csv.DictReader(f)
        records: list = []
        for row in reader:
            row["amount"] = Decimal(row["amount"])
            # noinspection PyTypeChecker
            row["debtors"] = row["debtors"].split(",")
            records.append(row)

    return records


def main(records_file: str) -> None:
    """
    run for file `records_file`
    :param records_file:
    :return:
    """
    records = load_records(records_file)
    balances = calculate_balances(records)

    print("final balances:")
    for person, balance in balances.items():
        print(f"{person}:\t\t{balance}")

    transactions, neg_debts, neg_credits = resolve_transfers(balances)

    print("transactions:")
    for transaction in transactions:
        print(
            f'{transaction["sender"]}\ttransfers\t{transaction["amount"]}\tto\t{transaction["receiver"]}'
        )

    for amount, person in neg_debts:
        print("missed debt due to rounding:")
        print(f"{person}: {abs(amount)}")

    for amount, person in neg_credits:
        print("missed credit due to rounding:")
        print(f"{person}: {abs(amount)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "records_file", type=str, help="path to json file listing who paid for what"
    )
    args = parser.parse_args()

    main(args.records_file)

"""
Figure out who owns how much to whom, and generate minimal amount of transfers between people to settle balances
"""

import heapq
import itertools
import logging
from decimal import Decimal
import argparse
import csv

# see here https://stackoverflow.com/a/38537983
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
info = logging.info

RECORDS_FILENAME: str = "records_example.json"


def resolve_transfers(balances: dict):
    """
    given a balance for each person, determine who should transfer whom how much money. positive balance = person
    should receive money from the group, mutatis mutandis for negative. greedily tries to find minimum amount of
    transfers necessary to balance accounts under the constraint that people with positive balance should never have
    to transfer money to others, given that they already gave some advance to the group
    :param balances: {person: balance} dict
    :return: list of transactions to be carried out, list of remaining unbalanced debts, same for credit
    """

    # from below here: all credits + debts recorded as negative numbers so that heapq can be used to easily retrieve
    # largest unsettled credit and debt

    # note: this heap puts smallest element first, but want largest credit to appear first. thus invert with -1
    neg_credits = [
        (-1 * balance, person) for person, balance in balances.items() if balance > 0
    ]
    heapq.heapify(neg_credits)

    # debts are already negative, so largest negative debt will come first
    neg_debts = [
        (balance, person) for person, balance in balances.items() if balance < 0
    ]
    heapq.heapify(neg_debts)

    transactions: list = []
    while len(neg_credits) > 0 and len(neg_debts) > 0:
        debt, debtor = heapq.heappop(neg_debts)
        credit, creditor = heapq.heappop(neg_credits)

        # debit and credit both negative, thus `max` picks least negative number
        transaction_amount: Decimal = -1 * max(debt, credit)
        transactions.append(
            {"sender": debtor, "receiver": creditor, "amount": transaction_amount}
        )

        remaining_credit = credit + transaction_amount
        if remaining_credit < 0:
            # creditor is still owed money
            heapq.heappush(neg_credits, (remaining_credit, creditor))

        remaining_debt = debt + transaction_amount
        if remaining_debt < 0:
            # debtor still owes money
            heapq.heappush(neg_debts, (remaining_debt, debtor))

    return transactions, neg_debts, neg_credits


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

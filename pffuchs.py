"""
Figure out who owns how much to whom, and generate minimal amount of transfers between people to settle balances
"""

import itertools
import logging
from decimal import Decimal
import json
import argparse

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
    :return: missed balances, which is a {person, balance} dict indicating where someone will receive too much/too
    little money due to currency rounding. also returns transfers, which is a list of money transfers to be made
    """
    pos_bals: dict = {
        person: balance for person, balance in balances.items() if balance > 0
    }
    neg_bals: dict = {
        person: balance for person, balance in balances.items() if balance < 0
    }
    transactions: list = []
    while len(pos_bals) > 0 and len(neg_bals) > 0:
        max_debt: Decimal = Decimal("0.00")
        max_debtor: str = ""
        for debtor, debt in neg_bals.items():
            if debt < max_debt:
                max_debtor = debtor
                max_debt = debt
        debtor, debt = max_debtor, neg_bals.pop(max_debtor)

        max_credit: Decimal = Decimal("0.00")
        max_creditor: str = ""
        for creditor, credit in pos_bals.items():
            if credit > max_credit:
                max_creditor = creditor
                max_credit = credit
        creditor, credit = max_creditor, pos_bals.pop(max_creditor)

        # abs because debt is negative, will always be lower otherwise
        transaction_amount: Decimal = min(abs(debt), credit)
        transactions.append(
            {"sender": debtor, "receiver": creditor, "amount": transaction_amount}
        )
        remaining_credit = credit - transaction_amount
        if remaining_credit > 0:
            # creditor is still owed money
            pos_bals[creditor] = remaining_credit
        remaining_debt = debt + transaction_amount
        if remaining_debt < 0:
            # debtor still owes money
            neg_bals[debtor] = remaining_debt
    balance_errors = itertools.chain(pos_bals.items(), neg_bals.items())
    return balance_errors, transactions


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
        rec["amount"] = Decimal(rec["amount"])
        all_people: list = [rec["sponsor"]] + rec["debtors"]

        # sponsor gets credited with amount paid
        prev_balance_spons = balances.get(rec["sponsor"], Decimal("0.00"))
        balances[rec["sponsor"]] = prev_balance_spons + rec["amount"]

        # everyone involved in the transaction gets charged with amount owed
        owed = rec["amount"] / len(all_people)
        for person in all_people:
            prev_balance = balances.get(person, Decimal("0.00"))
            # rounding to full cents
            balances[person] = (prev_balance - owed).quantize(Decimal("0.01"))
    return balances


def load_records(records_file: str) -> dict:
    with open(records_file, "r") as f:
        records = json.load(f)
    return records


def main(records_file: str) -> None:
    """
    run for file `records_file`
    :param records_file:
    :return:
    """
    info(f'loading records from {records_file}')
    records = load_records(records_file)
    balances = calculate_balances(records)

    print("final balances:")
    for person, balance in balances.items():
        print(f"{person}:\t\t{balance}")

    balance_errors, transactions = resolve_transfers(balances)

    print("transactions:")
    for transaction in transactions:
        print(f'{transaction["sender"]}\ttransfers\t{transaction["amount"]}\tto\t{transaction["receiver"]}')

    for person, transaction_amount in balance_errors:
        print('missed balance:')
        print(f"{person}: {transaction_amount}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('records_file', type=str, help="path to json file listing who paid for what")
    args = parser.parse_args()

    main(args.records_file)

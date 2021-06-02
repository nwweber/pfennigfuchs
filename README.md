# pfennigfuchs
Split expenses between a group of people. 

Given a bunch of 'who paid for what' records determines final balances and generates transactions necessary between people, aiming to reduce number of transactions necessary. Sanely rounds currency amounts.

Please see `records_example.json` for a worked example on how to record past expenses.

Usage:
```bash
python pffuchs.py records_example.json
```
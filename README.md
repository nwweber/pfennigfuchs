# pfennigfuchs
Split expenses between a group of people. 

Given a bunch of 'who paid for what' records determines final balances and generates transactions necessary between people, aiming to reduce number of transactions necessary. Sanely rounds currency amounts.

Please see `records_example.csv` for a worked example on how to record past expenses.

You should be able to use any text or spreadsheet editor to edit your csv files. csv files are expected to be in excel
dialect - if you copy the example and modify it your editor should pick the right formatting automatically.

Usage:
```bash
python pffuchs.py records_example.csv
```
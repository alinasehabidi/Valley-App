# Add the bi-weekly neighbourhood files here

Supported files:

- DXBinteract sales and rental PDF reports;
- CSV files;
- Excel `.xlsx` and `.xlsm` files;
- official Dubai Land Department Transactions and Rents CSV exports.

Recommended names:

```text
Nara - Sales.pdf
Nara - Rentals.pdf
Elora - Sales.pdf
Elora - Rentals.pdf
```

Subfolders per neighbourhood are supported. Replace the previous current report for that neighbourhood; the generated files under `data/processed/` retain records already seen.

For DXBinteract PDFs, the report heading identifies sales or rentals and the transaction rows provide the neighbourhood. For CSV/Excel files, include a `cluster`/`project` column or make the neighbourhood clear in the filename.

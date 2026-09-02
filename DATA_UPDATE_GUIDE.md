# Bi-weekly cluster data update

## Normal update

1. Export one sales report and one rental report for each neighbourhood being tracked.
2. Put the files in `data/incoming/`.
3. Use clear names such as `Nara - Sales.pdf` and `Nara - Rentals.pdf`.
4. Replace that neighbourhood's previous current file rather than keeping many dated copies.
5. Commit and push the change to GitHub.

The included **Refresh processed market data** workflow will:

- read every supported PDF, CSV and Excel file under `data/incoming/`;
- identify sales and rental files;
- combine all available neighbourhoods;
- remove exact overlap with earlier exports;
- retain historic registrations in `data/processed/sales.csv` and `rentals.csv`;
- commit the refreshed processed files back to the repository.

The Streamlit deployment then refreshes from the updated repository.

## Building a full 12-month view

The chart can display a complete 12-month calendar window, but it can only plot months that exist in the transaction-level source files or the saved processed history. Summary totals in a PDF cannot be converted into missing monthly transactions.

For the first full year, add per-neighbourhood exports that cover the preceding 12 months, or add older exports in batches and run the data refresh after each batch. Thereafter, the processed CSV files retain newly seen registrations from every bi-weekly update. Months with no matching registrations remain blank rather than being estimated.

## Recommended folder layout

A flat folder works, but subfolders can make larger updates easier:

```text
data/incoming/
├── Nara/
│   ├── Nara - Sales.pdf
│   └── Nara - Rentals.pdf
├── Elora/
│   ├── Elora - Sales.pdf
│   └── Elora - Rentals.pdf
└── Talia/
    ├── Talia - Sales.pdf
    └── Talia - Rentals.pdf
```

The importer searches subfolders automatically.

## CSV and Excel fields

The simplest formats are shown in `data/templates/`. Common alternatives are also recognised, including:

- `Sale Price`, `Amount`, `Price / sqft`, `Beds`, `Room(s)` and `Transaction Date`;
- `Annual Rent`, `Contract Amount`, `Annual Amount`, `Rental Yield`, `Version`, `Start Date` and `End Date`;
- areas stated in square feet or Dubai Land Department square metres.

For a per-cluster CSV without a `cluster` or `project` column, include the neighbourhood in the filename, such as `Nara - Sales.csv`.

## Public privacy

The app does not provide a full-data download and displays only the latest eight matching registrations. Keep the repository private as well if the underlying source files must not be publicly accessible.

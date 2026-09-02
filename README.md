# Inside The Valley — Market Insights

A client-facing Streamlit application for `insidethevalley.ae`, designed around the website's understated cream, sand and forest-green visual language.

The public experience is intentionally simple: a visitor chooses one market, one neighbourhood and one filter option at a time. There is no multi-cluster comparison and no full-dataset download.

## Public experience

- Separate **Sales** and **Rentals** views.
- One neighbourhood at a time.
- One buyer/seller or tenant/landlord perspective at a time.
- One bedroom choice and one sale/contract type at a time.
- Clear **6 or 12-month** trends, with 12 months selected by default.
- Plain-language interpretation for buyers, sellers, tenants and landlords.
- Branded summary cards and mobile-friendly recent-record cards.
- Only the latest eight matching registrations are displayed.
- No public source-file browser or CSV download.

## Bi-weekly data workflow

The data layer accepts any number of per-cluster files in:

```text
data/incoming/
```

Supported formats:

- DXBinteract sales and rental PDF reports;
- CSV files;
- Excel `.xlsx` and `.xlsm` workbooks;
- Dubai Land Department Transactions and Rents CSV exports.

Clear filenames are recommended, for example:

```text
Nara - Sales.pdf
Nara - Rentals.pdf
Elora - Sales.pdf
Elora - Rentals.pdf
```

Replace each cluster's current report every two weeks. The GitHub workflow merges newly seen records into the persistent history under `data/processed/` and avoids re-adding exact overlaps from the previous export.

## Repository structure

```text
.
├── app.py                         # Streamlit Cloud entry point
├── src/
│   ├── analytics.py
│   ├── data_pipeline.py
│   └── theme.py
├── data/
│   ├── incoming/                  # add/replace bi-weekly cluster reports
│   ├── processed/                 # generated persistent history
│   └── templates/                 # simple CSV examples
├── scripts/update_data.py
├── tests/test_data_pipeline.py
├── DATA_UPDATE_GUIDE.md
├── DEPLOYMENT.md
└── docs/DXBINTERACT.md
```

## Local development

Local hosting is not required for production, but it can be used to preview changes:

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt
python -m streamlit run app.py
```

## Rebuild the persistent data

```bash
python scripts/update_data.py
```

## Cloud deployment

Deploy the repository using root file:

```text
app.py
```

Keep the GitHub repository private if the source PDFs and processed CSV history should remain private. The deployed Streamlit application can still be public and embedded in WordPress. See `DEPLOYMENT.md`.

## Optional environment settings

```text
ITV_CONTACT_URL       destination for the call-to-action buttons
ITV_LOGO_URL          alternative hosted logo URL
ITV_DEFAULT_CLUSTER   neighbourhood selected when no query parameter is supplied
ITV_SHOW_DATA_STATUS  set to true to expose administrator diagnostics
ITV_INCOMING_DIR      alternative incoming-data directory
ITV_PROCESSED_DIR     alternative processed-data directory
```

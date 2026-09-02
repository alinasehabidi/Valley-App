# DXBinteract connection status

## Supported and reliable now

This repository directly parses exported DXBinteract sales and rental PDF reports. Put each bi-weekly project or neighbourhood report in `data/incoming/`; the data workflow merges newly seen records into the persistent history.

CSV and Excel files are also supported.

## Automated extraction finding

DXBinteract provides downloadable market reports and advertises a Claude connector for asking questions about transactions, rents, yields and location trends. The official “Add to Claude” link points to the MCP endpoint `https://brain.dxbinteract.com/mcp`. I did not find public documentation confirming its transaction-row schema, unattended server authentication, rate limits or website-republication rights, and I did not find a documented transaction-level REST API that can safely power this website.

DXBinteract also publishes a downloadable CSV page, but that page describes project inventory and unit-layout fields such as unit types, bedroom configurations, actual areas and balcony areas. It is not described as the full sales and rental transaction feed required by this dashboard.

For that reason, the repository does **not** reverse-engineer private endpoints or scrape the DXBinteract interface. Such an integration should only be added after DXBinteract supplies written API documentation, authentication details and permission to cache and republish the data on `insidethevalley.ae`.

## Structured alternative

Dubai Land Department's official open-data page allows Transactions and Rents results to be downloaded as CSV. The importer in this repository recognises the main DLD fields, including:

- Transactions: project, transaction date, amount, registration type, property type, rooms and square-metre transaction/property size;
- Rents: project, start/end dates, contract amount, annual amount, version, property type, rooms and square-metre property size.

The DLD website currently presents these downloads through an interactive search with a captcha, so the practical workflow is still to download the CSV and place it in `data/incoming/`. Earlier-year data is directed to Dubai Pulse by DLD.

## Practical decision

Use the per-cluster DXBinteract PDF exports for the immediate bi-weekly workflow. DLD CSV exports are available as a second structured source. A direct live DXBinteract feed remains pending official API access and republication permission.

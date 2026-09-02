# Deployment and website embedding

## Recommended privacy setup

Keep the GitHub repository **private** because it contains the source PDF/CSV files and the processed history. Streamlit Community Cloud can be granted access to a private repository, while the deployed app itself can be made public for website visitors.

The public interface does not include a full-data download and only displays the latest eight matching records. A public GitHub repository would still expose the raw files, so do not make the repository public if you want to withhold the complete dataset.

## Streamlit Community Cloud

1. Upload this repository to a private GitHub repository.
2. Grant Streamlit Community Cloud permission to access private repositories.
3. Create a Streamlit app from the repository.
4. Set the main file path to `app.py`.
5. Make the deployed app public so it can be embedded on the website.

## Embed on insidethevalley.ae

Add a Custom HTML block in WordPress and use:

```html
<iframe
  src="https://YOUR-STREAMLIT-APP.streamlit.app/?embed=true"
  title="Inside The Valley market insights"
  width="100%"
  height="1550"
  style="border:0; border-radius:20px; overflow:hidden;"
  loading="lazy">
</iframe>
```

Replace the URL with the deployed application. Adjust the height after checking the page on mobile and desktop.

A cluster can be preselected with a query parameter:

```text
https://YOUR-STREAMLIT-APP.streamlit.app/?embed=true&market=Sales&goal=Buying&cluster=Nara
```

This allows a Nara community page, for example, to open directly on Nara while still keeping only one cluster selected.

## Generic hosting

The included `Procfile` and `Dockerfile` both start the root `app.py` entrypoint.

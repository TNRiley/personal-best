"""
Download the World Cube Association results export (TSV flavour) into ../.cache/ and unzip it.

    python fetch.py            # skips the download if the zip is already there
    python fetch.py --force    # fetch the current export again

The export is ~380 MB zipped and ~1.6 GB unpacked. The WCA republishes it daily; the
export date is recorded in .cache/metadata.json and carried into the payload.
"""
import json, os, sys, urllib.request, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "..", ".cache")
API = "https://www.worldcubeassociation.org/api/v0/export/public"

os.makedirs(CACHE, exist_ok=True)
zpath = os.path.join(CACHE, "wca.zip")
if "--force" in sys.argv or not os.path.exists(zpath):
    with urllib.request.urlopen(API) as r:
        info = json.load(r)
    print("export dated", info["export_date"], "->", info["tsv_url"])
    urllib.request.urlretrieve(info["tsv_url"], zpath)
with zipfile.ZipFile(zpath) as z:
    z.extractall(CACHE)
print("unpacked into", os.path.abspath(CACHE))

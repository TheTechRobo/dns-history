from flask import *
from subprocess import run
from rethinkdb import r
r.set_loop_type('asyncio')
import time, sys
from datetime import datetime

app = Flask(__name__)

@app.route("/Save", methods=("GET","POST"))
async def save():
    if request.method == "GET":
        return render_template("save.html")
    conn = await r.connect("localhost", 28015)
    try:
        sites = request.form["site"].strip().split(" ")
    except KeyError:
        abort(400)
    D = {}
    for site in sites:
        site = site.encode("idna").decode().lower()
        D[site] = run(
                [
                    "dig", site, "ANY", "@8.8.8.8"
                ], shell=False, capture_output=True
        )
        D[site].tsTTR = time.time()
        D[f'www.{site}'] = run(
                [
                    "dig", f"www.{site}", "ANY", "@8.8.8.8"
                ], shell=False, capture_output=True
        )
        D[f'www.{site}'].tsTTR = time.time()
    #    l = {f"www.{site}": sudo2, site: sudo}
    keys = []
    for site, i in D.items():
        ts = i.tsTTR
        ret = await r \
            .db("dns") \
            .table("entries") \
            .insert(
                    {
                        "ts": ts,
                        "data": i.stdout.decode(),
                        "error":i.stderr.decode(),
                        "site": site
                        }
                    ) \
            .run(conn)
        keys.append(ret["generated_keys"][0])
    return render_template("saved.html", siteLinks=D, siteIds=keys, site=site, ts=ts), 201
@app.route("/Clickclickclick", methods=["GET", "POST"])
async def read():
    if request.method == "POST":
        try:
            site = request.form['site'].lower().strip()
            getByIds = request.form.get('ids')
            json = request.form.get('json')
        except KeyError:
            abort(400)
    else:
        try:
           site = request.args['q'].lower().strip()
           getByIds = request.args.get('ids')
           json = request.args.get('json')
        except KeyError:
            abort(400)
    sites = site.split(" ")
    datums = {}
    for site in sites:
        tmp = []
        conn = await r.connect("localhost", 28015)
        if getByIds:
            i = await r.db("dns").table("entries").get(site) \
                    .run(conn)
            if i:
                tmp.append(i)
        else:
            cursor = await r.db("dns").table("entries").get_all(
                    site.encode("idna").decode(), index="site"
                    ).run(conn)
            async for i in cursor:
                tmp.append(i)
        await conn.close()
        datums[site] = tmp
    if json:
        return datums
    return render_template("searchresults.html",
            sitedatums=datums, datetime=datetime, sorted=sorted, checkSORTED=lambda s : s['ts']
    )
@app.route("/Read/<site>/<float:ts>")
async def redir(site, ts):
    return await old(site, ts)
@app.route("/Read/<site>/<float:ts>.<ext>")
async def old(site, ts, ext="html"):
    conn = await r.connect("localhost", 28015)
    cursor = await r.db("dns").table("entries").get_all(site, index="site").filter(
            {"ts": ts}
            ).run(conn)
    a = []
    async for i in cursor:
        a.append(i)
    if len(a) > 1:
        print("\tSomething funny happened.", a, file=sys.stderr)
        return "Inappropriate number of responses for the same TS", 500
    if len(a) == 0:
        a[0] = {'id': None}
    link = f"/Read/{a[0]['id']}"
    return await route(a[0]['id'], ext)
@app.route("/Read/<id>")
async def redir2(id):
    return await route(id)
@app.route("/Read/<id>.<ext>")
async def route(id, ext="html"):
    conn = await r.connect("localhost", 28015)
    data = await r.db("dns").table("entries").get(id).run(conn)
    if ext == "json":
        if not data:
            return data, 404
        return data
    if not data:
        return "Couldn't find that ID in the database.", 404
    data['data'] = "<h2>stdout:</h2>" + data['data'].lstrip("\n")
    if data.get('error'):
        data['data'] += f"\n\n<h2>stderr:</h2>{data['error']}"
    return data['data'].replace("\n","<br>"), 200

@app.route("/")
async def slash():
    return render_template("index.html")

@app.route("/api")
async def api():
    endpoints = [
            {"url": "/Clickclickclick", "title": "Searching for records (exact match)", "method": "GET", "p": "(query string)","params": {
                "q":"Domains to search for (space-separated)", "ids (optional)": "Set to any value to search by primary key rather than by domain name. Used in Save DNS Now", "json": "Set this parameter to return JSON."
                },
            }, {
                "nb": "You can access full record data (including the date!) as JSON by tacking on .json to the URL. Note however that this data is returned in the search results (/Clickclickclick) if JSON is requested. As such, if you are using the search results and following the links, just request JSON in your search results for one less request.", "url": "/Read/<id>", "title": "Read record data (minus date) by primary key", "method": "GET", "p": "(URL)", "params": {
                    "id": "The primary key of the document."
                },
            }, {
                "nb": "You can access full record data (including the date!) as JSON by tacking on .json to the URL. Note however that this data is returned in the search results (/Clickclickclick) if JSON is requested. As such, if you are using the search results and following the links, just request JSON in your search results for one less request.", "url": "/Read/<site>/<timestamp>", "title": "Read record data (minus date) by site and timestamp", "method": "GET", "p": "(URL)", "params": {
                    "site": "The domain name",
                    "timestamp": "The timestamp (UNIX epoch) of the record"
                },
            }, {
                "url": "/Save", "title": "Save DNS Now", "method": "POST", "p": "(request body)", "nb": "There is no JSON counterpart here; if you want to get the data, you will need to use HTML parsing.", "params": {
                    "site": "The DNS domains to save, space-separated"
                },
            },
        ]
    return render_template("api.html", endpoints=endpoints)

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
        return """
        <FORM ACTION="/Save" METHOD="POST">
        <INPUT ID="site" NAME="site" PLACEHOLDER="Domain to save">
        </FORM>
        <h1>Save Domain Now</h1>
        <h4>Will also grab www.{domain}</h4>
        """
    conn = await r.connect("localhost", 28015)
    try:
        site = request.form.get('site')
        if site is None: raise KeyError
    except KeyError:
        abort(400)
    site = site.encode("idna").decode().lower()
    #print(f"dig {site} ANY @8.8.8.8")
    sudo = run(
            [
                f"dig {site} ANY @8.8.8.8"
            ], shell=True, capture_output=True
    )
    sudo.tsTTR = time.time()
    sudo2 = run(
            [
                f"dig www.{site} ANY @8.8.8.8"
            ], shell=True, capture_output=True
    )
    sudo2.tsTTR = time.time()
    l = {f"www.{site}": sudo2, site: sudo}
    for site, i in l.items():
        ts = i.tsTTR
        keys = await r \
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
        key = keys["generated_keys"][0]
    return """
    Successfully saved page info.
    <br>You can view it <a href="/Read/{site}/{ts}">here</a>.
    """.format(site=site, id=key, ts=ts), 201
@app.route("/Clickclickclick", methods=["GET", "POST"])
async def read():
    if request.method == "POST":
        try:
            site = request.form['site'].lower()
        except KeyError:
            abort(400)
    else:
        try:
           site = request.args['q'].lower()
        except KeyError:
            abort(400)
    datums = []
    cursor = await r.db("dns").table("entries").get_all(
            site.encode("idna").decode(), index="site"
            ).run(await r.connect("localhost", 28015))
    async for i in cursor:
        datums.append(i)
    return render_template_string(
            """
            <h1>{{sitedata|length}} snapshots for {{site}}</h1>
            {% for i in sitedata %}
            <a href="/Read/{{i['site']}}/{{i['ts']}}">{{datetime.fromtimestamp(i['ts'])}}</a>
            <BR>
            {% endfor %}
            <h4>You've reached the end</h4>
            """,
            sitedata=datums, datetime=datetime, site=site
    ), 200
@app.route("/Read/<site>/<float:ts>")
async def old(site, ts):
    conn = await r.connect("localhost", 28015)
    cursor = await r.db("dns").table("entries").get_all(site, index="site").filter(
            {'site': site, "ts": ts}
            ).run(conn)
    a = []
    async for i in cursor:
        a.append(i)
    #print(a)
    if len(a) > 1:
        print("\tSomething funny happened.", a, file=sys.stderr)
        return "Inappropriate number of responses for the same TS", 500
    if len(a) == 0:
        return "<IMG SRC='https://web.archive.org/web/20211128194924im_/https://preview.redd.it/1htemhh633r21.jpg?width=960&crop=smart&auto=webp&s=259c2baf582e29e467d5d49f9f461a7bcd081d6d' ALT='WeirdChamp'>", 404
    link = f"/Read/{a[0]['id']}"
    return await route(a[0]['id'])
@app.route("/Read/<id>")
async def route(id):
    conn = await r.connect("localhost", 28015)
    data = await r.db("dns").table("entries").get(id).run(conn)
    if not data:
        return "Couldn't find that ID in the database.", 404
    if data.get('error'):
        data['data'] += f"\n\nstderr:\n{data['error']}"
    return data['data'].replace("\n","<br>"), 200

@app.route("/")
async def slash(): return """<form action="/Clickclickclick" method="get"><input name="q" id="q" placeholder="example.com"><label for="q">Domain name</label></form><i>Don't use https?://, or a path</i><br><br><h2>Save DNS Now</h2><a href="/Save">Here</a>"""

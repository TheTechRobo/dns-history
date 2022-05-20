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
        <p><i>Separate multiple domains with a space.</i></p>
        """
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
    return render_template_string("""
    Successfully saved page info for {{siteLinks|length}} sites.
    <br>You can view them <a href="/Clickclickclick?q={{" ".join(siteIds)}}&ids=1">here</a>
    """, siteLinks=D, siteIds=keys, site=site, ts=ts), 201
@app.route("/Clickclickclick", methods=["GET", "POST"])
async def read():
    if request.method == "POST":
        try:
            site = request.form['site'].lower().strip()
            getByIds = request.form.get('ids')
        except KeyError:
            abort(400)
    else:
        try:
           site = request.args['q'].lower().strip()
           getByIds = request.args.get('ids')
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
    return render_template_string(
            """
            <!DOCTYPE html><html><title>Search results for {{site}}</title><body>
            {% for site, sitedata in sitedatums.items() %}
                <div id="{{site}}">
                <h1>
                {% if sitedata|length == 0 %}
                    No snapshots
                {%elif sitedata|length == 1%}
                    Snapshot
                {%else%}
                    {{sitedata|length}} snapshots
                {%endif%}
                 for {{site}}
                {% if "." not in site %}
                    {% if sitedata|length != 0 %}
                        ({{sitedata[0]["site"]}})
                    {%endif%}
                {% endif %}</h1>
                {% for i in sitedata %}
                    <a href="/Read/{{i['site']}}/{{i['ts']}}">{{datetime.fromtimestamp(i['ts'])}}</a>
                    <BR>
                {% endfor %}
                <h4>You've reached the end</h4>
                </div>
            {%endfor%}</body>
            """,
            sitedatums=datums, datetime=datetime
    ), 200
@app.route("/Read/<site>/<float:ts>")
async def redir(site, ts):
    return await old(site, ts)
@app.route("/Read/<site>/<float:ts>.<ext>")
async def old(site, ts, ext="html"):
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
    return await route(a[0]['id'], ext)
@app.route("/Read/<id>")
async def redir2(id):
    return await route(id)
@app.route("/Read/<id>.<ext>")
async def route(id, ext="html"):
    conn = await r.connect("localhost", 28015)
    data = await r.db("dns").table("entries").get(id).run(conn)
    if ext == "json":
        return data
    if not data:
        return "Couldn't find that ID in the database.", 404
    if data.get('error'):
        data['data'] += f"\n\nstderr:\n{data['error']}"
    return data['data'].replace("\n","<br>"), 200

@app.route("/")
async def slash(): return """<form action="/Clickclickclick" method="get"><input name="q" id="q" placeholder="example.com"><label for="q">Domain name</label></form><i>Don't use https?://, or a path</i><br><br><h2>Save DNS Now</h2><a href="/Save">Here</a>"""

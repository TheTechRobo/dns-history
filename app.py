from flask import *
from subprocess import run
from rethinkdb import r
r.set_loop_type('asyncio')
import time
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
    sudo = run(
            [
                f"dig {site} ANY @8.8.8.8"
            ], shell=True, capture_output=True
    )
    sudo2 = run(
            [
                f"dig www.{site} ANY @8.8.8.8"
            ], shell=True, capture_output=True
    )
    l = {site: sudo, f"www.{site}": sudo2}
    for site, i in l.items():
        await r \
            .db("dns") \
            .table("entries") \
            .insert(
                    {
                        "ts": time.time(),
                        "data": i.stdout.decode(),
                        "site": site
                        }
                    ) \
            .run(conn)
    return "SavePageNow SUCCESS!!", 201
@app.route("/Clickclickclick", methods=["POST"])
async def read():
    if request.form.get('site') is None: abort(400)
    site = request.form['site']
    datums = []
    cursor = await r.db("dns").table("entries").filter(
            {'site': site}
            ).run(await r.connect("localhost", 28015))
    async for i in cursor:
        datums.append(i)
    if not datums:
        return "No such site in database", 404
    """
    if datums[0] is False:
        return "No such site in database", 410
    if datums[0] is None:
        return "No such site in database", 451
    """
    return render_template_string(
            """
            <h1>Snapshots for {{sitedata[0]['site']}}</h1>
            {% for i in sitedata %}
            <a href="/Read/{{i['site']}}/{{i['ts']}}">{{datetime.fromtimestamp(i['ts'])}}</a>
            <BR>
            {% endfor %}
            <h4>You've reached the end</h4>
            """,
            sitedata=datums, datetime=datetime
    ), 300
@app.route("/")
async def slash(): return """<form action="/Clickclickclick" method="post"><input name="site" id="site" placeholder="example.com"><label for="site">Domain name</label></form><i>Don't use https?://, or a path</i><br><br><h2>Save DNS Now</h2><a href="/Save">Here</a>"""

from flask import *
from rethinkdb import r

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
    try:
        site = request.form.get('site')
        if site is None: raise KeyError
    except KeyError:
        abort(400)
    return site

from rethinkdb import r

import copy

conn = r.connect()

from datetime import datetime

for i in r.db("dns").table("entries").run(conn):
    try:
        a = i['site'].split('.')
        nd = {
            'tld': a[-1],
            }
        try:
            nd['secondDeepDown'] = a[-2]
            nd['thirdDeepDown'] = a[-3]
        except IndexError:
            pass

        if not i.get("year"):
            dt = datetime.fromtimestamp(i['ts'])
            nd['year'] = dt.year
            nd['month'] = dt.month
            nd['day'] = dt.day

        r.db("dns").table("entries").get(i['id']).update(nd).run(conn, durability='soft')
    except (KeyError, IndexError):
        print(i)

r.db("dns").table("entries").sync()

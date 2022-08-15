from rethinkdb import r

import copy, gzip

conn = r.connect()

from datetime import datetime

input("This version of reindexDB will recompress everything with gzip. If you don't want that, comment out the code. Press ENTER to continue, Ctrl+C to cancel...")

for i in r.db("dns").table("entries").run(conn):
    try:
        try:
            i['site'] = i['site'].decode()
            i['error'] = i['error'].decode()
        except Exception:
            pass
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

        # gzip
        if not i.get("gzip"):
            nd['data'] = gzip.compress(bytes(i['data'], "utf-8"))
            if i.get('error'):
                nd['error'] = gzip.compress(bytes(i['error'], "utf-8"))
            nd['gzip'] = True
        # end gzip

        r.db("dns").table("entries").get(i['id']).update(nd).run(conn, durability='soft')
    except (KeyError, IndexError):
        print(i)

r.db("dns").table("entries").sync()

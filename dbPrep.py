from rethinkdb import r
from alive_progress import alive_bar # if this raises an exception, pip install alive_progress

print("PLEASE NOTE:")
print("\tIf the database already exists, the script will fail.")
print("\tRather than me updating the script to fix this, potentially overwriting people's DBs, if you already have a DNSHistory database for this script, follow the steps in TRANSGRADING.md.")

conn = r.connect()

print("Connected to RethinkDB.")
print("Transferring bytes at the speed of light...")

r.db_create("dns").run(conn)
r.db("dns").table_create("entries").run(conn)
r.db("dns").table_create("analytics").run(conn)

print("Created database with proper tables.")
print("Creating secondary indexes. This may take some time...")

with alive_bar(total=8) as bar:
    for i in ("day", "month", "secondDeepDown", "site", "thirdDeepDown", "tld", "ts", "year"):
        print(r.db("dns").table("entries").index_create(i).run(conn))
        bar()

print("Waiting for indexes to be ready...")
r.db("dns").table("entries").index_wait().run(conn)

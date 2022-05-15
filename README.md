# dns-history
Knockoff of dnshistory.org

## Initialisation
Install RethinkDB. Create a database called "dns"; add a table named "entries". Create a new secondary index called "site".

Now, run the WSGI however you want. I use gunicorn because it's simple.

**You're done!**

## Hosted version
http://thetechrobo.ca:8000

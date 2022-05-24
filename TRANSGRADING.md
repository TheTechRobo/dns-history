Tree:

```
dns
	entries
		secondary indexes:
			day
			month
			secondDeepDown
			site
			thirdDeepDown
			tld
			ts
			year
	analytics (optional)
		no secondary indexes
```

Please note: If you are transgrading from a previous commit, you will need to reindex your database. Otherwise, search filters that use those secondary indexes other than 'site' won't work. (Previously, the data stored did not contain some fields. There's no data loss from previous versions, but you will need to run reindexDB.py, which will be very slow if you have a lot of documents.)

MERGE (me:Person {id:"user:demo"}) SET me.name="Demo User"
MERGE (sf:Place {id:"place:san_francisco"}) SET sf.name="San Francisco"
MERGE (acme:Org {id:"org:acme"}) SET acme.name="Acme"
MERGE (me)-[:LIVES_IN]->(sf)
MERGE (me)-[:WILL_START_AT]->(acme)

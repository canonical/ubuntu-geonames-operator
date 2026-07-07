#!/usr/bin/python3
from flask import Flask, request, jsonify

import pymysql
import json
import pymysql.cursors
import psycopg2
try:
    from config import authstring
except ImportError:
    authstring = 'dbname=geonames user=geouser password=geopw host=localhost'

app = Flask(__name__)


SPHINXSEARCH_QUERY = 'SELECT id FROM geonames WHERE MATCH(\'"%s"\') ORDER BY population DESC LIMIT 100'

statement = """
SELECT
geoname.name,
admin1codes.name,
admin2codes.name,
countryInfo.name,
countryInfo.continent,
geoname.longitude,
geoname.latitude,
geoname.timezone,
geoname.population
FROM geoname
left join countryInfo on (geoname.country = countryInfo.iso_alpha2)
left join admin1codes on (admin1codes.code = geoname.country||'.'||geoname.admin1)
left join admin2codes on (admin2codes.code = geoname.country||'.'||geoname.admin1||'.'||geoname.admin2)
WHERE geoname.geonameid in %s
UNION
SELECT
alternatename.alternatename,
admin1codes.name,
admin2codes.name,
countryInfo.name,
countryInfo.continent,
geoname.longitude,
geoname.latitude,
geoname.timezone,
geoname.population
FROM
alternatename
left join geoname on (geoname.geonameid=alternatename.geonameid)
left join countryInfo on (geoname.country = countryInfo.iso_alpha2)
left join admin1codes on (admin1codes.code = geoname.country||'.'||geoname.admin1)
left join admin2codes on (admin2codes.code = geoname.country||'.'||geoname.admin1||'.'||geoname.admin2)
where alternatename.alternatenameId in %s
ORDER by population desc;
"""
jsonheader = '['
jsonfooter = ']'
jsonentry = '{"name" : "%s", "admin1" : "%s", "admin2" : "%s", "country" : "%s", "continent" : "%s", ' \
            '"longitude" : "%F", "latitude" : "%F" , "timezone" : "%s" }'


def handle_query(query):
    with pymysql.connect(host="127.0.0.1", port=9306, cursorclass=pymysql.cursors.DictCursor) as db:
        with db.cursor() as cur:
            cur.execute(SPHINXSEARCH_QUERY % query)
            row = cur.fetchall()
    result = row
    ret = []
    if result:
        connection = psycopg2.connect(authstring)
        cursor = connection.cursor()
        try:
            # We need at least one value for the sql in operator
            # and there are no locations with id 0
            statement_ids = ['0']
            altstatement_ids = ['0']
            for x in result:
                rawid = x['id']
                idval = int(rawid / 10)
                idtype = int(rawid % 10)
                if idtype == 1:
                    statement_ids.append(str(idval))
                else:
                    altstatement_ids.append(str(idval))

            statement_ids_str = '(' + ','.join(statement_ids) + ')'
            altstatement_ids_str = '(' + ','.join(altstatement_ids) + ')'
            fullstatement = statement % (statement_ids_str,
                                            altstatement_ids_str)
            cursor.execute(fullstatement)
            records = cursor.fetchall()
            for record in records:
                record = tuple([f or '' for f in record])
                # Do not expose population column
                ret.append(jsonentry % record[:-1])
        finally:
            cursor.close()
            connection.close()
    return jsonify(ret)

@app.route("/", methods=["GET", "POST"])
def index_root():
    query = request.args.get("query", None)
    if query:
        return handle_query(query)
    else:
        return {}


if __name__ == "__main__":
    app.run()

from mod_python import util
from mod_python import apache
import sphinxapi
import psycopg2
statement = "SELECT geoname.name, admin1codes.name, countryInfo.name, \
geoname.longitude, geoname.latitude FROM admin1codes, geoname, countryInfo \
WHERE code = geoname.country||'.'||geoname.admin1 AND \
countryInfo.iso_alpha2=geoname.country AND geoname.geonameid=%s;"
altstatement = "SELECT alternatename.alternateName, admin1codes.name, countryInfo.name, \
geoname.longitude, geoname.latitude FROM alternatename, admin1codes, geoname, countryInfo \
WHERE code = geoname.country||'.'||geoname.admin1 AND \
countryInfo.iso_alpha2=geoname.country AND alternatename.geonameid=geoname.geonameid AND alternatename.alternatenameId=%s;"
authstring = 'dbname=geonames user=geouser password=geopw host=localhost'
jsonheader = '['
jsonfooter = ']'
jsonentry = '{"name" : "%s", "admin1" : "%s", "country" : "%s", ' \
            '"longitude" : "%F", "latitude" : "%F" }'

def handler(req):
    fs = util.FieldStorage(req)
    req.content_type = 'application/json'
    if fs.has_key('query'):
        client = sphinxapi.SphinxClient()
        client.SetServer('localhost', 3312)
        client.SetSortMode(sphinxapi.SPH_SORT_ATTR_DESC, 'population')
        result = client.Query(fs['query'])
        if result:
            result = result['matches']
        ret = []
        if result:
            connection = psycopg2.connect(authstring)
            cursor = connection.cursor()
            try:
                for x in result:
                    rawid = x['id']
                    idval = rawid / 10
                    idtype = rawid % 10
                    if idtype == 1:
                        cursor.execute(statement % idval)
                    else:
                        cursor.execute(altstatement % idval)
                    record = cursor.fetchone()
                    if record:
                        ret.append(jsonentry % record)
            finally:
                cursor.close()
                connection.close()
        req.write(jsonheader + ', '.join(ret) + jsonfooter)
    return apache.OK

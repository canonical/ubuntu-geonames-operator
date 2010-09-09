import sphinxapi
import cherrypy
import psycopg2
statement = "SELECT geoname.name, admin1codes.name, countryInfo.name, \
geoname.longitude, geoname.latitude FROM admin1codes, geoname, countryInfo \
WHERE code = geoname.country||'.'||geoname.admin1 AND \
countryInfo.iso_alpha2=geoname.country AND geoname.geonameid=%s;"
authstring = 'dbname=geonames user=geouser password=geopw host=localhost'
xmlheader = '<results>'
xmlfooter = '</results>'
xmlentry = '<result><name>%s</name><admin1>%s</admin1><country>%s</country><longitude>%F</longitude><latitude>%F</latitude></result>'
testheader = ''
testfooter = ''
testentry = '%s (%s, %s) <font size="-2">[%F, %F]</font><br />'
jsonheader = '['
jsonfooter = ']'
jsonentry = '{"name" : "%s", "admin1" : "%s", "country" : "%s", "longitude" : "%F", "latitude" : "%F" }'

class Geoname:
    def index(self, query=""):
        client = sphinxapi.SphinxClient()
        client.SetServer('localhost', 3312)
        result = client.Query(query)
        if result:
            result = result['matches']
        ret = []
        if result:
            connection = psycopg2.connect(authstring)
            cursor = connection.cursor()
            try:
                for x in result:
                    cursor.execute(statement % x['id'])
                    record = cursor.fetchone()
                    if record:
                        ret.append(jsonentry % record)
                        #ret += teststring % record
            finally:
                cursor.close()
                connection.close()
        return jsonheader + ', '.join(ret) + jsonfooter
    index.exposed = True

cherrypy.root = Geoname()

if __name__ == '__main__':
    settings = { 'global' : { 'server.environment' : 'production' } }
    cherrypy.config.update(settings)
    cherrypy.server.start()

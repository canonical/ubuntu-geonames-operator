#!/bin/bash
# If DB is local pass no arguments else
# ./import-geonames.sh -u user -h host -p port -d dbname
while getopts u:h:p:d: flag; do
    case $flag in
        u) PGUSER=$OPTARG;
           PGUSER_PARAM="--username $OPTARG";;
        h) PGHOST="--host $OPTARG";;
        p) PGPORT="--port $OPTARG";;
        d) PGDBNAME="--dbname $OPTARG";;
    esac
done
PGDBNAME=${PGDBNAME:="geonames"}
PGUSER=${PGUSER:="geouser"}

PSQL_CMD="psql $PGUSER_PARAM $PGPASS $PGHOST $PGPORT $PGDBNAME"
WORKPATH="$(mktemp -d)"
 
chmod 755 $WORKPATH
cd $WORKPATH
trap "rm -rf $WORKPATH" EXIT HUP INT QUIT TERM
pwd 
# allCountries.zip contains allCountries.txt
# alternateNames.zip contains iso-languagecodes.txt alternateNames.txt
ZIPFILES="allCountries.zip alternateNames.zip"
TXTFILES="admin1CodesASCII.txt countryInfo.txt timeZones.txt"
for i in $ZIPFILES $TXTFILES
do
	wget "http://download.geonames.org/export/dump/$i"
done
for i in $ZIPFILES
do
	unzip -o -qq $i
done
 
# alter files for import
tail -n +2 iso-languagecodes.txt > iso-languagecodes.txt.tmp
grep -v '^#' countryInfo.txt > countryInfo.txt.tmp
tail -n +2 timeZones.txt > timeZones.txt.tmp

LOAD_POSTFIX="_load" 
BACKUP_POSTFIX="_bkup" 
$PSQL_CMD <<EOT
BEGIN;
DROP TABLE IF EXISTS geoname${LOAD_POSTFIX};
CREATE TABLE geoname${LOAD_POSTFIX} (
	geonameid int,
	name varchar(200),
	asciiname varchar(200),
	alternatenames varchar(12000),
	latitude float,
	longitude float,
	fclass char(1),
	fcode varchar(10),
	country varchar(2),
	cc2 varchar(60),
	admin1 varchar(20),
	admin2 varchar(80),
	admin3 varchar(20),
	admin4 varchar(20),
	population bigint,
	elevation int,
	gtopo30 int,
	timezone varchar(40),
	moddate date
);
\copy geoname${LOAD_POSTFIX} (geonameid,name,asciiname,alternatenames,latitude,longitude,fclass,fcode,country,cc2, admin1,admin2,admin3,admin4,population,elevation,gtopo30,timezone,moddate) from $WORKPATH/allCountries.txt null as ''

DROP TABLE IF EXISTS alternatename${LOAD_POSTFIX};
CREATE TABLE alternatename${LOAD_POSTFIX} (
	alternatenameId int,
	geonameid int,
	isoLanguage varchar(7),
	alternateName varchar(400),
	isPreferredName boolean,
	isShortName boolean,
	isColloquial boolean,
	isHistoric boolean
);
\copy alternatename${LOAD_POSTFIX}  (alternatenameid,geonameid,isoLanguage,alternateName,isPreferredName,isShortName,isColloquial,isHistoric) from $WORKPATH/alternateNames.txt null as '';

DROP TABLE IF EXISTS countryinfo${LOAD_POSTFIX};
CREATE TABLE countryinfo${LOAD_POSTFIX} (
	iso_alpha2 char(2),
	iso_alpha3 char(3),
	iso_numeric integer,
	fips_code character varying(3),
	name character varying(200),
	capital character varying(200),
	areainsqkm double precision,
	population bigint,
	continent char(2),
	tld char(3),
	currency char(3),
	currencyName character varying(20),
	Phone char(20), 
	postalCodeFormat char(60), 
	postalCodeRegex char(200), 
	languages character varying(200), 
	geonameId int,
	neighbours char(50), 
	equivalentFipsCode char(10)
);
\copy countryInfo${LOAD_POSTFIX} (iso_alpha2,iso_alpha3,iso_numeric,fips_code,name,capital,areaInSqKm,population,continent,tld,currency,currencyName,Phone,postalCodeFormat,postalCodeRegex,languages,geonameId,neighbours,equivalentFipsCode) from $WORKPATH/countryInfo.txt.tmp null as ''

DROP TABLE IF EXISTS iso_languagecodes${LOAD_POSTFIX};
CREATE TABLE iso_languagecodes${LOAD_POSTFIX}(
	iso_639_3 CHAR(4),
	iso_639_2 VARCHAR(50),
	iso_639_1 VARCHAR(50),
	language_name VARCHAR(200)
);
\copy iso_languagecodes${LOAD_POSTFIX} (iso_639_3, iso_639_2, iso_639_1, language_name) from $WORKPATH/iso-languagecodes.txt.tmp null as ''

DROP TABLE IF EXISTS admin1codes${LOAD_POSTFIX};
CREATE TABLE admin1codes${LOAD_POSTFIX} (
	code varchar(10),
	name TEXT,
	nameAscii TEXT,
	geonameid int
);
\copy admin1codes${LOAD_POSTFIX} (code,name,nameAscii,geonameid) from $WORKPATH/admin1CodesASCII.txt null as ''

DROP TABLE IF EXISTS timeZones${LOAD_POSTFIX};
CREATE TABLE timeZones${LOAD_POSTFIX} (
	code CHAR(2),
	timeZoneId VARCHAR(200),
	GMT_offset numeric(3,1),
	DST_offset numeric(3,1),
	RAW_offset numeric(3,1)
);
\copy timeZones${LOAD_POSTFIX} (code,timeZoneId,GMT_offset,DST_offset,RAW_offset) from $WORKPATH/timeZones.txt.tmp null as ''

DROP TABLE IF EXISTS continentCodes${LOAD_POSTFIX};
CREATE TABLE continentCodes${LOAD_POSTFIX} (
	code CHAR(2),
	name VARCHAR(20),
	geonameid INT
);
INSERT INTO continentCodes${LOAD_POSTFIX} VALUES ('AF', 'Africa', 6255146);
INSERT INTO continentCodes${LOAD_POSTFIX} VALUES ('AS', 'Asia', 6255147);
INSERT INTO continentCodes${LOAD_POSTFIX} VALUES ('EU', 'Europe', 6255148);
INSERT INTO continentCodes${LOAD_POSTFIX} VALUES ('NA', 'North America', 6255149);
INSERT INTO continentCodes${LOAD_POSTFIX} VALUES ('OC', 'Oceania', 6255150);
INSERT INTO continentCodes${LOAD_POSTFIX} VALUES ('SA', 'South America', 6255151);
INSERT INTO continentCodes${LOAD_POSTFIX} VALUES ('AN', 'Antarctica', 6255152);
CREATE INDEX geoname_id_idx${LOAD_POSTFIX} ON geoname${LOAD_POSTFIX}(geonameid);
CREATE INDEX geoname_admin1codes_code_idx${LOAD_POSTFIX} ON admin1codes${LOAD_POSTFIX}(code);
CREATE INDEX geoname_countryinfo_isoalpha2_idx${LOAD_POSTFIX} ON countryinfo${LOAD_POSTFIX}(iso_alpha2);
CREATE INDEX geoname_alternatename_idx${LOAD_POSTFIX} ON alternatename${LOAD_POSTFIX}(alternatenameId);
ANALYZE geoname${LOAD_POSTFIX};
ANALYZE admin1codes${LOAD_POSTFIX};
ANALYZE countryinfo${LOAD_POSTFIX};
ANALYZE alternatename${LOAD_POSTFIX};
COMMIT;
EOT

# If the live tables exist, back them up and drop the indexes
#TABLES_PRESENT=$(psql $PGUSER_PARAM $PGPASS $PGHOST $PGPORT $PGDBNAME -A -q -t -c "select count(*) from pg_tables where tablename='geoname'")
TABLES_PRESENT=$($PSQL_CMD -A -q -t -c "select count(*) from pg_tables where tablename='geoname'")
if [[ $TABLES_PRESENT == 1 ]]; then
    echo "Backing up current tables"
    $PSQL_CMD <<EOT
BEGIN;
DROP TABLE IF EXISTS geoname${BACKUP_POSTFIX};
DROP TABLE IF EXISTS alternatename${BACKUP_POSTFIX};
DROP TABLE IF EXISTS countryinfo${BACKUP_POSTFIX};
DROP TABLE IF EXISTS iso_languagecodes${BACKUP_POSTFIX};
DROP TABLE IF EXISTS admin1codes${BACKUP_POSTFIX};
DROP TABLE IF EXISTS timeZones${BACKUP_POSTFIX};
DROP TABLE IF EXISTS continentCodes${BACKUP_POSTFIX};
DROP INDEX IF EXISTS geoname_id_idx;
DROP INDEX IF EXISTS geoname_admin1codes_code_idx;
DROP INDEX IF EXISTS geoname_countryinfo_isoalpha2_idx;
DROP INDEX IF EXISTS geoname_alternatename_idx;
ALTER TABLE geoname RENAME TO geoname${BACKUP_POSTFIX};
ALTER TABLE alternatename RENAME TO alternatename${BACKUP_POSTFIX};
ALTER TABLE countryinfo RENAME TO countryinfo${BACKUP_POSTFIX};
ALTER TABLE iso_languagecodes RENAME TO iso_languagecodes${BACKUP_POSTFIX};
ALTER TABLE admin1codes RENAME TO admin1codes${BACKUP_POSTFIX};
ALTER TABLE timeZones RENAME TO timeZones${BACKUP_POSTFIX};
ALTER TABLE continentCodes RENAME TO continentCodes${BACKUP_POSTFIX};
COMMIT;
EOT
fi

# Put the load tables live and rebuild the indexes
$PSQL_CMD <<EOT
BEGIN;
ALTER TABLE geoname${LOAD_POSTFIX} RENAME TO geoname;
ALTER TABLE alternatename${LOAD_POSTFIX} RENAME TO alternatename;
ALTER TABLE countryinfo${LOAD_POSTFIX} RENAME TO countryinfo;
ALTER TABLE iso_languagecodes${LOAD_POSTFIX} RENAME TO iso_languagecodes;
ALTER TABLE admin1codes${LOAD_POSTFIX} RENAME TO admin1codes;
ALTER TABLE timeZones${LOAD_POSTFIX} RENAME TO timeZones;
ALTER TABLE continentCodes${LOAD_POSTFIX} RENAME TO continentCodes;
ALTER INDEX geoname_id_idx${LOAD_POSTFIX} RENAME TO geoname_id_idx;
ALTER INDEX geoname_admin1codes_code_idx${LOAD_POSTFIX} RENAME TO geoname_admin1codes_code_idx;
ALTER INDEX geoname_countryinfo_isoalpha2_idx${LOAD_POSTFIX} RENAME TO geoname_countryinfo_isoalpha2_idx;
ALTER INDEX geoname_alternatename_idx${LOAD_POSTFIX} RENAME TO geoname_alternatename_idx;
GRANT ALL PRIVILEGES ON geoname, admin1codes, countryInfo, alternatename TO $PGUSER;
GRANT SELECT ON geoname, admin1codes, countryInfo, alternatename TO public;
COMMIT;
EOT

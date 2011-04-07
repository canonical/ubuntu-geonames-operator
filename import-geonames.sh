#!/bin/bash
 
WORKPATH="$(mktemp -d)"
 
chmod 755 $WORKPATH
cd $WORKPATH
trap "rm -rf $WORKPATH" EXIT HUP INT QUIT TERM
 
# allCountries.zip contains allCountries.txt
# alternateNames.zip contains iso-languagecodes.txt alternateNames.txt
ZIPFILES="allCountries.zip alternateNames.zip"
TXTFILES="admin1Codes.txt admin1CodesASCII.txt countryInfo.txt timeZones.txt"
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
 
sudo -u postgres psql geonames <<EOT
BEGIN;
DROP TABLE IF EXISTS geoname;
CREATE TABLE geoname (
	geonameid int,
	name varchar(200),
	asciiname varchar(200),
	alternatenames varchar(6000),
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
copy geoname (geonameid,name,asciiname,alternatenames,latitude,longitude,fclass,fcode,country,cc2, admin1,admin2,admin3,admin4,population,elevation,gtopo30,timezone,moddate) from '$WORKPATH/allCountries.txt' null as '';

DROP TABLE IF EXISTS alternatename;
CREATE TABLE alternatename (
	alternatenameId int,
	geonameid int,
	isoLanguage varchar(7),
	alternateName varchar(200),
	isPreferredName boolean,
	isShortName boolean
);
copy alternatename  (alternatenameid,geonameid,isoLanguage,alternateName,isPreferredName,isShortName) from '$WORKPATH/alternateNames.txt' null as '';

DROP TABLE IF EXISTS countryinfo;
CREATE TABLE countryinfo (
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
copy countryInfo (iso_alpha2,iso_alpha3,iso_numeric,fips_code,name,capital,areaInSqKm,population,continent,tld,currency,currencyName,Phone,postalCodeFormat,postalCodeRegex,languages,geonameId,neighbours,equivalentFipsCode) from '$WORKPATH/countryInfo.txt.tmp' null as '';

DROP TABLE IF EXISTS iso_languagecodes;
CREATE TABLE iso_languagecodes(
	iso_639_3 CHAR(4),
	iso_639_2 VARCHAR(50),
	iso_639_1 VARCHAR(50),
	language_name VARCHAR(200)
);
copy iso_languagecodes (iso_639_3, iso_639_2, iso_639_1, language_name) from '$WORKPATH/iso-languagecodes.txt.tmp' null as '';

DROP TABLE IF EXISTS admin1Codes;
CREATE TABLE admin1Codes (
	code varchar(10),
	name TEXT
);
copy admin1Codes (code, name) from '$WORKPATH/admin1Codes.txt' null as '';

DROP TABLE IF EXISTS admin1CodesAscii;
CREATE TABLE admin1CodesAscii (
	code varchar(10),
	name TEXT,
	nameAscii TEXT,
	geonameid int
);
copy admin1CodesAscii (code,name,nameAscii,geonameid) from '$WORKPATH/admin1CodesASCII.txt' null as '';

DROP TABLE IF EXISTS timeZones;
CREATE TABLE timeZones (
	timeZoneId VARCHAR(200),
	GMT_offset numeric(3,1),
	DST_offset numeric(3,1)
);
copy timeZones (timeZoneId,GMT_offset,DST_offset) from '$WORKPATH/timeZones.txt.tmp' null as '';

DROP TABLE IF EXISTS continentCodes;
CREATE TABLE continentCodes (
	code CHAR(2),
	name VARCHAR(20),
	geonameid INT
);
INSERT INTO continentCodes VALUES ('AF', 'Africa', 6255146);
INSERT INTO continentCodes VALUES ('AS', 'Asia', 6255147);
INSERT INTO continentCodes VALUES ('EU', 'Europe', 6255148);
INSERT INTO continentCodes VALUES ('NA', 'North America', 6255149);
INSERT INTO continentCodes VALUES ('OC', 'Oceania', 6255150);
INSERT INTO continentCodes VALUES ('SA', 'South America', 6255151);
INSERT INTO continentCodes VALUES ('AN', 'Antarctica', 6255152);

CREATE INDEX geoname_id_idx ON geoname(geonameid);
CREATE INDEX geoname_admin1codes_code_idx ON admin1codes(code);
CREATE INDEX geoname_countryinfo_isoalpha2_idx ON countryinfo(iso_alpha2);
CREATE INDEX geoname_alternatename_idx ON alternatename(alternatenameId);
GRANT ALL PRIVILEGES ON geoname, admin1codes, countryInfo, alternatename TO geouser;
COMMIT;
EOT

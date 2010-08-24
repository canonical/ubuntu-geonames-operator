#!/bin/bash
 
 WORKPATH="/tmp/geodata"
 
 cd $WORKPATH
 
 # download all needed files and if needed unzip them
 ZIPFILES="allCountries.zip alternateNames.zip userTags.zip"
 TXTFILES="admin1Codes.txt admin1CodesASCII.txt admin2Codes.txt countryInfo.txt featureCodes.txt iso-languagecodes.txt timeZones.txt"
# for i in $ZIPFILES $TXTFILES
# do
# 	wget "http://download.geonames.org/export/dump/$i"
# 	echo "Done download $i"
# done
# for i in $ZIPFILES
# do
# 	unzip -o -qq $i
# done
# 
# # rename files because of name conflict
# mv allCountries.zip allGeoCountries.zip
# mv allCountries.txt allGeoCountries.txt
 
 # download the postalcodes. You must know yourself the url
 #wget <a href="http://xxx" target="_blank" rel="nofollow">http://xxx</a>
 #echo "Done download postal codes (xxx)"
 #unzip -o -qq xxx
 
 # rename files because of name conflict
 #mv xxx xxx
 #mv xxx xxx
 
 # alter files for import
 tail -n +2 iso-languagecodes.txt > iso-languagecodes.txt.tmp
 grep -v '^#' countryInfo.txt | tail -n +2 > countryInfo.txt.tmp
 tail -n +2 timeZones.txt > timeZones.txt.tmp
 
sudo -u postgres psql geonames <<EOT
DROP TABLE geoname;
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
copy geoname (geonameid,name,asciiname,alternatenames,latitude,longitude,fclass,fcode,country,cc2, admin1,admin2,admin3,admin4,population,elevation,gtopo30,timezone,moddate) from '${WORKPATH}/allGeoCountries.txt' null as '';

DROP TABLE alternatename;
CREATE TABLE alternatename (
	alternatenameId int,
	geonameid int,
	isoLanguage varchar(7),
	alternateName varchar(200),
	isPreferredName boolean,
	isShortName boolean
);
copy alternatename  (alternatenameid,geonameid,isoLanguage,alternateName,isPreferredName,isShortName) from '${WORKPATH}/alternateNames.txt' null as '';

DROP TABLE countryinfo;
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
copy countryInfo (iso_alpha2,iso_alpha3,iso_numeric,fips_code,name,capital,areaInSqKm,population,continent,tld,currency,currencyName,Phone,postalCodeFormat,postalCodeRegex,languages,geonameId,neighbours,equivalentFipsCode) from '${WORKPATH}/countryInfo.txt.tmp' null as '';

DROP TABLE iso_languagecodes;
CREATE TABLE iso_languagecodes(
	iso_639_3 CHAR(4),
	iso_639_2 VARCHAR(50),
	iso_639_1 VARCHAR(50),
	language_name VARCHAR(200)
);
copy iso_languagecodes (iso_639_3, iso_639_2, iso_639_1, language_name) from '${WORKPATH}/iso-languagecodes.txt.tmp' null as '';

DROP TABLE admin1Codes;
CREATE TABLE admin1Codes (
	code varchar(10),
	name TEXT
);
copy admin1Codes (code, name) from '${WORKPATH}/admin1Codes.txt' null as '';

DROP TABLE admin1CodesAscii;
CREATE TABLE admin1CodesAscii (
	code varchar(10),
	name TEXT,
	nameAscii TEXT,
	geonameid int
);
copy admin1CodesAscii (code,name,nameAscii,geonameid) from '${WORKPATH}/admin1CodesASCII.txt' null as '';

DROP TABLE featureCodes;
CREATE TABLE featureCodes (
	code CHAR(7),
	name VARCHAR(200),
	description TEXT
);
copy featureCodes (code,name,description) from '${WORKPATH}/featureCodes.txt' null as '';

DROP TABLE timeZones;
CREATE TABLE timeZones (
	timeZoneId VARCHAR(200),
	GMT_offset numeric(3,1),
	DST_offset numeric(3,1)
);
copy timeZones (timeZoneId,GMT_offset,DST_offset) from '${WORKPATH}/timeZones.txt.tmp' null as '';

DROP TABLE continentCodes;
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


DROP TABLE postalcodes;
CREATE TABLE postalcodes (
	countrycode char(2),
	postalcode varchar(10),
	placename varchar(180),
	admin1name varchar(100),
	admin1code varchar(20),
	admin2name varchar(100),
	admin2code varchar(20),
	admin3name varchar(100),
	latitude float,
	longitude float,
	accuracy smallint
);
copy postalcodes (countrycode,postalcode,placename,admin1name,admin1code,admin2name,admin2code,admin3name,latitude,longitude,accuracy) from '${WORKPATH}/allTZCountries.txt' null as '';
EOT

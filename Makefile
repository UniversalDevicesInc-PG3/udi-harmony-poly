
#
# The config file.
#
CONFIG_FILE = config.yaml

# Zip file for the ISY
ZIP_FILE  = profile_default.zip
# Source files put in the default profile zip.
ZIP_FILES = profile/version.txt profile/nls/*.txt profile/editor/editors.xml profile/nodedef/nodedefs.xml

all: ${ZIP_FILE}
config: ${CONFIG_FILE}
profile: ${ZIP_FILE}

profile_default:
	rm -f ${ZIP_FILE}
	${MAKE} profile

#
# Run xmlint on all xml files
#
# sudo apt-get install libxml2-utils libxml2-dev
check:
	xmllint --noout ${XML_FiLES}

#
# Generate the zip file of profile
#
${ZIP_FILE}: ${ZIP_FILES}
	echo '0.0.0.0' > profile/version.txt
	cp -f profile/nls/en_us.tmpl profile/nls/en_us.txt
	cd profile ; f=`echo $? | sed -e 's/profile\///g'` ; zip -r ../$@ $$f

profile/version.txt:
	echo '0.0.0.0' > profile/version.txt

.PHONY: ${CONFIG_FILE}
${CONFIG_FILE}:
	./write_profile.py

profile/nls/*.txt: profile/nls/*.tmpl

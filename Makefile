
#
# The config file.
#
CONFIG_FILE = config.yaml

# Zip file for the ISY
ZIP_FILE  = profile.zip
# Source files put in the zip.
XML_FiLES = profile/editor/*.xml profile/nodedef/*.xml 
ZIP_FILES = profile/version.txt profile/nls/*.txt ${XML_FiLES}

all: ${ZIP_FILE}
config: ${CONFIG_FILE}
profile: ${ZIP_FILE}

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
	cd profile ; f=`echo $? | sed -e 's/profile\///g'` ; zip -r ../$@ $$f

.PHONY: ${CONFIG_FILE}
${CONFIG_FILE}:
	./write_profile.py

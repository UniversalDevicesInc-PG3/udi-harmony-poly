

import sys
sys.path.insert(0,"pyharmony")
from pyharmony import ha_get_client
import os,socket,struct,hashlib,re,json,logging,yaml

CONFIG_DIR = "config"

logging.getLogger('sleekxmpp').setLevel(logging.INFO)
logging.getLogger('requests').setLevel(logging.INFO)
logging.getLogger('urllib3').setLevel(logging.INFO)
logging.getLogger('pyharmony').setLevel(logging.INFO)

# Geth file in config dir, move if it currently exists.
def get_file(logger,fname):
    fpath = CONFIG_DIR + "/" + fname
    if not os.path.exists(CONFIG_DIR):
        try:
            os.mkdir(CONFIG_DIR)
        except (Exception) as err:
            logger.error("Unable to mkdir {}: {}".format(CONFIG_DIR,err))
    if os.path.exists(fname):
        logger.debug("Moving {} -> {}".format(fname,fpath))
        try:
            os.rename(fname,fpath)
        except (Exception) as err:
            logger.error("Unable to rename {} -> {}: {}".format(fname,fpath,err))
    logger.debug('get_file: {} = {}'.format(fname,fpath))
    return fpath

def myint(value):
    """ round and convert to int """
    return int(round(float(value)))

def myfloat(value, prec=4):
    """ round and return float """
    return round(float(value), prec)

def ip2long(ip):
    """ Convert an IP string to long """
    packedIP = socket.inet_aton(ip)
    return struct.unpack("!L", packedIP)[0]

def long2ip(value):
    return socket.inet_ntoa(struct.pack('!L', value))


# isBit() returns True or False if bit at offset is set or not
def isBit(int_type, offset):
    mask = 1 << offset
    if (int_type & mask) == 0:
        return False
    return True

# isBit() returns 1 or 0 if bit at offset is set or not
def isBitI(int_type, offset):
    mask = 1 << offset
    if (int_type & mask) == 0:
        return 0
    return 1

# testBit() returns a nonzero result, 2**offset, if the bit at 'offset' is one.
def testBit(int_type, offset):
    mask = 1 << offset
    return(int_type & mask)

# setBit() returns an integer with the bit at 'offset' set to 1.
def setBit(int_type, offset):
    mask = 1 << offset
    return(int_type | mask)

# clearBit() returns an integer with the bit at 'offset' cleared.
def clearBit(int_type, offset):
    mask = ~(1 << offset)
    return(int_type & mask)

# toggleBit() returns an integer with the bit at 'offset' inverted, 0 -> 1 and 1 -> 0.
def toggleBit(int_type, offset):
    mask = 1 << offset
    return(int_type ^ mask)

def harmony_hub_client(host, port=5222):
    client = ha_get_client(host, port)
    return client

def uuid_to_address(uuid):
    return uuid[-12:]

def id_to_address(address,slen=14):
    slen = slen * -1
    m = hashlib.md5()
    m.update(address.encode())
    return m.hexdigest()[slen:]

# Removes invalid charaters for ISY Node description
def get_valid_node_name(name):
    # Only allow utf-8 characters
    #  https://stackoverflow.com/questions/26541968/delete-every-non-utf-8-symbols-froms-string
    name = bytes(name, 'utf-8').decode('utf-8','ignore')
    # Remove <>`~!@#$%^&*(){}[]?/\;:"'` characters from name
    return re.sub(r"[<>`~!@#$%^&*(){}[\]?/\\;:\"']+", "", name)

#
# Routines are here because they are used in write_profile.py
#
CONFIG_FILE = "config.yaml"

def write_config_file(logger,config_data):
    fpath = get_file(logger,CONFIG_FILE)
    try:
        with open(fpath, 'w') as outfile:
            yaml.dump(config_data, outfile, default_flow_style=False)
            outfile.close()
    except (Exception) as err:
        logger.error('harmony_hub_funcs:write_config_file: failed to write {0}: {1}'.format(fpath,err))
        return False
    return True

def load_config_file(logger):
    config = get_file(logger,CONFIG_FILE)
    if os.path.exists(config):
        logger.info('load_config: Loading Harmony config {}'.format(config))
        try:
            config_h = open(config, 'r')
        except:
            logger.error('load_config: failed to open cfg={0}'.format(config),exc_info=True)
            return False
        harmony_config = False
        try:
            harmony_config = yaml.load(config_h, Loader=yaml.SafeLoader)
        except:
            logger.error('load_config: failed to parse cfg={0}'.format(config),exc_info=True)
            return False
        finally:
            # This is always executed.
            config_h.close()
        return harmony_config
    else:
        logger.error('load_config: Harmony config does not exist {}'.format(config))

#
# We need a hubs file because write_profile is run  on install
#
HUBS_FILE = 'hubs.json'

def load_hubs_file(logger):
    fpath = get_file(logger,HUBS_FILE)
    try:
        with open(fpath) as data:
            hubs = json.load(data)
            data.close()
    except (Exception) as err:
        logger.error('harmony_hub_funcs:load_hubs_file: failed to read hubs file {0}: {1}'.format(fpath,err))
        return False
    else:
        return hubs

def save_hubs_file(logger,hubs):
    fpath = get_file(logger,HUBS_FILE)
    try:
        with open(fpath, 'w') as outfile:
            json.dump(hubs, outfile, sort_keys=True, indent=4)
    except (Exception) as err:
        logger.error('harmony_hub_funcs:save_hubs_file: failed to write {0}: {1}'.format(fpath,err))
        return False
    else:
        outfile.close()
    return True

def get_server_data(logger):
    # Read the SERVER info from the json.
    try:
        with open('server.json') as data:
            serverdata = json.load(data)
    except Exception as err:
        logger.error('harmony_hub_funcs:get_server_data: failed to read hubs file {0}: {1}'.format('server.json',err), exc_info=True)
        return False
    data.close()
    # Get the version info
    try:
        version = serverdata['credits'][0]['version']
    except (KeyError, ValueError):
        logger.info('Version not found in server.json.')
        version = '0.0.0.0'
    # Split version into two floats.
    sv = version.split(".");
    v1 = 0;
    v2 = 0;
    if len(sv) == 1:
        v1 = int(v1[0])
    elif len(sv) > 1:
        v1 = float("%s.%s" % (sv[0],str(sv[1])))
        if len(sv) == 3:
            v2 = int(sv[2])
        else:
            v2 = float("%s.%s" % (sv[2],str(sv[3])))
    serverdata['version'] = version
    serverdata['version_major'] = v1
    serverdata['version_minor'] = v2
    return serverdata

#!/usr/bin/env python3

import yaml,collections,re,os,zipfile
from harmony_hub_funcs import harmony_hub_client,get_server_data,load_hubs_file,get_file,CONFIG_FILE,load_config_file,write_config_file,get_file

pfx = "write_profile:"

VERSION_FILE = "profile/version.txt"


# TODO: Check that server node & name are defined.
#if 'server' in config and config['host'] is not None:
#    # use what the user has defined.
#    this_host = config['host']

NODEDEF_TMPL_HUB = """
  <nodeDef id="%s" nodeType="139" nls="%s">
    <sts>
      <st id="ST" editor="BOOL" />
      <st id="GV3" editor="%s" />
    </sts>
    <cmds>
      <sends>
    <cmd id="DON" />
    <cmd id="DOF" />
      </sends>
      <accepts>
        <cmd id="SET_ACTIVITY">
          <p id="" editor="%s" init="%s"/>
        </cmd>
        <cmd id="CHANGE_CHANNEL">
          <p id="" editor="CHANNEL"/>
        </cmd>
        <cmd id="QUERY" />
        <cmd id="DOF" />
        <cmd id="DFOF" />
        <cmd id="DEL" />
      </accepts>
    </cmds>
  </nodeDef>
"""
NODEDEF_TMPL_ACTIVITY = """
  <nodeDef id="%s" nodeType="139" nls="%s">
    <sts>
      <st id="ST" editor="BOOL" />
      <st id="GV3" editor="%s" />
    </sts>
    <cmds>
      <sends>
    <cmd id="DON" />
    <cmd id="DOF" />
      </sends>
      <accepts>
        <cmd id="SET_ACTIVITY">
          <p id="" editor="%s" init="%s"/>
        </cmd>
        <cmd id="CHANGE_CHANNEL">
          <p id="" editor="CHANNEL"/>
        </cmd>
        <cmd id="QUERY" />
        <cmd id="DOF" />
        <cmd id="DFOF" />
      </accepts>
    </cmds>
  </nodeDef>
"""
NODEDEF_TMPL_DEVICE = """
  <nodeDef id="%s" nodeType="139" nls="%s">
    <sts />
    <cmds>
      <sends />
      <accepts>
        <cmd id="SET_BUTTON">
          <p id="" editor="%s"/>
        </cmd>
        <cmd id="DON" />
        <cmd id="DOF" />
      </accepts>
    </cmds>
  </nodeDef>
"""
EDITOR_TMPL_S = """
  <editor id="%s">
    <range uom="25" subset="%s" nls="%s"/>
  </editor>
"""
EDITOR_TMPL_MM = """
  <editor id="%s">
    <range uom="25" min="%d" max="%d" nls="%s"/>
  </editor>
"""
# The NLS entries for the node definition
NLS_NODE_TMPL = """
ND-%s-NAME = %s
ND-%s-ICON = Input
"""
# The NLS entry for each indexed item
NLS_TMPL = "%s-%d = %s\n"

#
# Turn the list of button numbers, into a compacted subset string for the editor.
#
def reduce_subset(subset):
    subset_str = ""
    subset.sort()
    full_string = ",".join(map(str,subset))
    while len(subset) > 0:
        x = subset.pop(0)
        if subset_str != "":
            subset_str += ","
        subset_str += str(x)
        if len(subset) > 0 and x == subset[0] - 1:
            y = subset.pop(0)
            while len(subset) > 0 and (y == subset[0] or y == subset[0] - 1):
                y = subset.pop(0)
            subset_str += "-" + str(y)
    return { 'full_string': full_string, 'subset_string': subset_str }

def write_profile(logger,hub_list,poll_hubs=True):
    config_data = {}
    sd = get_server_data(logger)
    if sd is False:
        logger.error("Unable to complete without server data...")
        return False
    #
    # Initialize or Load config data
    #
    config_data = False
    config_file = get_file(logger,CONFIG_FILE)
    if os.path.exists(config_file):
        logger.info('Loading config: %s', CONFIG_FILE)
        config_data = load_config_file(logger)
        if config_data is False:
            logger.error("FAiLED to load config file, will have to regenrate...")
    if config_data is False:
        logger.info('Initializing config data')
        config_data = dict()
        config_data['info'] = dict()
        config_data['info']['activities'] = list()
        config_data['info']['functions'] = list()
    # This was added in 2.4.0
    # And we don't save from previous runs because we don't care
    # about index order
    config_data['info']['devices'] = list()
    # References to internal data structures
    activities = config_data['info']['activities']
    devices    = config_data['info']['devices']
    functions  = config_data['info']['functions']
    # Activity 0 is always power off
    if len(activities) == 0:
        logger.info("Initializing Activities List...")
        activities.append({'label':'Power Off','id':-1});
    # Set all counts back to zero
    for name in ['functions', 'devices', 'activities']:
        for item in config_data['info'][name]:
            item['cnt'] = 0
    #
    # Start the nls with the template data.
    #
    en_us_txt = "profile/nls/en_us.txt"
    logger.info("{0} Writing {1}".format(pfx,en_us_txt))
    nls_tmpl = open("profile/nls/en_us.tmpl", "r")
    nls      = open(en_us_txt,  "w")
    for line in nls_tmpl:
        nls.write(re.sub(r'^(ND-HarmonyController-NAME = Harmony Hub Controller).*',r'\1 {0}'.format(sd['version']),line))
    nls_tmpl.close()

    logger.info("{0} Writing profile/nodedef/custom.xml and profile/editor/custom.xml".format(pfx))
    nodedef = open("profile/nodedef/custom.xml", "w")
    editor  = open("profile/editor/custom.xml", "w")
    nodedef.write("<nodeDefs>\n")
    editor.write("<editors>\n")

    #
    # Loop over each Hub in the config data.
    #
    first_hub = True
    if len(hub_list) == 0:
        logger.error("{0} Hub list is empty?".format(pfx))
    for ahub in hub_list:
        #
        # Process this hub.
        #
        address  = ahub['address']
        host = ahub['host']
        name = ahub['name']
        info = "Hub: %s '%s'" % (address,name)
        nodedef.write("\n  <!-- === %s -->\n" % (info))
        nodedef.write(NODEDEF_TMPL_HUB % (address, 'HARMONYHUB', 'Act' + address, 'Act' + address, 'GV3'))
        nls.write("\n# %s" % (info))
        nls.write(NLS_NODE_TMPL % (address, name, address))
        #
        # Build or load the config file.
        #
        harmony_config_file = get_file(logger,address + ".yaml")
        #
        # Building a new config
        #
        if not poll_hubs:
            logger.debug('{} Loading hub config: {}'.format(pfx,harmony_config_file))
            try:
                with open(harmony_config_file, 'r') as infile:
                    harmony_config = yaml.load(infile,Loader=yaml.FullLoader)
            except:
                logger.error("{} Error loading config {} will poll hub".format(pfx,harmony_config_file),True)
                poll_hubs = True
        if poll_hubs:
            # Connect to the hub and get the configuration
            logger.info("{0} Initializing Client for {1} {2} {3}".format(pfx,address,name,host))
            client = harmony_hub_client(host=host)
            logger.info(pfx + " Client: " + str(client))
            if client is False:
                logger.error("{0} Error connecting to client {1} {2} {3}".format(pfx,address,name,host))
                continue
            harmony_config = client.get_config()
            client.disconnect(send_close=True)
            #
            # Save the config for reference.
            with open(harmony_config_file, 'w') as outfile:
                yaml.safe_dump(harmony_config, outfile, default_flow_style=False)
        #
        # Build the activities
        #
        # PowerOff is always first
        nls.write("# The index number is the matching list info->activities index\n")
        nls.write("# The activity id's are uniq across all hubs so we share the same list\n")
        subset = list()
        if first_hub:
            nls.write(NLS_TMPL % (address.upper(), 0, activities[0]['label']))
        subset.append(0)
        for a in harmony_config['activity']:
            # Skip -1 since we printed it already.
            if int(a['id']) != -1:
                # Print the Harmony Activities to the log
                logger.debug("%s Activity: %s  Id: %s" % (pfx, a['label'], a['id']))
                aname = str(a['label'])
                id = int(a['id'])
                index = next((index for (index, d) in enumerate(activities) if d['id'] == id), None)
                if index is None:
                    index = len(activities)
                    logger.debug('  Adding as new activity %d', index)
                    activities.append({'label':aname,'id':int(a['id']),'cnt':1});
                else:
                    logger.debug('  Using existing activity %s index=%d',activities[index],index)
                    activities[index]['cnt'] += 1
                nls.write(NLS_TMPL % (address.upper(), index, aname))
                # This is the list of button numbers in this device.
                subset.append(index)
        s = reduce_subset(subset)
        editor.write(EDITOR_TMPL_S % ('Act'+address, s['subset_string'],address.upper()))
        #
        # Build all the devices
        #
        for d in harmony_config['device']:
            info = "Device '%s', Type=%s, Manufacturer=%s, Model=%s" % (d['label'],d['type'],d['manufacturer'],d['model'])
            subset = []
            nodedef.write("\n  <!-- === %s -->" % info)
            nodedef.write(NODEDEF_TMPL_DEVICE % ('d' + d['id'], 'D' + d['id'], 'Btn' + d['id']))
            nls.write("\n# %s" % info)
            nls.write(NLS_NODE_TMPL % ('d' + d['id'], d['label'], 'd' + d['id']))
            logger.debug("%s   Device: %s  Id: %s" % (pfx, d['label'], d['id']))
            logger.debug("%s",devices)
            devices.append({'label':d['label'],'id':int(d['id']),'cnt': 1});
            #
            # Build all the button functions, these are global to all devices
            #
            for cg in d['controlGroup']:
                for f in cg['function']:
                    a = f['action'].replace('\\/','/')
                    try:
                        ay = yaml.load(a,Loader=yaml.FullLoader)
                    except (Exception) as err:
                        logger.error('{0} failed to parse string: {1}'.format(pfx,err))
                    else:
                        fname = f['name']
                        index = next((index for (index, d) in enumerate(functions) if d['name'] == fname), None)
                        if index is None:
                            index = len(functions)
                            logger.debug('  Adding as new function %d', index)
                            functions.append({'label':str(f['label']),'name':fname,'command':{str(d['id']):str(ay['command'])},cnt: 1});
                        else:
                            logger.debug('  Using existing function %s index=%d',functions[index],index)
                            functions[index]['cnt'] += 1
                        functions[index]['command'][str(d['id'])] = ay['command']
                        logger.debug("%s     Function: Index: %d, Name: %s,  Label: %s, Command: %s" % (pfx, index, f['name'], f['label'], ay['command']))
                        #nls.write("# Button name: %s, label: %s\n" % (f['name'], f['label']))
                        # This is the list of button numbers in this device.
                        if not index in subset:
                            subset.append(index)
            s = reduce_subset(subset)
            editor.write("\n  <!-- === %s -->\n" % info)
            editor.write("  <!-- full subset = %s -->" % s['full_string'])
            editor.write(EDITOR_TMPL_S % ('Btn' + d['id'], s['subset_string'], 'BTN'))


    nls.write("\n\n")
    for (index, d) in enumerate(functions):
        nls.write(NLS_TMPL % ('BTN', index, d['name']))

    editor.write("</editors>")
    nodedef.write("</nodeDefs>")

    nodedef.close()
    editor.close()
    nls.close()

    # Don't need zip file anymore
    if os.path.exists('profile.zip'):
        os.remove('profile.zip')

    write_config_file(logger,config_data)

    with open(VERSION_FILE, 'w') as outfile:
        outfile.write(sd['profile_version'])
    outfile.close()

    logger.info(pfx + " done.")

    return(config_data)


def write_profile_zip(logger):
    src = 'profile'
    abs_src = os.path.abspath(src)
    with zipfile.ZipFile('profile.zip', 'w') as zf:
        for dirname, subdirs, files in os.walk(src):
            # Ignore dirs starint with a dot, stupid .AppleDouble...
            if not "/." in dirname:
                for filename in files:
                    if filename.endswith('.xml') or filename.endswith('txt'):
                        absname = os.path.abspath(os.path.join(dirname, filename))
                        arcname = absname[len(abs_src) + 1:]
                        logger.info('write_profile_zip: %s as %s' % (os.path.join(dirname, filename),
                                                                     arcname))
                        zf.write(absname, arcname)
    zf.close()


if __name__ == "__main__":
    import logging,json
    logger = logging.getLogger(__name__)
    logging.basicConfig(
        level=10,
        format='%(levelname)s:\t%(name)s\t%(message)s'
    )
    logger.setLevel(logging.DEBUG)
    # Only write the profile if the version is updated.
    sd = get_server_data(logger)
    if sd is not False:
        local_version = None
        try:
            with open(VERSION_FILE,'r') as vfile:
                local_version = vfile.readline()
                local_version = local_version.rstrip()
                vfile.close()
        except (FileNotFoundError):
            pass
        except (Exception) as err:
            logger.error('{0} failed to read local version from {1}: {2}'.format(pfx,VERSION_FILE,err), exc_info=True)
        if local_version == sd['profile_version']:
            logger.info('{0} Not Generating new profile since local version {1} is the same current {2}'.format(pfx,local_version,sd['profile_version']))
        else:
            logger.info('{0} Generating new profile since local version {1} is not current {2}'.format(pfx,local_version,sd['profile_version']))
            hubs = load_hubs_file(logger)
            if hubs is False:
                logger.error('{0} Unable to load hubs file which does not exist on first run or before 2.1.0, please run Build Profile in admin console after restarting this nodeserver'.format(pfx))
            else:
                write_profile(logger,hubs)

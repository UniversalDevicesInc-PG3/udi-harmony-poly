#!/usr/bin/python

import yaml,collections,re,os,zipfile
from harmony_hub_funcs import harmony_hub_client

pfx = "write_profile:"

config_file_name = 'config.yaml'

#config_file = open(config_file_name, 'r')
#config_data = yaml.load(config_file)
#config_file.close

# TODO: Check that server node & name are defined.
#if 'server' in config and config['host'] is not None:
#    # use what the user has defined.
#    this_host = config['host']

NODEDEF_TMPL_ACTIVITY = """
  <nodeDef id="%s" nodeType="139" nls="%s">
    <sts>
      <st id="ST" editor="HUBST" />
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

def write_profile(logger,hub_list):
    config_data = {}
    #
    # Start the nls with the template data.
    #
    nls_tmpl = open("profile/nls/en_us.tmpl", "r")
    nls      = open("profile/nls/en_us.txt",  "w")
    for line in nls_tmpl:
        nls.write(line)
    nls_tmpl.close()

    nodedef = open("profile/nodedef/custom.xml", "w")
    editor  = open("profile/editor/custom.xml", "w")
    nodedef.write("<nodeDefs>\n")
    editor.write("<editors>\n")

    #
    # This is all the activities available for all hubs.
    #
    activites = collections.OrderedDict()
    ai = 0
    #
    # This is all the button functions available for all devices.
    #
    buttons = collections.OrderedDict()
    bi = 0
    #
    # Loop over each Hub in the config data.
    #
    config_data['info'] = dict()
    config_data['info']['activities'] = list()
    config_data['info']['functions'] = list()
    warn_string_1 = ""
    for ahub in hub_list:
        #
        # Process this hub.
        #
        address  = ahub['address']
        host = ahub['host']
        name = ahub['name']
        info = "Hub: %s '%s'" % (address,name)
        nodedef.write("\n  <!-- === %s -->\n" % (info))
        nodedef.write(NODEDEF_TMPL_ACTIVITY % (address, 'HARMONYHUB', 'Act' + address, 'Act' + address, 'GV3'))
        nls.write("\n# %s" % (info))
        nls.write(NLS_NODE_TMPL % (address, name, address))
        #
        # Connect to the hub and get the configuration
        logger.info("{0} Initializing Client for {1} {2} {3}".format(pfx,address,name,host))
        client = harmony_hub_client(host=host)
        logger.info(pfx + " Client: " + str(client))
        harmony_config = client.get_config()
        client.disconnect(send_close=True)
        #
        # Save the config for reference.
        harmony_config_file = address + ".yaml"
        with open(harmony_config_file, 'w') as outfile:
            yaml.safe_dump(harmony_config, outfile, default_flow_style=False)
        #
        # Build the activities
        #
        # PowerOff is always first
        ais = ai
        nls.write("# The index number is the matching list info->activities index\n")
        nls.write("# The activity id's are uniq across all hubs so we share the same list\n")
        nls.write(NLS_TMPL % (address.upper(), 0, 'Power Off'))
        if ais == 0:
            config_data['info']['activities'].append({'label':'Power Off','id':-1});
            ai += 1
        for a in harmony_config['activity']:
            # Skip -1 since we printed it already.
            if int(a['id']) != -1:
                # Print the Harmony Activities to the log
                logger.debug("%s Activity: %s  Id: %s" % (pfx, a['label'], a['id']))
                #aname = "%s (%s)" % (a['label'],a['id'])
                aname = str(a['label'])
                config_data['info']['activities'].append({'label':aname,'id':int(a['id'])});
                nls.write(NLS_TMPL % (address.upper(), ai, aname))
                ai += 1
        # All activities contain zero which is power off...
        if ais == 0:
            subset = "%d-%d" % (ais, ai-1)
        else:
            subset = "0,%d-%d" % (ais, ai-1)
        editor.write(EDITOR_TMPL_S % ('Act'+address, subset,address.upper()))
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
            #
            # Build all the button functions, these are global to all devices
            #
            for cg in d['controlGroup']:
                for f in cg['function']:
                    a = f['action']
                    ay = yaml.load(a.replace('\\',''))
                    bname = f['name']
                    if not bname in buttons:
                        cb = bi
                        buttons[bname] = bi
                        bi += 1
                        config_data['info']['functions'].append({'label':str(f['label']),'name':str(f['name']),'command':{str(d['id']):str(ay['command'])}});
                    else:
                        cb = buttons[bname]
                        config_data['info']['functions'][cb]['command'][str(d['id'])] = ay['command']
                    logger.debug("%s     Function: Index: %d, Name: %s,  Label: %s, Command: %s" % (pfx, cb, f['name'], f['label'], ay['command']))

                    if bname != f['name']:
                        warn_string_1 += " device %s has button with label=%s, command=%s\n" % (d['label'],f['label'],ay['command'])
                    #nls.write("# Button name: %s, label: %s\n" % (f['name'], f['label']))
                    # This is the list of button numbers in this device.
                    subset.append(cb)
            #
            # Turn the list of button numbers, into a compacted subset string for the editor.
            #
            subset_str = ""
            subset.sort()
            editor.write("\n  <!-- === %s -->\n" % info)
            editor.write("  <!-- full subset = %s -->" % ",".join(map(str,subset)))
            while len(subset) > 0:
                x = subset.pop(0)
                if subset_str != "":
                    subset_str += ","
                subset_str += str(x)
                if len(subset) > 0 and x == subset[0] - 1:
                    y = subset.pop(0)
                    while len(subset) > 0 and y == subset[0] - 1:
                        y = subset.pop(0)
                    subset_str += "-" + str(y)
            editor.write(EDITOR_TMPL_S % ('Btn' + d['id'], subset_str, 'BTN'))

    
    nls.write("\n\n")
    for key in buttons:
        nls.write(NLS_TMPL % ('BTN', buttons[key], key))
    
    editor.write("</editors>")
    nodedef.write("</nodeDefs>")
            
    nodedef.close()
    editor.close()
    nls.close()

    with open(config_file_name, 'w') as outfile:
        yaml.dump(config_data, outfile, default_flow_style=False)
    
        logger.info(pfx + " done.")

    write_profile_zip(logger)
    
    return(config_data)

#if warn_string_1 != "":
#    print "WARNING: If you are upgrading from 0.3.x and using any of the following in an ISY program, you will need to fix them"
#    print warn_string_1


def write_profile_zip(logger):
    src = 'profile'
    abs_src = os.path.abspath(src)
    with zipfile.ZipFile('profile.zip', 'w') as zf:
        for dirname, subdirs, files in os.walk(src):
            for filename in files:
                if filename.endswith('.xml') or filename.endswith('txt'):
                    absname = os.path.abspath(os.path.join(dirname, filename))
                    arcname = absname[len(abs_src) + 1:]
                    logger.info('write_profile_zip: %s as %s' % (os.path.join(dirname, filename),
                                                arcname))
                    zf.write(absname, arcname)
    zf.close()
    
if __name__ == "__main__":
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(
        level=10,
        format='%(levelname)s:\t%(name)s\t%(message)s'
    )
    logger.setLevel(logging.DEBUG)
    write_profile(logger,
        [
            { "address": "familyroom", "name": "HarmonyHub FamilyRoom", "host": "192.168.86.82" },
            { "address": "masterbedroom", "name": "HarmonyHub MasterBedroom", "host": "192.168.86.80" },
        ]
    )



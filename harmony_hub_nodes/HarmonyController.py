#
# HarmonyController
#
# TODO:
#
# This is the main Harmony Hub Node Controller
# Add a Configuration Parameter:
# Key=hub_FamilyRoom
# Value={ "name": "HarmonyHub FamilyRoom", "host": "192.168.86.82" }
# Key=hub_MasterBedroom
# Value={ "name": "HarmonyHub MasterBedroom", "host": "192.168.86.80" }
#

import sys
sys.path.insert(0,"pyharmony")
from polyinterface import Controller,LOG_HANDLER,LOGGER
import json,re,time,sys,os.path,yaml,logging,json,warnings,time
from traceback import format_exception
from copy import deepcopy
from threading import Thread
from harmony_hub_nodes import HarmonyHub
from harmony_hub_funcs import *
from write_profile import write_profile

class HarmonyController(Controller):
    """
    The Controller Class is the primary node from an ISY perspective. It is a Superclass
    of polyinterface.Node so all methods from polyinterface.Node are available to this
    class as well.

    Class Variables:
    self.nodes: Dictionary of nodes. Includes the Controller node. Keys are the node addresses
    self.name: String name of the node
    self.address: String Address of Node, must be less than 14 characters (ISY limitation)
    self.polyConfig: Full JSON config dictionary received from Polyglot.
    self.added: Boolean Confirmed added to ISY as primary node

    Class Methods (not including the Node methods):
    start(): Once the NodeServer config is received from Polyglot this method is automatically called.
    addNode(polyinterface.Node): Adds Node to self.nodes and polyglot/ISY. This is called for you
                                 on the controller itself.
    delNode(address): Deletes a Node from the self.nodes/polyglot and ISY. Address is the Node's Address
    longPoll(): Runs every longPoll seconds (set initially in the server.json or default 10 seconds)
    shortPoll(): Runs every shortPoll seconds (set initially in the server.json or default 30 seconds)
    query(): Queries and reports ALL drivers for ALL nodes to the ISY.
    runForever(): Easy way to run forever without maxing your CPU or doing some silly 'time.sleep' nonsense
                  this joins the underlying queue query thread and just waits for it to terminate
                  which never happens.
    """
    def __init__(self, polyglot):
        """
        Optional.
        Super runs all the parent class necessities. You do NOT have
        to override the __init__ method, but if you do, you MUST call super.
        """
        LOGGER.info('HarmonyController: Initializing')
        super(HarmonyController, self).__init__(polyglot)
        self.name = 'HarmonyHub Controller'
        self.address = 'harmonyctrl'
        self.primary = self.address
        # These start in threads cause they take a while
        self.discover_thread = None
        self.profile_thread = None
        self.do_poll = False
        self.lpfx = ""
        self.hb = 0

    def start(self):
        """
        Optional.
        Polyglot v2 Interface startup done. Here is where you start your integration.
        This will run, once the NodeServer connects to Polyglot and gets it's config.
        In this example I am calling a discovery method. While this is optional,
        this is where you should start. No need to Super this method, the parent
        version does nothing.
        """
        self.removeNoticesAll()
        serverdata = self.poly.get_server_data(check_profile=False)
        LOGGER.info('Started HarmonyHub NodeServer {}'.format(serverdata['version']))
                #polyinterface.LOGGER("start: This is {0} error {1}".format("an"))
        self.l_info('start','Starting')
        # Some are getting unclosed socket warnings from sleekxmpp when thread exits that I can't get rid if so ignore them.
        warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*<socket.socket.*>")
        # Show these for now
        self.l_debug("start","GV4={0} GV8={1}".format(self.getDriver('GV4'),self.getDriver('GV8')))
        self.set_debug_level(self.getDriver('GV4'))
        # Set Profile Status as Up To Date, if it's status 6=ISY Reboot Required
        val = self.getDriver('GV7')
        if val is None or int(val) == 6 or int(val) == 0:
            self.setDriver('GV7', 1)
        # Short Poll
        val = self.getDriver('GV5')
        self.l_debug("start","shortPoll={0} GV5={1}".format(self.polyConfig['shortPoll'],val))
        if val is None:
            self.setDriver('GV5',self.polyConfig['shortPoll'])
        elif (int(val) != 0):
            self.polyConfig['shortPoll'] = int(val)
        # Long Poll
        val = self.getDriver('GV6')
        self.l_debug("start","longPoll={0} GV6={1}".format(self.polyConfig['longPoll'],val))
        if val is None:
            self.setDriver('GV6',self.polyConfig['longPoll'])
        elif (int(val) != 0):
            self.polyConfig['longPoll'] = int(val)
        # Activiy method
        val = self.getDriver('GV9')
        if val is None:
            self.activity_method = 2 # The default
            self.setDriver('GV9',self.activity_method)
        else:
            self.activity_method = int(val)
        self.l_debug("start","GV9={0} activity_method={1}".format(val,self.activity_method))
        # Initialize hubs
        self.clear_hubs()
        self.hubs = list()
        # Watch Mode
        self.set_watch_mode(self.getDriver('GV10'))

        # New vesions need to force an update
        if not 'cver' in self.polyConfig['customData']:
            self.polyConfig['customData']['cver'] = 1
        self.l_debug("start","cver={0}".format(self.polyConfig['customData']['cver']))
        if int(self.polyConfig['customData']['cver']) < 2:
            self.l_debug("start","updating myself since cver {0} < 2".format(self.polyConfig['customData']['cver']))
            # Force an update.
            self.addNode(self,update=True)
            self.polyConfig['customData']['cver'] = 3
            self.saveCustomData(self.polyConfig['customData'])
        #
        # Add Hubs from the config
        #
        self._set_num_hubs(0)
        self.first_run = False
        #self.l_debug("start","nodes={}".format(self.polyConfig['nodes']))
        if self.polyConfig['nodes']:
            self.l_info("start","Adding known hubs...")
            # Load the config info about the hubs.
            self.load_config()
            # Load the hub info.
            self.load_hubs()
            if self.hubs is False:
                self.l_error("start","No hubs loaded, need to discover?")
                return
            # Build/Update profile if necessary
            serverdata = self.poly.check_profile(serverdata,build_profile=self._update_profile)
            # Restore known hubs from the poly config nodes
            self.add_hubs()
        else:
            # No nodes exist, that means this is the first time we have been run
            # after install, so do a discover
            self.l_info("start","First run, will start discover...")
            self.first_run = True
            self.discover()
        self.l_info("start","done")

    # TODO: Is it ok to reference nodesAdding?
    def allNodesAdded(self):
        LOGGER.debug('nodesAdding: %d', len(self.nodesAdding))
        return True if len(self.nodesAdding) > 0 else False

    def canPoll(self):
        if not self.allNodesAdded:
            LOGGER.debug('Waiting for all nodes to be added...')
            return False
        if self.discover_thread is not None:
            if self.discover_thread.is_alive():
                LOGGER.debug('discover thread still running...')
                return False
            else:
                LOGGER.debug('discover thread is done...')
                self.discover_thread = None
        if self.profile_thread is not None:
            if self.profile_thread.is_alive():
                LOGGER.debug('profile thread still running...')
                return False
            else:
                LOGGER.debug('profile thread is done...')
                self.profile_thread = None
        return True

    def shortPoll(self):
        #self.l_debug('shortPoll','...')
        if not self.canPoll():
            return False
        for node in self.nodes:
            if self.nodes[node].do_poll:
                self.nodes[node].shortPoll()

    def longPoll(self):
        #self.l_debug('longpoll','...')
        if not self.canPoll():
            return False
        for node in self.nodes:
            if self.nodes[node].do_poll:
                self.nodes[node].longPoll()
        self.heartbeat()

    def query(self):
        self.l_debug('query','...')
        if not self.canPoll():
            return False
        self.reportDrivers()
        for node in self.nodes:
            if self.nodes[node].do_poll:
                self.nodes[node].query()

    def discover(self):
        """
        Start the discover in a thread so we don't cause timeouts :(
        """
        self.discover_thread = Thread(target=self._discover)
        self.discover_thread.start()

    def heartbeat(self):
        self.l_info('heartbeat','hb={}'.format(self.hb))
        if self.hb == 0:
            self.reportCmd("DON",2)
            self.hb = 1
        else:
            self.reportCmd("DOF",2)
            self.hb = 0

    def _discover(self):
        # Clear the hubs now so we clear some that may have been improperly added.
        self.clear_hubs()
        # Set all hubs to not found
        for hub in self.hubs:
            hub['found'] = False
        #
        # Look for the hubs...
        #
        self.setDriver('GV7', 2)
        auto_discover = self.getDriver('GV8')
        discover_result = None
        if auto_discover is None:
            auto_discover = 1
        else:
            auto_discover = int(auto_discover)
        if (auto_discover == 0):
            self.l_info('discover','harmony_discover: skipping since auto discover={0}...'.format(auto_discover))
            discover_result = list()
        else:
            self.l_info('discover','harmony_discover: starting...')
            sys.path.insert(0,"pyharmony")
            from pyharmony import discovery as harmony_discovery
            harmony_discovery.logger = LOGGER
            try:
                discover_result = harmony_discovery.discover(scan_attempts=10,scan_interval=1)
            except (OSError) as err:
                self.setDriver('GV7', 9)
                self.l_error('discover','pyharmony discover failed. May need to restart this nodeserver: {}'.format(err), exc_info=True)
            self.l_info('discover','harmony_discover: {0}'.format(discover_result))
        #
        # Add the nodes
        #
        self.setDriver('GV7', 3)
        #
        # First from customParams.
        #
        for param in self.polyConfig['customParams']:
            # Look for customParam starting with hub_
            match = re.match( "hub_(.*)", param, re.I)
            self.l_info('discover','param={} match={}'.format(param,match))
            if match is not None:
                # The hub address is everything following the hub_
                address = match.group(1)
                self.l_info('discover','process param={0} address={1}'.format(param,address))
                # Get the customParam value which is json code
                #  { "name": "HarmonyHub FamilyRoom", "host": "192.168.1.86" }
                cfg = self.polyConfig['customParams'][param]
                cfgd = None
                try:
                    cfgd = json.loads(cfg)
                except:
                    err = sys.exc_info()[0]
                    self.l_error('discover','failed to parse cfg={0} Error: {1}'.format(cfg,err))
                if cfgd is not None:
                    # Check that name and host are defined.
                    addit = True
                    if not 'name' in cfgd:
                        self.l_error('discover','No name in customParam {0} value={1}'.format(param,cfg))
                        addit = False
                    if not 'host' in cfgd:
                        self.l_error('discover','No host in customParam {0} value={1}'.format(param,cfg))
                        addit = False
                    if addit:
                        self.hubs.append({'address': address, 'name': get_valid_node_name(cfgd['name']), 'host': cfgd['host'], 'port': 5222})

        #
        # Next the discovered ones
        #
        tst = time.strftime("%m%d%Y-%H%M%S")
        ust = 'uuid-save-%s' % (tst)
        if discover_result is not None:
            for config in discover_result:
                LOGGER.debug("hub config: %s",config)
                addit = True
                if 'current_fw_version' in config:
                    if config['current_fw_version'] == '4.15.206':
                        self.l_error('discover','current_fw_version={} which is not supported.  See: {}'.
                        format(
                            config['current_fw_version'],
                            'https://community.logitech.com/s/question/0D55A00008D4bZ4SAJ/harmony-hub-firmware-update-fixes-vulnerabilities'
                        ))
                        addit = False
                else:
                    self.l_error('discover','current_fw_version not in config?  Will try to use anyway {}'.format(config))
                if addit:
                    # See if the hub is already in the list.
                    hub_address = 'h'+id_to_address(config['uuid'],13)
                    hub_name    = get_valid_node_name(config['friendlyName'])
                    index = next((idx for (idx, hub) in enumerate(self.hubs) if hub['name'] == hub_name), None)
                    LOGGER.debug('found index=%s',index)
                    if index is None:
                        # Not seen, or is a different name
                        hub_hash = {
                            'address': hub_address,
                            'name':    hub_name,
                        }
                        self.hubs.append(hub_hash)
                    else:
                        # Keep the same address for this hub name.
                        hub_hash = self.hubs[index]
                        if 'uuid' in hub_hash:
                            if hub_hash['uuid'] != config['uuid']:
                                LOGGER.warning("Seems that hub '%s' uuid changed from '%s' to '%s' will continue using old address %s",hub_name,hub_hash['uuid'],config['uuid'],hub_address)
                                hub_hash[ust] = hub_hash['uuid']
                    # These always use the latest data.
                    hub_hash['date_time'] = tst
                    hub_hash['host']      = config['ip']
                    hub_hash['port']      = config['port']
                    hub_hash['found']     = True
                    hub_hash['save']      = True
                    hub_hash['uuid']      = config['uuid']
        #
        # Write warnings about previously known Hubs
        #
        for hub in self.hubs:
            if not 'found' in hub or not hub['found']:
                LOGGER.warning("Previously known hub '%s' did not respond to discover",hub['name'])

        self.save_hubs()
        #
        # Build the profile
        # It needs the hub_list set, so we will reset it later.
        if self._build_profile():
            #
            # Now really add them.
            self.add_hubs()

        # Check on the purge
        self.purge(do_delete=False)


    def add_hub(self,address,name,host,port,discover=False):
        self.l_debug("add_hub","address={0} name='{1}' host={2} port={3}".format(address,name,host,port))
        self.addNode(HarmonyHub(self, address, name, host, port, watch=self.watch_mode, discover=discover))

    def add_hubs(self):
        self._set_num_hubs(0)
        for hub in self.hubs:
            if not 'found' in hub or hub['found']:
                self.add_hub(hub['address'], hub['name'], hub['host'], hub['port'])
                self._set_num_hubs(self.num_hubs + 1)

    """
    This pulls in the save hub data.  Old versions stored this in the
    customParams, but since we need it available from install.sh we
    switched to using a local file.
    """
    def load_hubs(self):
        self.hubs = list()
        # Hack... if customParams has clear_hubs=1 then just clear them :(
        # This is the only way to clear a bad IP address until my changes to pyharmony are accepted.
        cdata = self.polyConfig['customParams']
        param_name = 'clear_hubs'
        if param_name in self.polyConfig['customParams'] and int(self.polyConfig['customParams'][param_name]) == 1:
            self.l_info("load_hubs","Clearing known hubs, you will need to run discover again since customParam {0} = {1}".format(param_name,self.polyConfig['customParams'][param_name]))
            self.clear_hubs()
            self.hubs = list()
        else:
            # If hubs exists in the customData, convert to .hubs list and save the json
            if 'hubs' in self.polyConfig['customData']:
                # Turn customData hubs hash into a list...
                self.l_info("load_hubs","Converting hubs from Polyglot DB to local file for {0}".format(self.polyConfig['customData']))
                # From: self.polyConfig['customData']['hubs'][address] = {'name': name, 'host': host, 'port': port}
                for address in self.polyConfig['customData']['hubs']:
                    hub_c = deepcopy(self.polyConfig['customData']['hubs'][address])
                    hub_c['address'] = address
                    self.hubs.append(hub_c)
                # Save the new json
                if self.save_hubs():
                    del self.polyConfig['customData']['hubs']
                    self.saveCustomData(self.polyConfig['customData'])
                    if 'hubs' in self.polyConfig['customData']:
                        # WTF, it wasn't deleted?
                        self.l_error("load_hubs","customData['hubs'] was not deleted? {0}".format(self.polyConfig))
                    else:
                        self.l_info("load_hubs","customData['hubs'] was deleted".format(self.polyConfig))
                    # Need to generate new profile
                    self.l_info("load_hubs","Building profile since data was migrated to external file.")
                    self.build_profile()
            else:
                self.hubs = load_hubs_file(LOGGER)
                # Temp test to put them back...
                #hdata = dict()
                #for hub in self.hubs:
                #    hdata[hub['address']] = hub
                #self.polyConfig['customData']['hubs'] = hdata
                #self.saveCustomData(self.polyConfig['customData'])
                #self.l_info("load_hubs","Force adding back customData['hubs'] {0}".format(self.polyConfig))


        # Always clear it so the default value shows for the user.
        self.addCustomParam({param_name: 0})

    def save_hubs(self):
        return save_hubs_file(LOGGER,self.hubs)

    def clear_hubs(self):
        # Clear how many hubs we manage
        self._set_num_hubs(0)

    def load_config(self):
        self.harmony_config = load_config_file(LOGGER)

    def delete(self):
        """
        Example
        This is sent by Polyglot upon deletion of the NodeServer. If the process is
        co-resident and controlled by Polyglot, it will be terminiated within 5 seconds
        of receiving this message.
        """
        self.l_info('delete','Oh God I\'m being deleted. Nooooooooooooooooooooooooooooooooooooooooo.')

    def _set_num_hubs(self, value):
        self.num_hubs = value
        self.l_info("_set_num_hubs","{}".format(self.num_hubs))
        self.setDriver('GV3', self.num_hubs)
        return True

    def purge(self,do_delete=False):
        LOGGER.info("%s starting do_delete=%s",self.lpfx,do_delete)
        self.removeNoticesAll()
        #LOGGER.debug("%s config=",self.lpfx,config)
        #
        # Check for removed activities or devices
        #
        # This can change while we are checking if another hub is being added...
        #LOGGER.debug("%s",self.controller.poly.config)
        # These are all the nodes from the config, not the real nodes we added...
        nodes = self.controller.poly.config['nodes'].copy()
        # Pattern match hub address s
        pch = re.compile('h([a-f0-9]+)$')
        # Pattern match activity and device addresses
        pcad = re.compile('(.)(\d+)$')
        activities = self.harmony_config['info']['activities']
        devices    = self.harmony_config['info']['devices']
        msg_pfx = "Deleting" if do_delete else "Want to delete"
        delete_cnt = 0
        # Check if we still have them.
        for node in nodes:
            address = node['address']
            if address != self.address:
                #LOGGER.info("%s Checking Node: %s",self.lpfx,node)
                LOGGER.info("%s Checking Node: %s",self.lpfx,address)
                match = pch.match(address)
                LOGGER.debug("  Match Hub: %s", match)
                if match:
                    id   = match.group(1)
                    #LOGGER.debug("Got: %s %s", type,match)
                    LOGGER.debug('%s   Check if Hub %s "%s" id=%s still exists',self.lpfx,address,node['name'],id)
                    ret = next((d for d in self.hubs if d['address'] == address), None)
                    LOGGER.debug('%s    Got: %s',self.lpfx,ret)
                    if ret is None:
                        delete_cnt += 1
                        msg = '%s Hub that is no longer found %s "%s"' % (msg_pfx,address,node['name'])
                        LOGGER.warning('%s %s',self.lpfx,msg)
                        self.addNotice(msg)
                        if do_delete:
                            self.controller.poly.delNode(address)
                else:
                    match = pcad.match(address)
                    LOGGER.debug("  Match AD: %s", match)
                    if match:
                        type = match.group(1)
                        id   = int(match.group(2))
                        LOGGER.debug(" np: %s", node['primary'])
                        if node['primary'] in self.nodes:
                            pname = self.nodes[node['primary']].name
                        else:
                            pname = node['primary']
                        #LOGGER.debug("Got: %s %s", type,match)
                        if type == 'a':
                            LOGGER.debug('%s   Check if Activity %s "%s" id=%s still exists',self.lpfx,address,node['name'],id)
                            item = next((d for d in activities if int(d['id']) == id), None)
                            LOGGER.debug('%s    Got: %s',self.lpfx,item)
                            if item is None or item['cnt'] == 0:
                                delete_cnt += 1
                                msg = '%s Activity for "%s" that is no longer used %s "%s"' % (msg_pfx,pname,address,node['name'])
                                LOGGER.warning('%s %s',self.lpfx,msg)
                                self.addNotice(msg)
                                if do_delete:
                                    self.controller.poly.delNode(address)
                        elif type == 'd':
                            LOGGER.debug('%s   Check if Device %s "%s" id=%s still exists',self.lpfx,address,node['name'],id)
                            item = next((d for d in devices if int(d['id']) == id), None)
                            LOGGER.debug('%s    Got: %s',self.lpfx,item)
                            if item is None or item['cnt'] == 0:
                                delete_cnt += 1
                                msg = '%s Device for "%s" that is no longer used %s "%s"' % (msg_pfx,pname,address,node['name'])
                                LOGGER.warning('%s %s',self.lpfx,msg)
                                self.addNotice(msg)
                                if do_delete:
                                    self.controller.poly.delNode(address)
                        else:
                            LOGGER.warning('%s Unknown type "%s" "%s" id=%s still exists',self.lpfx,type,address,node['name'])

        if delete_cnt > 0 and not do_delete:
            self.addNotice("Please run 'Purge Execute' on %s in Admin Console" % self.name)

        LOGGER.info("%s done",self.lpfx)
        self.purge_run = True

    def l_info(self, name, string):
        LOGGER.info("%s:%s: %s" %  (self.id,name,string))

    def l_error(self, name, string, exc_info=False):
        LOGGER.error("%s:%s: %s" % (self.id,name,string), exc_info=exc_info)

    def l_warning(self, name, string):
        LOGGER.warning("%s:%s: %s" % (self.id,name,string))

    def l_debug(self, name, string):
        LOGGER.debug("%s:%s: %s" % (self.id,name,string))

    # Just calls build_profile with poll_hubs=False
    def update_profile(self):
        self.build_profile(False)

    def build_profile(self,poll_hubs=True):
        """
        Start the build_profile in a thread so we don't cause timeouts :(
        """
        if poll_hubs:
            self.profile_thread = Thread(target=self._build_profile)
        else:
            self.profile_thread = Thread(target=self._update_profile)
        self.profile_thread.start()

    def _build_profile(self):
        """
        Build the profile by polling the hubs
        """
        self.setDriver('GV7', 4)
        # This writes all the profile data files and returns our config info.
        wrote_profile = False
        try:
            config_data = write_profile(LOGGER,self.hubs)
            wrote_profile = True
        except (Exception) as err:
            self.l_error('build_profile','write_profile failed: {}'.format(err), exc_info=True)
            self.setDriver('GV7', 7)
        # Reload the config we just generated.
        self.load_config()
        #
        # Upload the profile
        #
        st = self.install_profile()
        #
        # Restart the hubs since the config data files may have changed.
        #
        if not self.first_run:
            self.restart_hubs()
        return st

    def restart_hubs(self):
        self.l_debug('restart_hubs','restarting hubs')
        for hub in self.hubs:
            address = hub['address']
            if address in self.nodes:
                self.nodes[address].restart()
            else:
                self.l_debug('restart_hubs','hub {} does not seem to exist yet'.format(address))

    def _update_profile(self):
        """
        Build the profile from the previously saved info
        """
        self.setDriver('GV7', 4)
        # This writes all the profile data files and returns our config info.
        try:
            config_data = write_profile(LOGGER,self.hubs,False)
        except (Exception) as err:
            self.l_error('build_profile','write_profile failed: {}'.format(err), exc_info=True)
            self.setDriver('GV7', 7)
        # Reload the config we just generated, it shouldn't update, but it might.
        self.load_config()
        # Upload the profile
        st = self.install_profile()
        return st

    def install_profile(self):
        self.setDriver('GV7', 5)
        try:
            self.poly.installprofile()
        except:
            err = sys.exc_info()[0]
            self.setDriver('GV7', 8)
            self.l_error('discovery','Install Profile Error: {}'.format(err))
            return False
        # Now a reboot is required
        # TODO: This doesn't really mean it was complete, a response is needed from polyglot,
        # TODO: which is on the enhancement list.
        self.setDriver('GV7', 6)
        return True

    def set_all_logs(self,level):
        LOGGER.setLevel(level)
        logging.getLogger('sleekxmpp').setLevel(logging.ERROR)
        logging.getLogger('requests').setLevel(level)
        logging.getLogger('urllib3').setLevel(level)
        logging.getLogger('pyharmony').setLevel(level)

    def set_debug_level(self,level):
        # First run will be None, so default is all
        if level is None:
            level = 0
        else:
            level = int(level)
        self.setDriver('GV4', level)
        # 0=All 10=Debug are the same because 0 (NOTSET) doesn't show everything.
        if level == 0 or level == 10:
            self.set_all_logs(logging.DEBUG)
        elif level == 20:
            self.set_all_logs(logging.INFO)
        elif level == 30:
            self.set_all_logs(logging.WARNING)
        elif level == 40:
            self.set_all_logs(logging.ERROR)
        elif level == 50:
            self.set_all_logs(logging.CRITICAL)
        else:
            self.l_error("set_debug_level","Unknown level {0}".format(level))

    def set_watch_mode(self,val):
        if val is None:
            self.l_debug("set_watch_mode","{0}".format(val))
            val = 1
        self.watch_mode = True if int(val) == 1 else False
        self.l_debug("set_watch_mode","{0}={1}".format(val,self.watch_mode))
        for hub in self.hubs:
            address = hub['address']
            self.nodes[address].set_watch(self.watch_mode)
        self.setDriver('GV10',val)

    def _cmd_discover(self, command):
        self.discover()

    def _cmd_purge_check(self,command):
        self.l_info("_cmd_purge","building...")
        self.purge(do_delete=False)

    def _cmd_purge_execute(self,command):
        self.l_info("_cmd_purge","building...")
        self.purge(do_delete=True)

    def _cmd_build_profile(self,command):
        self.l_info("_cmd_build_profile","building...")
        self.build_profile()

    def _cmd_install_profile(self,command):
        self.l_info("_cmd_install_profile","installing...")
        self.poly.installprofile()

    def _cmd_update_profile(self,command):
        self.l_info("_cmd_update_profile","...")
        self.update_profile()

    def _cmd_set_debug_mode(self,command):
        val = int(command.get('value'))
        self.l_info("_cmd_set_debug_mode",val)
        self.set_debug_level(val)

    def _cmd_set_discover_mode(self,command):
        val = int(command.get('value'))
        self.l_info("_cmd_set_discover_mode",val)
        self.setDriver('GV8', val)

    def _cmd_set_activity_method(self,command):
        val = int(command.get('value'))
        self.l_info("_cmd_set_activity_method",val)
        self.setDriver('GV9', val)
        self.activity_method = val # The default

    def _cmd_set_shortpoll(self,command):
        val = int(command.get('value'))
        self.l_info("_cmd_set_short_poll",val)
        self.setDriver('GV5', val)
        self.polyConfig['shortPoll'] = val

    def _cmd_set_longpoll(self,command):
        val = int(command.get('value'))
        self.l_info("_cmd_set_log_poll",val)
        self.setDriver('GV6', val)
        self.polyConfig['longPoll'] = val

    def _cmd_set_watch_mode(self,command):
        val = int(command.get('value'))
        self.set_watch_mode(val)

    id = 'HarmonyController'
    """
       Commands:
    """
    commands = {
        'QUERY': query,
        'DISCOVER': _cmd_discover,
        'BUILD_PROFILE': _cmd_build_profile,
        'PURGE_CHECK': _cmd_purge_check,
        'PURGE_EXECUTE': _cmd_purge_execute,
        'INSTALL_PROFILE': _cmd_install_profile,
        'UPDATE_PROFILE': _cmd_update_profile,
        'SET_DEBUGMODE': _cmd_set_debug_mode,
        'SET_SHORTPOLL': _cmd_set_shortpoll,
        'SET_LONGPOLL':  _cmd_set_longpoll,
        'SET_DI_MODE': _cmd_set_discover_mode,
        'SET_ACTIVITY_METHOD': _cmd_set_activity_method,
        'SET_WATCH_MODE': _cmd_set_watch_mode
    }
    """
       Driver Details:
    """
    drivers = [
        {'driver': 'ST',  'value': 1,  'uom': 2},  #    bool:   Connection status (managed by polyglot)
        # No longer used.
        #{'driver': 'GV1', 'value': 0,  'uom': 56}, #   float:   Version of this code (Major)
        #{'driver': 'GV2', 'value': 0,  'uom': 56}, #   float:   Version of this code (Minor)
        {'driver': 'GV3', 'value': 0,  'uom': 25}, # integer: Number of the number of hubs we manage
        {'driver': 'GV4', 'value': 0,  'uom': 25}, # integer: Log/Debug Mode
        {'driver': 'GV5', 'value': 5,  'uom': 25}, # integer: shortpoll
        {'driver': 'GV6', 'value': 60, 'uom': 25}, # integer: longpoll
        {'driver': 'GV7', 'value': 0,  'uom': 25}, #    bool: Profile status
        {'driver': 'GV8', 'value': 1,  'uom': 25}, #    bool: Auto Discover
        {'driver': 'GV9', 'value': 2,  'uom': 25}, #    bool: Activity Method
        {'driver': 'GV10', 'value': 2,  'uom': 2}   #    bool: Activity Method
    ]

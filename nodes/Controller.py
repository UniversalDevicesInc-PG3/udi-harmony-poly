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
from udi_interface import Node,LOGGER,Custom,LOG_HANDLER
import json,re,time,sys,os.path,yaml,logging,json,warnings,time
from traceback import format_exception
from copy import deepcopy
from threading import Thread
from nodes import Hub
from harmony_hub_funcs import *
from write_profile import write_profile

class Controller(Node):
    def __init__(self, poly, primary, address, name):
        LOGGER.info('HarmonyController: Initializing')
        super(Controller, self).__init__(poly, primary, address, name)
        # These start in threads cause they take a while
        self.discover_thread = None
        self.profile_thread = None
        self.do_poll = False
        self.lpfx = ""
        self.hb = 0
        self.n_queue = []
        self.Notices         = Custom(poly, 'notices')
        self.Data            = Custom(poly, 'customdata')
        self.Params          = Custom(poly, 'customparams')
        self.Notices         = Custom(poly, 'notices')
        #self.TypedParameters = Custom(poly, 'customtypedparams')
        #self.TypedData       = Custom(poly, 'customtypeddata')
        poly.subscribe(poly.START,             self.handler_start, address) 
        poly.subscribe(poly.POLL,              self.handler_poll)
        poly.subscribe(poly.DISCOVER,          self.discover)
        poly.subscribe(poly.STOP,              self.handler_stop)
        poly.subscribe(poly.CUSTOMPARAMS,      self.handler_params)
        #poly.subscribe(poly.CUSTOMTYPEDPARAMS, self.handler_typed_params)
        #poly.subscribe(poly.CUSTOMTYPEDDATA,   self.handler_typed_data)
        poly.subscribe(poly.LOGLEVEL,          self.handler_log_level)
        poly.subscribe(poly.CONFIGDONE,        self.handler_config_done)
        poly.subscribe(poly.ADDNODEDONE,       self.node_queue)
        poly.ready()
        poly.addNode(self, conn_status="ST")

    '''
    node_queue() and wait_for_node_event() create a simple way to wait
    for a node to be created.  The nodeAdd() API call is asynchronous and
    will return before the node is fully created. Using this, we can wait
    until it is fully created before we try to use it.
    '''
    def node_queue(self, data):
        self.n_queue.append(data['address'])

    def wait_for_node_done(self):
        while len(self.n_queue) == 0:
            time.sleep(0.1)
        self.n_queue.pop()

    def add_node(self,node):
        LOGGER.debug("Node: address={node.address} name={node.name}")
        anode = self.poly.addNode(node)
        LOGGER.debug(f'got {anode}')
        self.wait_for_node_done()
        if anode is None:
            LOGGER.error('Failed to add node address')
        #else:
        #    enode = self.poly.getNode(node.address)
        #    if (node.name == "Watch a DVD" or node.name == "Watch a DVDx"):
        #        LOGGER.error(f"Name mismatch, node.name={node.name} anode={anode.name} enode={node.name}")
        return anode

    def handler_start(self):
        self.poly.Notices.clear()
        #serverdata = self.poly.get_server_data(check_profile=False)
        LOGGER.info(f"Started HarmonyHub NodeServer {self.poly.serverdata['version']}")
        # Some are getting unclosed socket warnings from sleekxmpp when thread exits that I can't get rid if so ignore them.
        warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*<socket.socket.*>")
        # Show these for now
        LOGGER.debug("GV8={}".format(self.getDriver('GV8')))
        # Set Profile Status as Up To Date, if it's status 6=ISY Reboot Required
        val = self.getDriver('GV7')
        if val is None or int(val) == 6 or int(val) == 0:
            self.setDriver('GV7', 1)
        # Short Poll
        #val = self.getDriver('GV5')
        #LOGGER.debug("shortPoll={0} GV5={1}".format(self.polyConfig['shortPoll'],val))
        #if val is None:
        #    self.setDriver('GV5',self.polyConfig['shortPoll'])
        #elif (int(val) != 0):
        #    self.polyConfig['shortPoll'] = int(val)
        # Long Poll
        #val = self.getDriver('GV6')
        #LOGGER.debug("longPoll={0} GV6={1}".format(self.polyConfig['longPoll'],val))
        #if val is None:
        #    self.setDriver('GV6',self.polyConfig['longPoll'])
        #elif (int(val) != 0):
        #    self.polyConfig['longPoll'] = int(val)
        # Activiy method
        val = self.getDriver('GV9')
        if val is None:
            self.activity_method = 2 # The default
            self.setDriver('GV9',self.activity_method)
        else:
            self.activity_method = int(val)
        LOGGER.debug("GV9={0} activity_method={1}".format(val,self.activity_method))

    def handler_config_done(self):
        LOGGER.info(f'{self.lpfx} enter')
        self.poly.addLogLevel('DEBUG_MODULES',9,'Debug + Modules')
        # Currently not gaurunteed all config handlers are called, so wait
        # until custom params are processed
        count = 0
        while self.config_st is None and count < 60:
            LOGGER.warning("Waiting for config to be loaded...")
            time.sleep(1)
            count += 1
        if count == 60:
            LOGGER.error("Timeout waiting for config to load, check log for other errors.")
            exit
        # Initialize hubs
        self.clear_saved_hubs()
        # Load em if we have em
        self.load_hubs()
        # Watch Mode
        self.set_watch_mode(self.getDriver('GV10'))
        #
        # Add Hubs from the config
        #
        self._set_num_hubs(0)
        self.first_run = False
        #LOGGER.debug("start","nodes={}".format(self.polyConfig['nodes']))
        if config_file_exists():
            LOGGER.info("Adding known hubs...")
            # Load the config info about the hubs.
            self.load_config()
            # Load the hub info.
            self.load_hubs()
            if self.hubs is False:
                LOGGER.error("No hubs loaded, need to discover?")
            else:
                # Build/Update profile if necessary
                serverdata = self.poly.checkProfile(self.poly.serverdata,build_profile=self._update_profile)
                # Restore known hubs from the poly config nodes
                self.add_hubs()
        else:
            # No nodes exist, that means this is the first time we have been run
            # after install, so do a discover
            LOGGER.info("First run, will start discover...")
            self.first_run = True
            self.discover()
        LOGGER.info(f'{self.lpfx} exit')

    def canPoll(self):
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

    def handler_poll(self, polltype):
        if polltype == 'longPoll':
            self.longPoll()
        elif polltype == 'shortPoll':
            self.shortPoll()
            
    def shortPoll(self):
        LOGGER.debug('...')
        if not self.canPoll():
            return False
        for node in self.poly.getNodes():
            if self.poly.getNode(node).do_poll:
                self.poly.getNode(node).shortPoll()

    def longPoll(self):
        LOGGER.debug('...')
        if not self.canPoll():
            return False
        for node in self.poly.getNodes():
            if self.poly.getNode(node).do_poll:
                self.poly.getNode(node).longPoll()
        self.heartbeat()

    def query(self):
        LOGGER.debug('...')
        if not self.canPoll():
            return False
        self.reportDrivers()
        for node in self.poly.getNodes():
            if self.poly.getNode(node).do_poll:
                self.poly.getNode(node).query()

    def discover(self):
        self.discover_thread = Thread(target=self._discover)
        self.discover_thread.start()

    def heartbeat(self):
        LOGGER.info('hb={}'.format(self.hb))
        if self.hb == 0:
            self.reportCmd("DON",2)
            self.hb = 1
        else:
            self.reportCmd("DOF",2)
            self.hb = 0

    def handler_params(self,params):
        LOGGER.debug(f'enter: Loading params')
        self.Params.load(params)
        self.poly.Notices.clear()
        """
        Check all user params are available and valid
        """
        # Assume it's good unless it's not
        config_st = True
        #
        # Clear Hubs
        #
        #if not 'clear_hubs' in self.Params:
        #    self.Params['clear_hubs'] = "0"
        self.config_st = config_st
        LOGGER.debug(f'exit: config_st={config_st}')

    def _discover(self):
        # Clear the hubs now so we clear some that may have been improperly added.
        self.clear_saved_hubs()
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
            LOGGER.info('harmony_discover: skipping since auto discover={0}...'.format(auto_discover))
            discover_result = list()
        else:
            LOGGER.info('harmony_discover: starting...')
            sys.path.insert(0,"pyharmony")
            from pyharmony import discovery as harmony_discovery
            harmony_discovery.logger = LOGGER
            try:
                discover_result = harmony_discovery.discover(scan_attempts=10,scan_interval=1)
            except (OSError) as err:
                self.setDriver('GV7', 9)
                LOGGER.error('pyharmony discover failed. May need to restart this nodeserver: {}'.format(err), exc_info=True)
            LOGGER.info('harmony_discover: {0}'.format(discover_result))
        #
        # Add the nodes
        #
        self.setDriver('GV7', 3)
        #
        # First from customParams.
        # TODO: Add back support of customParams
        #
        #for param in self.polyConfig['customParams']:
        #    # Look for customParam starting with hub_
        #    match = re.match( "hub_(.*)", param, re.I)
        #    LOGGER.info('param={} match={}'.format(param,match))
        #    if match is not None:
        #        # The hub address is everything following the hub_
        #        address = match.group(1)
        #        LOGGER.info('process param={0} address={1}'.format(param,address))
        #        # Get the customParam value which is json code
        #        #  { "name": "HarmonyHub FamilyRoom", "host": "192.168.1.86" }
        #        cfg = self.polyConfig['customParams'][param]
        #        cfgd = None
        #        try:
        #            cfgd = json.loads(cfg)
        #        except:
        #            err = sys.exc_info()[0]
        #            LOGGER.error('failed to parse cfg={0} Error: {1}'.format(cfg,err))
        #        if cfgd is not None:
        #            # Check that name and host are defined.
        #            addit = True
        #            if not 'name' in cfgd:
        #                LOGGER.error('No name in customParam {0} value={1}'.format(param,cfg))
        #                addit = False
        #            if not 'host' in cfgd:
        #                LOGGER.error('No host in customParam {0} value={1}'.format(param,cfg))
        #                addit = False
        #            if addit:
        #                hub_name = get_valid_node_name(cfgd['name'])
        #                hub_hash = {'address': address, 'name': hub_name, 'host': cfgd['host'], 'port': 5222, 'found': True, 'custom': True}
        #                index = next((idx for (idx, hub) in enumerate(self.hubs) if hub['name'] == hub_name), None)
        #                if index is None:
        #                    self.hubs.append(hub_hash)
        #                else:
        #                    self.hubs[index] = hub_hash
        #
        # Next the discovered ones
        #
        tst = time.strftime("%m%d%Y-%H%M%S")
        ust = 'uuid-save-%s' % (tst)
        if discover_result is not None:
            LOGGER.debug("hubs.list=%s",self.hubs)
            for config in discover_result:
                LOGGER.debug("hub config: %s",config)
                addit = True
                if 'current_fw_version' in config:
                    if config['current_fw_version'] == '4.15.206':
                        LOGGER.error('current_fw_version={} which is not supported.  See: {}'.
                        format(
                            config['current_fw_version'],
                            'https://community.logitech.com/s/question/0D55A00008D4bZ4SAJ/harmony-hub-firmware-update-fixes-vulnerabilities'
                        ))
                        addit = False
                else:
                    LOGGER.error('current_fw_version not in config?  Will try to use anyway {}'.format(config))
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
        LOGGER.debug("address={0} name='{1}' host={2} port={3}".format(address,name,host,port))
        self.add_node(Hub(self, address, name, host, port, watch=self.watch_mode, discover=discover))

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
        # Hack... if customParams has clear_hubs=1 then just clear them :(
        # This is the only way to clear a bad IP address until my changes to pyharmony are accepted.
        param_name = 'clear_hubs'
        if self.Params[param_name] == "1":
            LOGGER.info("Clearing known hubs, you will need to run discover again since customParam {0} = {1}".format(param_name,self.Params[param_name]))
            self.clear_saved_hubs()
            self.hubs = list()
            self.Params['clear_hubs'] = "0"
        else:
            self.hubs = load_hubs_file(LOGGER)
            if not self.hubs:
                self.hubs = list()

    def save_hubs(self):
        return save_hubs_file(LOGGER,self.hubs)

    def clear_saved_hubs(self):
        # Clear how many hubs we manage
        self._set_num_hubs(0)

    def load_config(self):
        self.harmony_config = load_config_file(LOGGER)

    def handler_stop(self):
        # TODO: exit threads?
        LOGGER.warning("Stopping...")
        self.poly.stop()

    def delete(self):
        LOGGER.info('Oh God I\'m being deleted. Nooooooooooooooooooooooooooooooooooooooooo.')

    def _set_num_hubs(self, value):
        self.num_hubs = value
        LOGGER.info("{}".format(self.num_hubs))
        self.setDriver('GV3', self.num_hubs)
        return True

    def purge(self,do_delete=False):
        LOGGER.info("%s starting do_delete=%s",self.lpfx,do_delete)
        self.Notices.clear()
        #LOGGER.debug("%s config=",self.lpfx,config)
        #
        # Check for removed activities or devices
        #
        # This can change while we are checking if another hub is being added...
        #LOGGER.debug("%s",self.controller.poly.config)
        # These are all the nodes from the config, not the real nodes we added...
        #nodes = self.controller.poly.config['nodes'].copy()
        # Pattern match hub address s
        pch = re.compile('h([a-f0-9]+)$')
        # Pattern match activity and device addresses
        pcad = re.compile('(.)(\d+)$')
        activities = self.harmony_config['info']['activities']
        devices    = self.harmony_config['info']['devices']
        msg_pfx = "Deleting" if do_delete else "Want to delete"
        delete_cnt = 0
        # Check if we still have them.
        for address in self.poly.getNodes():
            node = self.poly.getNode(address)
            if address != self.address:
                #LOGGER.info("%s Checking Node: %s",self.lpfx,node)
                LOGGER.info("%s Checking Node: %s",self.lpfx,address)
                match = pch.match(address)
                LOGGER.debug("  Match Hub: %s", match)
                if match:
                    id   = match.group(1)
                    #LOGGER.debug("Got: %s %s", type,match)
                    LOGGER.debug('%s   Check if Hub %s "%s" id=%s still exists',self.lpfx,address,node.name,id)
                    ret = next((d for d in self.hubs if d['address'] == address), None)
                    LOGGER.debug('%s    Got: %s',self.lpfx,ret)
                    if ret is None:
                        delete_cnt += 1
                        msg = '%s Hub that is no longer found %s "%s"' % (msg_pfx,address,node.name)
                        LOGGER.warning('%s %s',self.lpfx,msg)
                        self.Notices[address] = msg
                        if do_delete:
                            self.controller.poly.delNode(address)
                else:
                    match = pcad.match(address)
                    LOGGER.debug("  Match AD: %s", match)
                    if match:
                        type = match.group(1)
                        id   = int(match.group(2))
                        LOGGER.debug(" np: %s", node.primary)
                        if node.primary in self.poly.getNodes():
                            pname = self.poly.getNode(node.primary).name
                        else:
                            pname = node.primary
                        #LOGGER.debug("Got: %s %s", type,match)
                        if type == 'a':
                            LOGGER.debug('%s   Check if Activity %s "%s" id=%s still exists',self.lpfx,address,node.name,id)
                            item = next((d for d in activities if int(d['id']) == id), None)
                            LOGGER.debug('%s    Got: %s',self.lpfx,item)
                            if item is None or item['cnt'] == 0:
                                delete_cnt += 1
                                msg = '%s Activity for "%s" that is no longer used %s "%s"' % (msg_pfx,pname,address,node.name)
                                LOGGER.warning('%s %s',self.lpfx,msg)
                                self.Notices[address] = msg
                                if do_delete:
                                    self.controller.poly.delNode(address)
                        elif type == 'd':
                            LOGGER.debug('%s   Check if Device %s "%s" id=%s still exists',self.lpfx,address,node.name,id)
                            item = next((d for d in devices if int(d['id']) == id), None)
                            LOGGER.debug('%s    Got: %s',self.lpfx,item)
                            if item is None or item['cnt'] == 0:
                                delete_cnt += 1
                                msg = '%s Device for "%s" that is no longer used %s "%s"' % (msg_pfx,pname,address,node.name)
                                LOGGER.warning('%s %s',self.lpfx,msg)
                                self.Notices[address] = msg
                                if do_delete:
                                    self.controller.poly.delNode(address)
                        else:
                            LOGGER.warning('%s Unknown type "%s" "%s" id=%s still exists',self.lpfx,type,address,node.name)

        if not do_delete:
            if delete_cnt > 0:
                self.Notices['purge'] = "Please run 'Purge Execute' on %s in Admin Console" % self.name
            else:
                self.Notices['purge'] = "Nothing to purge"

        LOGGER.info(f"{self.lpfx} done")
        self.purge_run = True

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
            LOGGER.error('write_profile failed: {}'.format(err), exc_info=True)
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
        LOGGER.debug('restart_hubs','restarting hubs')
        for hub in self.hubs:
            address = hub['address']
            if address in self.poly.getNodes():
                self.poly.getNode(address).restart()
            else:
                LOGGER.debug('hub {} does not seem to exist yet'.format(address))

    def _update_profile(self):
        """
        Build the profile from the previously saved info
        """
        self.setDriver('GV7', 4)
        # This writes all the profile data files and returns our config info.
        try:
            config_data = write_profile(LOGGER,self.hubs,False)
        except (Exception) as err:
            LOGGER.error('write_profile failed: {}'.format(err), exc_info=True)
            self.setDriver('GV7', 7)
        # Reload the config we just generated, it shouldn't update, but it might.
        self.load_config()
        # Upload the profile
        st = self.install_profile()
        return st

    def install_profile(self):
        self.setDriver('GV7', 5)
        try:
            self.poly.updateProfile()
        except:
            err = sys.exc_info()[0]
            self.setDriver('GV7', 8)
            LOGGER.error('Install Profile Error: {}'.format(err))
            return False
        # Now a reboot is required
        # TODO: This doesn't really mean it was complete, a response is needed from polyglot,
        # TODO: which is on the enhancement list.
        self.setDriver('GV7', 6)
        return True

    def handler_log_level(self,level):
        LOGGER.info(f'enter: level={level}')
        if level['level'] < 10:
            LOGGER.info("Setting basic config to DEBUG...")
            #LOG_HANDLER.set_basic_config(True,logging.DEBUG)
            slevel = logging.DEBUG
        else:
            LOGGER.info("Setting basic config to WARNING...")
            #LOG_HANDLER.set_basic_config(True,logging.WARNING)
            slevel = logging.WARNING
        # 02/23/2022 Was logging.WARNING but was missing timeouts?
        logging.getLogger('sleekxmpp').setLevel(slevel)
        logging.getLogger('requests').setLevel(slevel)
        logging.getLogger('urllib3').setLevel(slevel)
        logging.getLogger('pyharmony').setLevel(slevel)
        LOGGER.info(f'exit: slevel={slevel}')

    def set_watch_mode(self,val):
        if val is None:
            LOGGER.debug("{0}".format(val))
            val = 1
        self.watch_mode = True if int(val) == 1 else False
        LOGGER.debug("{0}={1}".format(val,self.watch_mode))
        for hub in self.hubs:
            address = hub['address']
            if address in self.poly.getNodes():
                self.poly.getNode(address).set_watch(self.watch_mode)
        self.setDriver('GV10',val)

    def _cmd_discover(self, command):
        self.discover()

    def _cmd_purge_check(self,command):
        LOGGER.info("building...")
        self.purge(do_delete=False)

    def _cmd_purge_execute(self,command):
        LOGGER.info("building...")
        self.purge(do_delete=True)

    def _cmd_build_profile(self,command):
        LOGGER.info("building...")
        self.build_profile()

    def _cmd_install_profile(self,command):
        LOGGER.info("installing...")
        self.poly.updateProfile()

    def _cmd_update_profile(self,command):
        LOGGER.info("...")
        self.update_profile()

    def _cmd_set_discover_mode(self,command):
        val = int(command.get('value'))
        LOGGER.info(val)
        self.setDriver('GV8', val)

    def _cmd_set_activity_method(self,command):
        val = int(command.get('value'))
        LOGGER.info(val)
        self.setDriver('GV9', val)
        self.activity_method = val # The default

    def _cmd_set_shortpoll(self,command):
        val = int(command.get('value'))
        LOGGER.info(val)
        self.setDriver('GV5', val)
        self.polyConfig['shortPoll'] = val

    def _cmd_set_longpoll(self,command):
        val = int(command.get('value'))
        LOGGER.info(val)
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
        #'SET_DEBUGMODE': _cmd_set_debug_mode,
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
        {'driver': 'ST',  'value': 1,  'uom': 25},  #    bool:   Connection status (managed by polyglot)
        # No longer used.
        #{'driver': 'GV1', 'value': 0,  'uom': 56}, #   float:   Version of this code (Major)
        #{'driver': 'GV2', 'value': 0,  'uom': 56}, #   float:   Version of this code (Minor)
        {'driver': 'GV3', 'value': 0,  'uom': 25}, # integer: Number of the number of hubs we manage
        #Not used in PG3 {'driver': 'GV4', 'value': 0,  'uom': 25}, # integer: Log/Debug Mode
        {'driver': 'GV5', 'value': 5,  'uom': 25}, # integer: shortpoll
        {'driver': 'GV6', 'value': 60, 'uom': 25}, # integer: longpoll
        {'driver': 'GV7', 'value': 0,  'uom': 25}, #    bool: Profile status
        {'driver': 'GV8', 'value': 1,  'uom': 25}, #    bool: Auto Discover
        {'driver': 'GV9', 'value': 2,  'uom': 25}, #    bool: Activity Method
        {'driver': 'GV10', 'value': 1,  'uom': 2}  #    bool: Hub Watch Mode
    ]

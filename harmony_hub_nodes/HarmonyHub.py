
import polyinterface,sys,logging,yaml,re
from traceback import format_exception
from threading import Thread,Event
from harmony_hub_nodes import HarmonyDevice,HarmonyActivity
from harmony_hub_funcs import ip2long,long2ip,get_valid_node_name,get_file
from pyharmony import client as harmony_client
from sleekxmpp.exceptions import IqError, IqTimeout
from copy import deepcopy

LOGGER = polyinterface.LOGGER

class HarmonyHub(polyinterface.Node):
    """
    This is the class that all the Nodes will be represented by. You will add this to
    Polyglot/ISY with the controller.addNode method.

    Class Variables:
    self.primary: String address of the Controller node.
    self.parent: Easy access to the Controller Class from the node itself.
    self.address: String address of this Node 14 character limit. (ISY limitation)
    self.added: Boolean Confirmed added to ISY

    Class Methods:
    start(): This method is called once polyglot confirms the node is added to ISY.
    setDriver('ST', 1, report = True, force = False):
        This sets the driver 'ST' to 1. If report is False we do not report it to
        Polyglot/ISY. If force is True, we send a report even if the value hasn't changed.
    reportDrivers(): Forces a full update of all drivers to Polyglot/ISY.
    query(): Called when ISY sends a query request to Polyglot for this specific node
    """
    def __init__(self, parent, address, name, host, port, watch=True, discover=False):
        """
        Optional.
        Super runs all the parent class necessities. You do NOT have
        to override the __init__ method, but if you do, you MUST call super.

        :param parent: Reference to the Controller class
        :param address: This nodes address
        :param name: This nodes name
        :param watch: Allow turning off hub monitoring when you know the hubs are not responding.
        :             Set to false until it's all running so short/long poll and query won't also try to start it.
        :param discover: Only set to True when device is added by new discover
        """
        # The id (node_def_id) is the address because each hub has a unique nodedef in the profile.
        # The id using the original case of the string
        self.id     = address
        self.name   = name
        self.host   = host
        self.port   = port
        self.parent = parent
        self.discover = discover
        self.watch  = False # Not watching yet
        self.watch_init  = watch
        self.client = None
        self.current_activity = -2
        self.thread = None
        self.client_status = None
        self.event  = None
        self.harmony_config = self.parent.harmony_config['info']
        self.st     = 0
        # Can't poll until start runs.
        self.do_poll = False
        self.lpfx = "%s:%s:" % (name,address)
        self.l_info("init","hub '%s' '%s' %s" % (address, name, host))
        # But here we pass the lowercase, cause ISY doesn't allow the upper case!
        # A Hub is it's own primary
        super(HarmonyHub, self).__init__(parent, address.lower(), address.lower(), name)

    def start(self):
        """
        Optional.
        This method is run once the Node is successfully added to the ISY
        and we get a return result from Polyglot.
        """
        self.l_info("start","hub '%s' '%s' %s" % (self.address, self.name, self.host))
        self._set_st(0)
        #
        # Add host (IP) and port
        #
        self.setDriver('GV1', ip2long(self.host))
        self.setDriver('GV2', self.port)
        #
        # Connect to the hub if desired
        #
        self.set_watch(self.watch_init)
        #
        # Call query to initialize and pull the info from the hub.
        #
        self.do_poll = True
        self.l_info("start","done hub '%s' '%s' %s" % (self.address, self.name, self.host))

    def set_watch(self,val):
        if val:
            if self.watch:
                # Just make sure it's running
                self.check_client()
            else:
                # Not watching, start it up
                self.get_client()
                self.watch = val
        else:
            # Just shut it down no matter what
            self.stop()
        # In case we restart
        self.watch_init = val

    def shortPoll(self):
        # Query in poll mode, or if we haven't set the current_activity yet (which happens on startup)
        #self.l_debug('shortPoll','watch={} client_status={}'.format(self.watch,self.client_status))
        if self.watch:
            if self.parent.activity_method == 1:
                self._get_current_activity()

    def longPoll(self):
        #self.l_debug('longPoll','watch={} client_status={}'.format(self.watch,self.client_status))
        if self.watch:
            self.check_client()

    def query(self):
        """
        Called by ISY to report all drivers for this node. This is done in
        the parent class, so you don't need to override this method unless
        there is a need.
        """
        self.l_debug('query','watch={} client_status={}'.format(self.watch,self.client_status))
        if self.watch:
            if self.check_client():
                self._get_current_activity()
        self.reportDrivers()

    def stop(self):
        self.l_debug('stop','...')
        return self._close_client()

    def restart(self):
        # Called by controller to restart myself
        self.stop()
        self.start()

    def _set_current_activity(self, id, force=False):
        """
        Update Polyglot with the current activity.
        """
        val   = int(id)
        if self.current_activity == val:
            return True
        # The harmony activity number
        self.current_activity = val
        index = self._get_activity_index(val)
        self.l_info("_set_current_activity","activity=%d, index=%d" % (self.current_activity,index))
        # Set to -1 to force a change.
        self.setDriver('GV3', -1)
        self.setDriver('GV3', index)
        # Make the activity node current, unless it's -1 which is poweroff
        ignore_id=False
        if id != -1:
            sid = str(id)
            if sid in self.activity_nodes:
                self.activity_nodes[str(id)]._set_st(1)
                ignore_id=id
            else:
                self.l_error('_set_current_activity','activity {} not in nodes list.'.format(sid))
        # Update all the other activities to not be the current.
        self._set_all_activities(0,ignore_id=ignore_id)
        return True

    def get_client(self):
        """
        Start the client in a thread so if it dies, we don't die.
        """
        self.client_status = "init"
        self.l_debug('get_client','Starting Thread')
        self.event = Event()
        self.thread = Thread(target=self._get_client)
        self.thread.daemon = True
        self.l_debug('get_client','Starting Thread')
        st = self.thread.start()
        self.l_debug('get_client','Back from Thread start st={}'.format(st))

    def _get_client(self):
        self.l_info("get_client","Initializing PyHarmony Client")
        harmony_client.logger.setLevel(logging.INFO)
        self.last_activity_method = self.parent.activity_method
        try:
            if self.parent.activity_method == 2:
                self.client = harmony_client.create_and_connect_client(self.host, self.port, self._set_current_activity)
            else:
                self.client = harmony_client.create_and_connect_client(self.host, self.port)
            if self.client is False:
                self.l_error('get_client','harmony_client returned False, will retry connect during next shortPoll interval')
                self._set_st(0)
                self._close_client()
                self.client_status = "failed"
                return False
        except:
            self.l_error('get_client','Failed to connect to host "{}" port "{}"'.format(self.host,self.port),True)
            self._set_st(0)
            self._close_client()
            self.client_status = "failed"
            return False
        self.l_info("get_client","PyHarmony client= " + str(self.client))
        self._set_st(1)
        # Setup activities and devices
        self.init_activities_and_devices()
        self._get_current_activity()
        self.query()
        self.client_status = True
        # Hang around until asked to quit
        self.l_debug('_get_client','Wait until we are told to stop')
        self.event.wait()
        self.l_debug('_get_client','Event is done waiting, Goodbye')

    def check_client(self):
        # Thread is none before we try to start it.
        start_client = False
        if self.thread is None:
            self.l_info("check_client","Waiting for client thread to be created..")
            return False
        else:
            if self.client is None:
                self.l_info("check_client","Client was stopped. client{0}".format(self.client))
                self._set_st(1)
            else:
                # Then client_status will be True when client is ready
                if self.client_status is True:
                    if self.thread.is_alive():
                        if self.client.state.current_state() == 'connected':
                            # All seems good.
                            # If activity method changed from or to a 2 then we need to reconnect to register or unregister the callback
                            if self.last_activity_method != self.parent.activity_method and (self.last_activity_method == 2 or self.parent.activity_method == 2):
                                self.l_info("check_client","Activity method changed from {0} to {1}, need to restart client".format(self.last_activity_method,self.parent.activity_method))
                                self._set_st(0)
                            else:
                                self._set_st(1)
                                return True
                        else:
                            self.l_error("check_client","Client no longer connected. client.state={0}".format(self.client.state.current_state()))
                            self._close_client()
                    else:
                        # Need to restart the thread
                        self.l_error("check_client","Thread is dead, need to restart")
                        self._set_st(0)
                else:
                    if self.thread.is_alive():
                        self.l_info("check_client","Waiting for client startup to complete, status = {0}..".format(self.client_status))
                        return False
                    else:
                        self.l_error("check_client","Client startup thread dead?, Please send log package to developer.  status = {0}..".format(self.client_status))
                        self._set_st(0)
        # If we had a connection issue previously, try to fix it.
        if self.st == 0:
            self.l_debug("check_client","Calling get_client st=%d" % (self.st))
            if not self.get_client():
                return False
        self._set_st(1)
        return True

    def _close_client(self):
        self._set_st(0)
        self.l_debug('_close_client','client={}'.format(self.client))
        if self.client is not None:
            if self.client is False:
                self.l_debug('_close_client','we have no client={}'.format(self.client))
            else:
                try:
                    self.l_debug('_close_client','disconnecting client={}'.format(self.client))
                    self.client.disconnect(send_close=True)
                    self.l_debug('_close_client','disconnected client={}'.format(self.client))
                except:
                    self.l_error("_close_client",'client.disconnect failed',True)
                    return False
                finally:
                    self.client = None
        # Tells the thread to finish
        self.l_debug('_close_client','and finally client={} event={}'.format(self.client,self.event))
        if self.event is not None:
            self.l_debug('_close_client','calling event.set')
            self.event.set()
        self.l_debug('_close_client','returning')
        return True

    def _get_current_activity(self):
        self.l_debug("_get_current_activity",'...')
        if self.check_client():
            try:
                ca = self.client.get_current_activity()
            except IqTimeout:
                self.l_error("_get_current_activity",'client.get_current_activity timeout',False)
                self._close_client()
                return False
            except:
                self.l_error("_get_current_activity",'client.get_current_activity failed',True)
                self._set_st(0)
                return False
            self._set_st(1)
            if int(self.current_activity) != int(ca):
                self.l_debug("_get_current_activity"," poll={0} current={1}".format(ca,self.current_activity))
            self._set_current_activity(ca)
            return True
        else:
            return False

    def _set_st(self, value):
        value = int(value)
        if hasattr(self,'st') and self.st != value:
            self.st = int(value)
            self.l_info("_set_st","setDriver(ST,{0})".format(self.st))
            return self.setDriver('ST', self.st)

    def delete(self):
        """
        Delete all my children and then myself
        """
        LOGGER.warning("%s: Deleting myself and all my children",self.lpfx)
        # We use the list of nodes in the config, not just our added nodes...
        for node in self.controller.poly.config['nodes'].copy():
            address = node['address']
            if node['primary'] == self.address and node['address'] != self.address:
                LOGGER.warning('%s Deleting my child %s "%s"',self.lpfx,address,node['name'])
                self.controller.poly.delNode(address)
        LOGGER.warning('%s Deleting myself',self.lpfx)
        self.controller.poly.delNode(self.address)

    def init_activities_and_devices(self):
        self.l_info("init_activities_and_devices","start")
        self.activity_nodes = dict()
        self.device_nodes = dict()
        #
        # Add all activities except -1 (PowerOff)
        #
        for a in self.harmony_config['activities']:
            if a['id'] != '-1' and self.address in a['hub']:
                try:
                    self.l_info("init","Activity: %s  Id: %s" % (a['label'], a['id']))
                    self.add_activity(str(a['id']),a['label'])
                except:
                    LOGGER.error("%s Error adding activity",self.lpfx,exc_info=True)
        #
        # Add all devices
        #
        for d in self.harmony_config['devices']:
            try:
                self.l_info("init","Device :'%s' Id: '%s'" % (d['label'],d['id']))
                self.add_device(str(d['id']),d['label'])
            except:
                LOGGER.error("%s Error adding device",self.lpfx,exc_info=True)

        self.l_info("init_activities_and_devices","end")

    def add_device(self,number,name):
        # TODO: Pass in name and address as optional args.
        node = self.parent.addNode(HarmonyDevice(self, number, get_valid_node_name(name)))
        self.device_nodes[number] = node
        return node;

    def add_activity(self,number,name):
        node = self.parent.addNode(HarmonyActivity(self, number, get_valid_node_name(name)))
        self.activity_nodes[number] = node
        return node;

    def start_activity(self, id=False, index=False):
        """
        Start the activity
        """
        if index is False and id is False:
            self.l_error("start_activity","Must pass id or index")
            return False
        if index is False:
            index = self._get_activity_index(id)
        elif id is False:
            id = self._get_activity_id(index)
        self.l_debug("start_activity","id=%s index=%s" % (str(id),str(index)))
        if self.client is None:
            self.l_error("start_activity","No Client" )
            ret = False
        else:
            if id != -1:
                ret = self.client.start_activity(id)
                self.l_debug("start_activity","id=%s result=%s" % (str(id),str(ret)))
            else:
                ret = self.client.power_off()
                self.l_debug("start_activity","power_off result=%s" % (str(ret)))
            if ret:
                # it worked, push it back to polyglot
                self._set_current_activity(id)
        return ret

    def end_activity(self, id=False, index=False):
        """
        End the activity
        """
        if self.client is None:
            self.l_error("end_activity","No Client" )
            ret = False
        else:
            # Only way to end, is power_off (activity = -1)
            ret = self.client.power_off()
            # TODO: Currently released version of pyharmony always returns None
            # TODO: remove this if a new version is released.
            ret = True
            self.l_debug("end_activity","ret=%s" % (str(ret)))
            if ret:
                self._set_current_activity(-1)
        return ret

    def _set_all_activities(self,val,ignore_id=False):
        # All other activities are no longer current
        for nid in self.activity_nodes:
            if ignore_id is False:
                self.activity_nodes[nid]._set_st(val)
            else:
                if int(nid) != int(ignore_id):
                    self.activity_nodes[nid]._set_st(val)

    def _get_activity_id(self,index):
        """
        Convert from activity index from nls, to real activity number
        """
        self.l_debug("_get_activity_id"," %d" % (index))
        return self.harmony_config['activities'][index]['id']

    def _get_activity_index(self,id):
        """
        Convert from activity index from nls, to real activity number
        """
        self.l_debug("_get_activity_index", str(id))
        cnt = 0
        for a in self.harmony_config['activities']:
            if int(a['id']) == int(id):
                return cnt
            cnt += 1
        self.l_error("_get_activity_index","No activity id %s found." % (str(id)))
        # Print them out for debug
        for a in self.harmony_config['activities']:
            self.l_error("_get_activity_index","  From: label=%s, id=%s" % (a['label'],a['id']))
        return False

    def change_channel(self,channel):
        self.l_debug("change_channel","channel=%s" % (channel))
        # Push it to the Hub
        if self.client is None:
            self.l_error("change_channel","No Client for channel '%s'." % (channel))
            ret = False
        else:
            try:
                ret = self.client.change_channel(channel)
            except (Exception) as err:
                self.l_error('change_channel','failed {0}'.format(err), True)
                return False
            self.l_debug("change_channel","%s result=%s" % (channel,str(ret)))
            # TODO: This always returns False :(
            ret = True
        return ret

    def _cmd_set_current_activity(self, command):
        """
        This runs when ISY changes the current current activity
        """
        index = int(command.get('value'))
        return self.start_activity(index=index)

    def _cmd_change_channel(self, command):
        """
        This runs when ISY calls set button which passes the button index
        """
        channel = int(command.get('value'))
        self.l_debug("_cmd_change_channel","channel=%d" % (channel))
        return self.change_channel(channel)

    def _cmd_off(self, command):
        """
        This runs when ISY calls Off or Fast Off and sets the activity to poweroff
        """
        self.l_debug("_cmd_off","activity=%d" % (self.current_activity))
        return self.end_activity()

    def _cmd_delete(self, command):
        """
        Delete's this Hub and all it's children from Polyglot
        """
        self.l_debug("_cmd_delete","")
        return self.delete()

    def l_info(self, name, string):
        LOGGER.info("Hub:%s:%s:%s: %s" %  (self.id,self.name,name,string))

    def l_error(self, name, string, exc_info=False):
        LOGGER.error("Hub:%s:%s:%s: %s" % (self.id,self.name,name,string), exc_info=exc_info)

    def l_warning(self, name, string):
        LOGGER.warning("Hub:%s:%s:%s: %s" % (self.id,self.name,name,string))

    def l_debug(self, name, string):
        LOGGER.debug("Hub:%s:%s:%s: %s" % (self.id,self.name,name,string))


    drivers = [
        {'driver': 'ST',  'value': 0, 'uom': 2},  #    bool: Connection status to Hub
        {'driver': 'GV1', 'value': 0, 'uom': 56}, # integer: IP Address
        {'driver': 'GV2', 'value': 0, 'uom': 56}, # integer: Port
        {'driver': 'GV3', 'value': 0, 'uom': 25}, # integer: Current Activity
        {'driver': 'GV4', 'value': 0, 'uom': 56}, #
        {'driver': 'GV5', 'value': 0, 'uom': 56}, #
    ]
    commands = {
        'QUERY': query,
        'SET_ACTIVITY': _cmd_set_current_activity,
        'CHANGE_CHANNEL': _cmd_change_channel,
        'DOF': _cmd_off,
        'DFOF': _cmd_off,
        'DEL': _cmd_delete,
    }

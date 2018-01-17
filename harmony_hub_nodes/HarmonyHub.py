
import polyinterface,sys
from traceback import format_exception
from harmony_hub_nodes import HarmonyDevice,HarmonyActivity
from harmony_hub_funcs import harmony_hub_client,ip2long,long2ip

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
    def __init__(self, parent, address, name, host, port):
        """
        Optional.
        Super runs all the parent class necessities. You do NOT have
        to override the __init__ method, but if you do, you MUST call super.

        :param parent: Reference to the Controller class
        :param address: This nodes address
        :param name: This nodes name
        """
        # The id (node_def_id) is the address because each hub has a unique nodedef in the profile.
        # The id using the original case of the string
        self.id = address
        self.name   = name
        self.host   = host
        self.port   = port
        self.client = None
        self.current_activity = -2
        self.do_poll = True
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
        # Connect to the hub
        #
        self._get_client()
        #
        # Setup activities and devices
        #
        self.init_activities_and_devices()
        #
        # Call query to initialize and pull the info from the hub.
        #
        self.query();
        self.l_info("start","done hub '%s' '%s' %s" % (self.address, self.name, self.host))

    def shortPoll(self):
        # TODO: Poll the hub activity
        #self.l_debug("shortPoll","start")
        # If we had a connection issue previously, try to fix it.
        if self.st == 0:
            self.l_debug("poll","Calling get_client st=%d" % (self.st))
            if not self._get_client():
                return False
        self._get_current_activity()
        return True 
        
    def longPoll(self):
        pass
        
    def query(self):
        """
        Called by ISY to report all drivers for this node. This is done in
        the parent class, so you don't need to override this method unless
        there is a need.
        """
        self.l_debug('query','...')
        self._get_current_activity()
        self.reportDrivers()

    def _get_client(self):
        self.l_info("get_client","Initializing PyHarmony Client")
        try:
            self.client = harmony_hub_client(self.host, self.port)
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            err_str = ''.join(format_exception(exc_type, exc_value, exc_traceback))
            self.l_error("get_client",err_str)
            self._set_st(0)
            return False
        self._set_st(1)
        self.l_info("get_client","PyHarmony client= " + str(self.client))
        return True
    
    def _get_current_activity(self):
        try:
            ca = self.client.get_current_activity()
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            err_str = ''.join(format_exception(exc_type, exc_value, exc_traceback))
            self.l_error("get_current_activity",err_str)
            self._set_st(0)
            return False
        self._set_st(1)
        self.l_debug("poll","client.get_current_activity=%s" % str(ca))
        self._set_current_activity(ca)
        
    def _set_st(self, value):
        self.st = value
        return self.setDriver('ST', value)
    
    def init_activities_and_devices(self):
        self.l_info("init_activities_and_devices","start")
        self.activity_nodes = dict()
        self.device_nodes = dict()
        # TODO: Use parent.harmony_config which conmes from the yaml, or keep using the real one from the hub?
        harmony_config = self.client.get_config()
        #
        # Add all activities except -1 (PowerOff)
        #
        for a in harmony_config['activity']:
            if a['id'] != '-1':
                self.l_info("init","Activity: %s  Id: %s" % (a['label'], a['id']))
                self.add_activity(a['id'],a['label'])
        #
        # Add all devices
        #
        for d in harmony_config['device']:
            self.l_info("init","Device id='%s' name='%s', Type=%s, Manufacturer=%s, Model=%s" % (d['id'],d['label'],d['type'],d['manufacturer'],d['model']))
            self.add_device(d['id'],d['label'])
        self.l_info("init_activities_and_devices","end")
            
    def add_device(self,number,name):
        # TODO: Pass in name and address as optional args.
        node = self.parent.addNode(HarmonyDevice(self, number, name))
        self.device_nodes[number] = node
        return node;

    def add_activity(self,number,name):
        node = self.parent.addNode(HarmonyActivity(self, number, name))
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
        return self.parent.harmony_config['info']['activities'][index]['id']
    
    def _get_activity_index(self,id):
        """
        Convert from activity index from nls, to real activity number
        """
        self.l_debug("_get_activity_index", str(id))
        cnt = 0
        for a in self.parent.harmony_config['info']['activities']:
            if int(a['id']) == int(id):
                return cnt
            cnt += 1
        self.l_error("_get_activity_index","No activity id %s found." % (str(id)))
        # Print them out for debug
        for a in self.parent.harmony_config['info']['activities']:
            self.l_error("_get_activity_index","  From: label=%s, id=%s" % (a['label'],a['id']))
        return False
    
    def change_channel(self,channel):
        self.l_debug("change_channel","channel=%s" % (channel))
        # Push it to the Hub
        if self.client is None:
            self.l_error("change_channel","No Client for channel '%s'." % (channel))
            ret = False
        else:
            ret = self.client.change_channel(channel)
            self.l_debug("change_channel","%s result=%s" % (channel,str(ret)))
            # TODO: This always returns False :(
            ret = True
        return ret

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
        self.setDriver('GV3', index)
        # Make the activity node current, unless it's -1 which is poweroff
        ignore_id=False
        if id != -1:
            self.activity_nodes[str(id)]._set_st(1)
            ignore_id=id
        # Update all the other activities to not be the current.
        self._set_all_activities(0,ignore_id=ignore_id)
        return True

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

    def l_info(self, name, string):
        LOGGER.info("Hub:%s:%s:%s: %s" %  (self.id,self.name,name,string))
        
    def l_error(self, name, string):
        LOGGER.error("Hub:%s:%s:%s: %s" % (self.id,self.name,name,string))
        
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
    }

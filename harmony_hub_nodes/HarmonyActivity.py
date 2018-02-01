
import polyinterface,sys

LOGGER = polyinterface.LOGGER

class HarmonyActivity(polyinterface.Node):
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
    def __init__(self, parent, address, name):
        """
        Optional.
        Super runs all the parent class necessities. You do NOT have
        to override the __init__ method, but if you do, you MUST call super.

        :param parent: Reference to the parent HarmonyHub object
        :param address: This nodes address
        :param name: This nodes name
        """
        # The id (node_def_id) is address because each activiy has a unique nodedef in the profile.
        # The id using the original case of the string.
        self.number = address
        address = "a" + address
        # But here we pass the lowercase, cause ISY doesn't allow the upper case!
        super(HarmonyActivity, self).__init__(parent.controller, parent.address, address.lower(), name)
        #self.name   = name
        #self.address = address
        # Only Hub devices are polled.
        self.do_poll     = False
        # Add myself to the parents list of 

    def start(self):
        """
        Optional.
        This method is run once the Node is successfully added to the ISY
        and we get a return result from Polyglot.
        """
        pass
    
    def query(self):
        """
        Called by ISY to report all drivers for this node. This is done in
        the parent class, so you don't need to override this method unless
        there is a need.
        """
        self._set_st(self.st)
        return True

    def _set_st(self, st):
        self.st = st
        self.setDriver('ST',int(st))
        self.l_debug("_set_st","set=%s, get=%s" % (st,self.getDriver('ST')))
        
    def _cmd_on(self, command):
        """ 
        This runs when ISY calls on button
        """
        self.l_debug("_cmd_on","")
        # Push it to the Hub
        ret = self.primary.start_activity(id=self.number)
        self.l_debug("_cmd_on","ret=%s" % (str(ret)))
        if ret:
            self._set_st(1)
        return ret

    def _cmd_off(self, command):
        """ 
        This runs when ISY calls off/fast off button
        """
        self.l_debug("_cmd_off","")
        # Push it to the Hub
        ret = self.primary.end_activity(id=self.number)
        self.l_debug("_cmd_off","ret=%s" % (str(ret)))
        if ret:
            self._set_st(0)
        return ret

    def l_info(self, name, string):
        LOGGER.info("Activity:%s:%s:%s: %s" %  (self.address,self.name,name,string))
        
    def l_error(self, name, string):
        LOGGER.error("Activity:%s:%s:%s: %s" % (self.address,self.name,name,string))
        
    def l_warning(self, name, string):
        LOGGER.warning("Activity:%s:%s:%s: %s" % (self.address,self.name,name,string))
        
    def l_debug(self, name, string):
        LOGGER.debug("Activity:%s:%s:%s: %s" % (self.address,self.name,name,string))

    id = 'HarmonyActivity'
    drivers = [
        {'driver': 'ST',  'value': 0, 'uom': 2},  #    bool: Activity Status
    ]
    commands = {
        'QUERY': query,
        'DON': _cmd_on,
        'DOF': _cmd_off,
        'DFON': _cmd_on,
        'DFOF': _cmd_off,
    }

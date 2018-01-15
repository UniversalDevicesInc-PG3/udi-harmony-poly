
import polyinterface

class HarmonyDevice(polyinterface.Node):
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

        :param controller: Reference to the controller object
        :param parent: Reference to the parent HarmonyHub object
        :param address: This nodes address
        :param name: This nodes name
        """
        # The id (node_def_id) is the address because each hub has a unique nodedef in the profile.
        address = "d" + address
        self.id = address
        super(HarmonyDevice, self).__init__(parent.controller, parent.address, address, name)
        #self.name    = name
        #self.address = address
        #self.parent  = parent
        # Only Hub devices are polled.
        self.do_poll     = False

    def start(self):
        """
        Optional.
        This method is run once the Node is successfully added to the ISY
        and we get a return result from Polyglot.
        """
        self.setDriver('ST', 1)

    def setOn(self, command):
        """
        Example command received from ISY.
        Set DON on MyNode.
        Sets the ST (status) driver to 1 or 'True'
        """
        self.setDriver('ST', 1)

    def setOff(self, command):
        """
        Example command received from ISY.
        Set DOF on MyNode
        Sets the ST (status) driver to 0 or 'False'
        """
        self.setDriver('ST', 0)

    def query(self):
        """
        Called by ISY to report all drivers for this node. This is done in
        the parent class, so you don't need to override this method unless
        there is a need.
        """
        self.reportDrivers()

    def l_info(self, name, string):
        LOGGER.info("Device:%s:%s: %s" %  (self.id,name,string))
        
    def l_error(self, name, string):
        LOGGER.error("Device:%s:%s: %s" % (self.id,name,string))
        
    def l_warning(self, name, string):
        LOGGER.warning("Device:%s:%s: %s" % (self.id,name,string))
        
    def l_debug(self, name, string):
        LOGGER.debug("Device:%s:%s: %s" % (self.id,name,string))

    def _get_button_label(self,index):
        """
        Convert from button/function index from nls to real label
        because pyharmony needs the label.
        """
        self.l_debug("_get_button_label","index=%d" % (index))
        # TODO: Make sure it's a valid index?
        return self.parent.poly.nodeserver_config['info']['functions'][index]['label']

    def _get_button_command(self,index):
        """
        Convert from button/function index from nls to real label
        because pyharmony needs the label.
        """
        self.l_debug("_get_button_command","index=%d" % (index))
        # TODO: Make sure it's a valid index?
        return self.parent.poly.nodeserver_config['info']['functions'][index]['command'][self.id]

    def _send_command_by_index(self,index):
        name = self._get_button_command(index)
        self.l_debug("_send_command_by_index","index=%d, name=%s" % (index,name))
        return self._send_command(name)

    def _send_command(self,name):
        self.l_debug("_send_command","name=%s" % (name))
        # Push it to the Hub
        if self.primary.client is None:
            self.l_error("_send_command","No Client for command '%s'." % (name))
            ret = False
        else:
            ret = self.primary.client.send_command(self.id,name)
            self.l_debug("_send_command","%s,%s result=%s" % (str(self.id),name,str(ret)))
            # TODO: This always returns None :(
            ret = True
        return ret

    def _cmd_set_button(self, **kwargs):
        """ 
        This runs when ISY calls set button which passes the button index
        """
        index = myint(kwargs.get("value"))
        self.l_debug("_cmd_set_button","index=%d" % (index))
        return self._send_command_by_index(index)
    
    def _cmd_don(self, **kwargs):
        """ 
        This runs when ISY calls set button which passes the button index
        """
        self.l_debug("_cmd_don","")
        # TODO: If no PowerOn command, do PowerToggle
        return self._send_command('PowerOn')
    
    def _cmd_dof(self, **kwargs):
        """ 
        This runs when ISY calls set button which passes the button index
        """
        self.l_debug("_cmd_dof","")
        # TODO: If no PowerOn command, do PowerToggle
        return self._send_command('PowerOff')

    drivers = [{'driver': 'ST', 'value': 0, 'uom': 2}]
    id = 'HarmonyDevice'
    commands = {
        'SET_BUTTON': _cmd_set_button,
        'DON': _cmd_don,
        'DOF': _cmd_dof,
    }

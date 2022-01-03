
from udi_interface import Node,LOGGER

class Device(Node):
    def __init__(self, parent, address, name):
        # The id (node_def_id) is the address because each hub has a unique nodedef in the profile.
        self.did = address
        address = "d" + address
        self.id = address
        self.parent = parent
        super(Device, self).__init__(parent.controller.poly, parent.address, address, name)
        #self.name    = name
        #self.address = address
        self.hub  = parent
        # Only Hub devices are polled.
        self.do_poll     = False
        parent.controller.poly.subscribe(parent.controller.poly.START, self.handler_start, address) 

    def handler_start(self):
        self.setDriver('ST', 1)

    def setOn(self, command):
        self.setDriver('ST', 1)

    def setOff(self, command):
        self.setDriver('ST', 0)

    def query(self):
        self.reportDrivers()

    def _get_button_label(self,index):
        """
        Convert from button/function index from nls to real label
        because pyharmony needs the label.
        """
        LOGGER.debug("index=%d" % (index))
        # TODO: Make sure it's a valid index?
        return self.parent.harmony_config['info']['functions'][index]['label']

    def _get_button_command(self,index):
        """
        Convert from button/function index from nls to real label
        because pyharmony needs the label.
        """
        LOGGER.debug("index=%d" % (index))
        if index <= len(self.parent.harmony_config['info']['functions']):
            if not self.did in self.parent.harmony_config['info']['functions'][index]['command']:
                LOGGER.debug("This device id={0} not in command hash = {1}".format(self.did,self.parent.harmony_config['info']['functions'][index]['command']))
                return False
            command = self.parent.harmony_config['info']['functions'][index]['command'][self.did]
            LOGGER.debug("command=%s" % (command))
            return command
        else:
            LOGGER.debug("index={0} is not in functions len={1}: {2}".format(index,len(self.parent.harmony_config['info']['functions']),self.parent.harmony_config['info']['functions']))
            return False

    def _send_command_by_index(self,index):
        LOGGER.debug("index=%d" % (index))
        name = self._get_button_command(index)
        if name is False:
            LOGGER.debug("No name for index %d" % (index))
            return False
        LOGGER.debug("index=%d, name=%s" % (index,name))
        return self._send_command(name)

    def _send_command(self,name):
        LOGGER.debug("name=%s" % (name))
        # Push it to the Hub
        if self.hub.client is None:
            LOGGER.debug("No Client for command '%s'." % (name))
            ret = False
        else:
            ret = self.hub.client.send_command(self.did,name)
            LOGGER.debug("%s,%s result=%s" % (str(self.did),name,str(ret)))
            # TODO: This always returns None :(
            ret = True
        return ret

    def _cmd_set_button(self, command):
        """
        This runs when ISY calls set button which passes the button index
        """
        index = int(command.get('value'))
        LOGGER.debug("index=%d" % (index))
        return self._send_command_by_index(index)

    def _cmd_don(self, command):
        """
        This runs when ISY calls set button which passes the button index
        """
        LOGGER.debug("")
        # TODO: If no PowerOn command, do PowerToggle
        return self._send_command('PowerOn')

    def _cmd_dof(self, command):
        """
        This runs when ISY calls set button which passes the button index
        """
        LOGGER.debug("")
        # TODO: If no PowerOn command, do PowerToggle
        return self._send_command('PowerOff')

    drivers = [{'driver': 'ST', 'value': 0, 'uom': 2}]
    id = 'HarmonyDevice'
    commands = {
        'SET_BUTTON': _cmd_set_button,
        'DON': _cmd_don,
        'DOF': _cmd_dof,
    }

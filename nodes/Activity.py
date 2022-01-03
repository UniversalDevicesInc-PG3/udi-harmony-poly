

from udi_interface import Node,LOGGER

class Activity(Node):

    def __init__(self, parent, address, name):
        # The id (node_def_id) is address because each activiy has a unique nodedef in the profile.
        # The id using the original case of the string.
        self.parent = parent
        self.number = address
        address = "a" + address
        # But here we pass the lowercase, cause ISY doesn't allow the upper case!
        super(Activity, self).__init__(parent.controller.poly, parent.address, address.lower(), name)
        LOGGER.info("Activity")
        #self.name   = name
        #self.address = address
        # Only Hub devices are polled.
        self.do_poll     = False
        self.st = 0
        self.startup     = True
        parent.controller.poly.subscribe(parent.controller.poly.START,  self.handler_start, address.lower()) 

    def handler_start(self):
        self.query()

    def query(self):
        self._set_st(self.st)
        self.startup = False
        return True

    def _set_st(self, st):
        st = int(st)
        # Don't change on startup when self.st=-1
        if not self.startup and st != self.st:
            if st == 0:
                self.reportCmd("DOF",2)
            else:
                self.reportCmd("DON",2)
        self.setDriver('ST',st)
        self.st = int(st)
        LOGGER.debug("set=%s, get=%s" % (st,self.getDriver('ST')))

    def _cmd_on(self, command):
        """
        This runs when ISY calls on button
        """
        LOGGER.debug("")
        # Push it to the Hub
        ret = self.parent.start_activity(id=self.number)
        LOGGER.debug("ret=%s" % (str(ret)))
        if ret:
            self._set_st(1)
        return ret

    def _cmd_off(self, command):
        """
        This runs when ISY calls off/fast off button
        """
        LOGGER.debug("")
        # Push it to the Hub
        ret = self.parent.end_activity(id=self.number)
        LOGGER.debug("ret=%s" % (str(ret)))
        if ret:
            self._set_st(0)
            self.reportCmd("DOF",2)
        return ret

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

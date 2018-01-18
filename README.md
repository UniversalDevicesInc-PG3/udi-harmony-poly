# harmony-polyglot

This is the Harmony Hub Poly for the [Universal Devices ISY994i](https://www.universal-devices.com/residential/ISY) [Polyglot interface](http://www.universal-devices.com/developers/polyglot/docs/) with  [Polyglot V2](https://github.com/Einstein42/udi-polyglotv2)
(c) JimBoCA aka Jim Searle
MIT license. 

This node server is intended to support the [Logitech Harmony Hub](http://www.logitech.com/en-us/product/harmony-hub) using the [pyharmony Python Library](https://pypi.python.org/pypi/pyharmony).

## Installation

WARNING: If you are running the v1 polyglot harmony nodeserver it will not longer work after this one is installed.  But, initially I would advise everyone to install this in a new slot and leave the old one running.  If you go back to the old one you will need manually re-install the older version of pyharmony if you have polyglot v1 and v2 running on the same machine.

1. Backup Your ISY in case of problems!
   * Really, do the backup, please
2. Go to the Polyglot Store in the UI and install.
3. Add NodeServer in Polyglot Web
   * After the install completes, Polyglot will reboot your ISY, you can watch the status in the main polyglot log.
4. Once your ISY is back up open the Admin Console and you should see a new node 'HarmonyController'
   * If you don't see that node, then restart the Harmony node server from the Polyglot UI.
6. The auto-discover should automatically run and find your hubs and add them.  Verify by checkig the nodeserver log.  If it doesn't then Select the HarmonyController node and click the 'Discover'.
   * While this is running you can view the nodeserver log in the Polyglot UI to see what it's doing
7. This should find your Harmony Hubs and add them to the ISY with all devices and activities
8. Once all nodes are added you will need to reboot the ISY again since the new custom profile is loaded.

### Manual Hub Entries

If the discover does not work, or you prefer to not use it, you can add customParms in the Polyglot Web UI
to tell it about your hubs.

Create a param with the name 'hub_myhubaddress' with a value: { "name": "HarmonyHub FamilyRoom", "host": "192.168.1.86" }

## Requirements

* This has only been tested with ISY 5.0.11B so it is not garunteed to work with any other version.

# Release Notes

- 2.0.0
  - Not offically released

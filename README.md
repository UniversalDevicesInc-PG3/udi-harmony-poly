
[![Build Status](https://travis-ci.org/jimboca/udi-harmony-poly.svg?branch=master)](https://travis-ci.org/jimboca/udi-harmony-poly)

# harmony-polyglot

This is the Harmony Hub Poly for the [Universal Devices ISY994i](https://www.universal-devices.com/residential/ISY) [Polyglot interface](http://www.universal-devices.com/developers/polyglot/docs/) with  [Polyglot V2](https://github.com/Einstein42/udi-polyglotv2)
(c) JimBoCA aka Jim Searle
MIT license.

This node server is intended to support the [Logitech Harmony Hub](http://www.logitech.com/en-us/product/harmony-hub) using the [pyharmony Python Library](https://pypi.python.org/pypi/pyharmony).

## Installation

IMPORTANT: The latest harmony hub firmware broke access, you must manually enable xmpp for each hub in the Harmony App:  https://community.logitech.com/s/question/0D55A00008D4bZ4SAJ/harmony-hub-firmware-update-fixes-vulnerabilities
  - Connect to one of your Hubs in the Harmony App
  - Select Menu -> Harmony Setup -> Add/Edit Devices & Activities
  - Select Remote & Hub -> Enable XMPP
  - Do this for every hub.

WARNING: If you are running the v1 polyglot harmony nodeserver it will not longer work after this one is installed.  But, initially I would advise everyone to install this in a new slot and leave the old one running.  If you go back to the old one you will need manually re-install the older version of pyharmony if you have polyglot v1 and v2 running on the same machine.

1. Make sure your Harmony Hubs have a static IP assigned.  The nodeserver can not re-find the hub if it changes IP addresses.  This may be fixed in the future.
2. Backup Your ISY in case of problems!
   * Really, do the backup, please
3. Go to the Polyglot Store in the UI and install.
4. Add NodeServer in Polyglot Web
5. Open the admin console (close and re-open if you had it open) and you should see a new node 'HarmonyController'
6. The auto-discover should automatically run and find your hubs and add them.  Verify by checking the nodeserver log.  If it doesn't then Select the HarmonyController node and click the 'Discover'.
   * While this is running you can view the nodeserver log in the Polyglot UI to see what it's doing
7. This should find your Harmony Hubs and add them to the ISY with all devices and activities if your Harmony Hub and Polyglot are on the same subnet.  If they are not, then you can manually add the hub address as described in the next section,
8. Once all nodes are added you will need to close and re-open the admin console the new custom profile is loaded.

### Manual Hub Entries

If the discover does not work, or you prefer to not use it, you can add customParms in the Polyglot Web UI
to tell it about your hubs.

Create a param with the name 'hub_uniqueid' where uniqueid is the address that will be used for the ISY node, and with a value like: { "name": "HarmonyHub FamilyRoom", "host": "192.168.1.86" }

Anytime these params are added or modified you need to run the 'Discover' on the HarmonyController node.

## Grouping the hubs

Each activity and device is created with their Hub as primary.  This makes it easy to group the devices.  Just right click on a Hub, Activity or Device node and select 'group devices'.  This makes it easy to keep them all together.

## HarmonyHub Controller

This is the main node created by this nodeserver and manages the hubs.

### Node Settings
The settings for this node are

#### Node Server Connected
   * Status of nodeserver process, this should be monitored by a program if you want to know the status
   * There is a known issue in Polyglot that upon startup, this is not always properly set.
#### Version Major
   * The major version of this nodeserver
#### Version Minor
   * The minor version of this nodeserver
#### Hubs
   * The number of hubs currently managed
#### Debug Mode
   * The debug printing mode
#### Short Poll
   * This is how often it will Poll the Hub to get the current activity
#### Long Poll
   * Not currently used
#### Profile Status
   * This is updated during commands like Discover,Install Profile, and Build Profile to show what is currently happening
      * Uninitialized = This can only happen if the node server is installed, but never ran
      * Not Sure = Can't be sure what the status is.  Currently we can not read the profile version.  Hopefully this will be added in the future
      * Discovering Hubs
      * Adding Nodes
      * Building Profile
      * Installing Profile
      * ISY Reboot Required
         * The nodeserver thinks your ISY needs rebooted.  This means a new profile was installed on the ISY, but currently we can't tell if the ISY has been rebooted, so reboot the node server after rebooting the ISY to clear this status
      * Build Profile Failed
      * Install Profile Failed
      * PyHarmony Discover Failed
      * Out of Date
      * Write profile.zip Failed
#### Activity Method
   * None = Don't watch Harmony for activity changes
   * Short Poll = Poll Harmony Hub during each Short Poll Interval (Old default method)
   * Callback = The Harmony Hub reports changes directly to the nodeserver (prefered new method)
#### Watch Hubs
  * Enable/Disable watching the hubs.  If you know the hubs will be offline for a long time then set this False. I use this because I know when the power is turned off to the hub when I am not going to be home for an extended period of time.

### Node Commands

The commands for this node

#### Query
   * Poll's all hubs and sets all status in the ISY
#### Discover
   * Run's the harmony auto-discover to find your hubs, builds the profiel, and installs the profile
   * This should be run whenever you add a new hub, or update activities or devices on your hub
#### Install Profile
   * This uploads the currently built profile into the ISY.
   * Typically this is not necessary, but sometimes the ISY needs the profile uploaded twice.
#### Build Profile
   * This rebuilds the profile based on the currently managed hubs.
   * During the processes you can watch the nodeserver log (Not the polyglot log) to see what it's doing.
   * It will also update the 'Profile Status' to show what is happening from:
      * Building Profile
      * Installing Profile
      * ISY Reboot Required
   * Once it says ISY Reboot Required you should reboot the ISY.

## Harmony Hub

Each harmony hub found are configured will have a node.

## Harmony Activity

Each harmony hub activity will have a node.

## Harmony Hub

Each harmony hub device will have a node.

## Requirements

1. Polyglot V2 itself should be run on Raspian Stretch.
  To check your version, ```cat /etc/os-release``` and the first line should look like
  ```PRETTY_NAME="Raspbian GNU/Linux 9 (stretch)"```. It is possible to upgrade from Jessie to
  Stretch, but I would recommend just reimaging the SD card.  Some helpful links:
   * https://www.raspberrypi.org/blog/raspbian-stretch/
   * https://linuxconfig.org/raspbian-gnu-linux-upgrade-from-jessie-to-raspbian-stretch-9
1. This has only been tested with ISY 5.0.11 so it is not guaranteed to work with any other version.

# Issues

If you have an issue where the nodes are not showing up properly, open the Polyglot UI and go to HarmonyHub -> Details -> Log, and clock 'Download Log Package' and send that to jimboca3@gmail.com as an email attachment, or send it in a PM [Universal Devices Forum](https://forum.universal-devices.com/messenger)

# Upgrading

Open the Polyglot web page, go to nodeserver store and click "Update" for "HarmonyHub".

For Polyglot 2.0.35, hit "Cancel" in the update window so the profile will not be updated and ISY rebooted.  The install procedure will properly handle this for you.  This will change with 2.0.36, for that version you will always say "No" and let the install procedure handle it for you as well.

Then restart the HarmonyHub nodeserver by selecting it in the Polyglot dashboard and select Control -> Restart, then watch the log to make sure everything goes well.

The HarmonyHub keeps track of the version number and when a profile rebuild is necessary.  The profile/version.txt will contain the HarmonyHub profile_version which is updated in server.json when the profile should be rebuilt.  You can see the HarmonyHub version number used to rebuild the profile by checking the HarmonyHub Controller node title in the Admin Console which will contain the code version number, this can be newer than the profile_version number.

# Release Notes
- 2.3.0 04/10/2020
  - [Activity and/or Devices orders are not remembered when new ones are added](https://github.com/jimboca/udi-harmony-poly/issues/23)
- 2.2.12: 04/09/2020
  - Fix crash when discover failed to find a hub
  - Fix duplicate Functions that cause problem LG TV's
- 2.2.11: 02/01/2020
   - Fixed syntax error
- 2.2.10: 01/29/2020
  - Fixed bug when user custom config data is not properly parsed
- 2.2.9: 12/08/2019
  - Move config files into config directory so they will be included in backup thru persist_folder
- 2.2.8: 12/02/2019
  - Unique requirements_polisy.txt
- 2.2.7: 12/01/2019
  - Add missing netifaces to requirements.txt
- 2.2.6: 12/01/2019
  - Fix pyharmony to work on PolyIsy which it currently pulls from my github
- 2.2.5: 10/16/2019
  - Change pyaml to SafeLoader from FullLoader since latest pyaml is not available for all.
- 2.2.4: 09/22/2019
  - Remove version requirement on pyaml so latest gets installed
- 2.2.3: 09/09/2019
  - Try to fix issue with restart when new profile is installed.  Not fully tested...
- 2.2.2: 09/06/2019
  - Fix yaml.load depracation warning
  - Ignore sleekxmpp unclosed socket warnings
- 2.2.1 07/09/2019
  - Fix bug which tried to restart nodes that didn't exist yet when profile was built using custom params.
- 2.2.0 04/06/2019
  - Recover properly from a non responsive hub.  It will be polled on longPoll and reconnect when it's back
  - Added Watch Hubs setting which can be disabled when all hubs are down for an extended period of time
    Profile will be rebuilt on restart, so must restart admin console to see
- 2.1.27 03/31/2019
  - [Send DON/DOF when an Activity is turned on or off](https://github.com/jimboca/udi-harmony-poly/issues/19 )
- 2.1.26 03/31/2019
  - Fix issue where Current Activity would be -1 after startup until a query was run or activity was changed
  - [Nodeserver should used saved profile data](https://github.com/jimboca/udi-harmony-poly/issues/11)
  - [Build Profile doesn't add new devices or activities](https://github.com/jimboca/udi-harmony-poly/issues/16)
  - [device id=xx not in command hash](https://github.com/jimboca/udi-harmony-poly/issues/18)
- 2.1.25 02/20/2019
  - Might have finally fixed issue with not properly closing and reconnecting when there is a connection issue.
- 2.1.24 02/03/2019
  - Add note about unsupported firmware version 4.15.206
- 2.1.23 02/03/2019
  - Attempt to skip hubs with firmware that doesn't support xmpp
- 2.1.22 01/24/2019
  - More debug when get_client event should exit
- 2.1.21 12/27/2018
  - Added debugging for close client issues
- 2.1.20 11/28/2018
  - Fix bug with Activity st not being initialized.
- 2.1.19 09/16/2018
  - Added heartbeat DON/DOF
- 2.1.18 08/29/2018
  - Fix requirements to not include zip since it was causing pip3 errors, and shouldn't be required.
- 2.1.17 07/06/2018
  - Fix issue with button order for creating condensed editor index for buttons for when a button is duplicated.
- 2.1.16 06/06/2018
  - Fix issue with st not defined when initial startup fails to connect to hub
- 2.1.15 05/22/2018
  - Fix Hub Responding ST driver to initialize properly. For sure this time?
- 2.1.14 05/21/2018
    - Fix Hub Responding ST driver to initialize properly.
- 2.1.13 05/20/2018
  - Adding fix for crashing when hub timeout occurs since PyHarmony now traps it correctly. https://github.com/jimboca/udi-harmony-poly/issues/12
- 2.1.12 05/06/2018
  - Fix crashing when hub timeout occurs since PyHarmony now traps it correctly. https://github.com/jimboca/udi-harmony-poly/issues/12
  - Initialize ST properly on startup and restart https://github.com/jimboca/udi-harmony-poly/issues/13
  - Show hub name for activity in log https://github.com/jimboca/udi-harmony-poly/issues/10
- 2.1.11 03/01/2018
  - Trap change channel timeouts
- 2.1.10 02/28/2018
  - Fix syntax error created in previous release
- 2.1.9 02/27/2018
    - Print error for unknown command name instead of crashing
- 2.1.8 02/11/2018
   - Minor profile fixes
- 2.1.7 02/03/2018
   - Properly fixed escaped / in Harmony Function so it doesn't break other escaped functions.
   - Fix error message for non-existant profile on initial install
   - Allow using latest pyharmony 1.0.20
- 2.1.6 02/01/2018
   - Fixed Start/End on an activity node https://github.com/jimboca/udi-harmony-poly/issues/7
- 2.1.5 01/30/2018
   - Fix call to write_profile.py in install.sh.  No need to upgrade if you are on 2.1.4. This only affects new installs.
- 2.1.4 01/27/2018
   - All pyharmony interface code is run in a seperate thread to avoid timeouts in Polyglot
   - Fixed Debug mode so it actually works.
- 2.1.3 01/25/2018
   - Remove auto-rebuilding of profile since it was killing the polyglot mqtt processs, which was causing DB updates to be lost.  Will re-enable when we figure out what the issue is.
- 2.1.1 01/24/2018
   - Last minute change in 2.1.0 caused profile.zip to no longer be written out.
   - If you already installed 2.1.0 please run build profile again, and reboot
   - If you haven't then please read instructions below.
- 2.1.0 01/24/2018
   - When updating the node server, click cancel so the ISY will not be rebooted, it will need to be rebooted after restarting the nodeserver.
   - Added new [Activity Method setting](https://github.com/jimboca/udi-harmony-poly/blob/master/README.md#activity-method).  Setting this to Callback should greatly stop or greatly reduce the chances of errors caused by constantly polling the hubs for current activity, and activities are updated almost instantaneously!  
   - The list of hubs is stored in hubs.json so the profile can be updated at install time.
   - All versions after this will automatically update the profile when necessary at install time. For this version when you restart the nodeserver it will rebuild the profile automatically and you will need to restart the ISY when it shows Profile Status = ISY Reboot Required
- 2.0.8 01/21/2018
   - Turn on more debug logging for pyharmony
   - Start code reorg to in preparation for move to storing known hubs in local file instead of customParams
- 2.0.7 01/21/2018
   - Fix issue with hub defined in custom params https://github.com/jimboca/udi-harmony-poly/issues/6
- 2.0.6 01/20/2018
   - Trap issues in write_profile when it fails https://github.com/jimboca/udi-harmony-poly/issues/5
- 2.0.5 01/20/2018
   - Fixed initialzation of Auto Discover mode.
- 2.0.4 01/20/2018
   - https://github.com/jimboca/udi-harmony-poly/issues/4
- 2.0.3 01/20/2018
   - profile.zip is not longer in github, renamed to profile_default.zip to avoid conflicts on update.
- 2.0.2 01/19/2018
   - Fixed Intialization of hub params
   - Allow auto-discover mode to be turned off in case it's ever needed
   - A lot of documentation added please review.
- 2.0.1 01/18/2018
   - First announced release
- 2.0.0 01/17/2018
   - Not offically released

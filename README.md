
[![Build Status](https://travis-ci.org/jimboca/udi-harmony-poly.svg?branch=master)](https://travis-ci.org/jimboca/udi-harmony-poly)

# UDI Polyglot V3 Harmony Hub Nodeserver

This is the Harmony Hub Poly for the [Universal Devices Polisy](https://www.universal-devices.com) with Polyglot Version 3 (PG3)
(c) JimBoCA aka Jim Searle
MIT license.

This node server is intended to support the [Logitech Harmony Hub](http://www.logitech.com/en-us/product/harmony-hub) using the [pyharmony Python Library](https://pypi.python.org/pypi/pyharmony).

## Help

If you have any issues are questions you can ask on [PG3 Harmony Hub SubForum](https://forum.universal-devices.com/forum/311-harmonyhub/) or report an issue at [PG3 HarmonyHub Github issues](https://github.com/UniversalDevicesInc-PG3/udi-harmony-poly/issues).

## Moving from PG2

Make sure your PG3 version is at least 3.0.38

There are a few ways to move

### Backup and Restore

The best way to move from PG2 to PG3 is to backup on PG2 and restore on PG3, but the only option is to do all your nodeservers at once.  I don't have much information on this method, if you have questions please ask on the PG3 forum.

### Delete and add

If you can't or don't want backup/restore then you can delete the NS on PG2 and install on the same slot on PG2.  This may cause all the node addresses to change because of the way Harmony stores the id that we reference, so you will have to review all your programs to make sure they still work.  If the nodes are in a scene you will have to add them back.  But if the node address do not change, all your programs should work after doing an update and save on each one, or rebooting the ISY, especially any using the Controller node since it's ST value has changed.  If the node addresses changed you will see the program as information about the unknown node to help you put it back the way it was.

#### Manually copy data

IF doing the delete and add, and you are a little UNIX savy, something like this should copy from PG2 to PG3 on the same Polisy, where UUID is your Polisy UUID and S# is the slot number.
- Install the nodeserver
- Once it completes the startup, stop it
- Log into the Polisy with your favorite terminal program
- cd /var/polyglot/pg3/ns/UUID_S#
- sudo -u polyglot rm -rf config
- sudo -u polyglot cp -r /var/polyglot/nodeservers/HarmonyHub/config .
  - If PG2 is on another machine you can use scp instaed
- Restart the NS
- Open Admin Console and enable 

I have not tried this but it should work.  If you have issues please ask on the sub-forum.  Now that I think about it, I could have the nodeserver automatically do this if they are on the same machine.

### Add then delete

Another option is to install in a new slot then go edit all your programs and scenes that reference the nodes and switch to the new slots. 

## Installation

IMPORTANT: The latest harmony hub firmware broke access, you must manually enable xmpp for each hub in the Harmony App:  https://community.logitech.com/s/question/0D55A00008D4bZ4SAJ/harmony-hub-firmware-update-fixes-vulnerabilities
  - Connect to one of your Hubs in the Harmony App
  - Select Menu -> Harmony Setup -> Add/Edit Devices & Activities
  - Select Remote & Hub -> Enable XMPP
  - Do this for every hub.

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
#### Purge Check / Purge Execute
   * Check only does Checking, and Execute actually will delete them.
   * Deletes old Hubs and their Activities and Devices from Polyglot and the ISY that are no longer in the Harmony configuration
   * Please backup your ISY before running this in case there is an issue.
#### Install Profile
   * This uploads the currently built profile into the ISY.
   * Typically this is not necessary, but sometimes the ISY needs the profile uploaded twice.
#### Update Profile
  * This rebuilds the profile based on currently known hubs
  * Runs Install Profile
  * Typically this is not necessary, but sometimes the ISY needs the profile uploaded twice.
#### Build Profile
   * Scans network for hubs
   * Runs Update Profile
   * During the processes you can watch the nodeserver log (Not the polyglot log) to see what it's doing.
   * It will also update the 'Profile Status' to show what is happening from:
      * Building Profile
      * Installing Profile
      * Installed

Whenever the profile is updated you must close and re-open the Admin Console to see the changes

## Harmony Hub

Each harmony hub found are configured will have a node.

### Node Commands

The command for this Nodes

#### Query
  * Polls the hub and sets status in the ISY
#### Power Off / Fast Off
  * Runs hub power off activity
#### Delete Hub
  * Deletes the hub along with it's Activities and Devices from Polyglot and the ISY

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

Open the Polyglot web page, go to nodeserver page and restart.

The HarmonyHub keeps track of the version number and when a profile rebuild is necessary.  The profile/version.txt will contain the HarmonyHub profile_version which is updated in server.json when the profile should be rebuilt.  You can see the HarmonyHub version number used to rebuild the profile by checking the HarmonyHub Controller node title in the Admin Console which will contain the code version number, this can be newer than the profile_version number.

# Release Notes

Please create a **backup** of your **ISY AND Polyglot** before doing any upgrades in case there are issues.

- 3.0.4: 02/25/2022
  - [Renamed Activities don't show up on ISY](https://github.com/UniversalDevicesInc-PG3/udi-harmony-poly/issues/35)
    - Issue is fixed, but must still delete the node in PG3 UI, then "Build Profile"
  - [Purge Commands broken](https://github.com/UniversalDevicesInc-PG3/udi-harmony-poly/issues/33)
- 3.0.3: 01/17/2022
  - Removed config from zip file
- 3.0.2: 01/13/2022
  - Fix add notice calls in Purge
- 3.0.1: 01/03/2022
  - First real PG3 release
- 2.4.4 12/07/2020
  - Fix crash when using Manual Hub Entries in Configuration
- 2.4.3 04/17/2020
  - Fix crash on new installs
- 2.4.2 04/14/2020
  - Fix crash caused by write permission failed on config file.
- 2.4.1 04/13/2020
  - Keep track of hubs as well because Hub UUID's come back different now, and the node address is based on that UUID, so we keep the same address and record that the uuid changed in config/hubs.json as long as the Hub Name is the same.
    - This only happens during discover, and you will see the message like "Seems that hub '%s' uuid changed ..." if you that message can you please PM it to me along with the Polyglot Backup file so I can take a look.  
- 2.4.0 04/13/2020
  - [Delete devices that no longer exist](https://github.com/jimboca/udi-harmony-poly/issues/22)
    - After discover completes, or by selecting "Purge Check" on the controller it will check for hubs, activities and devices that are no longer in the configurations
    - Will display notices on the polyglot page of things that can be deleted
    - To actually delete them select the "Purge Execute" command on the HarmonyHub Controller Node.
  - Now requires polyinterface 2.0.40 which should be updated on install
  - Modified locally stored config file so nodeserver no longer loads the large hub config file which makes it startup a lot faster, and use less memory.
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

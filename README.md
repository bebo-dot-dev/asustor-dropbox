# asustor-dropbox
An Asustor NAS community open source version of a dropbox API v2 sync app

![Screenshot 1](https://github.com/jjssoftware/asustor-dropbox/blob/master/screenshots/Screenshot%202016-10-16%2015:52:34.png)

![Screenshot 2](https://github.com/jjssoftware/asustor-dropbox/blob/master/screenshots/Screenshot%202016-10-16%2015:53:32.png)

### Why bother?
I couldn't get the [Asustor provided dropbox app](http://forum.asustor.com/viewforum.php?f=59) reliably and safely working. The full story is here: http://forum.asustor.com/viewtopic.php?f=59&t=8202

### What does this do?
This app supports syncing with dropbox in one of the following modes: upload, download, full 2 way sync. Thanks go to the dropbox team / dropbox python sdk maintainers for the original supplied [updown.py sample](https://github.com/dropbox/dropbox-sdk-python/blob/master/example/updown.py)

### How do I set this thing up?
This app can be easily installed via the ADM App Central manual install feature using one of the [pre-compiled apk package release files](/../../releases). There is no UI at the present time so once installed, some manual configuration is required. Read [the setup guide](setup.md) for details.

### Is this app available for install directly in Asustor App Central?
Not yet. This app hasn't been submitted to Asustor to go through their approval process. I'm not sure how they'd feel about this app given it's a direct parallel to their own dropbox app. If someone wants to take on this crusade feel free.

### I don't trust pre-compiled .apk packages - what can I do?
The [pre-compiled apk packages](/../../releases) published in the release page are basically just a thin wrapper around the [updown.py python script](/bin/updown.py) included in this project. These .apk packages are created with the [Asustor apkg tool](http://developer.asustor.com/document/APKG_Utilities_2.0.zip). If you're not sure about trusting what's inside these packages there are a couple of things you can do:

1. .apk package files can be unzipped for review with any decent tool that supports compressed zip files. 
2. You can review the contents of the [updown.py python script](/bin/updown.py) to satisfy yourself that it's safe for use on your NAS box and once you're happy you can then [register](http://developer.asustor.com/user/registration) for an Asustor developer account so you read the docs to learn about how to compile your own .apk package with the [Asustor apkg tool](http://developer.asustor.com/document/APKG_Utilities_2.0.zip)

### updown.py python script cli options
Just execute the script at the command line with the --help option to see arguments that are supported:
```bash
joe@joes-HP-EliteBook-8470p ~/Code/python-asustor-NAS-dropbox-sync/bin $ ./updown.py --help
usage: updown.py [-h] [--token TOKEN] [--yes] [--no] [--default] [--hidden]
                 [--upload] [--download] [--sync]
                 [dropbox_folder] [local_sync_folder]

Synchronise a local folder with a remote Dropbox account

positional arguments:
  dropbox_folder     The target folder in your Dropbox account
  local_sync_folder  The local target folder to upload / populate from Dropbox
                     / sync

optional arguments:
  -h, --help         show this help message and exit
  --token TOKEN      Access token (see
                     https://www.dropbox.com/developers/apps)
  --yes, -y          Automated answer yes to all runtime prompt questions
  --no, -n           Automated answer no to all runtime prompt questions
  --default, -df     Take the default answer to all runtime prompt questions
  --hidden, -ih      Upload hidden files
  --upload, -u       Upload mode enabled
  --download, -d     Download mode enabled
  --sync, -s         Full upload/download sync mode enabled
```

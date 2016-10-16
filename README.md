# asustor-dropbox
An Asustor NAS community open source version of a dropbox API v2 sync upload app

![Screenshot 1](/screenshots/Screenshot 2016-10-16 15:52:34.png)

![Screenshot 2](/screenshots/Screenshot 2016-10-16 15:53:32.png)

### Why bother?
I couldn't get the [Asustor provided dropbox app](http://forum.asustor.com/viewforum.php?f=59) reliably and safely working. The full story is here: http://forum.asustor.com/viewtopic.php?f=59&t=8202

### What does this do?
At the present time this app only supports dropbox upload. Full 2 way sync may be supported in the future.

### How do I set this thing up?
This app can be easily installed via the ADM App Central manual install feature using one of the [pre-compiled apk package release files](/../../releases). There is no UI at the present time so once installed, some manual configuration is required. Read [the setup guide](setup.md) for details.

### Is this app available for install directly in Asustor App Central?
Not yet. This app hasn't been submitted to Asustor to go through their approval process. I'm not sure how they'd feel about this app given it's a direct parallel to their own dropbox app. If someone wants to take on this crusade feel free.

### I don't trust pre-compiled .apk packages - what can I do?
The [pre-compiled apk packages](/../../releases) published in the release page are basically just a thin wrapper around the [updown.py python script](/bin/updown.py) included in this project. These .apk packages are created with the [Asustor apkg tool](http://developer.asustor.com/document/APKG_Utilities_2.0.zip). If you're not sure about trusting what's inside these packages there area a couple of things you can do:

1. .apk package files can be unzipped for review with any decent tool that supports compressed zip files. 
2. You can review the contents of the [updown.py python script](/bin/updown.py) to satisfy yourself that it's safe for use on your NAS box and once you're happy you can then [register](http://developer.asustor.com/user/registration) for an Asustor developer account so you read the docs to learn about how to compile your own .apk package with the [Asustor apkg tool](http://developer.asustor.com/document/APKG_Utilities_2.0.zip)

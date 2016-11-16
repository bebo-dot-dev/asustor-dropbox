## Setup 
These are the manual setup steps for this app

1. Download the latest apk from the [releases page](/../../releases)
2. Install the apk using the ADM App Central manual install feature. This app is dependent on Python and the installer should ensure Python is installed
3. The installer will by default create a single crontab scheduled job in the root account crontab file. The root account crontab file can be found at this location on the NAS: 

  `/var/spool/cron/crontabs/root`

  The crontab line added to the end of this file will look like this:
  ```bash
# ~~~~~~ community dropbox job ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
0 */8 * * * python /usr/local/AppCentral/community-dropbox-upload/bin/updown.py --token [YOUR_OAUTH2_TOKEN] -y -u ~/ /home/admin/datasync/
# ~~~~~~ community dropbox job end ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  ```
    
  There are a few things to note about this crontab job:
  * `0 */8 * * *` represents a schedule that will execute every 8 hours. You can change this to whatever schedule you need. http://crontab.guru/ is a useful website for creating and verifying a cron schedule.
  * `[YOUR_OAUTH2_TOKEN]` is a placeholder for the required dropbox oauth2 token and this needs to be **completely replaced** (replace the square brackets too) with a real and valid dropbox oath2 token. See step 4. for further details to see how to generate a valid dropbox oath2 token.
  * `~/` is the target path in the dropbox account and this should be changed as required
  * `/home/admin/datasync/` is a local source datasync folder located somewhere on the NAS that is to be uploaded to dropbox and this path should be changed as required
 
4. Create a dropbox app here: https://www.dropbox.com/developers/apps. When you create the app, the *Generated access token* is the oauth2 token thing that you need to plug into the `[YOUR_OAUTH2_TOKEN]` placeholder in the cron job
5. Edit and save the root account crontab file mentioned in step (3) plugging in the oauth2 token you generated in step (4) along with any path changes you need to make
6. Done!

### Additonal Notes
1. The crontab file used to schedule the python script doesn't actually need to be the root account crontab file; it just so happens that when the app is installed, it's installed in the context of the root user so the installer by default creates the crontab scheduled job in the root users' crontab file.
2. There's nothing to stop you removing the root account crontab file entry and adding other crontab entries to other users' crontab files as required
3. Mutliple schedules can be added for different NAS source sync folders
4. Any valid dropbox oauth2 token can be used so if you need to sync to multiple different dropbox accounts just create dropbox apps for those accounts here: https://www.dropbox.com/developers/apps
5. When the scheduled job runs on it's schedule it will log progress and eventual completion to a log file as that will look like [this sample](log/20161023.082703645250.log). Log files are maintained at this location:
`/usr/local/AppCentral/community-dropbox-upload/log`

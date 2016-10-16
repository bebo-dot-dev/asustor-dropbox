#!/bin/sh

case "$APKG_PKG_STATUS" in
	install)
		#ensure script python module dependencies are in place
		pip install six
		pip install lockfile
		pip install dropbox		

		#create a default cron job on an 8hr schedule. The install is performed in the context of root so the crontab file == root
		#once the cron job is created ,<YOUR_OAUTH2_TOKEN> needs to be replaced with a valid OAUTH2 token and the other path and behavioural params need to be changed as required
		#see updown.py -h for details				
		CURRENT_USER_NAME=$(id -u -n) 
		CRON_JOB="0 */8 * * * python /usr/local/AppCentral/community-dropbox-upload/bin/updown.py --token [YOUR_OAUTH2_TOKEN] -y ~/ /home/admin/datasync/"
		(crontab -u $CURRENT_USER_NAME -l; echo "$CRON_JOB" ) | crontab -u $CURRENT_USER_NAME -
		;;

esac

exit 0

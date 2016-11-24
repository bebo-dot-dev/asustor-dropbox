#!/bin/sh

CRON_JOB_LABEL="# ~~~~~~ community dropbox job ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
CRON_JOB_LABEL_END="# ~~~~~~ community dropbox job end ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
CRON_JOB_UNIQUE_CONTENT="community-dropbox-sync/bin/updown.py"

CURRENT_USER_NAME=$(id -u -n) 

cronjob_exists() {
    crontab -u $CURRENT_USER_NAME -l 2>/dev/null | grep "$CRON_JOB_UNIQUE_CONTENT" >/dev/null 2>/dev/null
}

case "$APKG_PKG_STATUS" in
	install)
		#ensure script python module dependencies are in place
		easy_install -U setuptools
		pip install requests
		pip install six
		pip install lockfile
		pip install dropbox		

		if ! cronjob_exists; then
			#create a default cron job on an 8hr schedule. The install is performed in the context of root so the crontab file == root
			#once the cron job is created, [YOUR_OAUTH2_TOKEN] needs to be replaced with a valid OAUTH2 token and the other path and behavioural params need to be changed as required
			#see ./updown.py -h for details							
			CRON_JOB="0 */8 * * * python /usr/local/AppCentral/community-dropbox-sync/bin/updown.py --token [YOUR_OAUTH2_TOKEN] -y -u / /home/admin/datasync/"
			(crontab -u $CURRENT_USER_NAME -l; echo; echo $CRON_JOB_LABEL; echo "$CRON_JOB"; echo $CRON_JOB_LABEL_END; ) | crontab -u $CURRENT_USER_NAME -
		else
			echo 'Crontab entry already exists, skipping ...'
			echo
		fi
		;;

esac

exit 0

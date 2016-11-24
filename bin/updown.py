#!/usr/local/bin/python

"""
Uploads the contents of a given folder to Dropbox
This is an example app for API v2

This script is based on the updown.py example included in the dropbox python sdk here:
https://github.com/dropbox/dropbox-sdk-python/tree/master/example
"""

from __future__ import print_function

import argparse
import contextlib
import datetime
import lockfile
import logging
import os
import requests
import six
import sys
import time
import unicodedata

import dropbox
from dropbox.files import FileMetadata

import locale
locale.setlocale(locale.LC_ALL, ('en', 'utf-8'))

if sys.version.startswith('2'):
    input = raw_input

# OAuth2 access token
TOKEN = ''

parser = argparse.ArgumentParser(description='Synchronise a local folder with a remote Dropbox account')
parser.add_argument('dropbox_folder', nargs='?', default='Downloads', help='The target folder in your Dropbox account')
parser.add_argument('local_sync_folder', nargs='?', default='~/Downloads',
                    help='The local target folder to upload / populate from Dropbox / sync')
parser.add_argument('--token', default=TOKEN, help='Access token (see https://www.dropbox.com/developers/apps)')
parser.add_argument('--yes', '-y', action='store_true', help='Automated answer yes to all runtime prompt questions')
parser.add_argument('--no', '-n', action='store_true', help='Automated answer no to all runtime prompt questions')
parser.add_argument('--default', '-df', action='store_true',
                    help='Take the default answer to all runtime prompt questions')
parser.add_argument('--hidden', '-ih', action='store_true', help='Upload hidden files')
parser.add_argument('--upload', '-u', action='store_true', help='Upload mode enabled')
parser.add_argument('--download', '-d', action='store_true', help='Download mode enabled')
parser.add_argument('--sync', '-s', action='store_true', help='Full upload/download sync mode enabled')

# globals
processLockFile = ''
app_logger = None
start_time = None
# files not supported on dropbox (https://www.dropbox.com/help/145):
banned_files = set(['desktop.ini', 'thumbs.db', '.ds_store', 'icon\r', '.dropbox', '.dropbox.attr'])
dropbox_traverse_count = 0


# global exception handler
def handle_exception(exc_type, exc_value, exc_traceback):
    global app_logger
    releaseLock()
    logging.error('\n')
    logging.error('Caught unhandled exception', exc_info=(exc_type, exc_value, exc_traceback))
    log_runtime()
    abortProcess('Process terminated early due to exception', 2)


sys.excepthook = handle_exception


# main procedure
def main():
    global start_time
    start_time = time.time()

    log_info_event('Process started')

    args = validate_args()

    dropbox_folder = args.dropbox_folder
    local_sync_folder = os.path.expanduser(args.local_sync_folder)

    if not acquireLock(local_sync_folder):
        global processLockFile
        abortProcess('Unable to acquireLock for ' + processLockFile + '; script is likely already running', 3)

    dbx = dropbox.Dropbox(args.token)

    upload_result = (0, 0, 0)
    if args.upload or args.sync:
        upload_result = traverse_local_folders(dbx, local_sync_folder, dropbox_folder, args)

    download_result = (0, 0, 0)
    if args.download or args.sync:
        dropbox_root = dropbox_folder.replace('~', '')
        if dropbox_root == '/':
            dropbox_root = ''
        if test_dropbox_folder(dbx, dropbox_root):
            download_result = traverse_dropbox_folders(dbx, dropbox_root, local_sync_folder, args)
        else:
            print('unable to start dropbox files download')

    # process complete
    complete_process(
        upload_result[0],
        upload_result[1],
        upload_result[2],
        download_result[0],
        download_result[1],
        download_result[2])


# parses and validates cli arguments passed to this script
def validate_args():
    args = parser.parse_args()
    if sum([bool(b) for b in (args.yes, args.no, args.default)]) > 1:
        abortProcess('At most one of --yes, --no, --default is allowed', 2)

    if not args.token:
        abortProcess('--token is mandatory', 2)

    if args.token == '[YOUR_OAUTH2_TOKEN]':
        abortProcess(
            '--token == [YOUR_OAUTH2_TOKEN] and it needs to be correctly configured. Visit https://www.dropbox.com/developers/apps, create a new app and generate an oauth2 access token',
            2)

    dropbox_folder = args.dropbox_folder
    local_sync_folder = os.path.expanduser(args.local_sync_folder)

    print('Dropbox folder name:', dropbox_folder)
    print('Local directory:', local_sync_folder)

    if not os.path.exists(local_sync_folder):
        abortProcess(local_sync_folder + 'does not exist on your filesystem', 1)
    elif not os.path.isdir(local_sync_folder):
        abortProcess(local_sync_folder + 'is not a folder on your filesystem', 1)

    dbx = dropbox.Dropbox(args.token)
    if not checkToken(dbx):
        abortProcess('Invalid access token', 1)

    return args


# traverses local folders in the given local_sync_folder tree and uploads files
def traverse_local_folders(dbx, local_sync_folder, dropbox_folder, args):
    upload_new_file_count = 0
    upload_updated_file_count = 0
    upload_byte_count = 0
    loop_count = 0

    for dn, dirs, files in os.walk(local_sync_folder):

        if len(files) > 0:

            sub_folder = dn[len(local_sync_folder):].strip(os.path.sep)
            listing = list_folder(dbx, dropbox_folder, sub_folder)
            print('Descending into', sub_folder.encode('ascii', 'ignore'), '...')

            # Traverse all the files in this directory
            for filename in files:

                loop_count = check_log_runtime(loop_count, upload_new_file_count + upload_updated_file_count)

                full_filename = os.path.join(dn, filename)
                file_size = os.path.getsize(full_filename)

                if not isinstance(filename, six.text_type):
                    filename = filename.decode('utf-8')

                normalized_filename = unicodedata.normalize('NFC', filename)

                if not is_existing_valid_filename(args, filename):
                    continue
                elif normalized_filename in listing:
                    meta_data = listing[normalized_filename]
                    modified_time = os.path.getmtime(full_filename)
                    modified_datetime = datetime.datetime(*time.gmtime(modified_time)[:6])
                    if isinstance(meta_data,
                                  dropbox.files.FileMetadata) and modified_datetime == meta_data.client_modified and file_size == meta_data.size:
                        print(filename.encode('ascii', 'ignore'), 'is already synced [stats match]')
                    else:
                        print(filename.encode('ascii', 'ignore'), 'exists with different stats, downloading')
                        res = download(dbx, dropbox_folder, sub_folder, filename)
                        with open(full_filename) as f:
                            data = f.read()
                        if res is None:
                            print(filename.encode('ascii', 'ignore'), 'download failure')
                        elif res == data:
                            print(filename.encode('ascii', 'ignore'), 'is already synced [content match]')
                        else:
                            print(filename.encode('ascii', 'ignore'), 'has changed since last sync')
                            if yesno('Upload and overwrite %s' % filename, False, args):
                                res = upload(dbx, full_filename, dropbox_folder, sub_folder, filename, overwrite=True)
                                if res is not None:
                                    upload_updated_file_count += 1
                                    upload_byte_count += file_size

                elif yesno('Upload and save %s' % filename, True, args):
                    res = upload(dbx, full_filename, dropbox_folder, sub_folder, filename)
                    if res is not None:
                        upload_new_file_count += 1
                        upload_byte_count += file_size

        # Then setup the subdirectories to traverse
        keep = []
        for folder_name in dirs:
            if not is_valid_folder(args, folder_name):
                continue
            elif yesno('Descend into %s' % folder_name, True, args):
                print('Keeping directory:', folder_name.encode('ascii', 'ignore'))
                keep.append(folder_name)
            else:
                print('OK, skipping directory:', folder_name.encode('ascii', 'ignore'))
        dirs[:] = keep

    return upload_new_file_count, upload_updated_file_count, upload_byte_count


# returns an indicator whether the given path exists on dropbox
def test_dropbox_folder(dbx, path):
    # noinspection PyBroadException
    try:
        dbx.files_list_folder(path)
        return True
    except Exception as ex:
        print('dropbox path lookup failure for ', path.encode('ascii', 'ignore'))
        return False


# traverses remote dropbox folders and downloads files
def traverse_dropbox_folders(dbx, path, local_root_dir, args):
    global dropbox_traverse_count
    dl_file_count = 0
    dl_file_update_count = 0
    dl_byte_count = 0
    folder_metadata = None

    try:
        folder_metadata = dbx.files_list_folder(path)
    except (dropbox.exceptions.ApiError, Exception) as err:
        print('drop box folder traversal failure. files_list_folder failed for', path.encode('ascii', 'ignore'), err)

    if folder_metadata is not None:
        result = process_metadata_entries(dbx, folder_metadata.entries, path, local_root_dir, args)
        dl_file_count += result[0]
        dl_file_update_count += result[1]
        dl_byte_count += result[2]

    while folder_metadata is not None and folder_metadata.has_more:
        folder_metadata = None

        try:
            folder_metadata = dbx.files_list_folder_continue(folder_metadata.cursor)
        except (dropbox.files.ListFolderContinueError, Exception) as err:
            print('files_list_folder_continue failed for', path.encode('ascii', 'ignore'), err)

        if folder_metadata is not None:
            sub_traverse = process_metadata_entries(dbx, folder_metadata.entries, path, local_root_dir, args)
            dl_file_count += sub_traverse[0]
            dl_file_update_count += sub_traverse[1]
            dl_byte_count += sub_traverse[2]

    dropbox_traverse_count = check_log_runtime(dropbox_traverse_count, dl_file_count + dl_file_update_count, 1000, 300)

    return dl_file_count, dl_file_update_count, dl_byte_count, dropbox_traverse_count


# processes remote dropbox file and folder metadata
def process_metadata_entries(dbx, entries, path, local_root_dir, args):
    dl_file_count = 0
    dl_file_update_count = 0
    dl_byte_count = 0

    dropbox_root_folder = args.dropbox_folder.strip('~')

    for entry in entries:

        if isinstance(entry, dropbox.files.FolderMetadata):

            # folder traversal
            full_dropbox_folder_name = os.path.join(path, entry.name.strip('/'))

            try:

                print('folder: %s' % full_dropbox_folder_name.encode('ascii', 'ignore'))

                trimmed_dropbox_folder_name = (
                    full_dropbox_folder_name[len(dropbox_root_folder):].strip('/')
                    if dropbox_root_folder != '/'
                    else full_dropbox_folder_name.strip('/'))

                full_local_folder_name = os.path.join(local_root_dir, trimmed_dropbox_folder_name)
                if not os.path.exists(full_local_folder_name):
                    ensure_and_get_folder(full_local_folder_name, False)

                if path == '':
                    path = '/'
                sub_traverse = traverse_dropbox_folders(dbx, os.path.join(path, entry.name), local_root_dir, args)
                dl_file_count += sub_traverse[0]
                dl_file_update_count += sub_traverse[1]
                dl_byte_count += sub_traverse[2]

            except UnicodeEncodeError:
                print('folder: %s caused a UnicodeEncodeError' % full_dropbox_folder_name.encode('ascii', 'ignore'))

                log_info_event(
                    'Unable to download and save this folder due to a UnicodeEncodeError. ' +
                    'Check this folder path (invalid chars have been stripped): ' +
                    full_dropbox_folder_name.encode('ascii', 'ignore'))

        else:

            # file traversal
            full_dropbox_filename = os.path.join(path, entry.name.strip('/'))

            try:

                print('file: %s' % full_dropbox_filename.encode('ascii', 'ignore'))

                trimmed_dropbox_filename = full_dropbox_filename[len(dropbox_root_folder):].strip('/')

                full_local_filename = os.path.join(local_root_dir, trimmed_dropbox_filename)

                if not os.path.exists(full_local_filename):
                    if yesno('Download and save %s' % full_dropbox_filename, True, args):
                        file_data = download_and_save(dbx, full_dropbox_filename, full_local_filename)
                        if file_data is not None:
                            dl_file_count += 1
                            dl_byte_count += len(file_data)
                else:
                    local_file_modified_time = os.path.getmtime(full_local_filename)
                    local_file_modified_datetime = datetime.datetime(*time.gmtime(local_file_modified_time)[:6])
                    if entry.client_modified > local_file_modified_datetime:
                        if yesno('Download and overwrite %s' % full_dropbox_filename, True, args):
                            file_data = download_and_save(dbx, full_dropbox_filename, full_local_filename)
                            if file_data is not None:
                                dl_file_update_count += 1
                                dl_byte_count += len(file_data)

            except UnicodeEncodeError:
                print('file: %s caused a UnicodeEncodeError' % full_dropbox_filename.encode('ascii', 'ignore'))

                log_info_event(
                    'Unable to download and save this file due to a UnicodeEncodeError. ' +
                    'Check this file path (invalid chars have been stripped): ' +
                    full_dropbox_filename.encode('ascii', 'ignore'))

    return dl_file_count, dl_file_update_count, dl_byte_count


# performs a few tests on the given filename to determine whether the filename represents a valid existing file
def is_existing_valid_filename(args, filename):
    global banned_files
    valid = False
    if is_hidden(filename, args):
        print('Skipping hidden file:', filename.encode('ascii', 'ignore'))
    elif filename.lower() in banned_files:
        print('Skipping banned file:', filename.encode('ascii', 'ignore'))
    elif filename.startswith('@') or filename.endswith('~'):
        print('Skipping temporary file:', filename.encode('ascii', 'ignore'))
    elif filename.endswith('.pyc') or filename.endswith('.pyo'):
        print('Skipping generated file:', filename.encode('ascii', 'ignore'))
    else:
        valid = True
    return valid


# performs a few tests on the given folder_name to determine whether the folder_name represents a valid folder
def is_valid_folder(args, folder_name):
    valid = False
    if is_hidden(folder_name, args):
        print('Skipping hidden directory:', folder_name.encode('ascii', 'ignore'))
    elif folder_name.startswith('@') or folder_name.endswith('~'):
        print('Skipping temporary directory:', folder_name.encode('ascii', 'ignore'))
    elif folder_name == '__pycache__':
        print('Skipping generated directory:', folder_name.encode('ascii', 'ignore'))
    else:
        valid = True
    return valid


# returns an indicator whether the given item represents a hidden file or folder based on whether
# the item starts with a . and whether hidden files are allowed in the args supplied to the script (--hidden)
def is_hidden(item, args):
    if item.startswith('.') and not args.hidden:
        return True
    else:
        return False


# lists a folder and return a dictionary mapping unicode filenames to FileMetadata|FolderMetadata entries.
def list_folder(dbx, folder, subfolder):
    global app_logger
    path = '/%s/%s' % (folder, subfolder.replace(os.path.sep, '/'))
    while '//' in path:
        path = path.replace('//', '/')
    path = path.rstrip('/')
    try:
        with stopwatch('list_folder'):
            res = dbx.files_list_folder(path)
    except dropbox.exceptions.ApiError as err:
        print('Folder listing failed for', path.encode('ascii', 'ignore'), '-- assumped empty:', err)
        return {}
    except Exception as e:
        print('Folder listing exception for', path.encode('ascii', 'ignore'), '-- assumped empty:', e)
        app_logger.error('\n')
        logging.exception('Folder listing failed for %s', path)
        return {}
    else:
        rv = {}
        for entry in res.entries:
            rv[entry.name] = entry
        return rv


# attempts a file download from dropbox and return the bytes of the file or None if it doesn't exist.
def download(dbx, folder, sub_folder, name):
    path = '/%s/%s/%s' % (folder, sub_folder.replace(os.path.sep, '/'), name)
    while '//' in path:
        path = path.replace('//', '/')
    with stopwatch('download'):
        try:
            md, res = dbx.files_download(path)
        except (dropbox.exceptions.HttpError, Exception) as err:
            print('File download failed for', path.encode('ascii', 'ignore'), err)
            return None
    data = res.content
    print(len(data), 'bytes; md:', md)
    return data


# converts the given utc_datetime to a local datetime
def utc2local(utc_datetime):
    epoch = time.mktime(utc_datetime.timetuple())
    offset = datetime.datetime.fromtimestamp(epoch) - datetime.datetime.utcfromtimestamp(epoch)
    return utc_datetime + offset


# attempts a file download from dropbox, saves the file to the given target_file_name in the file system
# and returns the bytes of the file or None if it doesn't exist
def download_and_save(dbx, dropbox_file_name, target_file_name):
    with stopwatch('download and save'):
        try:
            md, res = dbx.files_download(dropbox_file_name)
            with open(target_file_name, 'wb') as f:
                f.write(res.content)

            local_datetime = utc2local(md.client_modified)
            mod_time = time.mktime(local_datetime.timetuple())
            os.utime(target_file_name, (mod_time, mod_time))

        except (dropbox.exceptions.HttpError, Exception) as err:
            print('File download failed for', dropbox_file_name.encode('ascii', 'ignore'), err)
            return None
    data = res.content
    print(len(data), 'bytes; md:', md)
    return data


# attempts a file upload to dropbox and returns the request response or None if an exception is caught

# note: dropbox considers 'aFile.txt' and 'afile.txt' to be exactly the same file - in other words dropbox does not
# support the concept of case sensitive files in the same way that linux does and uploading what dropbox considers a
# case insensitive duplicate file will cause a conflict failure exception on the call.

# dbx.files_upload does support a autorename parameter option which will attempt to prevent conflict failures by
# creating renamed versions of duplicate files in the account but it doesn't really work - it just results in lots and
# lots of copies of the same file being created in the account. For this reason, this method doesn't set
# autorename == True and will simply just log a conflict failure if one occurs.

# There is no reasonable solution to this dropbox problem other than to avoid case sensitive copies of files within a
# single folder..which is quite poor.

# see https://www.dropbox.com/en/help/145 case conflicts for further info

def upload(dbx, fullname, folder, subfolder, name, overwrite=False):
    global app_logger
    destination_path = '/%s/%s/%s' % (folder, subfolder.replace(os.path.sep, '/'), name)
    while '//' in destination_path:
        destination_path = destination_path.replace('//', '/')

    mode = (dropbox.files.WriteMode.overwrite if overwrite else dropbox.files.WriteMode.add)
    mtime = os.path.getmtime(fullname)

    CHUNK_SIZE = 4 * 1024 * 1024  # 4mb chunks
    MAX_SIZE = 10 * 1024 * 1024  # 10mb max

    f = open(fullname, 'rb')
    file_size = os.path.getsize(fullname)
    file_modified = datetime.datetime(*time.gmtime(mtime)[:6])
    with stopwatch('upload %d bytes' % file_size):
        try:

            if file_size <= MAX_SIZE:
                # one shot upload
                res = dbx.files_upload(f.read(), destination_path, mode, client_modified=file_modified, mute=True)
            else:
                # chunked upload for files > 10mb
                upload_session_start_result = dbx.files_upload_session_start(f.read(CHUNK_SIZE))
                cursor = dropbox.files.UploadSessionCursor(session_id=upload_session_start_result.session_id,
                                                           offset=f.tell())
                commit_info = dropbox.files.CommitInfo(path=destination_path)
                commit_info.client_modified = file_modified
                commit_info.mode = mode

                while f.tell() < file_size:
                    if (file_size - f.tell()) <= CHUNK_SIZE:
                        res = dbx.files_upload_session_finish(f.read(CHUNK_SIZE), cursor, commit_info)
                    else:
                        dbx.files_upload_session_append(f.read(CHUNK_SIZE), cursor.session_id, cursor.offset)
                        cursor.offset = f.tell()

        except (dropbox.exceptions.ApiError, dropbox.exceptions.InternalServerError) as err:
            print('*** API upload error for', fullname.encode('ascii', 'ignore'),
                  destination_path.encode('ascii', 'ignore'), err)
            app_logger.error('\n')
            logging.exception('Caught a dropbox exception at upload time; the process will continue. %s, %s, %s',
                              mode._tag, fullname, destination_path)
            return None

        except requests.exceptions.ReadTimeout as to:
            print('*** Timeout upload exception for', fullname.encode('ascii', 'ignore'),
                  destination_path.encode('ascii', 'ignore'), to)
            app_logger.error('\n')
            logging.exception(
                'Caught a request timeout exception at upload time; the process will continue. %s, %s, %s', mode._tag,
                fullname, destination_path)
            return None

        except Exception as e:
            print('*** General upload exception for', fullname.encode('ascii', 'ignore'),
                  destination_path.encode('ascii', 'ignore'), e)
            app_logger.error('\n')
            logging.exception('Caught a general exception at upload time; the process will continue. %s, %s, %s',
                              mode._tag, fullname, destination_path)
            return None

    print('uploaded as', res.name.encode('utf8', 'ignore'))
    return res


# A handy helper function to ask a yes/no question
def yesno(message, default, args):
    """
    Command line arguments --yes or --no force the answer;
    --default to force the default answer.

    Otherwise a blank line returns the default, and answering
    y/yes or n/no returns True or False.

    Retry on unrecognized answer.

    Special answers:
    - q or quit exits the program
    - p or pdb invokes the debugger
    """
    ascii_msg = message.encode('ascii', 'ignore')
    if args.default:
        print(ascii_msg + '? [auto]', 'Y' if default else 'N')
        return default
    if args.yes:
        print(ascii_msg + '? [auto] YES')
        return True
    if args.no:
        print(ascii_msg + '? [auto] NO')
        return False
    if default:
        ascii_msg += '? [Y/n] '
    else:
        ascii_msg += '? [N/y] '
    while True:
        answer = input(ascii_msg).strip().lower()
        if not answer:
            return default
        if answer in ('y', 'yes'):
            return True
        if answer in ('n', 'no'):
            return False
        if answer in ('q', 'quit'):
            print('Exit')
            raise SystemExit(0)
        if answer in ('p', 'pdb'):
            import pdb
            pdb.set_trace()
        print('Please answer YES or NO.')


# Performs an oauth2 token check by calling users_get_current_account()
def checkToken(dbx):
    # noinspection PyBroadException
    try:
        dbx.users_get_current_account()
        return True
    except:
        return False


# Returns the parent directory of the directory where this script resides in the file system
def app_base_path():
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


# Returns the run-time log directory for this script in the file system
def ensure_and_get_folder(folder_name, use_base_path=True):
    full_folder_path = (app_base_path() + '/' + folder_name if use_base_path else folder_name)
    try:
        os.makedirs(full_folder_path)
    except OSError:
        if not os.path.isdir(full_folder_path):
            raise
    return full_folder_path + '/'


# Attempts to acquire a lock for the script. Automatically creates a lock file for the given rootdir ensuring multiple
# instances of the script can run concurrently for different rootdir folders
def acquireLock(rootdir):
    global processLockFile
    lock_file_name = rootdir.replace('/', '.').replace('~', '')
    processLockFile = ensure_and_get_folder('lock') + lock_file_name
    if not os.path.isfile(processLockFile):
        fo = open(processLockFile, 'w')
        fo.close()

    lock = lockfile.FileLock(processLockFile)
    try:
        lock.acquire(0)
        return True
    except lockfile.AlreadyLocked:
        return False


# Releases a previously acquired lock
def releaseLock():
    global processLockFile
    lock = lockfile.FileLock(processLockFile)
    try:
        lock.release()
    except (lockfile.NotLocked, lockfile.NotMyLock):
        print('lock release failure')


# Aborts the process with a reason descriptor and an exit code
def abortProcess(reason, exitcode):
    print(reason)
    log_info_event('process aborted with: ' + reason, True)
    sys.exit(exitcode)


# helper logging procedure
def log_info_event(log_string, shutdown=False):
    global app_logger
    if not app_logger:
        log_filename = ensure_and_get_folder('log') + datetime.datetime.utcnow().strftime('%Y%m%d.%H%M%S%f') + '.log'
        app_logger = logging.getLogger('dropbox_app_logger')
        logging.basicConfig(filename=log_filename, level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                            datefmt='%d/%m/%Y %H:%M:%S')
        # quieten down noisy module loggers
        logging.getLogger('dropbox').setLevel(logging.WARNING)
        logging.getLogger('requests.packages.urllib3').setLevel(logging.WARNING)
    app_logger.info(log_string)
    if shutdown:
        logging.shutdown()


# logs the script runtime
def log_runtime():
    global start_time
    d = divmod(int(time.time()) - int(start_time), 86400)  # days
    h = divmod(d[1], 3600)  # hours
    m = divmod(h[1], 60)  # minutes
    s = m[1]  # seconds
    log_info_event('Runtime: {0} days {1} hours {2} mins {3} secs'.format(d[0], h[0], m[0], s))


# self managed log_runtime procedure
def check_log_runtime(loop_count, file_count, max_loops=3000, max_files=300):
    loop_count += 1

    loop_count_remainder = divmod(loop_count, max_loops)
    file_count_remainder = (
        (0, 1)
        if file_count == 0
        else divmod(file_count, max_files))

    if (loop_count_remainder[1] == 0) or (file_count_remainder[1] == 0):
        log_runtime()

        if file_count_remainder[1] == 0:
            # reset
            loop_count = 1

    return loop_count


# completes the process, called at script end
def complete_process(
        upload_new_file_count,
        upload_updated_file_count,
        upload_byte_count,
        download_new_file_count,
        download_updated_file_count,
        download_byte_count):
    log_info_event('New files uploaded: {}'.format(upload_new_file_count))
    log_info_event('Updated files uploaded: {}'.format(upload_updated_file_count))
    log_info_event('Total bytes uploaded: {}'.format(upload_byte_count))

    log_info_event('New files downloaded: {}'.format(download_new_file_count))
    log_info_event('Updated files downloaded: {}'.format(download_updated_file_count))
    log_info_event('Total bytes downloaded: {}'.format(download_byte_count))

    print(
        'New files uploaded: {}, Updated files uploaded: {}, Total bytes uploaded: {},'.format(
            upload_new_file_count,
            upload_updated_file_count,
            upload_byte_count),
        'New files downloaded: {}, Updated files downloaded: {}, Total bytes downloaded: {}'.format(
            download_new_file_count,
            download_updated_file_count,
            download_byte_count)
    )

    log_runtime()
    log_info_event('Process finished', True)
    releaseLock()


@contextlib.contextmanager
def stopwatch(message):
    """Context manager to print how long a block of code took."""
    t0 = time.time()
    try:
        yield
    finally:
        t1 = time.time()
        print('Total elapsed time for %s: %.3f' % (message, t1 - t0))


if __name__ == '__main__':
    main()

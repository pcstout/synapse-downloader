import os
import getpass
import synapseclient as syn
import logging
from datetime import datetime


class SynapseDownloaderOld:
    def __init__(self, starting_entity_id, download_path, username=None, password=None):
        self._synapse_client = None
        self._starting_entity_id = starting_entity_id
        self._username = username
        self._password = password

        self.start_time = None
        self.end_time = None

        var_path = os.path.expandvars(download_path)
        expanded_path = os.path.expanduser(var_path)
        self._download_path = expanded_path
        self.ensure_dirs(self._download_path)

    def synapse_login(self):
        logging.info('Logging into Synapse...')
        self._username = self._username or os.getenv('SYNAPSE_USERNAME')
        self._password = self._password or os.getenv('SYNAPSE_PASSWORD')

        if not self._username:
            self._username = input('Synapse username: ')

        if not self._password:
            self._password = getpass.getpass(prompt='Synapse password: ')

        try:
            self._synapse_client = syn.Synapse(skip_checks=True)
            self._synapse_client.login(self._username, self._password, silent=True)
        except Exception as ex:
            self._synapse_client = None
            logging.error('Synapse login failed: {0}'.format(str(ex)))

        return self._synapse_client is not None

    def ensure_dirs(self, local_path):
        if not os.path.isdir(local_path):
            os.makedirs(local_path)

    def execute(self):
        self.start_time = datetime.now()

        self.synapse_login()
        parent = self._synapse_client.get(self._starting_entity_id, downloadFile=False)
        if type(parent) not in [syn.Project, syn.Folder]:
            raise Exception('Starting entity must be a Project or Folder.')
        logging.info('Starting entity: {0} ({1})'.format(parent.name, parent.id))
        logging.info('Downloading to: {0}'.format(self._download_path))
        logging.info('')

        self.download_children(parent, self._download_path)

        self.end_time = datetime.now()
        logging.info('')
        logging.info('Run time: {0}'.format(self.end_time - self.start_time))

    def download_children(self, parent, local_path):
        syn_folders = []
        syn_files = []

        try:
            children = self._synapse_client.getChildren(parent, includeTypes=["folder", "file"])

            for child in children:
                child_id = child.get('id')
                child_name = child.get('name')

                if child.get('type') == 'org.sagebionetworks.repo.model.Folder':
                    # self.download_folder(child_id, child_name, local_path)
                    syn_folders.append({'id': child_id, 'name': child_name, 'local_path': local_path})
                else:
                    # self.download_file(child_id, child_name, local_path)
                    syn_files.append({'id': child_id, 'name': child_name, 'local_path': local_path})

            if syn_files:
                for syn_file in syn_files:
                    self.download_file(syn_file['id'], syn_file['name'], syn_file['local_path'])

            if syn_folders:
                for syn_folder in syn_folders:
                    self.download_folder(syn_folder['id'], syn_folder['name'], syn_folder['local_path'])

        except Exception as ex:
            logging.exception(ex)

    def download_folder(self, syn_id, name, local_path):
        try:
            full_path = os.path.join(local_path, name)
            logging.info('Folder: {0} -> {1}'.format(syn_id, full_path))
            self.ensure_dirs(full_path)
            self.download_children(syn_id, full_path)
        except Exception as ex:
            logging.exception(ex)

    def download_file(self, syn_id, name, local_path):
        try:
            full_path = os.path.join(local_path, name)
            logging.info('File  : {0} -> {1}'.format(syn_id, full_path))
            self._synapse_client.get(syn_id,
                                     downloadFile=True,
                                     downloadLocation=local_path,
                                     ifcollision='overwrite.local')
        except Exception as ex:
            logging.exception(ex)

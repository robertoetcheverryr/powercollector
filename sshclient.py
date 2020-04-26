# ****************************************************************************
# * powercollector.sshclient                                                 *
# * Module for ssh classes and functions, based on code from:
# * Hackers and Slackers
# * Author: Roberto Etcheverry (retcheverry@roer.com.ar)                     *
# * Ver: 1.0.5 2020/04/24                                                    *
# ****************************************************************************

import socket

from loguru import logger
from paramiko import SSHClient, AutoAddPolicy
from paramiko.auth_handler import AuthenticationException
from scp import SCPClient, SCPException


class RemoteClient:
    # Client to interact with a remote host via SSH & SCP.

    def __init__(self, host, user, password, remote_path):
        self.host = host
        self.user = user
        self.password = password
        self.remote_path = remote_path
        self.client = None
        self.scp = None
        self.conn = None

    def _connect(self):
        # Open connection to remote host.

        if self.conn is None:
            try:
                self.client = SSHClient()
                self.client.load_system_host_keys()
                self.client.set_missing_host_key_policy(AutoAddPolicy())
                self.client.connect(self.host,
                                    username=self.user,
                                    password=self.password,
                                    look_for_keys=False,
                                    timeout=120)
                self.scp = SCPClient(self.client.get_transport())
            except AuthenticationException as error:
                logger.error('Authentication failed')
                if __debug__:
                    logger.exception(error)
                raise error
            except socket.gaierror as error:
                logger.error('Invalid or unreachable hostname or IP address')
                if __debug__:
                    logger.exception(error)
                raise error
            except TimeoutError as error:
                logger.error('Timeout encountered when attempting to connect')
                if __debug__:
                    logger.exception(error)
                raise error
        return self.client

    def disconnect(self):
        # Close ssh connection.

        self.client.close()
        self.scp.close()

    def bulk_upload(self, files):
        # Upload multiple files to a remote directory.
        # :param files: List of strings representing file paths to local files.

        self.conn = self._connect()
        uploads = [self.upload_file(file) for file in files]
        logger.info(f'Finished uploading {len(uploads)} files to {self.remote_path} on {self.host}')

    def upload_file(self, file):
        # Upload a single file to a remote directory.
        try:
            self.scp.put(file,
                         recursive=True,
                         remote_path=self.remote_path)
        except SCPException as error:
            if __debug__:
                logger.exception(error)
            raise error
        finally:
            logger.info(f'Uploaded {file} to {self.remote_path}')

    def download_file(self, file, path='.'):
        # Download file from remote host.
        try:
            self.conn = self._connect()
            self.scp.get(file, path)
        except Exception as e:
            if __debug__:
                logger.exception(e)
            logger.error(f'Error downloading file {file} from {path}')

    def execute_command(self, command, timeout=None, vios=False):
        # Execute one command and return the output
        # In the specific case of Virtual IO Server, since the commands need to be root,
        # TODO find a better solution than a vios flag and all the duplication.

        try:
            logger.info(f'INPUT: {command}')
            self.conn = self._connect()
            if vios:
                logger.info('Special VIOS command mode. Sending ioscli oem_setup_env before command.')
                stdin, stdout, stderr = self.client.exec_command('ioscli oem_setup_env', timeout=timeout)
                # after sending the oem_setup_env, the system DOES NOT give back so we have to manually send
                # the string and an exit command to return to the shell.
                stdin.write('%s\n%s\n' % (command, 'exit'))
                stdin.flush()
            else:
                stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)

            response = stdout.readlines()
            if response is None:
                logger.info(f'INPUT: {command} | OUTPUT: No output')
            for line in response:
                line = line.replace('\n', '')
                logger.info(f'INPUT: {command} | OUTPUT: {line}')
            return response
        except socket.timeout as e:
            if __debug__:
                logger.exception(e)
            logger.error(f' INPUT: {command} raised a socket.timeout exception.')
        except Exception as e:
            if __debug__:
                logger.exception(e)
            logger.error(f' INPUT: {command} raised a socket.timeout exception.')
            raise e

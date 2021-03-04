# ****************************************************************************
# * powercollector.common                                                    *
# * Module for common classes and functions                                  *
# * Author: Roberto Etcheverry (retcheverry@roer.com.ar)                     *
# * Ver: 1.0.13 2020/03/04                                                   *
# ****************************************************************************

# Import logger for the main log file
from loguru import logger
# Import subprocess to run external processes
import subprocess
# Import os to use file functions
import os
# Import Jsonizable to store and read the data
from jsonizable import Jsonizable
import json
# Import re to work with regular expressions
import re
# Import socket to do low-level networking
import socket
# Import the RemoteClient class from the sshclient file
from paramiko import AuthenticationException
# Import the RemoteClient to connect to HMC and LPAR
from sshclient import RemoteClient
# Import copy to deepcopy modules
import copy


# Define LPAR class
# We inherit form Jsonizable, to have the ability to read and write json, the subclass Meta has a dictionary of
# how the LPAR class will be read or written
class LPAR(Jsonizable):
    # Use slots to make Python reduce RAM usage, since it doesn't use a dict to store attributes and
    # the attributes are defined from the start.
    __slots__ = ['name', 'id', 'env', 'os_level', 'rmc_ip', 'state']

    # All of our inits will now also accept a json object, which we'll use to call the parent class' init
    def __init__(self, json_in=None, name=None, lpar_id=None, lpar_env=None,
                 lpar_os_level=None, state=None, rmc_ip=None):
        self.name = name or ''
        self.id = lpar_id or ''
        self.os_level = lpar_os_level or ''
        self.rmc_ip = rmc_ip or ''
        self.state = state or ''
        self.env = lpar_env or ''
        super().__init__(json_in)

    class Meta:
        schema = {
            "name": str,
            # Is it worth it to get type-happy with things like ID?
            "env": str,
            "id": str,
            "os_level": str,
            "rmc_ip": str,
            "state": str,
        }


# Define Enclosure Topology class
class EnclosureTopology(Jsonizable):
    __slots__ = ['enclosure', 'leading_hub_port', 'trailing_hub_port']

    def __init__(self, json_in=None, enclosure=None, leading_hub_port=None, trailing_hub_port=None):
        self.enclosure = enclosure or ''
        self.leading_hub_port = leading_hub_port or ''
        self.trailing_hub_port = trailing_hub_port or ''
        super().__init__(json_in)

    class Meta:
        schema = {
            "enclosure": str,
            "leading_hub_port": str,
            "trailing_hub_port": str,
        }


# Define FSP class
class FSP(Jsonizable):
    __slots__ = ['temp_ecnumber', 'temp_level', 'perm_ecnumber', 'perm_level']

    def __init__(self, json_in=None, temp_ecnumber=None, temp_level=None,
                 perm_ecnumber=None, perm_level=None):
        self.temp_ecnumber = temp_ecnumber or ''
        self.temp_level = temp_level or ''
        self.perm_ecnumber = perm_ecnumber or ''
        self.perm_level = perm_level or ''
        super().__init__(json_in)

    class Meta:
        schema = {
            "temp_ecnumber": str,
            "temp_level": str,
            "perm_ecnumber": str,
            "perm_level": str,
        }


class IOSlot(Jsonizable):
    __slots__ = ['feature_codes', 'description', 'unit_phys_loc', 'phys_loc', 'drc_name']

    def __init__(self, json_in=None, feature_codes=None, description=None,
                 unit_phys_loc=None, phys_loc=None, drc_name=None):
        self.feature_codes = feature_codes or ''
        self.description = description or ''
        self.unit_phys_loc = unit_phys_loc or ''
        self.phys_loc = phys_loc or ''
        self.drc_name = drc_name or ''
        super().__init__(json_in)

    class Meta:
        schema = {
            "feature_codes": str,
            "description": str,
            "unit_phys_loc": str,
            "phys_loc": str,
            "drc_name": str,
        }


# Define Managed System class
class ManagedSystem(Jsonizable):
    __slots__ = ['name', 'mt', 'serial', 'partition_list', 'enclosure_topo',
                 'fsp_primary', 'fsp_secondary', 'capabilities', 'io_slots']

    def __init__(self, json_in=None, name=None, mt=None, serial=None):
        self.name = name or ''
        self.mt = mt or ''
        self.serial = serial or ''
        self.partition_list: list = []
        self.enclosure_topo: list = []
        self.io_slots: list = []
        self.fsp_primary = FSP()
        self.fsp_secondary = FSP()
        self.capabilities = ''
        if json_in:
            super().__init__(json_in)

    class Meta:
        schema = {
            "name": str,
            "mt": str,
            "serial": str,
            "fsp_primary": FSP,
            "fsp_secondary": FSP,
            "capabilities": str,
            "io_slots?": [IOSlot],
            "partition_list?": [LPAR],
            "enclosure_topo?": [EnclosureTopology],
        }


# Define HMC Class
class HMC(Jsonizable):
    __slots__ = ['hostname', 'domain', 'version', 'mt', 'serial', 'managed_systems']

    def __init__(self, json_in=None, hostname=None, domain=None, version=None,
                 mt=None, serial=None, managed_systems=None):
        self.hostname = hostname or ''
        self.domain = domain or ''
        self.version = version or ''
        self.mt = mt or ''
        self.serial = serial or ''
        self.managed_systems = managed_systems or []
        if json_in:
            super().__init__(json_in)

    class Meta:
        schema = {
            "hostname": str,
            "domain?": str,
            "version": str,
            "mt": str,
            "serial": str,
            "managed_systems?": [ManagedSystem],
        }


def print_red(text):
    print(f"\033[91m{text}\033[00m")


def check_java(base_dir):
    # Check for bundled Java or fallback to installed
    java = None
    regex = re.compile(r'.*jre')
    # Search the base_dir for the jre directory
    for file in os.listdir(base_dir):
        if regex.search(file):
            try:
                # Search the JRE directory for the Java exe and return it
                if os.path.exists(file + '\\bin\\' + 'java.exe'):
                    java = base_dir + "\\" + file + '\\bin\\' + 'java.exe'
                outputs = subprocess.run(java + ' -version', capture_output=True, text=True)
                logger.info(f'Bundled Java is available: {outputs.stderr}')
                return java
            except FileNotFoundError:
                continue
    # If the Bundled search fails, check the system version
    try:
        outputs = subprocess.run('java -version', capture_output=True, text=True)
    except FileNotFoundError:
        return False
    # TODO do we need to check for an specific Java version?
    regex = re.compile(' version.".*"', re.IGNORECASE)
    result = regex.search(str(outputs.stderr))
    if not result:
        return False
    else:
        if result.group(0) < " version \"1.6":
            logger.info(f'Default System Java is not compatible: {result.string}')
        logger.info(f'System Java is available: {result.string}')
        return "java"


def save_hmc_data(hmc_src, hmc, output_dir):
    # File format: HMC object first then ManagedSystem objects
    output_file = output_dir + '\\' + hmc_src + '-SystemsManagedByHMC-' + hmc.hostname + '.json'
    with open(output_file, "w+") as file:
        # Write HMC's JSON
        file.write(json.dumps(hmc.write(), indent=4))
    print('Reading written file for consistency.')
    read_hmc = read_hmc_data(output_file)
    # noinspection PyUnresolvedReferences
    if read_hmc.write() == hmc.write():
        # HMC object is correct
        print('File is consistent.')
        logger.info('File is consistent.')
        return True
    else:
        print_red('Failure checking file consistency.')
        logger.error('Failure checking file consistency.')
        return False


def read_hmc_data(input_file):
    """
    : Reads a powercollector JSON file to populate and returns the HMC object
    """
    with open(input_file, "r") as file:
        print('Attempting to open JSON File: ' + str(input_file))
        logger.info('Attempting to open JSON File: ' + str(input_file))
        try:
            hmc_ = HMC(json_in=json.loads(file.read()))
            print('HMC and Managed Systems loaded successfully.')
            logger.info('HMC and Managed Systems loaded successfully.')
            return hmc_
        except json.JSONDecodeError as e:
            print_red(f'{e.msg} line {e.lineno} column {e.colno} (char {e.pos})')
            logger.error(f'{e.msg} line {e.lineno} column {e.colno} (char {e.pos})')
            # noinspection PyUnreachableCode
            if __debug__:
                logger.exception(e)
            return False
        except Exception as e:
            print_red('Invalid input file.')
            logger.error('Invalid input file.')
            if __debug__:
                logger.exception(e)
            return False


def check_host(hostname):
    """
    :This function checks if a provided hostname is pingable.
    :Returns True if the host is reachable and False if not.
    :Logs to the console and logfile any problems.
    """
    try:
        host = socket.gethostbyname(hostname)
        subprocess.run('ping -n 1 ' + host, check=True, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print_red('Host: ' + hostname + ' is not responding to ICMP Ping.')
        logger.error('Host: ' + hostname + ' is not responding to ICMP Ping.')
        return False
    except socket.error:
        print_red('Host: ' + hostname + ' is not resolvable.')
        logger.error('Host: ' + hostname + ' is not resolvable.')
        return False
    return True


def save_os_level_data_for_sys(managed_systems, base_dir, output_dir, today, oscollector_path=None):
    # Connect to each partition to run the collection script
    print('LPAR OS-level collection started.')
    logger.info('LPAR OS-level collection started.')
    non_collected_lpars = []
    if oscollector_path is None:
        oscollector_path = base_dir
    oscollector = get_oscollector(oscollector_path)
    for system in managed_systems:
        if not system.partition_list:
            print_red('No LPARs defined for System: ' + system.name)
            logger.info('No LPARs defined for System: ' + system.name)
            continue
        print('LPAR OS-level collection for System: ' + system.name + ' started.')
        logger.info('LPAR OS-level collection for System: ' + system.name + ' started.')
        for lpar in system.partition_list:
            print('LPAR: ' + lpar.name + '\'s OS-level collection started.')
            logger.info('LPAR: ' + lpar.name + '\'s OS-level collection started.')
            if not save_lpar_os_data(lpar=lpar, oscollector=oscollector, path_to_oscollector=base_dir,
                                     output_path=output_dir, system_name=system.name, today=today):
                non_collected_lpars.append(copy.deepcopy(lpar))
                non_collected_lpars[-1].name = system.name + '-' + lpar.name
            print('LPAR: ' + lpar.name + '\'s OS-level collection ended.')
            logger.info('LPAR: ' + lpar.name + '\'s OS-level collection ended.')
        print('LPAR OS-level collection for System: ' + system.name + ' completed.')
        logger.info('LPAR OS-level collection for System: ' + system.name + ' completed.')
    if non_collected_lpars:
        print_red('Unable to collect OS-level data for some LPARs, please' +
                  ' run oscollector manually on each one. Check the log file for the LPAR list.')
        logger.error('Unable to collect OS-level data for the following LPARs, please' +
                     ' run oscollector manually on each one.')
        for lpar in non_collected_lpars:
            logger.info(f'System LPAR: {lpar.name} rmc_ip: {lpar.rmc_ip} state: {lpar.state}')
        with open(output_dir + '\\' + 'NonCollectedLPARList.json', "w+") as file:
            # Write HMC's JSON
            for lpar in non_collected_lpars:
                file.write(json.dumps(lpar.write()) + '\n')
            logger.info('List of LPARs that require manual collection written to file: ' + output_dir + '\\' +
                        'NonCollectedLPARList.json')
    print('LPAR OS-level collection completed.')
    logger.info('LPAR OS-level collection completed.')
    return True


def get_oscollector(path_to_oscollector):
    """
    : This function takes a path and returns the name of the latest oscollector
    """
    # Check for oscollector.v.X.X.ksh
    if not os.path.exists(path_to_oscollector):
        logger.error('Path: ' + str(path_to_oscollector) + ' is not a path.')
        return False
    oscollector = None
    regex = re.compile(r'oscollector\..*\.ksh')
    for file in os.listdir(path_to_oscollector):
        if regex.search(file):
            if oscollector:
                # oscollector files are oscollector.vX.x.ksh
                # remove everything but the X.x and we can just cast it to float to test
                curr_ver = oscollector.replace('oscollector.v', '')
                curr_ver = curr_ver.replace('.ksh', '')
                new_ver = file.replace('oscollector.v', '')
                new_ver = new_ver.replace('.ksh', '')
                if float(new_ver) > float(curr_ver):
                    oscollector = file
            else:
                oscollector = file
    if oscollector:
        logger.info('Found oscollector file: ' + oscollector)
        return oscollector
    else:
        logger.error('oscollector not found.')
        return False


def save_lpar_os_data(lpar, oscollector, path_to_oscollector, output_path, today, password=None, username=None,
                      system_name=None):
    """
    : get lpar os data takes the lpar, oscollector
    """
    # Safeguard clauses and username/password setup
    if 'Running' not in lpar.state:
        # continue halts the current loop and moves to the next iterable, in this case, next lpar
        print_red('LPAR: ' + lpar.name + ' LPAR must be running to be collected. Please '
                                         'run oscollector manually if needed.')
        logger.error('LPAR: ' + lpar.name + ' must be running to be collected. Please '
                                            'run oscollector manually if needed.')
        return False
    if 'os400' in lpar.env:
        print_red('LPAR: ' + lpar.name + ' is running IBM i, cannot run oscollector.')
        logger.info('LPAR: ' + lpar.name + ' is running IBM i, cannot run oscollector.')
        return False
    # AIX and Linux share the same "env" so if the os version is known, we can exclude Linux from collection
    elif 'Linux' in lpar.os_level:
        print_red('LPAR: ' + lpar.name + ' is running Linux, cannot run oscollector.')
        logger.info('LPAR: ' + lpar.name + ' is running Linux, cannot run oscollector.')
        return False
    # The LPAR is AIX/Linux/VIOS, set passwords if not set
    elif 'vioserver' in lpar.env:
        username = username or 'padmin'
        password = password or 'padmin'
    else:
        username = username or 'root'
        password = password or 'password'
    if lpar.rmc_ip == '':
        # If the LPAR is Running but doesn't have an RMC IP Address, we cannot connect and something is
        # wrong with the LPAR.
        print_red('LPAR: ' + lpar.name + ' is running but doesn\'t have an RMC IP address. Please '
                                         'run oscollector manually and check RMC services if' 
                                         'this is an AIX or VIOS LPAR.')
        logger.error('LPAR: ' + lpar.name + ' is running but doesn\'t have an RMC IP address. Please '
                                            'run oscollector manually and check RMC services if' 
                                            'this is an AIX or VIOS LPAR.')
        return False
    if not check_host(lpar.rmc_ip):
        # If the rmc_ip is unreachable, something is wrong at the networking level
        # since the HMC did reach it.
        print_red('Error during connection to LPAR: ' + lpar.name + ', please check log file and run '
                                                                    'oscollector manually')
        logger.error('Error during connection to LPAR: ' + lpar.name + ', please check log file and run '
                                                                       'oscollector manually')
        return False
    for attempt in range(5):
        print('Please input username and password or press enter to use the proposed value.')
        # Ask for input, if the input is empty, use the current value
        username = input('Username for LPAR: ' + lpar.name + ' (' + username + '): ') or username
        password = input('Password for user ' + username + ' (' + password + '): ') or password
        try:
            lpar_ssh = RemoteClient(host=lpar.rmc_ip, user=username, password=password, remote_path='.')
            lpar_ssh.execute_command('hostname', 10)
            logger.info('Authentication successful.')
        except AuthenticationException:
            if attempt == 4:
                return False
            logger.info('Authentication error. Retrying connection with LPAR:' + lpar.name +
                        ', attempt ' + str(attempt + 2) + ' of 5')
            print_red('Authentication error. Retrying connection with LPAR ' + lpar.name +
                      ', attempt ' + str(attempt + 2) + ' of 5')
        except Exception as e:
            # Any other exception, abort connection and move to next LPAR
            print_red('Error during connection to LPAR: ' + lpar.name +
                      ', please check log file and run oscollector manually on the LPAR.')
            if __debug__:
                logger.exception(e)
            logger.error('Error during connection to LPAR: ' + lpar.name +
                         ', please check previous messages and run oscollector manually on the LPAR.')
            return False
        # Fun Fact: Try Except blocks also have an else condition, it's triggered when it exits cleanly.
        else:
            # Once we got a connection to the LPAR, send the file, exec the script and retrieve the file.
            try:
                if system_name is None:
                    output_file = lpar.name.replace(' ', '-') + '-' + today
                else:
                    output_file = system_name.replace(' ', '-') + '-' + lpar.name.replace(' ', '-') + '-' + today
                # If the LPAR is VIOS, we need to execute as root instead of padmin
                # How to find out if LPAR is VIOS:
                # 1. Run lsdev searching for vios0 device. Newer VIOSes might answer, olders might not.
                # 2. If there's no answer, try again with oem_setup_env, VIOS WILL answer, AIX will not.
                set_vios = False
                if not lpar.env:
                    logger.info('Detecting LPAR OS.')
                    response, _ = lpar_ssh.execute_command('uname -s', 30, want_errors=True)
                    if not response:
                        response, _ = lpar_ssh.execute_command('lsdev | grep vios0', 30,
                                                               vios=True, want_errors=True)
                        if response:
                            # VIOS doesn't run some commands via exec and the vios0 device only exists on VIOS
                            logger.info('Detected a VIOS LPAR.')
                            lpar.env = 'vioserver'
                        else:
                            logger.info('Detected an AIX/Linux LPAR')
                            lpar.env = 'aixlinux'
                    else:
                        logger.info('Detected an AIX/Linux LPAR')
                        lpar.env = 'aixlinux'
                if 'vioserver' in lpar.env:
                    set_vios = True
                # Cleanup file if it exists, then upload
                lpar_ssh.execute_command('rm /f ' + oscollector, 60, vios=set_vios)
                lpar_ssh.upload_file(path_to_oscollector + '\\' + oscollector)
                lpar_ssh.execute_command('chmod 777 ' + oscollector, 30, vios=set_vios)
                response = lpar_ssh.execute_command('ksh ./' + oscollector, 900, vios=set_vios)
                # Check the output to find the generated filename OR raise an alert due to the script failing.
                old_name = None
                for line in response:
                    if 'genero el archivo' in line:
                        regex = re.compile('(?<=vo ).*tar')
                        found = regex.search(line)
                        old_name = found.group(0)
                        break
                if not old_name:
                    print_red('Error encountered during transfer or execution of script on LPAR: ' + lpar.name +
                              ', please check log file and run oscollector manually on the LPAR.')
                    logger.error(
                        'Error encountered during transfer or execution of script on LPAR: ' + lpar.name +
                        ', please check previous messages and run oscollector manually on the LPAR.')
                    return False
                # Rename and download the file.
                lpar_ssh.execute_command('mv ' + old_name + ' ' + output_file + '.tar', 60,
                                         want_errors=True, vios=set_vios)
                old_name = old_name.replace('.tar', '')
                lpar_ssh.download_file(output_file + '.tar', output_path)
            except Exception as e:
                print_red('Error encountered during transfer or execution of script on LPAR: ' + lpar.name +
                          ', please check log file and run oscollector manually on the LPAR.')
                if __debug__:
                    logger.exception(e)
                logger.error('Error encountered during transfer or execution of script on LPAR: ' + lpar.name +
                             ', please check previous messages and run oscollector manually on the LPAR.')
                return False
            else:
                return True
            finally:
                try:
                    logger.info('Starting cleanup on LPAR: ' + lpar.name)
                    lpar_ssh.execute_command('rm ' + old_name + '-config.txt', 30, want_errors=True, vios=set_vios)
                    lpar_ssh.execute_command('rm ' + old_name + '-error.txt', 30, want_errors=True, vios=set_vios)
                    lpar_ssh.execute_command('rm ' + old_name + '-lsgcl.txt', 30, want_errors=True, vios=set_vios)
                    lpar_ssh.execute_command('rm ' + oscollector, 60, want_errors=True, vios=set_vios)
                    lpar_ssh.execute_command('rm ' + old_name + '.tar', 30, want_errors=True, vios=set_vios)
                    lpar_ssh.execute_command('rm ' + output_file + '.tar', 30, want_errors=True, vios=set_vios)
                except:
                    print_red('Error encountered during cleanup on LPAR: ' + lpar.name +
                              ', please check log file and delete the files manually on the LPAR.')
                    if __debug__:
                        logger.exception(e)
                    logger.error('Error encountered during during cleanup on LPAR: ' + lpar.name +
                                 ', please check previous messages and delete the files manually on the LPAR.')
                    return False
                lpar_ssh.disconnect()
    # Another Fun Fact: For loops ALSO have else conditions, this one is triggered on loop reaching the end.
    else:
        print_red('Error during connection to LPAR: ' + lpar.name + ', please check log file.')
        logger.error('Error during connection to LPAR: ' + lpar.name + ', please check previous messages.')
        return False


def is_hmc(hmc):
    """
    : Checks if the host is an HMC
    : Takes an SSHClient object as input
    """
    try:
        response = hmc.execute_command('lshmc -v | grep Console', 10)
        for line in response:
            if '*DS Hardware Management Console' in line:
                return True
        else:
            return False
    except Exception as e:
        raise e


def run_hmc_scan(hmc_scan_path, base_dir, hmc, user, password, output_path):
    # Check that the supplied path exists AND JAVA is installed
    if not os.path.exists(hmc_scan_path + '\\' + 'hmcScanner.jar'):
        logger.error('Missing HMC Scanner files, aborting HMC Scanner invocation.')
        return False
    java = check_java(base_dir)
    if java:
        hmc_scanner_command = java + ' -Duser.language=en -cp "' + hmc_scan_path + '\\' + 'jsch-0.1.55.jar";"' + \
                              hmc_scan_path + '\\' + 'hmcScanner.jar";"' + hmc_scan_path + '\\' + \
                              'jxl.jar" hmcScanner.Loader ' + hmc + ' ' + user + ' -p ' + \
                              password + ' -dir "' + output_path + '"'
        logger.info('| Calling HMC Scanner: ' + hmc_scanner_command)
        subprocess.run(hmc_scanner_command)
        return True
    else:
        logger.error('Java is not available, aborting HMC Scanner invocation.')
        return False


def exec_hmc_cmd_adapt(hmc, command, timeout):
    """
    : Execute a command on the provided and opened ssh connection to an HMC
    : check if the command fails due to invalid attributes or parameters
    : delete them and retry
    """
    try:
        out = hmc.execute_command(command, timeout)
        while 'An invalid' in out[0]:
            # This regex matches the invalid attribute OR invalid parameter
            regex = re.compile(r'(?<= is )[^ .]*|(?<=rs) [^ .]*')
            result = regex.search(out[0])
            invalid_part = result.group(0)
            # Remove the offending attribute from command, also remove trailing, leading or double :
            command = command.replace(invalid_part, '')
            command = command.replace(': ', ' ')
            command = command.replace(' :', ' ')
            command = command.replace('::', ':')
            logger.info("Retrying command without " + invalid_part)
            out = hmc.execute_command(command, timeout)
        return out
    except Exception as e:
        raise e

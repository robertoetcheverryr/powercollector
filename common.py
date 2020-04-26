# ****************************************************************************
# * powercollector.common                                                    *
# * Module for common classes and functions                                  *
# * Author: Roberto Etcheverry (retcheverry@roer.com.ar)                     *
# * Ver: 1.0.7 2020/04/26                                                    *
# ****************************************************************************

# Import logger for the main log file
from loguru import logger

# Import subprocess to run external processes
import subprocess

# Import Jsonizable to store and read the data
from jsonizable import Jsonizable
import json

# Import re to work with regular expressions
import re

# Import socket to do lowlevel networking
import socket


# Define LPAR class
# We inherit form Jsonizable, to have the ability to read and write json, the subclass Meta has a dictionary of
# how the LPAR class will be read or written
class LPAR(Jsonizable):
    # Use slots to make Python reduce RAM usage, since it doesn't use a dict to store attributes and
    # the attributes are defined from the start.
    __slots__ = ['name', 'id', 'os', 'rmc_ip', 'state']

    # All of our inits will now also accept a json object, which we'll use to call the parent class' init
    def __init__(self, json_in=None, name=None, lpar_id=None, lpar_os=None, state=None, rmc_ip=None):
        self.name = name or ''
        self.id = lpar_id or ''
        self.os = lpar_os or ''
        self.rmc_ip = rmc_ip or ''
        self.state = state or ''
        super().__init__(json_in)

    class Meta:
        schema = {
            "name": str,
            # Is it worth it to get type-happy with things like ID?
            "id": str,
            "os": str,
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
    __slots__ = ['hostname', 'domain', 'version', 'mt', 'serial']

    def __init__(self, json_in=None, hostname=None, domain=None, version=None, mt=None, serial=None):
        self.hostname = hostname or ''
        self.domain = domain or ''
        self.version = version or ''
        self.mt = mt or ''
        self.serial = serial or ''
        super().__init__(json_in)

    class Meta:
        schema = {
            "hostname": str,
            "domain": str,
            "version": str,
            "mt": str,
            "serial": str,
        }


def check_java():
    # Check for java and return the output
    outputs = subprocess.run('java -version', capture_output=True, text=True)
    regex = re.compile(' version.".*"', re.IGNORECASE)
    result = regex.search(str(outputs.stderr))
    if not result:
        return False
    else:
        return result.string


def save_hmc_data(hmc_src_, hmc_, managed_systems_, output_dir_):
    # File format: HMC object first then ManagedSystem objects
    output_file = output_dir_ + '\\' + hmc_src_ + '-SystemsManagedByHMC-' + hmc_.hostname + '.json'
    with open(output_file, "w+") as file:
        # Write HMC's JSON
        file.write(json.dumps(hmc_.write()) + '\n')
        # Write Managed Systems' JSON
        for system_ in managed_systems_:
            file.write(json.dumps(system_.write()) + '\n')
    print('Reading written file for consistency.')
    read_hmc, read_managed_systems = read_hmc_data(output_file)
    # noinspection PyUnresolvedReferences
    if read_hmc.write() == hmc_.write():
        # HMC object is correct
        if len(read_managed_systems) == len(managed_systems_):
            # Both objects are same size
            for index, system in enumerate(managed_systems_):
                # noinspection PyUnresolvedReferences
                if read_managed_systems[index].write() != system.write():
                    print('Failure checking file consistency.')
                    logger.error('Failure checking file consistency.')
                    return False
            print('File is consistent.')
            logger.info('File is consistent.')
            return True
        else:
            print('Failure checking file consistency.')
            logger.error('Failure checking file consistency.')
            return False
    else:
        print('Failure checking file consistency.')
        logger.error('Failure checking file consistency.')
        return False


def read_hmc_data(input_):
    with open(input_, "r") as file:
        print('Attempting to open JSON File: ' + str(input_))
        logger.info('Attempting to open JSON File: ' + str(input_))
        try:
            hmc_ = HMC(json_in=json.loads(file.readline()))
        except json.JSONDecodeError as e:
            print(f'{e.msg} line {e.lineno} column {e.colno} (char {e.pos})')
            logger.error(f'{e.msg} line {e.lineno} column {e.colno} (char {e.pos})')
            if __debug__:
                logger.exception(e)
            return False
        except Exception as e:
            print('Invalid input file.')
            logger.error('Invalid input file.')
            if __debug__:
                logger.exception(e)
            return False
        else:
            try:
                managed_systems_ = []
                lines = file.readlines()
                for index, line in enumerate(lines):
                    managed_systems_.append(ManagedSystem(json_in=json.loads(line)))
                print('HMC and Managed Systems loaded successfully.')
                logger.info('HMC and Managed Systems loaded successfully.')
                return hmc_, managed_systems_
            except json.JSONDecodeError as e:
                print(f'{e.msg} line {e.lineno + index} column {e.colno} (char {e.pos})')
                logger.error(f'{e.msg} line {e.lineno + index} column {e.colno} (char {e.pos})')
                if __debug__:
                    logger.exception(e)
                return False


def check_host(hostname_):
    """
    :This function checks if a provided hostname is reachable.
    :Returns True if the host is reachable and False if not.
    :Logs to the console and logfile any problems.
    """
    try:
        host = socket.gethostbyname(hostname_)
        subprocess.run('ping -n 1 ' + host, check=True, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print('Host: ' + hostname_ + ' is not reachable.')
        logger.error('Host: ' + hostname_ + ' is not reachable.')
        return False
    except socket.error:
        print('Host: ' + hostname_ + ' is not resolvable.')
        logger.error('Host: ' + hostname_ + ' is not resolvable.')
        return False
    return True

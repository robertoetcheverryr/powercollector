# ****************************************************************************
# * powercollector                                                           *
# * This program collects HMC, Managed System, LPAR and OS data from         *
# * IBM Power systems.                                                       *
# * Author: Roberto Etcheverry (retcheverry@roer.com.ar)                     *
# * Ver: 1.0.6 2020/04/26                                                    *
# ****************************************************************************

# Import common classes and functions from common.py
from common import HMC, ManagedSystem, IOSlot, EnclosureTopology, LPAR
from common import check_java, read_hmc_data, save_hmc_data, check_host

# Import the RemoteClient class from the sshclient file
from sshclient import RemoteClient

# Import logger for the main log file
from loguru import logger

# Import date to get current date
from datetime import datetime

# Import sys, exit() is only for interactive sessions, when using PyInstaller you need to use sys.exit()
import sys

# Import os to use file functions
import os

# Import pathlib to work with paths
from pathlib import Path

# Import subprocess to run external processes
import subprocess

# Import argparse and path to parse command line arguments and use path utilities
import argparse

# Import exceptions
from paramiko import AuthenticationException

# Import JSON to output json files
import json

# Import re to work with regular expressions
import re


def is_hmc(hmc_):
    """
    : Checks if the host is an HMC
    : Takes an SSHClient object as input
    """
    response_ = hmc_.execute_command('lshmc -v | grep Console', 10)
    for line_ in response_:
        if '*DS Hardware Management Console' in line_:
            return True
    else:
        return False


def run_hmc_scan(hmc_scan_path_, hmc_, user_, password_, output_path_):
    # Check that the supplied path exists AND JAVA is installed
    if os.path.exists(hmc_scan_path_):
        if not os.path.exists(hmc_scan_path_ + '\\' + 'hmcScanner.jar'):
            logger.error('Missing HMC Scanner files, aborting HMC Scanner invocation.')
            return False
        java = check_java()
        if java:
            logger.info(f'Java is available: {java}')
            hmc_scanner_command = 'java -Duser.language=en -cp "' + hmc_scan_path_ + '\\' + 'jsch-0.1.55.jar";"' + \
                                  hmc_scan_path_ + '\\' + 'hmcScanner.jar";"' + hmc_scan_path_ + '\\' + \
                                  'jxl.jar" hmcScanner.Loader ' + hmc_ + ' ' + user_ + ' -p ' + \
                                  password_ + ' -dir "' + output_path_ + '"'
            logger.info('| Calling HMC Scanner: ' + hmc_scanner_command)
            subprocess.run(hmc_scanner_command)
            return True
        else:
            logger.error('Java is not available, aborting HMC Scanner invocation.')
            return False
    else:
        return False


def save_os_level_data(managed_systems_, base_dir_, output_dir_, today_):
    # Check for oscollector.v.X.X.ksh
    if os.path.exists(base_dir_):
        oscollector = None
        for file_ in os.listdir(base_dir):
            # TODO is it faster and cleaner with regex?
            if file_.endswith('.ksh'):
                if file_.startswith('oscollector.v'):
                    if oscollector is not None:
                        # oscollector files are oscollector.v.X.x.ksh
                        # remove everything but the X.x and we can just cast it to float to test
                        curr_ver = oscollector.replace('oscollector.v', '')
                        curr_ver = curr_ver.replace('.ksh', '')
                        new_ver = file_.replace('oscollector.v', '')
                        new_ver = new_ver.replace('.ksh', '')
                        if float(new_ver) > float(curr_ver):
                            oscollector = file_
                    else:
                        oscollector = file_
        logger.info('Found oscollector file: ' + oscollector)
        if oscollector is None:
            logger.error('Missing oscollector, aborting OS-level data collection.')
            return False
    # Connect to each partition to run the collection script
    username = 'root'
    password = 'abc123'
    print('LPAR OS-level collection started.')
    logger.info('LPAR OS-level collection started.')
    for system in managed_systems_:
        print('Collection for System: ' + system.name + '\'s LPARs started.')
        logger.info('Collection for System: ' + system.name + '\'s LPARs started.')
        for lpar in system.partition_list:
            failed_lpars = []
            if 'VIOS' in lpar.os or 'AIX' in lpar.os:
                if 'Running' not in lpar.state:
                    # continue halts the current loop and moves to the next iterable, in this case, next lpar
                    failed_lpars.append(lpar)
                    continue
                print('LPAR: ' + lpar.name + '\'s OS-level collection started.')
                logger.info('LPAR: ' + lpar.name + '\'s OS-level collection started.')
                if lpar.rmc_ip == '':
                    # If the LPAR is Running but doesn't have an RMC IP Address, we cannot connect and something is
                    # wrong with the LPAR.
                    print('LPAR: ' + lpar.name + 'is an AIX or VIOS LPAR but doesn\'t have an RMC IP address. Please '
                                                 'run oscollector manually and check rmc services.')
                    logger.error('LPAR: ' + lpar.name + 'is an AIX or VIOS LPAR but doesn\'t have an RMC IP address. '
                                                        'Please run oscollector manually and check rmc services.')
                    failed_lpars.append(lpar)
                    continue
                if not check_host(lpar.rmc_ip):
                    # If the rmc_ip is unreachable, something is wrong at the networking level
                    # since the HMC did reach it.
                    print('Error during connection to LPAR: ' + lpar.name + ', please check log file and run '
                                                                            'oscollector manually')
                    logger.error('Error during connection to LPAR: ' + lpar.name + ', please check log file and run '
                                                                                   'oscollector manually')
                    failed_lpars.append(lpar)
                    continue
                for attempt in range(5):
                    print('Please input username and password or press enter to use the stored value.')
                    # Ask for input, if the input is empty, use the current value
                    username = input('Username for LPAR: ' + lpar.name + ' (' + username + '): ') or username
                    password = input('Password for user ' + username + ' (' + password + '): ') or password
                    try:
                        lpar_ssh = RemoteClient(host=lpar.rmc_ip, user=username, password=password, remote_path='.')
                        lpar_ssh.execute_command('hostname', 10)
                    except AuthenticationException:
                        logger.info('Authentication error. Retrying connection with LPAR:' + lpar.name +
                                    ', attempt ' + str(attempt + 2) + ' of 5')
                        print('Authentication error. Retrying connection with LPAR ' + lpar.name +
                              ', attempt ' + str(attempt + 2) + ' of 5')
                    except Exception as e:
                        # Any other exception, abort connection and move to next LPAR
                        print('Error during connection to LPAR: ' + lpar.name +
                              ', please check log file and run oscollector manually on the LPAR.')
                        if __debug__:
                            logger.exception(e)
                        logger.error('Error during connection to LPAR: ' + lpar.name +
                                     ', please check previous messages and run oscollector manually on the LPAR.')
                        failed_lpars.append(lpar)
                        continue
                    # Fun Fact: Try Except blocks also have an else condition, it's triggered when it exits cleanly.
                    else:
                        # Once we got a connection to the LPAR, send the file, exec the script and retrieve the file
                        try:
                            output_file = system.name + '-' + lpar.name + '-' + today_
                            lpar_ssh.upload_file(base_dir_ + '\\' + oscollector)
                            if 'VIOS' in lpar.os:
                                lpar_ssh.execute_command('chmod 777 ' + oscollector, 30, vios=True)
                                response_ = lpar_ssh.execute_command('./' + oscollector, 60, vios=True)
                            else:
                                lpar_ssh.execute_command('chmod 777 ' + oscollector, 30)
                                response_ = lpar_ssh.execute_command('./' + oscollector, 60)

                            for line in response_:
                                if 'genero el archivo' in line:
                                    # noinspection PyPep8
                                    regex = re.compile('vo .*\.tar', )
                                    old_name = regex.search(line)
                                    break
                            old_name = old_name.group(0).replace('vo ', '')
                            lpar_ssh.execute_command('mv ' + old_name + ' ' + output_file + '.tar')
                            lpar_ssh.execute_command('rm ' + old_name + '-config.txt', 30)
                            lpar_ssh.execute_command('rm ' + old_name + '-error.txt', 30)
                            lpar_ssh.execute_command('rm ' + old_name + '-lsgcl.txt', 30)
                            lpar_ssh.execute_command('rm ' + oscollector, 60)
                            lpar_ssh.download_file(output_file + '.tar', output_dir_)
                            lpar_ssh.execute_command('rm ' + output_file + '.tar', 30)
                        except Exception as e:
                            lpar_ssh.disconnect()
                            print('Error encountered during transfer or execution of script on LPAR: ' + lpar.name +
                                  ', please check log file and run oscollector manually on the LPAR.')
                            if __debug__:
                                logger.exception(e)
                            logger.error(
                                'Error encountered during transfer or execution of script on LPAR: ' + lpar.name +
                                ', please check previous messages and run oscollector manually on the LPAR.')
                            failed_lpars.append(lpar)
                            break
                        else:
                            lpar_ssh.disconnect()
                            print('LPAR: ' + lpar.name + '\'s OS-level collection completed succesfully')
                            logger.info('LPAR: ' + lpar.name + '\'s OS-level collection completed succesfully')
                            break
                # Another Fun Fact: For loops ALSO have else conditions, this one is triggered on loop reaching the end.
                else:
                    print('Error during connection to LPAR: ' + lpar.name + ', please check log file.')
                    logger.error('Error during connection to LPAR: ' + lpar.name + ', please check previous messages.')
        print('Collection for System: ' + lpar.name + '\'s LPAR\'s OS-level data completed.')
        logger.info('Collection for System: ' + lpar.name + '\'s LPAR\'s OS-level data completed.')
    print('LPAR OS-level collection completed.')
    logger.info('LPAR OS-level collection completed.')
    return True


# Program START!
try:
    # Fistly, disable logger, we'll only have console output until output_dir is defined.
    logger.remove()
    # Create parser and define arguments for the program
    parser = argparse.ArgumentParser(prog='powercollector',
                                     description='Connect to an HMC to collect configuration and events. A full '
                                                 'collection will also connect to each Running LPAR to collect '
                                                 'OS-level data. To only collect HMC-level data, use the --hmconly '
                                                 'flag. To only collect the OS-level data, provide a previously '
                                                 'generated JSON file with the --input parameter.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--hmc', metavar='hmc00', type=str, help='HMC Hostname or IP Address.')
    parser.add_argument('--user', metavar='hscroot', type=str, help='HMC Username.')
    parser.add_argument('--password', metavar='abc123', type=str, help='HMC Password.')
    parser.add_argument('--hmconly', action='store_true', help='Collect HMC and Managed Systems information only.')
    group.add_argument('--input', metavar='Path', type=Path, help='Not compatible with --hmc, specifies a previously '
                                                                  'created JSON file to use as the base for OS-level '
                                                                  'data collection.')
    parser.add_argument('--hmcscanpath', metavar='Path', type=Path, help='Path to the HMC Scanner package. Defaults to '
                                                                         'HMCScanner in the current directory')
    parser.add_argument('--output', metavar='Path', type=Path, help='Output path for all generated files. Defaults to '
                                                                    'the current directory')
    # TODO Add web service to receive data directly and implement uploading
    # parser.add_argument('--uploadurl', metavar='URL', type=str, help='URL of the webservice that receives the data.')

    # Obtain the arguments
    args = parser.parse_args()

    # If no valid input, print help and exit
    if args.input is None:
        if args.hmc is None or args.user is None or args.password is None:
            parser.print_help()
            sys.exit(0)

    print('powercollector version 1.0.6')
    # Create folder for output and set folder variables
    # now is an object, we turn that into a string with a format of our choosing
    today = datetime.now().strftime("%Y%m%d-%H-%M")

    # https://stackoverflow.com/questions/404744/determining-application-path-in-a-python-exe-generated-by-pyinstaller
    # when frozen into an exe, the path resolving methods change. In this case we want to bundle HMC Scanner OUTSIDE of
    # the exe, so we use sys._MEIPASS to obtain the exe's path
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle, the pyInstaller bootloader
        # extends the sys module by a flag frozen=True and sets the app
        # path into variable sys._MEIPASS'.
        # But app path != exe path, and that is what we need, so, changing to sys.executable
        base_dir = str(Path(sys.executable).resolve().parent)
    else:
        base_dir = str(Path(__file__).resolve().parent)

    # If the user specified the output dir, set it. Otherwise set it to the exe or script's location.
    if args.output is None:
        output_dir = base_dir
    else:
        if os.path.exists(args.output):
            output_dir = str(args.output)
        else:
            print('Output directory is invalid. Defaulting to .exe location: ' + base_dir)
            logger.error('Output directory is invalid. Defaulting to .exe location: ' + base_dir)
            output_dir = base_dir

    # If the user specified the HMC Scanner dir, set it. Otherwise set it to the exe or script's location + HMCScanner.
    if args.hmcscanpath is None:
        hmc_scan_path = base_dir + '\\' + 'HMCScanner'
    else:
        hmc_scan_path = str(args.hmcscanpath)

    # If the user specified an input file, set the output directory to the input file's. Otherwise create a new one.
    if args.hmc:
        output_dir += '\\' + args.hmc + '-' + today
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
    else:
        output_dir = str(args.input.parent)

    # Start main logging

    # logger.add(sys.stderr, level="ERROR")
    print('Base directory: ' + base_dir)
    print('Output directory: ' + output_dir)
    logger.add(output_dir + '\\' + 'powercollector-Main-log_{time:YYYY-MM-DD}.log',
               format="{time} | {level} | {module}:{function} | {message}",
               level="INFO")
    logger.info('powercollector version 1.0.6')
    logger.info('Base directory: ' + base_dir)
    logger.info('Output directory: ' + output_dir)

    # Either collect info from the specified HMC or load the specified file.
    if not args.input:
        # Connect to HMC
        if check_host(args.hmc):
            hmc = HMC()
            hmc_ssh = None
            print('Trying to connect to HMC: ' + args.hmc)
            logger.info('Trying to connect to HMC: ' + args.hmc)
            try:
                hmc_ssh = RemoteClient(host=args.hmc, user=args.user, password=args.password, remote_path='.')
                if not is_hmc(hmc_=hmc_ssh):
                    if hmc_ssh.conn is not None:
                        hmc_ssh.disconnect()
                    print('Host: ' + args.hmc + ' is not an HMC. Exiting now.')
                    logger.error('Host: ' + args.hmc + ' is not an HMC. Exiting now.')
                    sys.exit(1)

            # The PEP manual doesn't like handling broad exceptions but since we already handle
            # the exceptions in the module what is wrong with just propagating all the way to main and exiting here?
            except Exception as error:
                print('HMC Connection error - please check log file.')
                if __debug__:
                    logger.exception(error)
                logger.error('HMC Connection error - please check previous messages.')
                sys.exit(1)

            # Obtain HMC hostname, domain, mt, serial and version
            print('Connection to HMC: ' + args.hmc + ' Successful, collection started.')
            logger.info('Connection to HMC: ' + args.hmc + ' Successful, collection started.')
            response = hmc_ssh.execute_command('lshmc -n', 10)

            # Take the first line of the response, split it by comma and take the first two values only
            hmc.hostname, hmc.domain = response[0].split(',')[0:2]
            hmc.hostname = hmc.hostname.replace('hostname=', '')
            hmc.domain = hmc.domain.replace('domain=', '')

            # Obtain HMC VPD and populate remaining fields
            response = hmc_ssh.execute_command('lshmc -v', 10)
            for line in response:
                if '*TM' in line:
                    hmc.mt = line.replace('*TM ', '').replace('\n', '')
                elif '*SE' in line:
                    hmc.serial = line.replace('*SE ', '').replace('\n', '')
                elif '*RM' in line:
                    hmc.version = line.replace('*RM ', '').replace('\n', '')
                else:
                    continue

            # Query FSP connection status and write JSON file
            j_list = hmc_ssh.execute_command('lssysconn -r all', 30)
            with open(output_dir + '\\' + args.hmc + '-FSPlist.json', "w+") as f:
                f.write(json.dumps(j_list, indent=4))

            # Query all hardware events and write JSON file
            j_list = hmc_ssh.execute_command('lssvcevents -t hardware -F --header', 30)
            with open(output_dir + '\\' + args.hmc + '-AllSVCEvents.json', "w+") as f:
                f.write(json.dumps(j_list, indent=4))

            # Query open hardware events and write JSON file
            j_list = hmc_ssh.execute_command('lssvcevents -t hardware --filter "status=open" -F '
                                             'refcode:first_time:last_time:sys_name:text:analyzing_mtms:ref_code_extn'
                                             ':sys_refcode:fru_details --header', 30)
            with open(output_dir + '\\' + args.hmc + '-OpenSVCEvents.json', "w+") as f:
                f.write(json.dumps(j_list, indent=4))

            # Query HMC events and write JSON file
            j_list = hmc_ssh.execute_command('lssvcevents -t console', 30)
            with open(output_dir + '\\' + args.hmc + '-ConsoleEvents.json', "w+") as f:
                f.write(json.dumps(j_list, indent=4))

            print('HMC VPD and events collection finished.')
            logger.info('HMC VPD and events collection finished.')

            print('Managed Systems collection started.')
            logger.info('Managed Systems collection started.')
            # Obtain Managed System list
            managed_systems = []
            response = hmc_ssh.execute_command('lssyscfg -r sys -F name:type_model:serial_num', 30)

            # Split response and populate system list
            for system in response:
                sys_name, sys_mt, sys_serial = system.replace('\n', '').split(':')
                managed_systems.append(ManagedSystem(name=sys_name, mt=sys_mt, serial=sys_serial))

            # Obtain FSP levels, IO Topo, LPAR list and their IP addresses for each managed system
            # lssyscfg -r lpar -m P7Server-8233-E8B-SN10095BP -F lpar_id,name,os_version,state,rmc_ipaddr --osrefresh
            for system in managed_systems:
                print('Collection started for System: ' + system.name)
                logger.info('Collection started for System: ' + system.name)
                # Obtain FSP levels lslic -t sys -m 8233-E8B*10095BP -F
                # temp_ecnumber_primary:temp_level_primary:temp_ecnumber_secondary:temp_level_secondary
                # :perm_ecnumber_primary:perm_level_primary:perm_ecnumber_secondary:perm_level_secondary
                response = hmc_ssh.execute_command('lslic -t sys -m ' + system.name + ' -F temp_ecnumber_primary' +
                                                   ':temp_level_primary:perm_ecnumber_primary:perm_level_primary:' +
                                                   'temp_ecnumber_secondary:temp_level_secondary:' +
                                                   'perm_ecnumber_secondary:perm_level_secondary', 30)
                # Due to the long variable names, split the 8 variable assignment
                system.fsp_primary.temp_ecnumber, \
                    system.fsp_primary.temp_level, \
                    system.fsp_primary.perm_ecnumber, \
                    system.fsp_primary.perm_level, \
                    system.fsp_secondary.temp_ecnumber, \
                    system.fsp_secondary.temp_level, \
                    system.fsp_secondary.perm_ecnumber, \
                    system.fsp_secondary.perm_level = response[0].replace('\n', '').split(':')
                # Obtain system capabilities
                response = hmc_ssh.execute_command('lssyscfg -r sys -m ' + system.name + ' -F capabilities', 30)
                system.capabilities = response[0].replace('\n', '')

                # Obtain system state, if it's not Operating or Standby we cannot collect anything else
                response = hmc_ssh.execute_command('lssyscfg -r sys -m ' + system.name + ' -F state', 30)

                if 'Operating' in response[0] or 'Standby' in response[0]:
                    # Obtain IO slots
                    response = hmc_ssh.execute_command('lshwres -m ' + system.name + ' -r io --rsubtype slot -F ' +
                                                       'feature_codes:description:unit_phys_loc:phys_loc:drc_name')
                    try:
                        for slot in response:
                            fc, desc, upl, pl, drcn = slot.replace('\n', '').split(':')
                            system.io_slots.append(IOSlot(feature_codes=fc, description=desc, unit_phys_loc=upl,
                                                          phys_loc=pl, drc_name=drcn))
                    except Exception as e:
                        print('No IO Slot information available for System: ' + system.name + ' please check log file.')
                        if __debug__:
                            logger.exception(e)
                        logger.info('No IO Slot information available for System: ' + system.name +
                                    ' please check previous messages.')

                    # Obtain LPAR list
                    response = hmc_ssh.execute_command('lssyscfg -r lpar -m ' + system.name +
                                                       ' -F lpar_id:name:os_version:state:rmc_ipaddr --osrefresh', 30)
                    try:
                        for lpar in response:
                            l_id, lpar_name, l_os, running, lpar_rmc_ip = lpar.replace('\n', '').split(':')
                            system.partition_list.append(LPAR(name=lpar_name, lpar_id=l_id, lpar_os=l_os,
                                                              state=running, rmc_ip=lpar_rmc_ip))
                    except Exception as e:
                        print('No LPAR information available for System: ' + system.name + ' please check log file.')
                        if __debug__:
                            logger.exception(e)
                        logger.info('No LPAR information available for System: ' + system.name +
                                    ' please check previous messages.')
                    # Obtain IO topology
                    response = hmc_ssh.execute_command('lsiotopo -m ' + system.name +
                                                       ' -F slot_enclosure:leading_hub_port:trailing_hub_port', 30)
                    # Convert response to dictionary and back to list, a dictionary cannot have duplicate keys.
                    deduped_response = list(dict.fromkeys(response))

                    # Populate the system object with each enclosure (CEC included)
                    try:
                        for enclosure in deduped_response:
                            enclosure_name, leading_port, trailing_port = enclosure.replace('\n', '').split(':')
                            system.enclosure_topo.append(
                                EnclosureTopology(enclosure=enclosure_name, leading_hub_port=leading_port,
                                                  trailing_hub_port=trailing_port))
                    except Exception as e:
                        print('No IO Topology information available for System: ' + system.name +
                              ' please check log file.')
                        if __debug__:
                            logger.exception(e)
                        logger.info('No IO Topology information available for System: ' + system.name +
                                    ' please check previous messages.')

                else:
                    # If system is not powered on and connected, we cannot collect the rest of the data
                    print('System: ' + system.name + ' must be "Operating" or "Standby" for complete collection')
                    logger.info('System: ' + system.name + ' must be "Operating" or "Standby" for complete collection')

                print('Collection finished for System: ' + system.name)
                logger.info('Collection finished for System: ' + system.name)
            # Close the ssh connection
            if hmc_ssh.conn is not None:
                hmc_ssh.disconnect()

            # Save HMC + managed_systems to file
            if not save_hmc_data(hmc_src_=args.hmc, hmc_=hmc, managed_systems_=managed_systems, output_dir_=output_dir):
                # If the data saving fails for any reason, abort.
                sys.exit(1)
            if not run_hmc_scan(hmc_scan_path_=hmc_scan_path, hmc_=args.hmc, user_=args.user,
                                password_=args.password, output_path_=output_dir):
                print('HMC Scanner run was aborted. Please check the log file and run it manually')
                logger.error('HMC Scanner run was aborted. Please check previous messages and run it manually')
            # If only collecting HMC info, exit now
            if args.hmconly:
                print('powercollector has completed succesfully.')
                logger.info('powercollector has completed succesfully.')
                sys.exit(0)
            else:
                save_os_level_data(managed_systems_=managed_systems, base_dir_=base_dir,
                                   output_dir_=output_dir, today_=today)
        else:
            print('HMC Connection error - please check log file.')
            logger.error('HMC Connection error - please check previous messages.')
            sys.exit(1)
    else:
        try:
            hmc, managed_systems = read_hmc_data(args.input)
        except Exception:
            print('Error loading file. Exiting now.')
            logger.info('Error loading file. Exiting now.')
            sys.exit(1)
        save_os_level_data(managed_systems_=managed_systems, base_dir_=base_dir, output_dir_=output_dir, today_=today)
    print('powercollector has completed succesfully.')
    logger.info('powercollector has completed succesfully.')
    sys.exit(0)

    # TODO: storwize collector - connect via cli - obtain snap - what else? - obtain partners and connect to them?
except KeyboardInterrupt:
    # Cleanup?
    logger.error('powercollector killed by ctrl-C. Output may be invalid.')
    print('\npowercollector killed by ctrl-C. Output may be invalid.')
    pass

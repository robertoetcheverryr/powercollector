# ****************************************************************************
# * powercollector                                                           *
# * This program collects HMC, Managed System, LPAR and OS data from         *
# * IBM Power systems.                                                       *
# * Author: Roberto Etcheverry (retcheverry@roer.com.ar)                     *
# * Ver: 1.0.11 2020/07/04                                                   *
# ****************************************************************************
# TODO Check for root or padmin when loggin into LPAR
# Import argparse and path to parse command line arguments and use path utilities
import argparse
# Import JSON to output json files
import json
# Import os to use file functions
import os
# Import sys, exit() is only for interactive sessions, when using PyInstaller you need to use sys.exit()
import sys
# Import date to get current date
from datetime import datetime
# Import pathlib to work with paths
from pathlib import Path
# Import logger for the main log file
from loguru import logger
# Import common classes and functions from common.py
from common import HMC, ManagedSystem, IOSlot, EnclosureTopology, LPAR, print_red
from common import read_hmc_data, save_hmc_data, check_host, run_hmc_scan
from common import save_os_level_data_for_sys, is_hmc, exec_hmc_cmd_adapt
# Import the RemoteClient class from the sshclient file
from sshclient import RemoteClient
from sshclient import AuthenticationException
# Import colorama for console colors
from colorama import init, Fore, Back, Style

# Program START!
try:
    # Colorama initialization
    init()
    # Firstly, disable logger, we'll only have console output until output_dir is defined.
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
    # parser.add_argument('--upload_url', metavar='URL', type=str, help='URL of the webservice that receives the data.')

    # Obtain the arguments
    args = parser.parse_args()

    # If no valid input, print help and exit
    if args.input is None:
        if args.hmc is None or args.user is None or args.password is None:
            parser.print_help()
            sys.exit(0)

    print('powercollector version 1.0.11')
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

    # If the user specified an input file, set the output directory to the input file's. Otherwise create a new one.

    # If no output nor input file are specified, use the base dir for output
    if args.output:
        output_dir = str(args.output)
    elif args.input:
        output_dir = str(args.input.parent)
    else:
        output_dir = base_dir + '\\' + args.hmc + '-' + today
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
    try:
        # Try to write to the specified directory, if it fails default to the EXE's dir.
        dir_test = open(output_dir + '\\' + 'temp.file', 'w+')
    except Exception as e:
        print_red('Output directory is invalid. Defaulting to .exe location: ' + base_dir)
        logger.error('Output directory is invalid. Defaulting to .exe location: ' + base_dir)
        if args.hmc:
            output_dir = base_dir + '\\' + args.hmc + '-' + today
        else:
            output_dir = base_dir + '\\' + today
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
    else:
        dir_test.close()
        os.remove(output_dir + '\\' + 'temp.file')

    # If the user specified the HMC Scanner dir, set it. Otherwise set it to the exe or script's location + HMCScanner.
    if args.hmcscanpath is None:
        hmc_scan_path = base_dir + '\\' + 'HMCScanner'
    else:
        hmc_scan_path = str(args.hmcscanpath)

    # Start main logging
    # logger.add(sys.stderr, level="ERROR")
    print('Base directory: ' + base_dir)
    print('Output directory: ' + output_dir)
    logger.add(output_dir + '\\' + 'powercollector-log_{time:YYYY-MM-DD}.log',
               format="{time} | {level} | {module}:{function} | {message}",
               level="INFO")
    logger.info('powercollector version 1.0.11')
    logger.info('Base directory: ' + base_dir)
    logger.info('Output directory: ' + output_dir)

    # Either collect info from the specified HMC or load the specified file.
    if args.input:
        try:
            hmc = read_hmc_data(args.input)
        except Exception:
            print_red('Error loading file. Exiting now.')
            logger.info('Error loading file. Exiting now.')
            sys.exit(1)
        save_os_level_data_for_sys(managed_systems=hmc.managed_systems, base_dir=base_dir,
                                   output_dir=output_dir, today=today)
        print('powercollector has completed successfully.')
        logger.info('powercollector has completed successfully.')
        sys.exit(0)
    # Connect to HMC
    if not check_host(args.hmc):
        print_red('HMC not resolvable or doesn\'t answer to ICMP Ping - please check log file.')
        logger.error('HMC not resolvable or doesn\'t answer to ICMP Ping - please check previous messages.')
        sys.exit(1)
    hmc = HMC()
    hmc_ssh = None
    print('Trying to connect to HMC: ' + args.hmc)
    logger.info('Trying to connect to HMC: ' + args.hmc)
    try:
        hmc_ssh = RemoteClient(host=args.hmc, user=args.user, password=args.password, remote_path='.')
        if not is_hmc(hmc=hmc_ssh):
            if hmc_ssh.conn is not None:
                hmc_ssh.disconnect()
            print_red('Host: ' + args.hmc + ' is not an HMC. Exiting now.')
            logger.error('Host: ' + args.hmc + ' is not an HMC. Exiting now.')
            sys.exit(1)

    # The PEP manual doesn't like handling broad exceptions but since we already handle
    # the exceptions in the module what is wrong with just propagating all the way to main and exiting here?
    except AuthenticationException as error:
        print_red('HMC Connection error - Invalid User or Password - please check log file.')
        if __debug__:
            logger.exception(error)
        logger.error('HMC Connection error - Invalid User or Password - please check previous messages.')
        sys.exit(1)
    except Exception as error:
        print_red('HMC Connection error - please check log file.')
        if __debug__:
            logger.exception(error)
        logger.error('HMC Connection error - please check previous messages.')
        sys.exit(1)
    try:
        # Obtain HMC hostname, domain, mt, serial and version
        print('Connection to HMC: ' + args.hmc + ' Successful, collection started.')
        logger.info('Connection to HMC: ' + args.hmc + ' Successful, collection started.')
        response = hmc_ssh.execute_command('lshmc -n', 10)

        # Take the first line of the response, split it by comma and take the first two values only
        hmc.hostname, hmc.domain = response[0].split(',')[0:2]
        hmc.hostname = hmc.hostname.replace('hostname=', '')
        hmc.domain = hmc.domain.replace('domain=', '')
    except:
        print_red('HMC VPD Collection incomplete. Please check the log file.')
        logger.error('HMC VPD Collection incomplete. Please check previous messages.')
    try:
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
    except:
        print_red('HMC VPD collection incomplete. Please check the log file.')
        logger.error('HMC VPD collection incomplete. Please check previous messages.')
    try:
        # Query FSP connection status and write JSON file
        j_list = hmc_ssh.execute_command('lssysconn -r all', 120)
        with open(output_dir + '\\' + args.hmc + '-FSPlist.json', "w+") as f:
            f.write(json.dumps(j_list, indent=4))
    except:
        print_red('HMC Connections collection error. Please check the log file.')
        logger.error('HMC Connections collection error. Please check previous messages.')
        # Query all hardware events and write JSON file
    try:
        j_list = hmc_ssh.execute_command('lssvcevents -t hardware -F --header', 120)
        with open(output_dir + '\\' + args.hmc + '-AllSVCEvents.json', "w+") as f:
            f.write(json.dumps(j_list, indent=4))
    except:
        print_red('HMC service events collection incomplete. Please check the log file.')
        logger.error('HMC service events collection incomplete. Please check previous messages.')
    try:
        # Query open hardware events and write JSON file
        # Python says: Ask for forgiveness rather than permission, AKA, try and catch. so......
        # Since somewhere between V7R7.7 and V7.7.9 the analyzing_mtms parameter appeared...
        # just check the output and retry without that parameter...
        # look for: An invalid attribute was entered. and remove it
        cmd = 'lssvcevents -t hardware --filter "status=open" -F refcode:first_time:last_time:sys_name:' \
              'text:analyzing_mtms:ref_code_extn:sys_refcode:fru_details --header'
        j_list = exec_hmc_cmd_adapt(hmc_ssh, cmd, 120)
        with open(output_dir + '\\' + args.hmc + '-OpenSVCEvents.json', "w+") as f:
            f.write(json.dumps(j_list, indent=4))
    except:
        print_red('HMC open service events collection incomplete. Please check the log file.')
        logger.error('HMC open service events collection incomplete. Please check previous messages.')
    try:
        # Query HMC events and write JSON file
        j_list = hmc_ssh.execute_command('lssvcevents -t console', 60)
        with open(output_dir + '\\' + args.hmc + '-ConsoleEvents.json', "w+") as f:
            f.write(json.dumps(j_list, indent=4))
    except:
        print_red('HMC console events collection incomplete. Please check the log file.')
        logger.error('HMC console events collection incomplete. Please check previous messages.')
    print('HMC VPD and events collection finished.')
    logger.info('HMC VPD and events collection finished.')
    try:
        print('Managed Systems collection started.')
        logger.info('Managed Systems collection started.')
        # Obtain Managed System list
        response = hmc_ssh.execute_command('lssyscfg -r sys -F name:type_model:serial_num', 60)

        # Split response and populate system list
        for system in response:
            sys_name, sys_mt, sys_serial = system.replace('\n', '').split(':')
            hmc.managed_systems.append(ManagedSystem(name=sys_name, mt=sys_mt, serial=sys_serial))
    except:
        print_red('HMC Managed Systems collection failed. Please check the log file.')
        logger.error('HMC Managed Systems collection failed. Please check previous messages.')
        sys.exit(1)

    # Obtain FSP levels, IO Topo, LPAR list and their IP addresses for each managed system
    # lssyscfg -r lpar -m P7Server-8233-E8B-SN10095BP -F lpar_id,name,os_version,state,rmc_ipaddr --osrefresh
    for system in hmc.managed_systems:
        print('Collection started for System: ' + system.name)
        logger.info('Collection started for System: ' + system.name)
        # Obtain FSP levels lslic -t sys -m 8233-E8B*10095BP -F
        # noinspection SpellCheckingInspection
        # temp_ecnumber_primary:temp_level_primary:temp_ecnumber_secondary:temp_level_secondary
        # :perm_ecnumber_primary:perm_level_primary:perm_ecnumber_secondary:perm_level_secondary
        try:
            response = hmc_ssh.execute_command('lslic -t sys -m ' + "\"" + system.name + "\"" +
                                               ' -F temp_ecnumber_primary:temp_level_primary:' +
                                               'perm_ecnumber_primary:perm_level_primary', 30)
            # Due to the long variable names, split the 4 variable assignment
            system.fsp_primary.temp_ecnumber, \
                system.fsp_primary.temp_level, \
                system.fsp_primary.perm_ecnumber, \
                system.fsp_primary.perm_level = response[0].replace('\n', '').split(':')
        except:
            logger.error('Error obtaining primary FSP\'s data, check previous messages.')

        try:
            response = hmc_ssh.execute_command('lslic -t sys -m ' + "\"" + system.name + "\"" +
                                               ' -F temp_ecnumber_secondary:temp_level_secondary:' +
                                               'perm_ecnumber_secondary:perm_level_secondary', 30)
            if "unavailable" not in response:
                system.fsp_secondary.temp_ecnumber, \
                    system.fsp_secondary.temp_level, \
                    system.fsp_secondary.perm_ecnumber, \
                    system.fsp_secondary.perm_level = response[0].replace('\n', '').split(':')
        except:
            logger.error('Error obtaining secondary FSP\'s data, check previous messages.')
        # Obtain system capabilities - This fails safe, if the command doesn't exist, it'll store that response
        response = hmc_ssh.execute_command('lssyscfg -r sys -m ' + "\"" + system.name + "\"" + ' -F capabilities', 30)
        system.capabilities = response[0].replace('\n', '')

        # Obtain system state, if it's not Operating or Standby we cannot collect anything else
        response = hmc_ssh.execute_command('lssyscfg -r sys -m ' + "\"" + system.name + "\"" + ' -F state', 30)

        if 'Operating' in response[0] or 'Standby' in response[0]:
            # Obtain IO slots
            try:
                response = hmc_ssh.execute_command('lshwres -m ' + "\"" + system.name + "\"" +
                                                   ' -r io --rsubtype slot -F feature_codes:description:' +
                                                   'unit_phys_loc:phys_loc:drc_name')
                for slot in response:
                    fc, desc, upl, pl, drcn = slot.replace('\n', '').split(':')
                    system.io_slots.append(IOSlot(feature_codes=fc, description=desc, unit_phys_loc=upl,
                                                  phys_loc=pl, drc_name=drcn))
            except Exception as e:
                print_red('Error during IO Slot collection for System: ' + system.name + ' please check log file.')
                if __debug__:
                    logger.exception(e)
                logger.info('Error during IO Slot collection for System: ' + system.name +
                            ' please check previous messages.')

            # Obtain LPAR list
            try:
                command = 'lssyscfg -r lpar -m ' + "\"" + system.name + "\"" + \
                          ' -F lpar_id:name:lpar_env:state'
                response = hmc_ssh.execute_command(command, 120)
                for lpar in response:
                    l_id, l_name, l_env, running = lpar.replace('\n', '').split(':')
                    system.partition_list.append(LPAR(name=l_name, lpar_id=l_id, state=running, lpar_env=l_env))
                for lpar in system.partition_list:
                    command = 'lssyscfg -r lpar -m ' + "\"" + system.name + "\"" + \
                              ' --filter \"lpar_names=' + lpar.name + \
                              '\" -F os_version:rmc_ipaddr --header --osrefresh'
                    response = exec_hmc_cmd_adapt(hmc_ssh, command, 120)
                    if "rmc_ipaddr" in response[0]:
                        lpar.os_level, lpar.rmc_ip = response[1].replace('\n', '').split(':')
                    elif "os_version" in response[0]:
                        lpar.os_level = response[1].replace('\n', '')

            except Exception as e:
                print_red('Error during LPAR information collection for System: ' + system.name +
                          ' please check log file.')
                if __debug__:
                    logger.exception(e)
                logger.info('Error during LPAR information collection for System: ' + system.name +
                            ' please check previous messages.')
            try:
                # Obtain IO topology
                response = hmc_ssh.execute_command('lsiotopo -m ' + "\"" + system.name + "\"" +
                                                   ' -F slot_enclosure:leading_hub_port:trailing_hub_port', 30)
                # Convert response to dictionary and back to list, a dictionary cannot have duplicate keys.
                deduped_response = list(dict.fromkeys(response))

                # Populate the system object with each enclosure (CEC included)
                for enclosure in deduped_response:
                    enclosure_name, leading_port, trailing_port = enclosure.replace('\n', '').split(':')
                    system.enclosure_topo.append(
                        EnclosureTopology(enclosure=enclosure_name, leading_hub_port=leading_port,
                                          trailing_hub_port=trailing_port))
            except Exception as e:
                print_red('Error during IO Topology collection for System: ' + system.name +
                          ' please check log file.')
                if __debug__:
                    logger.exception(e)
                logger.info('Error during IO Topology collection for System: ' + system.name +
                            ' please check previous messages.')

        else:
            # If system is not powered on and connected, we cannot collect the rest of the data
            print_red('System: ' + system.name + ' must be "Operating" or "Standby" for complete collection')
            logger.info('System: ' + system.name + ' must be "Operating" or "Standby" for complete collection')

        print('Collection finished for System: ' + system.name)
        logger.info('Collection finished for System: ' + system.name)

    # Save HMC + managed_systems to file
    if not save_hmc_data(hmc_src=args.hmc, hmc=hmc, output_dir=output_dir):
        # If the data saving fails for any reason, abort.
        sys.exit(1)
    if not run_hmc_scan(hmc_scan_path=hmc_scan_path, hmc=args.hmc, user=args.user,
                        password=args.password, output_path=output_dir):
        print_red('HMC Scanner run was aborted. Please check the log file and run it manually')
        logger.error('HMC Scanner run was aborted. Please check previous messages and run it manually')

    # viosvrcmd -m 9406-570*A0001234 --id 4 -c "lsdev -virtual"
    for system in hmc.managed_systems:
        for lpar in system.partition_list:
            if "vioserver" in lpar.env and "Running" in lpar.state:
                try:
                    j_list = hmc_ssh.execute_command('viosvrcmd -m ' + "\"" + system.name + "\"" +
                                                     ' --id ' + lpar.id + ' -c "errlog"')
                    j_list += hmc_ssh.execute_command('viosvrcmd -m ' + "\"" + system.name + "\"" +
                                                      ' --id ' + lpar.id + ' -c "errlog -ls"')
                    with open(output_dir + '\\' + system.name + '-' + lpar.name + '-ErrorLog.json', "w+") as f:
                        f.write(json.dumps(j_list, indent=4))
                except:
                    print_red('Error trying to get error log from VIOS: ' + lpar.name + ' for system: ' + system.name)
                    if __debug__:
                        logger.exception(e)
                    logger.info('Error trying to get error log from VIOS: ' + lpar.name + ' for system: ' + system.name)
                try:
                    j_list = hmc_ssh.execute_command('viosvrcmd -m ' + "\"" + system.name + "\"" +
                                                     ' --id ' + lpar.id + ' -c "lsdev -vpd"')

                    with open(output_dir + '\\' + system.name + '-' + lpar.name + '-vpd.json', "w+") as f:
                        f.write(json.dumps(j_list, indent=4))
                except:
                    print_red('Error trying to get VPD from VIOS: ' + lpar.name + ' for system: ' + system.name)
                    if __debug__:
                        logger.exception(e)
                    logger.info('Error trying to get VPD from VIOS: ' + lpar.name + ' for system: ' + system.name)

    # If only collecting HMC info, exit now
    # Close the ssh connection
    if hmc_ssh.conn is not None:
        hmc_ssh.disconnect()
    if args.hmconly:
        print('powercollector has completed successfully with --hmconly. '
              'Please run oscollector manually on the LPARs if the managed system is running.')
        logger.info('powercollector has completed successfully --hmconly. '
                    'Please run oscollector manually on the LPARs if the managed system is running.')
        sys.exit(0)
    else:
        save_os_level_data_for_sys(managed_systems=hmc.managed_systems, base_dir=base_dir,
                                   output_dir=output_dir, today=today)
    print('powercollector has completed successfully.')
    logger.info('powercollector has completed successfully.')
    sys.exit(0)

except KeyboardInterrupt:
    # Cleanup?
    logger.error('powercollector killed by ctrl-C. Output may be invalid.')
    print_red('powercollector killed by ctrl-C. Output may be invalid.')

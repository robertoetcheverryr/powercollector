# ****************************************************************************
# * oscollectorHelper                                                        *
# * This program simplifies running oscollector on one or more LPARs         *
# * it uploads and runs the .ksh file and downloads the results              *
# * Author: Roberto Etcheverry (retcheverry@roer.com.ar)                     *
# * Ver: 1.0.0 2020/04/26                                                    *
# ****************************************************************************

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
# Import colorama for console colors
from colorama import init, Fore, Back, Style
# Import from common
from common import LPAR, print_red, save_lpar_os_data, get_oscollector


def load_lpar_list(list_file):
    with open(list_file, "r") as file:
        print('Attempting to open JSON File: ' + str(list_file))
        logger.info('Attempting to open JSON File: ' + str(list_file))
        lpar_list = []
        try:
            lines = file.readlines()
            for line in lines:
                lpar_list.append(LPAR(json_in=json.loads(line)))
            return lpar_list
        except json.JSONDecodeError as e:
            print_red(f'{e.msg} line {e.lineno} column {e.colno} (char {e.pos})')
            logger.error(f'{e.msg} line {e.lineno} column {e.colno} (char {e.pos})')
            print_red('Invalid input file.')
            logger.error('Invalid input file.')
            # noinspection PyUnreachableCode
            if __debug__:
                logger.exception(e)
            return None
        except Exception as e:
            print_red('Invalid input file.')
            logger.error('Invalid input file.')
            if __debug__:
                logger.exception(e)
            return None


# Program Start!
try:
    # colorama init
    init()
    # Firstly, disable logger, we'll only have console output until output_dir is defined.
    logger.remove()
    # Create parser and define arguments for the program
    parser = argparse.ArgumentParser(prog='oscollectorHelper',
                                     description='Connect to an LPAR to collect configuration and error log.'
                                                 ' Supports reading a JSON file for multiple LPARs.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--lpar', metavar='myAIXLPAR', type=str, help='LPAR Hostname or IP Address.')
    parser.add_argument('--user', metavar='root', type=str, help='LPAR Username.')
    parser.add_argument('--password', metavar='abc123', type=str, help='LPAR Password.')
    group.add_argument('--input', metavar='Path', type=Path, help='Not compatible with --lpar, specifies a JSON file'
                                                                  ' listing the LPARs on which to run oscollector.')
    parser.add_argument('--output', metavar='Path', type=Path, help='Output path for all generated files. Defaults to '
                                                                    'the current directory.')

    # Obtain the arguments
    args = parser.parse_args()

    # If no valid input, print help and exit
    if args.input is None:
        if args.lpar is None or args.user is None or args.password is None:
            parser.print_help()
            sys.exit(0)

    print('oscollectorHelper version 1.0.0')
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
        output_dir = base_dir + '\\' + 'oscollector-output-' + today
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
    try:
        # Try to write to the specified directory, if it fails default to the exe's dir.
        dir_test = open(output_dir + '\\' + 'temp.file', 'w+')
    except Exception as e:
        print_red('Output directory is invalid. Defaulting to .exe location: ' + base_dir)
        logger.error('Output directory is invalid. Defaulting to .exe location: ' + base_dir)
        output_dir = base_dir + '\\' + 'oscollector-output-' + today
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
    else:
        dir_test.close()
        os.remove(output_dir + '\\' + 'temp.file')

    # Start main logging
    # logger.add(sys.stderr, level="ERROR")
    print('Base directory: ' + base_dir)
    print('Output directory: ' + output_dir)
    logger.add(output_dir + '\\' + 'oscollectorHelper-log_{time:YYYY-MM-DD}.log',
               format="{time} | {level} | {module}:{function} | {message}",
               level="INFO")
    logger.info('powercollector version 1.0.7')
    logger.info('Base directory: ' + base_dir)
    logger.info('Output directory: ' + output_dir)
    if args.lpar:
        lpars = [LPAR(name=args.lpar, rmc_ip=args.lpar, state='Running')]
    else:
        lpars = load_lpar_list(str(args.input))
    if lpars is None:
        logger.error('Failed to load LPARs. Please check previous messages')
        print_red('Failed to load LPARs. Please check previous messages')
        sys.exit(1)
    oscollector = get_oscollector(base_dir)
    if not oscollector:
        print_red('No oscollector file found. Exiting now.')
        sys.exit(1)
    for lpar in lpars:
        save_lpar_os_data(lpar=lpar, path_to_oscollector=base_dir, oscollector=oscollector, output_path=output_dir,
                          today=today, username=args.user, password=args.password)
    logger.info('oscollectorHelper has completed.')
    print('\noscollectorHelper has completed.')
    sys.exit(0)

except KeyboardInterrupt:
    # Cleanup?
    logger.error('oscollectorHelper killed by ctrl-C. Output may be invalid.')
    print_red('\noscollectorHelper killed by ctrl-C. Output may be invalid.')
    pass

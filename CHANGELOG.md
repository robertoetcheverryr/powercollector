# v1.0.7 - 26/04/2020

- Added listing of non-collected LPARs for manual collection
- Added more validation and fixed some error messages
- Improved README.md

# v1.0.6 - 26/04/2020

- Added handling of `ctrl-c`
- Other minor enhancements
- Enclosed main program in Try-Catch to catch `ctrl-c` termination
- Added additional checks for input file

# v1.0.5 - 25/04/2020

- Added a lot of validations for inputs and required files
- Added more exception handling and validation for the ssh module
- Enabled detection of oscollector file for future-proofing
- Split functionality into common.py for re-use server-side

# v1.0.3 - 23/04/2020

- Added Changelog
- Moved a lot of functionality to their own functions
- Added Java and HMC Scanner presence check
- Added Exception logging and improved error handling for SSH and File IO
- Expanded execute_command to contemplate running a root command on VIOS
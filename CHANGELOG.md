# v1.0.12 - 06/12/2020

- Fixed bug in Java detection

# v1.0.11 - 04/07/2020

- Fixed oscollector execution when remote shell is not KSH
- Changed various timeouts to be more flexible with slow systems 

# v1.0.10 - 12/06/2020

- Fixed behaviour when system or LPAR contains spaces
- Expanded viosrcmd data
- Clarified error messages
- General code cleanup

# v1.0.9 - 21/05/2020

- Added VIOS errlog and VPD collection using viosrcmd command
 
# v1.0.8 - 03/05/2020

- Extensive refactoring to enable auxiliary modules like oscollectorHelper
- Initial release of oscollectorHelper
- Solved bugs related to old HMC versions not having all the attributes or parameters for some commands
- Improved code flow using safeguard clauses instead of nesting
- Added output of non-collected LPARs, including powered off, Linux and IBM i LPARs
- Refactored HMC class to comply with JSON standards for output file
- Added lpar_env to LPAR class, this allows to better determine the running OS
- Improved LPAR collection to account for older HMC's lack of rmc_ip, --osrefresh and a plethora of other attributes

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

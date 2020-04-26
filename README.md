# powercollector v1.0.6
Powercollector is a tool to collect information from an IBM HMC (Hardware Management Console), it's Managed Systems, their hardware configuration, and PowerVM configuration.

It features JSON formatted output for the HMC, Managed Systems, and LPAR information, it also invokes HMC Scanner to obtain additional information and a pretty Excel file.
Finally, it connects to each LPAR's RMC IP Address to run oscollector to obtain OS-level configuration and error data.

__Guide:__
* [Quickstart](#quickstart)
* [Optional Parameters](#optional-parameters)
* [Credits](#credits)

## Quickstart

To use the full functionality of powercollector you need to have Java installed, the HMCScanner binaries and oscollector.v.X.x.ksh, place the HMC Scanner binaries in a folder called HMCScanner and oscollector.vX.x.ksh in the same folder as powercollector.exe

To collect all information invoke powercollector with the `--hmc`, `--user` and `--password` parameters.
The user must have authority for each Managed System and their objects, it is recommended to use the hscroot user.

After the initial HMC collection, the program will attempt to connect to each LPAR's RMC IP address and will prompt you for the credentials.
The user must be root for AIX or padmin for VIOS

A basic execution would be:
```
powercollector.exe --hmc 10.0.0.1 --user hscroot --password abc1234
```

##Optional-parameters
Currently, powercollector supports the following parameters:
```
optional arguments:
  -h, --help          show this help message and exit
  --hmc hmc00         HMC Hostname or IP Address.
  --user hscroot      HMC Username.
  --password abc123   HMC Password.
  --hmconly           Collect HMC and Managed Systems information only.
  --input Path        Not compatible with --hmc, specifies a previously
                      created JSON file to use as the base for OS-level data
                      collection.
  --hmcscanpath Path  Path to the HMC Scanner package. Defaults to HMCScanner
                      in the current directory
  --output Path       Output path for all generated files. Defaults to the
                      current directory
```

##Credits
Uses HMC Scanner by Federico Vagnini (http://ibm.biz/hmcScanner)

Uses oscollector by Leandro Villar

"Icon made by Eucalyp from www.flaticon.com"
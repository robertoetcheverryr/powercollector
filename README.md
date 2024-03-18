# powercollector v1.0.15
Powercollector is a tool to collect information from an IBM HMC (Hardware Management Console), it's Managed Systems, their hardware configuration, and PowerVM configuration.

It features JSON formatted output for the HMC, Managed Systems, and LPAR information, it also invokes HMC Scanner to obtain additional information and a pretty Excel file.
Finally, it connects to each LPAR's RMC IP Address to run oscollector and obtain OS-level configuration and error data.

__Guide:__
* [Pre-requisites](#pre-requisites)
* [Quickstart](#quickstart)
* [Optional Parameters](#optional-parameters)
* [Auxiliary programs](#auxiliary-programs)
* [Author](#author)
* [License](#license)
* [Acknowledgments](#acknowledgments)

## Pre-requisites

To use the full functionality of powercollector you need:
* Any modern Java JRE installed or bundled with powercollector (e.g. https://adoptopenjdk.net)
* HMC Scanner files (http://ibm.biz/hmcScanner)
* oscollector.v.1.0.ksh or greater

Place the HMC Scanner in a folder called HMCScanner and oscollector.vX.x.ksh in the same folder as powercollector.exe

If using a bundled Java JRE, make sure it is placed in a `jre` folder in the same folder as powercollector.exe

## Quickstart

To do a full collection, invoke powercollector with the `--hmc`, `--user` and `--password` parameters.
The user must have authority for each Managed System and their objects, it is recommended to use the hscroot user.

After the initial HMC collection, the program will attempt to connect to each LPAR's RMC IP address and will prompt you for the credentials.
The user must be root for AIX or padmin for VIOS.

A basic execution would be:
```
powercollector.exe --hmc 10.0.0.1 --user hscroot --password abc1234
```

The output will be dependant on the invocation parameters:

`--output` overrides any other parameter and will output to the specified folder.

`--hmc` will create a folder with the format: HMC-CurrentDate in powercollector's current directory.

`--input` will create a folder with the format: CurrentDate in the input file's directory.


## Optional-parameters

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

## Auxiliary-programs

oscollectorHelper is a simple tool to either specify an LPAR, user and password or  read a JSON file with an LPAR list, run oscollector on each one and obtain their OS-level data.

Examples:
```
oscollectorHelper.exe --lpar 10.0.0.1  --user root --password password
or
oscollectorHelper.exe --input lparlist.json
```

## Author

* **Roberto Jose Etcheverry Romero**  - (https://github.com/robertoetcheverryr)


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Uses HMC Scanner by Federico Vagnini (http://ibm.biz/hmcScanner)

Uses oscollector by Leandro Villar

sshclient based on work by Hackers and Slackers (https://hackersandslackers.com)

"Icon made by Eucalyp from www.flaticon.com"

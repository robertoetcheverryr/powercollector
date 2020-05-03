# oscollectorHelper 1.0.0

oscollectorHelper is an auxiliary tool for powercollector.
It allows for manual collection of OS-level data using the `--lpar` parameter for a single LPAR or `--input` for a list of LPARs in JSON format.

__Guide:__
* [Pre-requisites](#pre-requisites)
* [Quickstart](#quickstart)
* [Optional Parameters](#optional-parameters)
* [Author](#author)
* [License](#license)
* [Acknowledgments](#acknowledgments)

## Pre-requisites

oscollectorHelper is only a tool to automate oscollector, so it requires oscollector.v.1.0.ksh or greater.

Place oscollector in the same folder as oscollectorHelper.

## Quickstart

To do a single LPAR run, invoke oscollectorHelper with the `--lpar`, `--user` and `--password` parameters.
The user must be root or equivalent.

To collect multiple LPARs, use the `--input` parameter and point to the .json file

A basic execution would be:
```
oscollectorHelper.exe --lpar 10.0.0.1 --user root --password ibm123
```

The output will be dependant on the invocation parameters:

`--output` overrides any other parameter and will output to the specified folder.

`--lpar` will create a folder with the format: LPAR-CurrentDate in oscollectorHelper's current directory.

`--input` will create a folder with the format: CurrentDate in the input file's directory.


## Optional-parameters

Currently, oscollectorHelper supports the following parameters:
```
Connect to an LPAR to collect configuration and error log. Supports reading a JSON file for multiple LPARs.

optional arguments:
  -h, --help         show this help message and exit
  --lpar myAIXLPAR   LPAR Hostname or IP Address.
  --user root        LPAR Username.
  --password abc123  LPAR Password.
  --input Path       Not compatible with --lpar, specifies a JSON file listing the LPARs on which to run oscollector.
  --output Path      Output path for all generated files. Defaults to the current directory.
```

## Author

* **Roberto Jose Etcheverry Romero**  - (https://github.com/robertoetcheverryr)


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Uses oscollector by Leandro Villar

sshclient based on work by Hackers and Slackers (https://hackersandslackers.com)

"Icon made by Eucalyp from www.flaticon.com"
# powercollector v1.0.18
Powercollectorは、IBM HMC（ハードウェア管理コンソール）から情報を収集するためのツールであり、管理対象システム、そのハードウェア構成、およびPowerVM構成を含みます。

HMC、管理システム、LPAR情報のJSON形式の出力を特徴としており、追加情報を取得するためにHMCスキャナーも呼び出し、きれいなExcelファイルを生成します。最後に、各LPARのRMC IPアドレスに接続してoscollectorを実行し、OSレベルの設定およびエラーデータを取得します。

__Guide:__
* [Pre-requisites](#pre-requisites)
* [Quickstart](#quickstart)
* [Optional Parameters](#optional-parameters)
* [Auxiliary programs](#auxiliary-programs)
* [Author](#author)
* [License](#license)
* [Acknowledgments](#acknowledgments)

## Pre-requisites

Powercollectorの全機能を使用するには、以下が必要です：
* Microsoft Windows 8.1以上
* 最新のJava JREがインストールされているか、powercollectorにバンドルされていること（例：https://adoptopenjdk.net）
* HMCスキャナーファイル（http://ibm.biz/hmcScanner）
* oscollector.v1.0.ksh 以上

HMCスキャナーを「HMCScanner」というフォルダーに配置し、oscollector.vX.x.kshをpowercollector.exeと同じフォルダーに配置してください。

バンドルされたJava JREを使用している場合は、jreフォルダーを作成し、powercollector.exeと同じフォルダー内に配置してください。

## Quickstart

全コレクションを実行するには、--hmc、--user、および --password パラメーターを指定して powercollector を呼び出します。
ユーザーは各管理システムとそのオブジェクトに対する権限を持っている必要があり、hscroot ユーザーの使用が推奨されます。

初回の HMC コレクションの後、プログラムは各 LPAR の RMC IP アドレスに接続を試み、資格情報を入力するように促します。
ユーザーは AIX の場合は root、VIOS の場合は padmin である必要があります。

基本的な実行は次のとおりです：
```
powercollector.exe --hmc 10.0.0.1 --user hscroot --password abc1234
```


## Optional-parameters

Currently, powercollector supports the following parameters:
```
optional arguments:
オプションパラメーター：
  -h, --help          このヘルプメッセージを表示して終了します
  --hmc hmc00         HMCのホスト名またはIPアドレス。
  --user hscroot      HMCのユーザー名。
  --password abc123   HMCのパスワード。
  --hmconly           HMCと管理システムの情報のみを収集します。
  --viosonly          HMC、管理システム、およびVIOSの情報のみを収集します。
  --input Path        --hmcとは互換性がなく、OSレベルのデータ収集の基盤として使用する
                      以前に作成されたJSONファイルを指定します。
  --hmcscanpath Path  HMCスキャナーパッケージのパス。デフォルトは現在のディレクトリの
                      HMCScannerです。
  --output Path       すべての生成ファイルの出力パス。デフォルトは
                      現在のディレクトリです。
```

## Auxiliary-programs

oscollectorHelperは、LPAR、ユーザー名、パスワードを指定するか、LPARリストを含むJSONファイルを読み込み、それぞれのLPARでoscollectorを実行し、OSレベルのデータを取得するためのシンプルなツールです。

例：
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

# MWS Cup 2026

# プレイ方法
## インストール
以下を利用する環境にご用意ください
- python 3.14 系
- pygame-ce 2.5.8をインストール

リポジトリを取得し,依存パッケージを仮想環境にインストールしてください

**Linux / macOS**

```sh
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python src/main.py
```

**Windows（PowerShell）**

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe src/main.py
```

`requirements.txt` では,Python 3.14で使える `pygame-ce==2.5.8` を指定しています。ゲーム内での読み込み名は `pygame` です

## 起動

以下でゲームを起動します
```
python3 src/main.py
```

# Wwise Project Validator

A small Python tool that connects to a running Wwise project through WAAPI and checks it for common setup mistakes. It writes the results to a CSV report, with the rule that failed, a severity, the object path and a suggested fix, so problems can be reviewed and fixed before they reach the game build.

## What it checks

| Rule | Severity | What it finds | Why it matters |
|---|---|---|---|
| `empty-event` | Error | Events with no Actions | An Event that does nothing is usually a broken or forgotten hook, and the game will post it silently. |
| `space-in-name` | Warning | Objects with whitespace in their name | Spaces cause problems in naming conventions, scripts and engine-side lookups. |
| `main-bus` | Warning | Objects routed directly to the Main Bus | Sounds should go through a dedicated bus so they can be mixed and controlled properly. |
| `no-attenuation` | Warning | Sounds with 3D Spatialization (Position or Position + Orientation) and no Attenuation assigned | A spatialized sound with no attenuation curve plays at full volume at any distance. |

## Requirements

- Wwise (version tested: 2025.1.10.9233)
- WAAPI enabled in Wwise (Project > User Preferences > Enable Wwise Authoring API). The tool connects to the default address, `ws://127.0.0.1:8080/waapi`
- Python 3.13 (the version it was developed and tested on)
- The `waapi-client` package

Install the dependency:

```
pip install -r requirements.txt
```

## Configuration

At the top of the script, edit the `CONTAINERS` constant to list the work units or folders of your project that should be scanned for the name and bus checks:


For example:
```python
CONTAINERS = r'"\Containers\Default Work Unit", "\Containers\SFX"'
```

Each path is wrapped in double quotes and separated by commas. The Main Bus check compares against `"Bus:Main Bus"`, so if your project uses a different default bus name, change it in `checkMainBus`.

## Usage

1. Open your project in Wwise.
2. Run the script:

```
python project_validator.py
```

3. Open `validator_report.csv`, which is created next to the script.

The console prints the number of findings, the number of errors and the path of the report.

## Output

`validator_report.csv` has one row per finding:

| Column | Content |
|---|---|
| `rule` | Identifier of the check that failed (for example `empty-event`) |
| `severity` | `Error` or `Warning` |
| `name` | Name of the object |
| `type` | Wwise object type |
| `path` | Full Wwise path of the object |
| `id` | Wwise object GUID |
| `fix` | Suggested fix |

Example:

```
rule,severity,name,type,path,id,fix
empty-event,Error,Play_Door,Event,\Events\Default Work Unit\Play_Door,{00000000-0000-0000-0000-000000000000},"Add an Action to the Event, or delete it if it is unused."
```

Filter on the `rule` column in Excel or any spreadsheet tool to work through one type of problem at a time.

## Exit code

The script exits with code `1` when at least one finding has the severity `Error`, and with `0` otherwise. Warnings do not change the exit code. This makes it usable in scripts and automated checks.

## Project structure

```
project_validator.py   the validator
requirements.txt       Python dependency
.gitignore             excludes generated reports
```
from waapi import WaapiClient
from pathlib import Path
from enum import IntEnum
import re, csv, json, sys, os

VERSION = "1.1"
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "containers.json"
DEFAULT_CONTAINERS: list[str] = [r'"\Containers\Default Work Unit"']

class Option(IntEnum):
    VALIDATE = 1
    DISPLAY = 2
    #AUTO_ADD = 3
    ADD = 3
    REMOVE = 4
    EXIT = 5

def loadContainers() -> list[str]:
    if not CONFIG_FILE.exists():
        try:
            saveContainers(DEFAULT_CONTAINERS)
            print("CONTAINERS.JSON CREATED")
        except PermissionError:
            print(f"Cannot write {CONFIG_FILE}. Move the validator to a folder you can write to.", file=sys.stderr)
            sys.exit(1)
        return DEFAULT_CONTAINERS.copy()

    with CONFIG_FILE.open(encoding="utf-8") as f:
        return json.load(f)

def saveContainers(containers: list[str]) -> None:
    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        json.dump(containers, f, indent=4, ensure_ascii=False)

def checkEmptyContainer():
    if containers == []:
        input("\nThere are currently no containers inside the list. Press enter to continue: ")
        acceptInput()

def containerQuery() -> str:
    return ", ".join(containers)

def setInclusionFlag() -> None:
    isInclusionFlagSet = False
    global inclusionFlag

    while isInclusionFlagSet == False:
        inclusionFlag = None
        inclusionOption = None

        inclusionOption = input("\nDo you want to include unchecked objects from the project? (y/n/cancel)\n")
        inclusionOption = inclusionOption.lower()

        if inclusionOption == "y":
            inclusionFlag = True
            isInclusionFlagSet = True
        elif inclusionOption == "n":
            inclusionFlag = False
            isInclusionFlagSet = True
        elif inclusionOption == "cancel":
            print("\nValidation cancelled.")
            acceptInput()
        else:
            print('\nPlease type "y", "n" or "cancel" and try again.')

containers = loadContainers()

def main(option) -> None:
    match option:
        case Option.VALIDATE:
            checkEmptyContainer()
            setInclusionFlag()
            
            def makeFinding(rule, severity, obj, fix):
                finding = {
                    "rule": rule,
                    "severity": severity,
                    "name": obj["name"],
                    "type": obj["type"],
                    "path": obj["path"],
                    "id": obj["id"],
                    "fix": fix,
                }
                return finding

            def checkEmptyEvents(client):
                findings = []

                if inclusionFlag: args = {'waql': r'$ from type event where childrenCount = 0'}
                else: args = {'waql': r'$ from type event where childrenCount = 0 and Inclusion = true'}

                options = {'return': ['name', 'type', 'path', 'id']}

                result = client.call("ak.wwise.core.object.get", args, options=options)

                for obj in result["return"]:
                    findings.append(makeFinding(
                        "empty-event", "Error", obj,
                        "Add an Action to the Event, or delete it if it is unused."))

                return findings

            def checkSpacesInNames(client):
                findings = []

                if inclusionFlag: args = {'waql': f'$ {containerQuery()} select descendants'}
                else: args = {'waql': f'$ {containerQuery()} select descendants where Inclusion = true'}
                options = {'return': ['name', 'type', 'path', 'id']}

                result = client.call("ak.wwise.core.object.get", args, options=options)

                for obj in result["return"]:
                    if re.search(r"\s", obj["name"]):
                        findings.append(makeFinding(
                            "space-in-name", "Warning", obj,
                            "Rename the object with _, -, or another symbol to remove the space."))
                
                return findings

            def checkMainBus(client):
                findings = []
                if inclusionFlag: args = {'waql': f'$ {containerQuery()} select descendants where type != "AudioFileSource" and type != "Folder" and outputBus = "Bus:Main Bus"'}
                else: args = {'waql': f'$ {containerQuery()} select descendants where type != "AudioFileSource" and type != "Folder" and outputBus = "Bus:Main Bus" and Inclusion = true'}
                
                options = {'return': ['name', 'type', 'path', 'id']}

                result = client.call("ak.wwise.core.object.get", args, options=options)

                for obj in result["return"]:
                    findings.append(makeFinding(
                        "main-bus", "Warning", obj,
                        "Manually assign a bus to the object."))
                    
                return findings

            def checkNoAttenuation(client):
                findings = []
                if inclusionFlag: args = {'waql': f'$ {containerQuery()} select descendants where ListenerRelativeRouting = true and Attenuation = "No Attenuation"'}
                else: args = {'waql': f'$ {containerQuery()} select descendants where ListenerRelativeRouting = true and Attenuation = "No Attenuation" and Inclusion = true'}
                options = {'return': ['name', 'type', 'path', 'id', '3DSpatialization']}

                result = client.call("ak.wwise.core.object.get", args, options=options)

                for obj in result["return"]:
                    if obj.get("3DSpatialization") in (1, 2):
                        findings.append(makeFinding(
                            "no-attenuation", "Warning", obj,
                            "Assign an Attenuation ShareSet or set 3D Spatialization to None."))
                        
                return findings

            def writeCsv(findings, filename):
                columns = ["rule", "severity", "name", "type", "path", "id", "fix"]

                with open(filename, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=columns)
                    writer.writeheader()
                    for finding in findings:
                        writer.writerow(finding)

            try:
                with WaapiClient() as client:
                    findings = checkEmptyEvents(client) + checkSpacesInNames(client) + checkMainBus(client) + checkNoAttenuation(client)
            except ConnectionRefusedError as e:
                print(f"\n{e}\n")
                sys.exit(1)
            except RuntimeError as e:
                print(f"\n{e}\n")
                sys.exit(1)
            except TypeError:
                input("\nPlease update the Container's list to reflect your Wwise project's and try again: ")
                acceptInput()
            
            script_dir = os.path.dirname(os.path.abspath(__file__))
            csv_path = os.path.join(script_dir, "validator_report.csv")

            try:
                writeCsv(findings, csv_path)
            except PermissionError:
                print(f"\nError: cannot write {csv_path}. Close it if it is open in Excel, then run again.\n")
                acceptInput()

            # Count errors (warnings don't count)
            errors = 0
            for finding in findings:
                if finding["severity"] == "Error":
                    errors += 1

            if not len(findings):
                print("\nThe selected object(s) contain(s) no findings.\n")
                acceptInput()
            
            print(f"\n{len(findings)} finding(s), of which {errors} are errors written to {csv_path}\n")

        case Option.DISPLAY:
            checkEmptyContainer()

            print("\nYour Containers:")

            for container in containers:
                container = container.strip(r'"')
                print(f"\t- {container}")

            input("\nPress enter to continue: ")
            main(option = acceptInput())

        # TODO: case Option.AUTO_ADD: auto detect containers
        #     ...

        case Option.ADD:
            is_duplicate: bool = False
            new_container: str = str(input('\nType the name of the Container you want to add (type nothing to go back to the menu):\n\\Containers\\'))

            if new_container == "":
                new_container = None
                main(option = acceptInput())

            new_container = '"\\Containers\\' + new_container + '"'

            for container in containers:
                if new_container == container:
                    is_duplicate = True

            if is_duplicate:
                print(f'\n{new_container} already exists, please choose another name.')
                new_container = None
                main(3)
            else:
                containers.append(new_container)
                print(f"\n{new_container} has been added to the list of Containers")
                saveContainers(containers)
                new_container = None
                main(option = acceptInput())

        case Option.REMOVE:
            checkEmptyContainer()
            del_container: str = str(input("\nType the name of the Container you want to delete (type nothing to go back to the menu, type '*' to clear the list):\n\\Containers\\"))
            
            if del_container == "":
                del_container = None
                main(option = acceptInput())
            elif del_container == "*":
                containers.clear()
                saveContainers(containers)
                print("\nContainer list cleared.")
                acceptInput()

            del_container = '"\\Containers\\' + del_container + '"'

            for container in containers:
                if del_container == container:
                    containers.remove(del_container)
                    print(f"\n{del_container} has been removed from the list of Containers")
                    saveContainers(containers)
                    del_container = None
                    main(option = acceptInput())

            print(f"\n{del_container} does not exist.")
            main(4)

        case Option.EXIT:
            print("\nGoodbye.\n")
            sys.exit(0)

        case _:
            acceptInput()

# TODO: "3 = Update Containers list from opened Wwise project (auto)"
def validatorMenu() -> int:
    print("""\nPlease select an option:
    1 = Validate current project
    2 = Display Containers list
    3 = Add Containers to the list (manual)
    4 = Remove Containers from the list (manual)
    5 = Exit

    Please type in an integer from 1 to 5: 
    """)

    return input("")

def acceptInput():
    while True:
        option = 0

        try:
            option = int(validatorMenu())

            if option <= 0:
                input("\nError: integer is too small, please press enter and try again: ")
                continue
            elif option > 5:
                input("\nError: integer is too big, please press enter and try again: ")
                continue

            main(option)
        except KeyboardInterrupt:
            print("\nExited through KeyboardInterrupt.\n")
            sys.exit(0)
        except ValueError:
            input("\nError: Wrong type of value, please press enter and try again: ")
            continue
        except Exception:
            print("Error: Something went wrong.")
            sys.exit(1)

print(f"""
┌--------------------------------┐
| WAAPI Project Validator (v{VERSION}) |
└--------------------------------┘""")

acceptInput()
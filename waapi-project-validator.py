# Project Validator

from waapi import WaapiClient
import re
import csv
import os
import sys

# Add each container of your project here (e.g. "\Containers\Default Work Unit")
CONTAINERS = r'"\Containers\Default Work Unit"'

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
    args = {'waql': r'$ from type event where childrenCount = 0'}
    options = {'return': ['name', 'type', 'path', 'id']}

    result = client.call("ak.wwise.core.object.get", args, options=options)

    for obj in result["return"]:
        findings.append(makeFinding(
            "empty-event", "Error", obj,
            "Add an Action to the Event, or delete it if it is unused."))
    return findings

def checkSpacesInNames(client):
    findings = []
    args = {'waql': f'$ {CONTAINERS} select descendants'}
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
    args = {'waql': f'$ {CONTAINERS} select descendants where type != "AudioFileSource" and type != "Folder" and outputBus = "Bus:Main Bus"'}
    options = {'return': ['name', 'type', 'path', 'id']}

    result = client.call("ak.wwise.core.object.get", args, options=options)

    for obj in result["return"]:
        findings.append(makeFinding(
            "main-bus", "Warning", obj,
            "Manually assign a bus to the object."))
    return findings


def checkNoAttenuation(client):
    findings = []
    args = {'waql': f'$ {CONTAINERS} select descendants where ListenerRelativeRouting = true and Attenuation = "No Attenuation"'}
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

# Connect to the WAAPI Client
with WaapiClient() as client:
    findings = []
    findings += checkEmptyEvents(client)
    findings += checkSpacesInNames(client)
    findings += checkMainBus(client)
    findings += checkNoAttenuation(client)

script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, "validator_report.csv")

writeCsv(findings, csv_path)
print(f"{len(findings)} findings written to {csv_path}")

# Count errors (warnings don't count)
errors = 0
for finding in findings:
    if finding["severity"] == "Error":
        errors += 1

print(f"{len(findings)} findings, {errors} errors.")
print(f"CSV:  {csv_path}")

if errors > 0:
    sys.exit(1)
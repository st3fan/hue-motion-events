# Hue Motion Events Recorder
_Stefan Arentz, November 2022_

This program connects to the Philips Hue Bridge to listen to events and then record Motion events coming from Motion Sensors to a Postgres database. I wrote this because I was curious whether our cats were triggering the sensors (and this lights) at night. That story does not have a conclusion yet.

## Running

This is supposed to be a Docker container. But until that is done, basically:

Setup a Postgres database:

```shell
psql -U hue -h 1.2.3.4 -f setup.sql hue
```

Create a venv and run this thing:

```shell
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export HUE_APPLICATION_KEY=...
export HUE_BRIDGE_ADDRESS=1.2.3.4
export POSTGRES_DSN=postgresql://hue:REDACTED@1.2.3.4/hue
python main.py
```

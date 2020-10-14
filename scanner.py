"""iBeacon to MQTT bridge"""

import json
import logging
import time

import paho.mqtt.client as mqtt
from beacontools import BeaconScanner, IBeaconAdvertisement
from expiringdict import ExpiringDict

MQTT_BROKER = "192.168.1.42"
BEACON_HOLDDOWN = 15

logging.basicConfig(level=logging.DEBUG)
client = mqtt.Client()
ibeacons = ExpiringDict(max_len=100, max_age_seconds=BEACON_HOLDDOWN)


def callback(bt_addr, rssi, packet, additional_info):
    if packet.uuid in ibeacons:
        logging.debug("Skip MQTT publish for %s", packet.uuid)
        return
    ibeacons[packet.uuid] = True
    payload = {
        "timestamp": int(time.time()),
        "rssi": rssi,
        "uuid": packet.uuid,
        "major": packet.major,
        "minor": packet.minor,
        "tx_power": packet.tx_power,
    }
    mqtt_payload = json.dumps(payload)
    client.publish(f"ibeacon/{packet.uuid}", mqtt_payload)
    logging.debug("MQTT publish: %s", mqtt_payload)


logging.info("Trying to connect to MQTT broker %s", MQTT_BROKER)
client.connect(MQTT_BROKER)
logging.info("Connected to MQTT broker %s", MQTT_BROKER)

scanner = BeaconScanner(callback, packet_filter=IBeaconAdvertisement)
scanner.start()
# scanner.stop()

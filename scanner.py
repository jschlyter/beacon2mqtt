"""iBeacon to MQTT bridge"""

import argparse
import json
import logging
import time

import paho.mqtt.client as mqtt
from beacontools import BeaconScanner, IBeaconAdvertisement, IBeaconFilter
from expiringdict import ExpiringDict


def generate_callback(beacons: ExpiringDict, client: mqtt.Client, topic: str):
    """Generate callback function"""

    def callback(bt_addr, rssi, packet, additional_info):
        if packet.uuid in beacons:
            logging.debug("Skip MQTT publish for %s", packet.uuid)
            return
        beacons[packet.uuid] = True
        payload = {
            "id": packet.uuid,
            "timestamp": int(time.time()),
            "rssi": rssi,
            "uuid": packet.uuid,
            "major": packet.major,
            "minor": packet.minor,
            "tx_power": packet.tx_power,
        }
        mqtt_payload = json.dumps(payload)
        mqtt_topic = f"{topic}/{packet.uuid}"
        client.publish(mqtt_topic, mqtt_payload)
        logging.debug("MQTT publish on %s: %s", mqtt_topic, mqtt_payload)

    return callback


def main():

    parser = argparse.ArgumentParser(description="beacon2mqtt")
    parser.add_argument(
        "--broker",
        dest="mqtt_broker",
        metavar="hostname",
        help="MQTT Broker",
        default="127.0.0.1",
    )
    parser.add_argument(
        "--topic",
        dest="mqtt_topic",
        metavar="topic",
        help="MQTT Topic",
        default="ibeacons",
    )
    parser.add_argument(
        "--room", dest="room", metavar="room", help="Room name", default="default"
    )
    parser.add_argument(
        "--max-age",
        dest="max_age",
        metavar="seconds",
        help="Beacon timeout",
        type=int,
        default=10,
    )
    parser.add_argument(
        "--max-beacons",
        dest="max_beacons",
        metavar="count",
        help="Maximum number of beacons to track",
        type=int,
        default=100,
    )
    parser.add_argument(
        "--debug", dest="debug", action="store_true", help="Enable debugging"
    )
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    availability_topic = f"{args.mqtt_topic}/scanner/{args.room}"
    devices_topic = f"{args.mqtt_topic}/devices/{args.room}"
    beacons = ExpiringDict(max_len=args.max_beacons, max_age_seconds=args.max_age)

    client = mqtt.Client()

    logging.info("Trying to connect to MQTT broker %s", args.mqtt_broker)
    client.connect(args.mqtt_broker)
    logging.info("Connected to MQTT broker %s", args.mqtt_broker)

    client.will_set(availability_topic, "DISCONNECTED", retain=False)
    client.publish(availability_topic, "CONNECTED", retain=False)

    callback = generate_callback(beacons=beacons, client=client, topic=devices_topic)
    scanner = BeaconScanner(callback, packet_filter=IBeaconAdvertisement)
    scanner.start()


if __name__ == "__main__":
    main()

"""MQTT transport for hardware devices (ESP32). Everything MQTT-specific lives in this package.

Business logic never publishes MQTT: commands still go through CommandService, which
calls a Device; only ESP32MQTTDevice and MQTTManager use this package.
"""

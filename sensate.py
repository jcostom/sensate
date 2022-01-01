#!/usr/bin/python3

import usb.core
import usb.util
import sys
import os
import asyncio
import time
from kasa import SmartPlug
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

# Shift these to environment variables for Docker container
plugIP = os.getenv('plugIP')
low = int(os.getenv('low', 35))
high = int(os.getenv('high',45))
stateChangeSleep = int(os.getenv('stateChangeSleep', 1800))
monitorSleep = int(os.getenv('monitorSleep', 300))
Temperhum_Vendor = int(os.getenv('Temperhum_Vendor', 0x413d), 16)
Temperhum_Product = int(os.getenv('Temperhum_Product', 0x2107), 16)
Temperhum_Interface = int(os.getenv('Temperhum_Interface', 1))
influxBucket = os.getenv('influxBucket', "atmos")
influxOrg = os.getenv('influxOrg', "atmos")
influxToken = os.getenv('influxToken')
influxURL = os.getenv('influxURL', "http://influxdb:8086/")

Temperhum_ID = hex(Temperhum_Vendor) + ':' + hex(Temperhum_Product)
Temperhum_ID = Temperhum_ID.replace( '0x', '')

def byte_array_to_hex_string( byte_array ):
    array_size = len(byte_array)
    if array_size == 0:
        s = ""
    else:
        s = ""         
        for var in list(range(array_size)):
            b = hex(byte_array[var])
            b = b.replace( "0x", "")
            if len(b) == 1:
                b = "0" + b
            b = "0x" + b
            s = s + b + " "
    return (s.strip())

def twos_complement(value,bits):
#    value = int(hexstr,16)
    if value & (1 << (bits-1)):
        value -= 1 << bits
    return value

def c2f(celsius):
    return (celsius * 9/5) + 32

def readSensor():
    device = usb.core.find(idVendor = Temperhum_Vendor, idProduct = Temperhum_Product)
    cfg = device[0]
    inf = cfg[Temperhum_Interface,0]
    result = usb.util.claim_interface(device, Temperhum_Interface)
    ep_read = inf[0]
    ep_write = inf[1]
    ep_read_addr = ep_read.bEndpointAddress
    ep_write_addr = ep_write.bEndpointAddress

    # send request to sensor
    try:
        msg = b'\x01\x80\x33\x01\0\0\0\0'
        sendit = device.write(ep_write_addr, msg)
    except:
        print ("Error: sending request to device")
        exit(0)
    
    # read result from sensor
    try:
        data = device.read(ep_read_addr, 0x8)
    except:
        print ("Error: reading data from device")
        exit(0)
    
    C = round( ( twos_complement( (data[2] * 256) + data[3],16 ) ) / 100, 1 )
    F = int(c2f(C))
    rH = int( ( (data[4] * 256) + data[5] ) / 100 )
    result = usb.util.dispose_resources(device)
    return (C, F, rH)

async def readConsumption(ip):
    p = SmartPlug(ip)
    await p.update()
    watts = await p.current_consumption()
    return(watts)

async def plugOff(ip):
    p = SmartPlug(ip)
    await p.update()
    await p.turn_off()

async def plugOn(ip):
    p = SmartPlug(ip)
    await p.update()
    await p.turn_on()

def main():
    influxClient = InfluxDBClient(url=influxURL,token=influxToken,org=influxOrg)
    write_api = influxClient.write_api(write_options=SYNCHRONOUS)
    
    # start expecting to be in off state, turn on, sleep monitor interval
    asyncio.run(plugOn(plugIP))
    changedState = 1
    time.sleep(monitorSleep)

    # Now loop forever running checks and maintain plug on/off status
    while True:
        (degreesC, degreesF, rH) = readSensor()
        watts = asyncio.run(readConsumption(plugIP))
        print("C: {} / F: {} / rH: {} / watts: {}".format(degreesC, degreesF, rH, watts))

        if rH < low:
            asyncio.run(plugOff(plugIP))
            changedState = 1
        elif rH > high:
            asyncio.run(plugOn(plugIP))
            changedState = 1
        else:
            # no plug state change, reset changedState
            changedState = 0

        # Push data to InfluxDB Here
        record = [
            {
                "measurement": "atm_conditions",
                "tags": {
                    "location": "humidor"
                },
                "time": int(time.time()),
                "fields": {
                    "degF": degreesF,
                    "rHum": rH,
                    "power": watts
                }
            }
        ]
        write_api.write(bucket=influxBucket, record=record)

        if changedState == 0:
            time.sleep(monitorSleep)
        else:
            time.sleep(stateChangeSleep)

if __name__ == "__main__":
    main()
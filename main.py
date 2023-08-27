import asyncio
from bleak import BleakScanner, BleakClient


class AllPowersData:
    battery_percentage = 0
    dc_on = False
    ac_on = False
    torch_on = False
    output_power = 0
    input_power = 0
    minutes_remaining = 0
    haveUpdated = False


targetServiceUUID = "0000FFF0-0000-1000-8000-00805F9B34FB"
targetNotifyCharacteristicUUID = "0000FFF1-0000-1000-8000-00805F9B34FB"
targetWriteCharacteristicUUID = "0000FFF2-0000-1000-8000-00805F9B34FB"
allPowersData = AllPowersData()


def notification_handler(sender, data):
    allPowersData.battery_percentage = data[8]
    allPowersData.dc_on = data[7] >> 0 & 1 == 1
    allPowersData.ac_on = data[7] >> 1 & 1 == 1
    allPowersData.torch_on = data[7] >> 4 & 1 == 1
    allPowersData.output_power = (256 * data[11]) + data[12]
    allPowersData.input_power = (256 * data[9]) + data[10]
    allPowersData.minutes_remaining = (256 * data[13]) + data[14]
    allPowersData.haveUpdated = True


def set_bit(v, index, x):

    mask = 1 << index
    if x:
        v |= mask
    else:
        v &= ~mask
    return v


async def change_status_to_device(client: BleakClient, xdata: AllPowersData):

    full = bytes.fromhex("a56500b10101000071")
    s = bytearray(9)
    for x in range(9):
        s[x] = full[x]

    s[7] = 0
    s[7] = set_bit(s[7], 5, xdata.torch_on)
    s[7] = set_bit(s[7], 0, xdata.dc_on)
    s[7] = set_bit(s[7], 1, xdata.ac_on)

    s[8] = 113 - s[7]
    if xdata.ac_on:
        s[8] = s[8] + 4

    await client.write_gatt_char(targetWriteCharacteristicUUID, s)


async def main():
    my_device = None
    while my_device is None:
        print("Searching...")
        devices = await BleakScanner.discover()
        for d in devices:
            if d.name is not None:
                print(d.name + " - " + d.address + " - ")
                if d.name == "AP S300 V2.0":
                    print("Connecting...")
                    my_device = d
                    async with BleakClient(my_device.address) as client:
                        print("Connected")

                        for service in client.services:
                            for char in service.characteristics:
                                if "notify" in char.properties:
                                    print(char)
                                    await client.start_notify(char, notification_handler)
                        while True:
                            while not allPowersData.haveUpdated:
                                await asyncio.sleep(0.001)
                            print("Battery " + str(allPowersData.battery_percentage) + "%, AC: " + str(
                                allPowersData.ac_on) + ", DC: " + str(
                                allPowersData.dc_on) + ", Torch:" + str(allPowersData.torch_on) + ", output: " + str(
                                allPowersData.output_power) + ", input: " + str(
                                allPowersData.input_power) + ", mins: " + str(allPowersData.minutes_remaining))
                            allPowersData.haveUpdated = False
                            if not allPowersData.ac_on:
                                allPowersData.ac_on = True
                                await change_status_to_device(client, allPowersData)

asyncio.run(main())

# Tuya Tiny Web
**@readwithai** - [X](https://x.com/readwithai) - [Blog](https://readwithai.substack.com/) - [Machine-Aided Reading](https://www.reddit.com/r/machineAidedReading/) - [📖](https://readwithai.substack.com/p/what-is-reading-broadly-defined) [⚡️](https://readwithai.substack.com/s/technical-miscellany) [🖋️](https://readwithai.substack.com/p/note-taking-with-obsidian-much-of)

This is a wrapper around the [tinytuya](https://github.com/jasonacox/tinytuya) tool, which allows local access to Tuya Wi-Fi Internet of Things devices, such as power sockets and lightbulbs, without needing to connect to Tuya's cloud (except for initial setup).

## Motivation
Home automation is fun (though it requires some work in practice). Companies providing IoT devices often aim for ease of use, which involves connecting devices to their cloud infrastructure. However, the idea of someone else controlling my lightbulbs through an internet connection strikes me as a little insane, and it makes sense to want more control. Devices from these companies are often affordable, and you might buy them by mistake, so repurposing cloud-controlled IoT devices for local control is valuable.

One approach is to flash these devices with open firmware, but this doesn't always work and can be a fiddly process. Instead, you can set up a device through the Tuya infrastructure and obtain credentials (specifically a local key) to use Tuya locally. This is what tinytuya enables.

*This app* addresses a few annoyances with using tinytuya. First, if you use DHCP, you are not guaranteed to have a fixed IP address. You *could* configure your DHCP server to assign a fixed IP based on a device's MAC address, but this requires understanding your DHCP server, and I prefer to avoid using IP addresses or DNS entirely. This service periodically scans your network for Tuya devices and maps their fixed device IDs to current IP addresses.

Second, this app allows you to assign friendly names to your devices, making code easier to understand. Third, it handles secrets for IoT devices, consolidating separate credentials into an HTTP endpoint that you can secure as needed.

## Alternatives and Prior Work
This is a thin wrapper around [tinytuya](https://github.com/jasonacox/tinytuya). Tools like [Tuya Convert](https://github.com/ct-Open-Source/tuya-convert) allow you to flash *some* Tuya hardware with the [Tasmota](https://github.com/arendst/Tasmota) mini-operating system, which supports local device configuration.

## Installation
You can install tuya-tiny-web with [pipx](https://github.com/pypa/pipx):

```bash
pipx install tuya-tiny-web
```

## Usage
First set up your devices to connect to your local network with Tuya by configuring them from the Smart Tuya app. Unfortunately, this requires the network you connect to to be able to communicate with the internet, after you have configured your devices you can detach this network from the internet.

You then need to obtain the *local key* for each device. This can be done through the [Tuya developer interface](#tuya-developer). Once you have obtained both the device id and the local keys for all the devices you want to connect you must create a tuya devices file normally `tuya-devices.json` in the current directory - but see the --devices-flag.

This file has the following form:

```json
{
  "1234567890abcdef": {
    "name": "Living Room Lamp",
    "local_key": "XXXXXXXXX",
    "version": "3.3"
  },
  "abcdef1234567890": {
    "name": "Heater",
    "local_key": "XXXXXXXX",
    "version": "3.4"
  }
}
```

Where:

`name` is a user-defined label for easier reference (optional).
`local_key` is secret key used to authenticate with the device (required).
`version` is the Tuya protocol version ("3.3", "3.4", etc). (required)

Unfortunately, the developer portal does not tend to provide version info, but the version  can only take a limited number of values so you can try different versions until one works. At the time the values that this could take is: `3.1`, `3.2`, `3.3`, `3.4`, `3.5`.

## Getting local keys from the Tuya Developer portal
Getting the local keys out of the Tuya Developer portal is quite an annoying process with hidden GUI controls and out of data documentation from websites. I shall describe the process at the time of writing, but this may be out of date when you come to use the time.

1. Log into the Tuya Developer IoT portal
2. Create a 'cloud project'. This is on the left hand side bar.
3. Set the data center for this project by going to the page that lists projects clicking the ellipsis button and clicking edit. You must set the data center to match the are in which you installed the Smart Tuya app. The data centers are [listed here](https://github.com/tuya/tuya-home-assistant/wiki/Countries-Regions-and-Tuya-Data-Center).
4. Go to `Devices > Link App Account`. Then scan the code provided in the Tuya Account with the Scan option that can be reached by pressing the button in the top left.
5. You should then be able to see the device in the Manage Devices button for this linked account and copy the device id.
6. The click on the cloud icon and go to API Explorer option
7. Click on the `Query Device` api call and use the device id to obtain details.
8. This will contain the local key.

There also a *wizard* process for tinytuay which you may use.

## Caveats
Note that IoT devices can make you dependent on the power grid and Wi-Fi connections; this tool doesn't address that dependency.

Unfortunately, Tuya Wi-Fi devices must still be set up using their app and proprietary protocol before tinytuya can be used. This creates a dependency on Tuya's infrastructure, and your device may not be reconfigurable if Tuya ceases to exist, leaving it tied to a specific Wi-Fi network and password. I couldn't find a process that reverse-engineered the Tuya Wi-Fi pairing process (which is mediated by an initial Bluetooth connection).

To avoid this, you can use [Zigbee](https://en.wikipedia.org/wiki/Zigbee) devices, flash firmware (if possible for your device), or choose devices that support app-free setup (some have automatic, physical button-driven Wi-Fi pairing).

## About Me
I am **@readwithai**. I create tools for reading, research, and agency, sometimes using the markdown editor [Obsidian](https://readwithai.substack.com/p/what-exactly-is-obsidian).

I also share a [stream of tools](https://readwithai.substack.com/p/my-productivity-tools) related to my work.

I write about various topics, including tools like this, on [X](https://x.com/readwithai). My [blog](https://readwithai.substack.com/) focuses more on reading, research, and agency.

# Home Assistant integration for Husqvarna Automower

# This fork varies from @Thomas55555 as follows

- Adds a zone sensor to track the zone the mower is in.  This is configurable and supports polygon zones.
- Uses a binary error sensor that has an error number and state for attributes.
- Better mower location icon
- Allows setting a home position, this is where the mower charger is located, when the mower is home the location of the zone will indicate home and the map camera will show the mower at the charger instead of it's reported position.
- Zones can be given a color and drawn on the map camera.
- Path color for map camera is configurable.

Custom component to support Automower.


- [About](#about)
- [Supported devices](#supported-devices)
- [Installation](#installation)
  - [Installation through HACS](#installation-through-hacs)
  - [Manual installation](#manual-installation)
- [Configuration](#configuration)
  - [Husqvarna API-Key](#husqvarna-api-key)
  - [Home Assistant](#home-assistant)
  - [Camera Sensor](#Camera-sensor)
- [Usage](#usage)
- [Debugging](#Debugging)
- [Troubleshooting](#Troubleshooting)

## About

This Home Assistant integration provides status and control of supported Husqvarna  Automowers.  The official Husqvarna  [API](https://developer.husqvarnagroup.cloud/) uses websocket connection for pushed updates, so no polling is performed.  Park and Start commands including schedule overrides are supported by the integration allowing for robust automations to be implemented in Home Assistant.  Diagnostic and statics provided by the API are included with the integration for monitoring mower usage and performance.

![Screenshot of the integration](/images/screenshot_husqvarna_automower.png)

## Supported devices

Husqvarna Automowers with built-in *Automower® Connect* or with the *Automower® Connect Module* are supported.


## Installation

Requires Home Assistant 2022.9.0b0 or newer.

### Installation through HACS

Installation using Home Assistant Community Store (HACS) is recommended.

1. If HACS is not installed, follow HACS installation and configuration at https://hacs.xyz/.

2. In HACS, search under integrations for Husqvarna Automower and install.

3. Restart Home Assistant!

### Manual installation

1. Download the `husqvarna_automower.zip` file from the repository [release section](https://github.com/Thomas55555/husqvarna_automower/releases).

2. Extract and copy the content into the path `/config/custom_components/husqvarna_automower` of your HA installation.

   Do **not** download directly from the `main` branch.

3. Restart Home Assistant!

## Configuration


### Husqvarna API-Key

In order to use this integration you must properly configure OAuth2 credentials using your Husqvarna account.  Refer to [this guide](https://developer.husqvarnagroup.cloud/docs/get-started) for general overview of the process.  Username/password authentication for this integration is no longer supported as of version 2022.7.0.

Your Husqvarna account username/password used for the *Automower® Connect*  phone app is required.  Most users probably created a Husqvarna account during initial mower setup.

1. Go to <https://developer.husqvarnagroup.cloud/> and sign in with Husqvarna account.  Sign in page has password recovery/reset using registered email address if needed.  Authorize *Developer Porthole* to access Husqvarna account when prompted.

2. After signing in you will be automatically redirected to "Your applications". (Otherwise go to: <https://developer.husqvarnagroup.cloud/applications>)

3. Create a new application:

   * Name is required but can be anything, for example "My Home Assistant"

   * Description is optional

   * Redirect URL:

     ```
     https://my.home-assistant.io/redirect/oauth
     ```

     Confirm no extra spaces were appended at end of URL from copy and paste.

   * Click **CREATE**.  *Application Key* and *Application Secret* will be generated and shown.  Protect these like a username and password.

4. Click on **CONNECT NEW API** and connect the **Authentication API**

5. Click on **CONNECT NEW API** again and connect the **Husqvarna Automower API**.

6. Leave this tab open in browser and continue with Home Assistant configuration.

### Home Assistant

The My Home Assistant redirect feature needs to be setup to redirect to your home assistant installation.  See https://my.home-assistant.io/faq/ for additional information.

1. Add the integration to your home assistant installation and test the redirect feature by following below link:
   [![my_button](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=husqvarna_automower)

2. Acknowledge prompts to open link, install Husqvarna Automower integration

3. Acknowledge prompt to setup application credentials.

4. Enter the following from the Husqvrana developer tab:

   * The name of the application assigned in Step 3 above
   * Copy and paste the *Application Key* into the *OAuth Client ID* field
   * Copy and paste the *Application Secret* into the *OAuth Client Secret* field

5. Click **Create**

6. Browser will be redirected to Husqvarna Developer site.  Sign in and Authorize the integration to connect with your Husqvarna account

7. After authorizing the integration the browser will show the my Home Assistant redirect link to link this account.  Click on **Link Account**.

8. Confirm successful connection of mower and assign to an HA area if desired.

### Camera Sensor

#### Example of map camera
![Example of camera](/images/map_camera.png)

#### Example of map camera with zones enabled
![Example of camera with zones enabled](/images/map_camera_zone.png)

The camera entity is disabled by default.  The camera entity will plot the current coordinates and location history of the mower on a user provided image. To configure the entity you need to upload your desired map image and determine the coordinates of the top left corner and the bottom right corner of your selected image.

The camera entity is configured via the configure option on the integration. To enter the coordinates, ensure that they are in Signed Degree format and separated by a comma for example (40.689209, -74.044661)

You can then provide the path to the image you would like to use for the map and mower, this has been tested with the PNG format, other formats may work.

The path color can be changes by providing an RGB value such as (255,0,0).


### Configuring the zone sensor

The optional zone sensor allows zones to be designated by coorinates, this sensor will then return the name of the zone the mower is currently located.

To create a Zone, select new then enter a name for the zone and the coordinates of the zone.  Coordinates are entered in Signed Degree format with latitude and lognitude seperated by a comma and each coordinate seperated by a semi colon. You must enter at least three coordinates to define a zone. For example: ```40.689209, -74.044661; 40.689210, -74.044652; 40.689211, -74.044655``` You must select save and then submit, exiting the flow in another manner will cause any entered zones to be lost.

If disaplay zone is selected the zone will be drawn as an overlay on the map camera in the provided RGB color.  To change the color provide an RGB string such as (255,255,255).

If a Home Zone is set, the sensor will return Home and the camera will display the mower at the home location, when the mower is charging or at the docking station.

## Usage

* `vacuum.start`
  The mower continues to mow, within the specified schedule

* `vacuum.pause`
  Pauses the mower until a new command

* `vacuum.stop`
  The mower returns to the base and parks there until the next schedule starts

* `vacuum.return_to_base`
  The mower returns to the base and parks there until it gets a new start command

* `number.automower_park_for`
  Override schedule to park mower for specified number of minutes.

* `number.automower_mow_for`
  Override schedule to mow for specified number of minutes.

* `number.automower_cutting_height`
  Set mower cutting height.

* `select.automower_headlight_mode`
  Set the mower headlight operating mode

### Services

* `husqvarna_automower.calendar`
  Allows mower schedule to be revised.  Supports single schedule per day, this will override existing schedule.

  ```
  service: husqvarna_automower.calendar
  data:
    start: '11:45:00'
    end: '21:30:00'
    monday: true
    tuesday: true
    wednesday: true
    thursday: true
    friday: true
    saturday: false
    sunday: false
  target:
    entity_id: vacuum.automower
  ```
  `start` must be less than `end`.  Seconds are ignored.

* `husqvarna_automower.custom_command`
  Allows custom JSON formatted commands to be sent.

  Example equivalent to `vacuum.start`
  ```
  service: husqvarna_automower.custom_command
  data:
    command_type: actions
    json_string: >-
      {
       "data": {"type": "ResumeSchedule"}
      }
  target:
    entity_id: vacuum.automower
  ```
  See Husqvarna [API reference](https://developer.husqvarnagroup.cloud/apis/Automower+Connect+API#/swagger) for additional details.

## Debugging

To enable debug logging for this integration and related libraries you can control this in your Home Assistant `configuration.yaml` file.

Example:

```
logger:
  default: info
  logs:
    custom_components.husqvarna_automower: debug
    aioautomower: debug
```

After a restart detailed log entries will appear in `/config/home-assistant.log`.

## Troubleshooting

### Remove Credentials

The OAuth2 credentials can be removed from the home assistant user interface.  Navigate to the Integrations tab under settings.  Access the *Application Credentials* menu  by clicking on the Kebab (3 vertical dot menu icon) .  Direct link: https://my.home-assistant.io/redirect/application_credentials/

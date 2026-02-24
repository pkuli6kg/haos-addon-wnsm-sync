# Wiener Netze Smart Meter Sync

A Home Assistant add-on that fetches electricity consumption data from the official **Wiener Netze Smart Meter REST API** and publishes it to MQTT, making it available in the Home Assistant Energy Dashboard.

---

## How it works

1. Authenticates with the Wiener Netze OAuth2 server using **client credentials** (no browser, no PKCE).
2. Fetches 15-minute interval consumption data (`QUARTER_HOUR`) for the configured metering point (Zählpunkt).
3. Publishes each interval as a JSON payload to MQTT.
4. Home Assistant auto-discovers two sensors via MQTT Discovery:
   - **WNSM Energy** – per-interval consumption in kWh
   - **WNSM Sync Status** – last/next sync timestamps and error info

---

## Installation

[![Open your Home Assistant instance and show the add add-on repository dialog.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FZakiZtraki%2Fhaos-addon-wnsm-sync)

Or manually:

1. In Home Assistant, go to **Settings → Add-ons → Add-on Store**.
2. Click the **⋮** menu → **Repositories** and add:
   ```
   https://github.com/ZakiZtraki/haos-addon-wnsm-sync
   ```
3. Find **Wiener Netze Smartmeter Sync** and click **Install**.

---

## Configuration

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `CLIENT_ID` | string | ✅ | — | OAuth2 client ID from the Wiener Netze portal |
| `CLIENT_SECRET` | string | ✅ | — | OAuth2 client secret |
| `API_KEY` | string | ✅ | — | x-Gateway-APIKey for the WN Smart Meter API |
| `ZP` | string | ✅ | — | Zählpunktnummer (metering point identifier) |
| `MQTT_HOST` | string | ✅ | `core-mosquitto` | MQTT broker hostname or IP |
| `MQTT_PORT` | int | | `1883` | MQTT broker port |
| `MQTT_USERNAME` | string | | — | MQTT username (if auth required) |
| `MQTT_PASSWORD` | string | | — | MQTT password (if auth required) |
| `MQTT_TOPIC` | string | | `smartmeter/energy/state` | Base MQTT topic |
| `UPDATE_INTERVAL` | int | | `86400` | Seconds between sync cycles (min 60) |
| `HISTORY_DAYS` | int | | `1` | Days of history to fetch per cycle |
| `WERTETYP` | string | | `QUARTER_HOUR` | Data resolution: `QUARTER_HOUR` or `DAY` |
| `USE_MOCK_DATA` | bool | | `false` | Use simulated data (for testing) |
| `RETRY_COUNT` | int | | `3` | API retry attempts |
| `RETRY_DELAY` | int | | `10` | Base delay (s) between retries |
| `DEBUG` | bool | | `false` | Enable verbose logging |

### Example configuration

```yaml
CLIENT_ID: "46a6d05c-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
CLIENT_SECRET: "d1f784f0-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
API_KEY: "291919f1-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
ZP: "AT0010000000000000001000004392265"
MQTT_HOST: core-mosquitto
UPDATE_INTERVAL: 86400
HISTORY_DAYS: 1
```

---

## How to get API credentials

1. Log in to the [Wiener Netze Smart Meter Portal](https://smartmeter-web.wienernetze.at/).
2. Navigate to **API Access** or **Mein Profil → API-Zugang**.
3. Generate OAuth2 client credentials (`CLIENT_ID`, `CLIENT_SECRET`) and note the `API_KEY`.
4. Your **Zählpunktnummer** (`ZP`) is displayed in the portal under your meter details.

---

## MQTT payload format

Each 15-minute measurement is published to `MQTT_TOPIC` as:

```json
{
  "value_kwh": 0.234,
  "timestamp": "2024-01-15T00:15:00+00:00",
  "obis_code": "1-1:1.9.0",
  "quality": "VAL"
}
```

| Field | Description |
|-------|-------------|
| `value_kwh` | Energy consumed in the interval (kWh) |
| `timestamp` | UTC start of the 15-minute interval (ISO 8601) |
| `obis_code` | OBIS measurement code |
| `quality` | `VAL` (validated), `EST` (estimated), `SUB` (substituted) |

---

## Home Assistant Energy Dashboard

1. Go to **Settings → Dashboards → Energy**.
2. Under **Electricity grid**, click **Add consumption**.
3. Select the **WNSM Energy** entity.
4. Set the statistics type to **Use an integration**.

---

## Troubleshooting

**Authentication fails**
- Double-check `CLIENT_ID`, `CLIENT_SECRET`, and `API_KEY` in the portal.
- Ensure the credentials have not expired or been revoked.

**No data returned**
- Verify your `ZP` is correct (visible in the Wiener Netze portal).
- Increase `HISTORY_DAYS` if yesterday's data is not yet available (data is typically delayed by 24–48 hours).
- Enable `DEBUG: true` and check the add-on logs.

**MQTT connection refused**
- Confirm the Mosquitto add-on is running and `MQTT_HOST` is correct.
- If using authentication, set `MQTT_USERNAME` and `MQTT_PASSWORD`.

**Testing without real credentials**
- Set `USE_MOCK_DATA: true` to run the add-on with randomly generated data.

---

## License

MIT

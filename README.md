# QR Code and Barcode Reader for Home Assistant

**HACS status:** **Pending** — this integration is **not yet listed in the HACS default store**. It is under review / awaiting moderation to be added. Until then, install it as a **custom repository** in HACS (see below) or copy the files manually into `custom_components`.

---

I needed reliable QR and barcode reading inside Home Assistant. I was surprised that the obvious options were old legacy pieces that barely held together and were painful to use. So I ended up writing my own integration from scratch, with a clear config flow, sensible defaults, and decoding that actually works on real camera frames.

**Disclaimer:** this is honest-to-goodness **vibe-coded** software — I asked a large language model to help build and iterate on it (architecture, code, docs, i18n, release hygiene). Treat it like any other small OSS project: review if you care, file issues if something breaks, and enjoy the ride.

## Features

- **QR codes and common barcodes** via [pyzbar](https://github.com/NaturalHistoryMuseum/pyzbar) / ZBar.
- **Configurable preprocessing** with [Pillow](https://python-pillow.org/): original color frame, grayscale enhancements (autocontrast, histogram equalize, Otsu threshold), and optional **scaled variants** for difficult shots (CPU-heavy).
- **Automatic scanning** on an interval, or **interval `0`** for on-demand use only (call `image_processing.scan` when you need a read).
- **QR-only mode** to skip linear barcodes if you only care about QR.
- **`image_processing` entity** with decoded payload as state; last successful scan metadata in the **`scan_json`** attribute (compact JSON: decode path, symbol type, geometry, quality, orientation where available).
- **Logging**: **start of scan**, **no barcode**, and per-variant **`trying …`** lines are **`debug`**; a **successful decode** is always **`info`** with payload, decode pipeline label, and full **`scan_json`** metadata. Failures stay **`error`** / **`exception`**.
- **Translations** for all [Home Assistant frontend languages](https://github.com/home-assistant/core/blob/dev/homeassistant/generated/languages.py). **English** and **Russian** are hand-written or reviewed; other locales came from automated translation and were spot-checked — fine for the UI, occasionally a bit stiff. PRs that polish wording are welcome.

## Requirements

- Home Assistant **2024.1** or newer (see `hacs.json`).
- A working **`camera`** entity that can provide still images.
- **System ZBar libraries** for `pyzbar` (the Python wheels do not bundle native ZBar). Examples:
  - Debian/Ubuntu: `libzbar0`
  - Alpine: `zbar`
  - Many Home Assistant Container / supervised setups already ship suitable images; if you get import or decode errors, install ZBar in the environment that runs Home Assistant.

Python packages are declared in `manifest.json` (`Pillow`, `pyzbar`) and installed automatically.

## Installation

### HACS (custom repository until default listing)

1. Open HACS → **Integrations** → menu (⋮) → **Custom repositories**.
2. Repository URL: `https://github.com/ClusterM/ha-qr-code-reader`  
   Category: **Integration** → **Add**.
3. Find **QR Code and Barcode Reader** in HACS, **Download**, then **restart Home Assistant**.

**One-click (My Home Assistant):** add this repo to HACS (you still confirm in the UI):

[![Open your Home Assistant instance and open the repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ClusterM&repository=ha-qr-code-reader&category=integration)

### Manual

Copy the `custom_components/qr_code_reader` folder from this repository into your configuration directory’s `custom_components/`, then restart Home Assistant.

## Configuration

1. **Settings** → **Devices & Services** → **Add integration** → **QR Code and Barcode Reader**.
2. Pick the **camera**, optional **entity name**, **scan interval** (seconds; `0` = no automatic scans), and enable **at least one** preprocessing path (original image, grayscale enhancements, and/or scaled variants).
3. After setup, use **Configure** on the integration entry to change options without removing the device.

### Options explained

| Option | Purpose |
|--------|--------|
| **Automatic scan interval** | Seconds between snapshots. `0` disables the timer; use `image_processing.scan` or automations. |
| **Original color image** | Try decoding the raw color frame first. |
| **Grayscale and enhancements** | Autocontrast, equalize, Otsu — good default for uneven lighting. |
| **Scaled variants** | Tries multiple scales; slow — use only if the image is very poor and the host is strong enough. |
| **Ignore barcodes** | Only decode QR codes; skip other symbologies. |

## Usage

- **Entity:** `image_processing.<your_name>` — **state** is the decoded UTF-8 string, or `unknown`/empty when nothing is found (depends on HA/`image_processing` behaviour for your version).
- **Service:** `image_processing.scan` with `entity_id` targeting your scanner entity to force a capture and decode.
- **Attribute `scan_json`:** after a successful read, compact JSON with metadata about the detected symbol (for automations or logging).

## Troubleshooting

- **Nothing decodes:** improve lighting, aim, and resolution; enable **grayscale enhancements**; as a last resort try **scaled variants** on capable hardware.
- **Errors mentioning zbar / pyzbar:** install OS-level **ZBar** in the Home Assistant environment.
- **More detail while tuning:** set  
  `custom_components.qr_code_reader: debug` to see scan starts, empty results, and internal decode attempts (`trying …` variants).

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE).

## Links

- [Issue tracker](https://github.com/ClusterM/ha-qr-code-reader/issues)
- [Repository](https://github.com/ClusterM/ha-qr-code-reader)

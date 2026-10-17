# Brand assets for the Home Assistant brands repository

Home Assistant and HACS show integration icons from the central
[home-assistant/brands](https://github.com/home-assistant/brands) repository, not from the integration itself.
The folder `custom_integrations/icloud_mcp/` contains the images in the required format:

| File              | Size        | Purpose                         |
|-------------------|-------------|---------------------------------|
| `icon.png`        | 256 × 256   | integration icon                |
| `icon@2x.png`     | 512 × 512   | icon for high-DPI screens       |
| `logo.png`        | 605 × 128   | wide logo                       |
| `logo@2x.png`     | 1210 × 256  | wide logo for high-DPI screens  |
| `dark_logo.png`   | 605 × 128   | logo variant for dark themes    |
| `dark_logo@2x.png`| 1210 × 256  | dark logo for high-DPI screens  |

To publish them, fork `home-assistant/brands`, copy this folder to `custom_integrations/icloud_mcp/` and open a
pull request. Until it is merged, Home Assistant shows a generic placeholder; the integration itself (README, panel)
already uses the artwork from `../assets/`.

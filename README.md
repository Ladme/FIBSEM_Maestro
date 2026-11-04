# FIBSEM Maestro 2

![Python](https://img.shields.io/badge/python-3.14-blue?logo=python&logoColor=white)
![Platforms](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey)
[![Release](https://img.shields.io/github/v/release/cemcof/fibsem_maestro2?include_prereleases)](https://github.com/cemcof/fibsem_maestro2/releases)
[![Installer](https://img.shields.io/github/v/release/cemcof/fibsem_maestro2_installer?include_prereleases&label=installer)](https://github.com/cemcof/fibsem_maestro2_installer/releases/latest)
[![License: GPL v3](https://img.shields.io/badge/license-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![CI](https://github.com/cemcof/fibsem_maestro2/actions/workflows/ci.yml/badge.svg)](https://github.com/cemcof/fibsem_maestro2/actions/workflows/ci.yml)
![Status](https://img.shields.io/badge/status-under%20development-orange)

> [!CAUTION]
> This software is under development and many features are missing. Be cautious when using it!

Software for (cryo/RT) volume-EM acquisition. It allows to acquire the big volume in constant high quality.

## Installation

FIBSEM Maestro 2 can be installed using the [**FIBSEM Maestro 2 Installer**](https://github.com/cemcof/FIBSEM_Maestro2_Installer).

## Before you start

To control a microscope, FIBSEM Maestro needs the manufacturer's library installed on the computer.

For ThermoFisher microscopes this is **Autoscript**, which is licensed separately by ThermoFisher and is not included with FIBSEM Maestro. Linking the library is **optional**: without it, FIBSEM Maestro runs with a simulated microscope. You can link it during installation or at any time later.

If you want to link Autoscript, make a note of the folder where it is installed. It is the folder that contains a subfolder named `autoscript_sdb_microscope_client`.

Administrator rights are not required. Everything, including a private Python interpreter, is installed for the current user only.

---

## Windows

### Online installation

Use this if the computer has internet access.

1. Open the releases page of the installer repository in your browser:

   `https://github.com/cemcof/fibsem_maestro2_installer/releases/latest`

2. Under **Assets**, download
   `fibsem-maestro-installer-windows-x86_64.exe`.

3. Double-click the downloaded file to start the wizard.

   > Windows may show a "Windows protected your PC" warning because the installer is not code-signed. Click **More info**, then **Run anyway**.

4. Follow the wizard:
   - Confirm the installation folder (the default is fine).
   - Wait for the installation to finish.
   - On the **Microscope libraries** page, select your **Autoscript folder**, or leave it empty to skip.
     The wizard checks the folder right away and shows the Autoscript version when it works.

5. When it finishes, FIBSEM Maestro is available from the **Start Menu**.

### Offline installation

Use this if the microscope computer has no internet access. You will need a second computer with internet access and a USB drive.

**On the computer with internet access:**

1. Download the installer as described in steps 1–2 above.

2. Open the releases page of the application repository:

   `https://github.com/cemcof/fibsem_maestro2/releases/latest`

3. Under **Assets**, download `fibsem-maestro-bundle-windows-x86_64.tar.gz`.

4. Copy **both** files to the USB drive.

**On the microscope computer:**

5. Copy both files from the USB drive into the same folder, for example `C:\Users\<you>\Downloads\maestro\`.

6. Right-click `fibsem-maestro-bundle-windows-x86_64.tar.gz` and extract it **into that same folder**. You should end up with:

```
   maestro\
   ├── fibsem-maestro-installer-windows-x86_64.exe
   └── bundle\
       ├── uv.exe
       ├── manifest.json
       ├── python\
       └── wheels\
```

> The `bundle` folder must sit next to the `.exe`, not inside another folder!

7. Double-click the installer. The wizard will say that the installation will proceed using an offline bundle.

8. Follow the wizard as in the online instructions.

---

## Linux

> [!IMPORTANT]
> FIBSEM Maestro 2 and its installer need the `libxcb-cursor0` system library. Install it first:
>
> ```bash
> sudo apt install libxcb-cursor0
> ```
>
> Without it, neither program starts (they exit without showing a window).

### Online installation

Use this if the computer has internet access.

1. Download the installer and make it executable:

```bash
   curl -L -o fibsem-maestro-installer \
     https://github.com/cemcof/fibsem_maestro2_installer/releases/latest/download/fibsem-maestro-installer-linux-x86_64
   chmod +x fibsem-maestro-installer
```

2. Run it:

```bash
   ./fibsem-maestro-installer
```

3. Follow the wizard:
   - Confirm the installation folder (the default is fine).
   - Wait for the installation to finish.
   - On the **Microscope libraries** page, select your **Autoscript folder**, or leave it empty to skip.

4. When it finishes, FIBSEM Maestro appears in your applications menu. You can also start it from a terminal with:

```bash
   ~/.local/share/fibsem-maestro/runtime/bin/fibsem-maestro
```

### Offline installation

Use this if the microscope computer has no internet access. You will need a second computer with internet access and a USB drive.

**On the computer with internet access:**

1. Download both files into one folder:

```bash
   mkdir maestro && cd maestro

   curl -L -o fibsem-maestro-installer \
     https://github.com/cemcof/fibsem_maestro2_installer/releases/latest/download/fibsem-maestro-installer-linux-x86_64

   curl -L -O \
     https://github.com/cemcof/fibsem_maestro2/releases/latest/download/fibsem-maestro-bundle-linux-x86_64.tar.gz
```

2. Copy the whole `maestro` folder to the USB drive.

**On the microscope computer:**

3. Copy the `maestro` folder from the USB drive, then unpack the bundle
   inside it:

```bash
   cd maestro
   tar -xzf fibsem-maestro-bundle-linux-x86_64.tar.gz
   chmod +x fibsem-maestro-installer
```

You should end up with:

```
   maestro/
   ├── fibsem-maestro-installer
   └── bundle/
       ├── uv
       ├── manifest.json
       ├── python/
       └── wheels/
```

> The `bundle` folder must sit next to the installer, not inside another folder!

4. Run the installer:

```bash
   ./fibsem-maestro-installer
```

The wizard will say that the installation will proceed using an offline bundle.

5. Follow the wizard as in the online instructions.

---

## After installation

Run the installer again at any time to:

- **Update** to the latest version
- **Repair** a damaged installation
- **Manage microscope libraries**: link, change or unlink Autoscript
- **Uninstall** FIBSEM Maestro

The wizard detects the existing installation, shows which libraries are linked and offers these options instead of installing again.

---

## Troubleshooting

**"This folder does not contain `autoscript_sdb_microscope_client`"**

You selected the wrong folder. Look one level up or down from what you chose: you need the folder that _contains_ `autoscript_sdb_microscope_client`, not the subfolder itself.

**"✘ Does not work" with "Autoscript could not be imported"**

The folder was found, but Autoscript could not be loaded from it. The details below the folder show the reason. This usually means the Autoscript installation is incomplete or does not work with FIBSEM Maestro's Python version. Fix or reinstall Autoscript, or leave the field empty to install without it.

**After an update, the wizard says a linked library does not work**

The update itself has finished and FIBSEM Maestro is usable. The linked library, however, no longer loads with the new version, e.g. because the update moved FIBSEM Maestro to a newer Python. Select the correct folder or unlink the library. Without it, FIBSEM Maestro runs with the simulated microscope only.

**"FIBSEM Maestro ... requires Python ..., but this installer provides Python ..."**

The installer is older than the FIBSEM Maestro release it tried to install. Download the latest installer and run it again. Your current installation was not changed.

**"The installer says it cannot reach GitHub"**

The computer has no internet access, or it is blocked by a firewall. Use the offline installation instructions instead.

**On Linux, the installer or FIBSEM Maestro does not start at all**

Install `libxcb-cursor0` (see [Linux](#linux)). FIBSEM Maestro writes start-up errors to `~/.local/share/fibsem-maestro/logs/crash.log`.

**"Uninstall fails saying the folder is in use"**

FIBSEM Maestro is still running. Close it and try again.

---

## License

Copyright (C) 2024-2026 CEMCOF

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

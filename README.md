# FIBSEM_Maestro

> [!CAUTION]
> This software is under development and many features are missing. Be cautious when using it!

Software for (cryo/RT) volume-EM acquisition. It allows to acquire the big volume in constant high quality.  

Key features:
- Usage of deep learning model for segmentation of region of interest. The segmented region is used for:
  - Resolution calculation ([siFRC](https://github.com/prabhatkc/siFRC) or others)
  - Autofocusing, autostigmator, auto-lens alignment (multiple criterions and sweeping strategies)
  - Drift correction & FoV optimization (template matching, or segmented region centering)
  - Auto contrast-brightness (whole image or segmented region)
- Email attention
- Works with ThermoFisher Autoscript. Support of [OpenFIBSEM](https://github.com/DeMarcoLab/fibsem) for other vendors (Tescan, Zeiss) is planned.

Drift correction with segmentation aid


https://github.com/user-attachments/assets/45ff2652-db7e-494b-bb37-505d80c9be56


FoV optimization with segmentation aid


https://github.com/user-attachments/assets/0c56cf67-b3c6-4034-a15c-69c574f1049c

## Installation

FIBSEM Maestro can be installed using the [**FIBSEM Maestro Installer**](https://github.com/Ladme/FIBSEM_Maestro_Installer).

## Before you start

You need an existing **Autoscript** installation on the computer. Autoscript is licensed separately by ThermoFisher and is not included with FIBSEM Maestro.

Make a note of the folder where Autoscript is installed. You will be asked for it during installation. It is the folder that contains a subfolder named `autoscript_sdb_microscope_client`.

Administrator rights are not required. Everything is installed for the current user only.

---

## Windows

### Online installation

Use this if the computer has internet access.

1. Open the releases page of the installer repository in your browser:

   `https://github.com/Ladme/fibsem_maestro_installer/releases/latest`

2. Under **Assets**, download
   `fibsem-maestro-installer-windows-x86_64.exe`.

3. Double-click the downloaded file to start the wizard.

   > Windows may show a "Windows protected your PC" warning because the installer is not code-signed. Click **More info**, then **Run anyway**.

4. Follow the wizard:
   - Confirm the installation folder (the default is fine).
   - Select your **Autoscript folder**.
   - Click through to start the installation.

5. When it finishes, FIBSEM Maestro is available from the **Start Menu**.

### Offline installation

Use this if the microscope computer has no internet access. You will need a second computer with internet access and a USB drive.

**On the computer with internet access:**

1. Download the installer as described in step 1-2 above.

2. Open the releases page of the application repository:

   `https://github.com/Ladme/fibsem_maestro/releases/latest`

3. Under **Assets**, download `fibsem-maestro-bundle-windows-x86_64.tar.gz`.

4. Copy **both** files to the USB drive.

**On the microscope computer:**

5. Copy both files from the USB drive into the same folder, for example `C:\Users\<you>\Downloads\fibsem-maestro\`.

6. Right-click `fibsem-maestro-bundle-windows-x86_64.tar.gz` and extract it **into that same folder**. You should end up with:

```
   maestro\
   ├── fibsem-maestro-installer-windows-x86_64.exe
   └── bundle\
       ├── uv.exe
       ├── python\
       └── wheels\
```

   > The `bundle` folder must sit next to the `.exe`, not inside another folder!

7. Double-click the installer. It will say that an **offline bundle was detected** and that no internet connection is required.

8. Follow the wizard as in the online instructions.

---

## Linux

### Online installation

Use this if the computer has internet access.

1. Download the installer and make it executable:

```bash
   curl -L -o fibsem-maestro-installer \
     https://github.com/Ladme/fibsem_maestro_installer/releases/latest/download/fibsem-maestro-installer-linux-x86_64
   chmod +x fibsem-maestro-installer
```

2. Run it:

```bash
   ./fibsem-maestro-installer
```

3. Follow the wizard:
   - Confirm the installation folder (the default is fine).
   - Select your **Autoscript folder**.
   - Click through to start the installation.

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
     https://github.com/Ladme/fibsem_maestro_installer/releases/latest/download/fibsem-maestro-installer-linux-x86_64

   curl -L -O \
     https://github.com/Ladme/fibsem_maestro/releases/latest/download/fibsem-maestro-bundle-linux-x86_64.tar.gz
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
       ├── python/
       └── wheels/
```

   > The `bundle` folder must sit next to the installer, not inside another folder!

4. Run the installer:

```bash
   ./fibsem-maestro-installer
```

   It will say that an **offline bundle was detected** and that no internet connection is required.

5. Follow the wizard as in the online instructions.

---

## After installation

Run the installer again at any time to:

- **Update** to the latest version
- **Repair** a damaged installation
- **Change the Autoscript location**
- **Uninstall** FIBSEM Maestro

The wizard detects the existing installation and offers these options instead of installing again.

---

## Troubleshooting

**"This folder does not contain `autoscript_sdb_microscope_client`"**

You selected the wrong folder. Look one level up or down from what you chose - you need the folder that *contains* `autoscript_sdb_microscope_client`, not the subfolder itself.

**"The installer says it cannot reach GitHub"**

The computer has no internet access, or it is blocked by a firewall. Use the offline installation instructions instead.

**"Autoscript could not be imported"**

The folder was found, but Autoscript could not be loaded from it. This usually means the Autoscript installation is incomplete or was built for a different Python version. Reinstall Autoscript and try again.

**"Uninstall fails saying the folder is in use"**

FIBSEM Maestro is still running. Close it and try again.

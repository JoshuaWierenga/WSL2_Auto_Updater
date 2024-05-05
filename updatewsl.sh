#! /bin/bash -e
shopt -s dotglob nullglob

OUTPUT_PATH=$HOME/opt/wslautoupdater
OUTPUT_ZIP=$OUTPUT_PATH/release.zip
OUTPUT_ZIP_TEMP_DIR=$OUTPUT_PATH/WSL2_Auto_Updater-release

# Backup this script and switch to it to avoid any issues from overriding it during updating
if [ "$(realpath "$0")" = "$OUTPUT_PATH/updatewsl.sh" ] && [ "$1" != updated ]; then
    cp "$0" "$0.bak"
    "$0.bak"
    exit 0
fi

if [ "$(realpath "$0")" = "$OUTPUT_PATH/updatewsl.sh.bak" ]; then
  printf "Updating scripts\n"

  mkdir -p "$OUTPUT_PATH"
  wget https://github.com/JoshuaWierenga/WSL2_Auto_Updater/archive/refs/heads/release.zip -O "$OUTPUT_ZIP"
  unzip -o "$OUTPUT_ZIP" -d "$OUTPUT_PATH"
  mv "$OUTPUT_ZIP_TEMP_DIR"/* "$OUTPUT_PATH"
  rm "$OUTPUT_ZIP" -r "$OUTPUT_ZIP_TEMP_DIR"
fi

# Now that updating scripts is done, switch to the updated version of this script 
if [ "$(realpath "$0")" = "$OUTPUT_PATH/updatewsl.sh.bak" ]; then
  "$OUTPUT_PATH/updatewsl.sh" updated
  exit 0
fi

rm "$0.bak"

#TODO: Avoid using sudo since it can't be automated, use wsl.exe instead?
sudo apt update
sudo apt upgrade
python ./updatekernel.py

#!/bin/bash

# Script expects 4 or more arguments:
# - log file
# - hostname
# - root password
# - debug
# - wlan config (optional)
echo "Starting create_image.sh" >> "$1" 2>&1
if [ "$#" -lt 4 ]; then
	echo "Illegal number of arguments provided!" >> "$1" 2>&1
	echo "Expected 3 or more arguments, got $#" >> "$1" 2>&1
	echo "Given arguments: $@" >> "$1" 2>&1
    return -1
fi
# restart networking (to ensure dhcp correctly sets DNS server)
/etc/init.d/networking restart >> "$1" 2>&1
# Set locales (TODO: make this configurable?)
locale-gen en_GB en_US en_US.UTF-8 >> "$1" 2>&1
echo "Updating apt-get" >> "$1" 2>&1
apt-get -q -y update >> "$1" 2>&1
echo "Install raspi-config" >> "$1" 2>&1
apt-get -q -y install raspi-config >> "$1" 2>&1
if [ "$#" -gt 4 ]; then
    echo "Install wireless firmware" >> "$1" 2>&1
    # Install wireless
    apt-get -q -y install firmware-brcm80211 wpasupplicant iw crda wireless-regdb >> "$1" 2>&1
    # Append config section to interfaces
    echo "
    allow-hotplug wlan0
    iface wlan0 inet manual
    wpa-roam /etc/wpa_supplicant/wpa_supplicant.conf
    iface default inet dhcp" >> /etc/network/interfaces
    # Create config for wireless
    echo "$5" > /etc/wpa_supplicant/wpa_supplicant.conf
    # Set country for CRDA (Country: BE, so we have all channels)
    echo "REGDOMAIN=BE" > /etc/default/crda
    echo "Wireless config done" >> "$1" 2>&1
fi
echo "Changing root password" >> "$1" 2>&1
(echo "root:$3" | chpasswd) >> "$1" 2>&1
echo "Setting hostname to: $2" >> "$1" 2>&1
# Set hostname
echo "$2" > /etc/hostname
# If debug, don't disable SSH
if [ "$4" != "True" ]; then
    echo "Disabling SSH" >> "$1" 2>&1
    update-rc.d ssh disable >> "$1" 2>&1
fi
echo "Installing python tools" >> "$1" 2>&1
# Install python
apt-get -q -y install python python-dev python-pip >> "$1" 2>&1
# Update setuptools
echo "Update setuptools" >> "$1" 2>&1
easy_install -U setuptools >> "$1" 2>&1
# Install necessary pip modules
echo "Pip base installs" >> "$1" 2>&1
pip install twisted pyopenssl sqlalchemy service-identity pycrypto >> "$1" 2>&1
echo "Running python install script for dependencies" >> "$1" 2>&1
cd /usr/src/client
python dependency_install.py >> "$1" 2>&1
echo "Creating startup script" >> "$1" 2>&1
cp /usr/src/client/bin/pipot /etc/init.d/pipot >> "$1" 2>&1
chmod 755 /etc/init.d/pipot >> "$1" 2>&1
update-rc.d pipot defaults >> "$1" 2>&1
touch "/first-boot.txt"
echo "Ensuring that the pipotd is executable"
chmod +x /usr/src/client/bin/pipotd >> "$1" 2>&1
echo "Done in chroot environment" >> "$1" 2>&1
exit
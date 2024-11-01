#!/bin/bash

# Update package list
apt-get update

# Install required packages for downloading and installing Chrome
apt-get install -y wget unzip

# Download Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb

# Install Chrome and resolve dependencies
dpkg -i google-chrome-stable_current_amd64.deb || apt-get -fy install
